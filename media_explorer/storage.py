from django.core.files.storage import FileSystemStorage
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.encoding import filepath_to_uri

class DMEFileSystemStorage(FileSystemStorage):
    """
    Override the url method
    """                                                              
    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        if name.startswith("http://") or name.startswith("https://"):
            return name
        url = filepath_to_uri(name)
        if url is not None:
            url = url.lstrip('/')
        return urljoin(self.base_url, url)
