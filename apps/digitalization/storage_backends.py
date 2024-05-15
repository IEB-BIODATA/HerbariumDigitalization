from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class CustomDomainStorage(S3Boto3Storage):
    custom_domain = False

    def url(self, name, parameters=None, expire=None, http_method=None) -> str:
        if self.custom_domain:
            return "http{}:/{}/{}".format(
                "s" if settings.USE_SSL else "",
                self.custom_domain,
                name
            )
        return super().url(name, parameters, expire, http_method)


class StaticStorage(CustomDomainStorage):
    if settings.DEBUG:
        location = settings.STATICFILES_DIRS
    else:
        location = settings.AWS_STATIC_LOCATION
        custom_domain = settings.STATIC_URL


class PublicMediaStorage(CustomDomainStorage):
    location = settings.AWS_PUBLIC_MEDIA_LOCATION
    custom_domain = settings.MEDIA_URL
    file_overwrite = False


class PrivateMediaStorage(S3Boto3Storage):
    location = settings.AWS_PRIVATE_MEDIA_LOCATION
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
