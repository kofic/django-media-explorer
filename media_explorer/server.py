import os
import mimetypes
import requests
from threading import Lock
from boto3 import client as boto3Client

from localhost.conf.settings import settings

from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse

try:
    #For Django version 1.8.13 and below
    from django.db.models import get_model
except ImportError:
    #For Django version 1.9 and above
    from django.apps import apps
    get_model = apps.get_model

try:
    #For Django version 1.8.13 and below
    from django.core.servers.basehttp import FileWrapper
except ImportError:
    #For Django version 1.9 and above
    from wsgiref.util import FileWrapper


class MediaServer(object):
    """Use to server media by masking file URL"""

    def __init__(self):
        self._lock = Lock()

    def serve(self, **kwargs):
        """Serve image files"""
        site_id = kwargs.get("site_id", None)
        element_id = kwargs.get("element_id", None)
        url = kwargs.get("url", None)
        # eg. 210x400, small, medium, large
        size = kwargs.get("size", "small")
        get_exact_size = kwargs.get("get_exact_size", False)
        get_url = kwargs.get("get_url", False)
        redirect_url = kwargs.get("redirect_url", False)

        def _http(resized_file):
            # TODO - account for nginx file proxies
            file_name = None
            file_obj = None
            file_size = 0
            content_type = None
            try:
                file_name = resized_file.image.file_name
                file_size = resized_file.image.image.size
                file_obj = resized_file.image.image
                content_type = mimetypes.guess_type(file_name)[0]
            except Exception as e:
                pass

            if file_obj and get_url:
                return HttpResponse(file_obj.url, status=200)

            if file_obj and redirect_url:
                return HttpResponseRedirect(file_obj.url)

            if not file_obj and resized_file.s3_path:
                if resized_file.s3_is_public:
                    if get_url:
                        return HttpResponse(resized_file.image.image_url, status=200)
                    return HttpResponseRedirect(resized_file.image.image_url)
                else:

                    timeout = settings.get( 
                            "DME_S3_GENERATED_URL_TIMEOUT",
                            resized_file.site_id,
                            use_django_default=True
                            )

                    with self._lock:
                        client = boto3Client(
                                's3', 
                                settings.DME_S3_REGION,
                                aws_access_key_id=settings.DME_S3_ACCESS_KEY_ID,
                                aws_secret_access_key=settings.DME_S3_SECRET_ACCESS_KEY
                                )

                        url = client.generate_presigned_url(
                                'get_object', 
                                Params = {
                                    'Bucket': resized_file.s3_bucket, 
                                    'Key': resized_file.s3_path
                                }, 
                                ExpiresIn=timeout
                            )

                        if get_url:
                            return HttpResponse(url, status=200)

                        if redirect_url:
                            return HttpResponseRedirect(url)

                        try:
                            content_type = mimetypes.guess_type(resized_file.s3_path)[0]
                        except Exception as e:
                            pass

                        r = requests.get(url, stream=True)

                        # TODO - get cache-control from kwargs
                        response = StreamingHttpResponse(
                            (chunk for chunk in r.iter_content(512 * 1024)),
                            content_type=content_type
                        )
                        response['Cache-Control'] = "public, max-age=31557600"
                        return response

            wrapper = FileWrapper(file_obj)
            response = HttpResponse(wrapper, content_type=content_type)
            response['Content-Length'] = file_size
            response['Cache-Control'] = "public, max-age=31557600"
            return response

        if not site_id:
            return HttpResponse("Site id is required", status=404)

        if not element_id and not url:
            return HttpResponse("Element id or URL is required", status=404)

        image = None
        ResizedImage = get_model("media_explorer", "ResizedImage")

        fields = {}
        fields["site_id"] = site_id
        if element_id:
            fields["image__id"] = element_id
        else:
            fields["image__image_url"] = url

        if not ResizedImage.objects.filter(**fields).exists():
            return HttpResponse("Image not found", status=404)

        fields2 = fields.copy()
        if "x" in size:
            if "," in size:
                fields2["size__in"] = size.replace(" ", "").split(",")
            else:
                fields2["size"] = size

            if ResizedImage.objects.filter(**fields2).exists():
                image = ResizedImage.objects.filter(**fields2)[0]
            elif get_exact_size:
                return HttpResponse("Image with exact size '%s' not found" % size, status=404)

            if not image:
                size = "small"

        if image:
            return _http(image)

        fields2 = fields.copy()
        if size == "large":
            image = ResizedImage.objects.filter(**fields2).order_by("-image_area")[0]

        elif size == "medium":
            images = list(ResizedImage.objects.filter(**fields2).order_by("image_area"))
            image = images.pop((len(images)-1)/2)

        elif size == "small":
            image = ResizedImage.objects.filter(**fields2).order_by("image_area")[0]
                
        if image:
            return _http(image)

        return HttpResponse("Image not found" % size, status=404)
