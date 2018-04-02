import os, re, traceback, mimetypes
from localhost.conf.settings import settings

try:
    #For Django version 1.8.13 and below
    from django.db.models import get_model
except ImportError:
    #For Django version 1.9 and above
    from django.apps import apps
    get_model = apps.get_model

try:
	from PIL import Image, ImageOps
except ImportError:
	import Image
	import ImageOps


class S3Helper(object):
    """S3 helper functions"""
    def get_s3_headers(self, url, is_public):
        headers = {}
        if is_public:
            headers["ACL"] = "public-read"
        if mimetypes.guess_type(url)[0]:
            headers["ContentType"] = mimetypes.guess_type(url)[0]
        return headers

    def get_s3_path(self, guid, path):
        s3_path = "%s/%s" % (guid, path.lstrip("/"))
        if settings.DME_S3_FOLDER:
            s3_path = "%s/%s/%s" % (settings.DME_S3_FOLDER.strip("/"), guid, path.lstrip("/"))
        return s3_path

    def get_s3_url(self, path, **kwargs):
        s3_bucket = kwargs.get(
            "s3_bucket", 
            settings.DME_S3_BUCKET
        )
        return "%s/%s/%s" % ("https://s3.amazonaws.com", s3_bucket, path)

    def file_is_remote(self, url):
        if url and "https:" in url \
                or "http:" in url \
                or "http%3A" in url \
                or "https%3A" in url:
            return True
        return False

    def upload_element_to_s3(self, instance):

        if not settings.DME_UPLOAD_TO_S3:
            return instance

        #If S3 upload is set and file is local then upload to S3 then delete local
        file_saved_to_s3 = False
        if instance.file_local_path and not self.file_is_remote(instance.file_url):
            try:
                from boto3 import client as boto3Client
                from boto3.s3.transfer import S3Transfer
                client = boto3Client(
                        's3', 
                        settings.DME_S3_REGION,
                        aws_access_key_id=settings.DME_S3_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.DME_S3_SECRET_ACCESS_KEY
                        )
                transfer = S3Transfer(client)

                file_s3_path = self.get_s3_path(instance.guid, instance.file_local_path)

                transfer.upload_file(
                        str(settings.PROJECT_ROOT + instance.file_local_path),
                        settings.DME_S3_BUCKET,
                        file_s3_path,
                        extra_args=self.get_s3_headers(file_s3_path, instance.file_s3_is_public)
                        )

                file_saved_to_s3 = True
                file_s3_url = self.get_s3_url(file_s3_path)

                instance.file_s3_path = file_s3_path
                instance.file_s3_bucket = settings.DME_S3_BUCKET
                instance.file_url = file_s3_url
                instance.save()
            except Exception as e:
                print traceback.format_exc()

        #If S3 upload is set and image is local then upload to S3 then delete local
        saved_to_s3 = False
        if instance.local_path and not self.file_is_remote(instance.image_url):
            try:
                from boto3 import client as boto3Client
                from boto3.s3.transfer import S3Transfer
                client = boto3Client(
                        's3', 
                        settings.DME_S3_REGION,
                        aws_access_key_id=settings.DME_S3_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.DME_S3_SECRET_ACCESS_KEY
                        )
                transfer = S3Transfer(client)

                s3_path = self.get_s3_path(instance.guid, instance.local_path)

                transfer.upload_file(
                        str(settings.PROJECT_ROOT + instance.local_path),
                        settings.DME_S3_BUCKET,
                        s3_path,
                        extra_args=self.get_s3_headers(s3_path, instance.s3_is_public)
                        )

                saved_to_s3 = True
                s3_url = self.get_s3_url(s3_path)

                instance.s3_path = s3_path
                instance.s3_bucket = settings.DME_S3_BUCKET
                instance.image_url = s3_url
                instance.save()
            except Exception as e:
                print traceback.format_exc()

        #If S3 upload is set and thumbnail image is local then upload to S3 then delete local
        thumbnail_saved_to_s3 = False
        if instance.thumbnail_local_path and not self.file_is_remote(instance.thumbnail_image_url):
            try:
                from boto3 import client as boto3Client
                from boto3.s3.transfer import S3Transfer
                client = boto3Client(
                        's3', 
                        settings.DME_S3_REGION,
                        aws_access_key_id=settings.DME_S3_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.DME_S3_SECRET_ACCESS_KEY
                        )
                transfer = S3Transfer(client)

                s3_path = self.get_s3_path(instance.guid, instance.thumbnail_local_path)

                transfer.upload_file(
                        str(settings.PROJECT_ROOT + instance.thumbnail_local_path),
                        settings.DME_S3_BUCKET,
                        s3_path,
                        extra_args=self.get_s3_headers(s3_path, instance.s3_is_public)
                        )

                thumbnail_saved_to_s3 = True
                thumbnail_s3_url = self.get_s3_url(s3_path)

                instance.thumbnail_s3_path = s3_path
                instance.thumbnail_s3_bucket = settings.DME_S3_BUCKET
                instance.thumbnail_image_url = thumbnail_s3_url
                instance.save()

            except Exception as e:
                print traceback.format_exc()


        if file_saved_to_s3:
            try:
                if os.path.isfile(settings.PROJECT_ROOT + instance.file_local_path):
                    os.remove(settings.PROJECT_ROOT + instance.file_local_path)
                    instance.file = file_s3_url
                    instance.file_local_path = None
                    instance.save()

            except:
                print traceback.format_exc()

        if saved_to_s3:
            try:
                if os.path.isfile(settings.PROJECT_ROOT + instance.local_path):
                    os.remove(settings.PROJECT_ROOT + instance.local_path)
                    instance.image = s3_url
                    instance.local_path = None
                    instance.save()

            except:
                print traceback.format_exc()

        if thumbnail_saved_to_s3:
            try:
                if os.path.isfile(settings.PROJECT_ROOT + instance.thumbnail_local_path):
                    os.remove(settings.PROJECT_ROOT + instance.thumbnail_local_path)
                    instance.thumbnail_image = thumbnail_s3_url
                    instance.thumbnail_local_path = None
                    instance.save()

            except:
                print traceback.format_exc()

        return instance


class ImageHelper(object):
    """Image helper functions"""

    def get_exif_data(self, full_path):

        exif_data = {}

        try:
            import PIL.ExifTags

            image = Image.open(full_path)

            exif = {
                PIL.ExifTags.TAGS[k]: v
                for k, v in image._getexif().items()
                if k in PIL.ExifTags.TAGS
            }

            for k, v in exif.iteritems():
                try:
                    exif_data[k] = v.decode('utf8')
                except:
                    pass
            
        except Exception as e:
            pass

        try:
            kOrientationEXIFTag = 0x0112
            if hasattr(image, '_getexif'):
                e = image._getexif()
                if e is not None:
                    exif_data["exif_orientation"] = e[kOrientationEXIFTag]
        except:
            pass

        return exif_data


    def get_resized_images(self, url, site_id):
        """Get resized images by url"""
        ResizedImage = get_model("media_explorer", "ResizedImage")
        images = ResizedImage.objects.filter(image__image_url=url, image__site_id=site_id)
        image_dict = {}
        sorted_images = []
        for image in images:
            if image.image_width and image.image_height:
                area = int(image.image_width) * int(image.image_height)
                if area not in image_dict:
                    image_dict[area] = []
                image_dict[area].append(image)
        sorted_areas = sorted(image_dict.keys())
        for area in sorted_areas:
            for resizedImage in image_dict[area]:
                sorted_images.append(
                    {
                        "area": area,
                        "size": resizedImage.size,
                        "width": resizedImage.image_width,
                        "height": resizedImage.image_height,
                        "url": resizedImage.image_url,
                    }
                )
        return sorted_images

    def resize(self, instance):
        rtn = {}
        rtn["success"] = False
        rtn["message"] = ""
        rtn["thumbnail_image_url"] = None

        ResizedImage = get_model("media_explorer","ResizedImage")

        url = instance.image_url
        full_path = settings.PROJECT_ROOT + "/" + url.strip("/")

        #Clean file name
        file_name = os.path.basename(url)
        file_name = re.sub(r'\'|\"|\(|\)|\$','',file_name)
        file_name = re.sub(r'\s','-',file_name)

        extension = ""

        if "." in file_name:
            file_name_array = file_name.split(".")
            extension = file_name_array.pop()
            file_name = ".".join(file_name_array)

        try:
            if os.path.exists(full_path):
                image = Image.open(full_path)
            else:
                rtn["message"] = "File path does not exist"
                return rtn
        except Exception as e:
            rtn["message"] = e.__str__()
            return rtn

        if extension.lower() not in ["png","jpg","gif","bmp","jpeg","tiff"]:
            extension = image.format.lower()

        extension = extension.lower()

        image_width, image_height = image.size
        instance.image_width = image_width
        instance.image_height = image_height
        instance.save()

        if not settings.DME_RESIZE:

            # Even though DME_RESIZE = False - save the original image
            defaults = {
                "file_name": file_name + "_orig." + extension,
                "image_url": instance.image_url,
                "image_height": image_height,
                "image_width": image_width,
                "size": "orig",
                "s3_is_public": instance.s3_is_public
            }
            ri, created = ResizedImage.objects.get_or_create(image=instance, site_id=instance.site_id, defaults=defaults)

            rtn["message"] = "The image was not resized since settings.DME_RESIZE is set to False"
            return rtn

        #create DME_RESIZE_DIRECTORY directory
        resize_dir = settings.PROJECT_ROOT + "/"
        resize_dir += settings.MEDIA_URL.strip("/") +  "/"
        resize_dir += settings.DME_RESIZE_DIRECTORY.strip("/")
        if not os.path.exists(resize_dir): os.makedirs(resize_dir)
        new_dir = "/" + settings.MEDIA_URL.strip("/") +  "/" + settings.DME_RESIZE_DIRECTORY.strip("/") + "/"

        url_orig_cropped = new_dir + file_name + "_orig_c." + extension
        orig_cropped_height = image_height
        orig_cropped_width = image_width

        #Aspect ratio for horizontal numerator
        ar_h_n = int(settings.DME_RESIZE_HORIZONTAL_ASPECT_RATIO.split(":")[0])
        #Aspect ratio for horizontal denominator
        ar_h_d = int(settings.DME_RESIZE_HORIZONTAL_ASPECT_RATIO.split(":")[1])
        #Aspect ratio for vertical numerator
        ar_v_n = int(settings.DME_RESIZE_VERTICAL_ASPECT_RATIO.split(":")[0])
        #Aspect ratio for vertical denominator
        ar_v_d = int(settings.DME_RESIZE_VERTICAL_ASPECT_RATIO.split(":")[1])

        if image_width > image_height:
            #Horizontal
            #orig_cropped_height = int(5/float(8)*image_width)
            orig_cropped_height = int(ar_h_d/float(ar_h_n)*image_width)

            if orig_cropped_height > image_height:
                orig_cropped_height = image_height
                #orig_cropped_width = int(8/float(5)*image_height)
                orig_cropped_width = int(ar_h_n/float(ar_h_d)*image_height)

        elif image_width < image_height:
            #Vertical
            #orig_cropped_width = int(320/float(414)*image_height)
            orig_cropped_width = int(ar_v_n/float(ar_v_d)*image_height)
            if orig_cropped_width > image_width:
                orig_cropped_width = image_width
                #orig_cropped_height = int(414/float(320)*image_width)
                orig_cropped_height = int(ar_v_d/float(ar_v_n)*image_width)
        else:
            #Square
            pass

        rtn_crop = self._crop_and_resize(image, orig_cropped_width, orig_cropped_height, url_orig_cropped)
        if not rtn_crop["success"]:
            return rtn_crop

        #We will work from the aspect-ratio cropped out version
        ri = ResizedImage()
        ri.image = instance
        ri.file_name = file_name + "_orig_c." + extension
        ri.image_url = url_orig_cropped
        ri.image_height = orig_cropped_height
        ri.image_width = orig_cropped_width
        ri.size = "orig_c"
        ri.site_id = instance.site_id
        ri.s3_is_public = instance.s3_is_public
        ri.save()

        image_cropped = Image.open(settings.PROJECT_ROOT + url_orig_cropped)

        ar_d = 0
        ar_n = 0
        if orig_cropped_width > orig_cropped_height:
            image_orientation = "horizontal"
            ar_d = ar_h_d
            ar_n = ar_h_n
        elif orig_cropped_width < orig_cropped_height:
            image_orientation = "vertical"
            ar_d = ar_v_d
            ar_n = ar_v_n
        else:
            image_orientation = "square"

		#Handle horizontal and vertical images
        if image_orientation in ["horizontal","vertical"]:
            for size_width in settings.DME_RESIZE_WIDTHS[image_orientation]:

                size_height = int(size_width*ar_d/ar_n)
                size = str(size_width) + "x" + str(size_height)

                if (orig_cropped_width >= size_width) and (orig_cropped_height >= size_height):
                    new_file_name = file_name + "_" + size + "." + extension
                    new_url = new_dir + new_file_name
                    rtn_resize = self._crop_and_resize(image_cropped, size_width, size_height, new_url)
                    if rtn_resize["success"]:
                        ri = ResizedImage()
                        ri.image = instance
                        ri.file_name = new_file_name
                        ri.image_url = new_url
                        ri.image_height = size_height
                        ri.image_width = size_width
                        ri.size = size
                        ri.site_id = instance.site_id
                        ri.s3_is_public = instance.s3_is_public
                        ri.save()

                    if size_width in settings.DME_RESIZE_WIDTHS["retina_2x"]:
                        retina_size_width = 2*size_width
                        retina_size_height = int(retina_size_width*ar_d/ar_n)
                        retina_size = str(retina_size_width) + "x" + str(retina_size_height)

                        if (orig_cropped_width >= retina_size_width) and (orig_cropped_height >= retina_size_height):
                            new_file_name = file_name + "_" + size + "@2x." + extension
                            new_url = new_dir + new_file_name
                            rtn_resize = self._crop_and_resize(image_cropped, retina_size_width, retina_size_height, new_url)
                            if rtn_resize["success"]:
                                ri = ResizedImage()
                                ri.image = instance
                                ri.file_name = new_file_name
                                ri.image_url = new_url
                                ri.image_height = retina_size_height
                                ri.image_width = retina_size_width
                                ri.size = size + "@2x"
                                ri.site_id = instance.site_id
                                ri.s3_is_public = instance.s3_is_public
                                ri.save()

		#Handle non-cropped images (vertical, horizontal, square)
        for size_width in settings.DME_RESIZE_WIDTHS["non_cropped"]:
            size_height = int(image_height/float(image_width)*size_width)
            size = str(size_width) + "nc"

            retina_size_width = 2*size_width
            retina_size_height = int(image_height/float(image_width)*retina_size_width)

            if (image_width >= size_width) and (image_height >= size_height):
                new_file_name = file_name + "_" + size + "." + extension
                new_url = new_dir + new_file_name
                rtn_resize = self._crop_and_resize(image, size_width, size_height, new_url)
                if rtn_resize["success"]:
                    ri = ResizedImage()
                    ri.image = instance
                    ri.file_name = new_file_name
                    ri.image_url = new_url
                    ri.image_height = size_height
                    ri.image_width = size_width
                    ri.size = size
                    ri.site_id = instance.site_id
                    ri.s3_is_public = instance.s3_is_public
                    ri.save()


            if (image_width >= retina_size_width) and (image_height >= retina_size_height):
                new_file_name = file_name + "_" + size + "@2x." + extension
                new_url = new_dir + new_file_name
                rtn_resize = self._crop_and_resize(image, retina_size_width, retina_size_height, new_url)
                if rtn_resize["success"]:
                    ri = ResizedImage()
                    ri.image = instance
                    ri.file_name = new_file_name
                    ri.image_url = new_url
                    ri.image_height = retina_size_height
                    ri.image_width = retina_size_width
                    ri.size = size + "@2x"
                    ri.site_id = instance.site_id
                    ri.s3_is_public = instance.s3_is_public
                    ri.save()

        #Now process thumbnail_image_url
        size_width = settings.DME_RESIZE_WIDTHS["thumbnail"]
        size_height = int(image_height/float(image_width)*size_width)
        size = str(size_width) + "x" + str(size_height) + ".thumbnail"

        new_file_name = file_name + "_" + size + "." + extension
        new_url = new_dir + new_file_name
        rtn_resize = self._crop_and_resize(image, size_width, size_height, new_url)
        if rtn_resize["success"]:
            rtn["thumbnail_image_url"] = new_url

        rtn["success"] = True
        return rtn


    def _crop_and_resize(self, image, width, height, new_path):
        rtn = {}
        rtn["success"] = False
        rtn["message"] = ""
        try:
            imagefit = ImageOps.fit(image, (width, height), Image.ANTIALIAS)
            imagefit.save(settings.PROJECT_ROOT + new_path, image.format, quality=100)
        except Exception as e:
            rtn["message"] = e.__str__()
            return rtn

        rtn["success"] = True
        return rtn

    def _resize(self, image, width, height, new_path):
        rtn = {}
        rtn["success"] = False
        rtn["message"] = ""
        try:
            resized = image.resize((width,height),Image.ANTIALIAS).save(settings.PROJECT_ROOT + new_path)
        except Exception as e:
            rtn["message"] = e.__str__()
            return rtn

        rtn["success"] = True
        return rtn


class FileHelper(object):
    """File helper functions"""

    def save_file_from_url(self, url, model, file_field_name):
        """
        The file_field_name should be of type MediaImageField or MediaFileField
        """
        rtn = {}
        rtn["success"] = False
        rtn["message"] = ""

        import requests
        import tempfile
        from django.core import files

        try:
            # Python 3
            from urllib.parse import urlparse, parse_qs
        except ImportError:
            # Python 2
            from urlparse import urlparse, parse_qs

        url_obj = urlparse(url)
        # Remove the query - some file url have query string (eg. signed urls)
        url2 = url_obj._replace(query=None).geturl()

        # Stream the file
        resp = requests.get(url, stream=True)

        # Was the request OK?
        if resp.status_code != requests.codes.ok:
            rtn["message"] = "The file '" + url2 + "' could not be downloaded."
            rtn["message"] += "Status code: " + str(resp.status_code)
            return rtn

        try:
            # Get the filename from the url, used for saving later
            # Remember to use url2 (which has no query string)
            file_name = url2.split('/')[-1]

            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile()

            # Read the streamed file in sections
            for block in resp.iter_content(1024 * 8):
                # If no more file then stop
                if not block:
                    break
                # Write file block to temporary file
                temp_file.write(block)

            file_field = getattr(model, file_field_name)
            file_field.save(file_name, files.File(temp_file))

        except Exception as e:
            rtn["message"] = "The file '" + url2 + "' could not be downloaded. "
            rtn["message"] += "ERROR: " + str(e)
            return rtn

        rtn["success"] = True
        return rtn
