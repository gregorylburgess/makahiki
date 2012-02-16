"""
Avatar Manager package
"""
import os.path

from django.conf import settings

try:
    from PIL import Image
except ImportError:
    import Image

AUTO_GENERATE_AVATAR_SIZES = getattr(settings, 'AUTO_GENERATE_AVATAR_SIZES',
    (80,))
AVATAR_RESIZE_METHOD = getattr(settings, 'AVATAR_RESIZE_METHOD',
    Image.ANTIALIAS)
AVATAR_STORAGE_DIR = getattr(settings, 'AVATAR_STORAGE_DIR', 'avatars')
AVATAR_GRAVATAR_BACKUP = getattr(settings, 'AVATAR_GRAVATAR_BACKUP', False)
AVATAR_DEFAULT_URL = getattr(settings, 'AVATAR_DEFAULT_URL',
    settings.STATIC_URL + os.path.join('images', 'default_avatar.png'))

from django.db.models import signals
from lib.avatar.models import Avatar

def create_default_thumbnails(instance=None, created=False, **kwargs):
    _ = kwargs
    if created:
        for size in AUTO_GENERATE_AVATAR_SIZES:
            instance.create_thumbnail(size)

signals.post_save.connect(create_default_thumbnails, sender=Avatar)
