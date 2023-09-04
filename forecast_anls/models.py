
import os
import uuid

from django.db import models
from django.conf import settings
from user_auth.models import CdmsUser
# Create your models here.

class user_asset(models.Model):

    file = models.FileField("file for upload", upload_to=settings.USER_ASSET_UPLOAD_TO)
    identifier = models.UUIDField("unique identifier for asset",
        default=uuid.uuid4, editable=False, unique=True
    )
    creation_time = models.DateTimeField("creation time", auto_now_add=True)
    user = models.ForeignKey(CdmsUser, on_delete=models.CASCADE)
    info = models.JSONField("schema info of asset", default=dict)

    def name_only(self):

        return self.file.name.split("/")[-1]

    def __str__(self):
        return f'{self.file} // {self.identifier}'

    def delete(self, *args, **kwargs):
        os.remove(os.path.join(settings.MEDIA_ROOT, self.file.name))
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Asset"
        verbose_name_plural = "Assets"
        indexes = [
            models.Index(fields=['identifier']),
        ]