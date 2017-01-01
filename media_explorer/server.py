import os, re, traceback, mimetypes
from localhost.conf.settings import settings

from django.http import HttpResponse, Http404

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

    def serve(self, **kwargs):
        """Serve image files"""
        site_id = kwargs.get("site_id", None)
        element_id = kwargs.get("element_id", None)
        url = kwargs.get("url", None)
        # eg. 210x400, small, medium, large
        size = kwargs.get("size", "small")
        get_exact_size = kwargs.get("get_exact_size", False)

        def _http(file):
            file_name = None
            file_obj = None
            file_size = 0
            content_type = None
            if file.image.image:
                file_name = file.image.file_name
                file_size = file.image.image.size
                file_obj = file.image.image
                content_type = mimetypes.guess_type(file_name)[0]
            else:
                # TODO - handle S3 files and local_path files
                pass

            # TODO - account for S3 files
            #if s3_helper.file_is_remote(instance.image_url):
            #settings.DME_UPLOAD_TO_S3 \

            # TODO - account for nginx file proxies

            #wrapper = FileWrapper(file(filename))
            #response['Content-Length'] = os.path.getsize(filename)

            wrapper = FileWrapper(file_obj)
            response = HttpResponse(wrapper, content_type=content_type)
            response['Content-Length'] = file_size

            return response

        if not site_id:
            raise Http404

        if not element_id and not url:
            raise Http404

        image = None
        ResizedImage = get_model("media_explorer", "ResizedImage")

        fields = {}
        fields["site_id"] = site_id
        if element_id:
            fields["image__id"] = element_id
        else:
            fields["image__image_url"] = url

        if not ResizedImage.objects.filter(**fields).exists():
            raise Http404

        fields2 = fields.copy()
        if "x" in size:
            if "," in size:
                fields2["size__in"] = size.replace(" ", "").split(",")
            else:
                fields2["size"] = size

            if ResizedImage.objects.filter(**fields2).exists():
                image = ResizedImage.objects.filter(**fields2)[0]
            elif get_exact_size:
                raise Http404

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

        raise Http404
