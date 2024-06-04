from django.core.exceptions import ValidationError


def validate_file_size(value):
    filesize = value.file.size
    megabyte_limit = 10.0
    if filesize > megabyte_limit*1024*1024:
        raise ValidationError("The maximum file size that can be uploaded is 10MB")
