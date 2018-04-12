import traceback, csv, copy
from django.http import HttpResponse
from localhost import admin
from localhost.conf.settings import settings
from localhost.core.models import User
from media_explorer.models import Element, Gallery, GalleryElement, ResizedImage, element_post_save
from django.shortcuts import render
from django.db.models import signals


class ElementAdmin(admin.ModelAdmin):
    search_fields = ["name", "description", "credit", "image_url", "file_url", "file_name"]
    list_display = ('id', 'name')
    list_filter = ('type',)

    actions = ['view_s3_files']

    def view_s3_files(self, request, queryset):
        from .server import MediaServer
        mediaServer = MediaServer()

        urls = []
        for q in queryset:
            url = {}
            file_url = ""
            try:
                if q.image:
                    url["type"] = "image"
                    file_url=q.image.url
                elif q.file:
                    url["type"] = "file"
                    file_url=q.file.url

                response = mediaServer.serve(
                    url=file_url,
                    get_url=True,
                    redirect_url=False,
                    site_id=q.site_id
                )

                url["name"] = q.name
                url["url"] = file_url
                url["authenticated_url"] = response.content
                urls.append(url)
            except Exception as e:
                pass

        return render(request,
                      'admin/view_s3_files.html',
                      context={'queryset':queryset, 'urls': urls})

    view_s3_files.short_description = "View S3 files"

    def save_model(self, request, obj, form, change):
        if "manual_embed_code" in form.cleaned_data \
                and form.cleaned_data["manual_embed_code"]:
            #Disconnect signal if we are manually entering embed code
            signals.post_save.disconnect(element_post_save, sender=Element)
            obj.save()
            #Reconnect after save is done
            signals.post_save.connect(element_post_save, sender=Element)
        else:
            obj.save()

    def get_form(self, request, obj=None, **kwargs):
        self.exclude = ("type",)
        form = super(ElementAdmin, self).get_form(request, obj, **kwargs)
        return form


class GalleryAdmin(admin.ModelAdmin):
    search_fields = ["name","description"]
    list_display = ('id','name',)

class GalleryElementAdmin(admin.ModelAdmin):
    search_fields = ["gallery","element"]
    list_display = ('id','gallery','element','sort_by')

class ResizedImageAdmin(admin.ModelAdmin):
    search_fields = ["file_name"]
    list_display = ('id','file_name','image','size','image_width','image_height','html_img')
    #list_filter = ('image',)

admin.site.register(Element, ElementAdmin)
admin.site.register(Gallery, GalleryAdmin)
admin.site.register(GalleryElement, GalleryElementAdmin)
admin.site.register(ResizedImage, ResizedImageAdmin)
