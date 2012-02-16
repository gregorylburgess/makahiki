import urllib

from django import template
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.hashcompat import md5_constructor

from lib.avatar import AVATAR_DEFAULT_URL, AVATAR_GRAVATAR_BACKUP

register = template.Library()

def avatar_url(user, size=80):
    if not isinstance(user, User):
        try:
            user = User.objects.get(username=user)
        except User.DoesNotExist:
            return AVATAR_DEFAULT_URL
    avatars = user.avatar_set.order_by('-date_uploaded')
    primary = avatars.filter(primary=True)
    if primary.count() > 0:
        avt = primary[0]
    elif avatars.count() > 0:
        avt = avatars[0]
    else:
        avt = None
    if avt is not None:
        if not avt.thumbnail_exists(size):
            avt.create_thumbnail(size)
        return avt.avatar_url(size)
    else:
        if AVATAR_GRAVATAR_BACKUP:
            return "http://www.gravatar.com/avatar/%s/?%s" % (
                md5_constructor(user.email).hexdigest(),
                urllib.urlencode({'s': str(size)}),)
        else:
            return AVATAR_DEFAULT_URL
register.simple_tag(avatar_url)

def avatar(user, size=80):
    if not isinstance(user, User):
        try:
            user = User.objects.get(username=user)
            alt = unicode(user)
            url = avatar_url(user, size)
        except User.DoesNotExist:
            url = AVATAR_DEFAULT_URL
            alt = _("Default Avatar")
    else:
        alt = unicode(user)
        url = avatar_url(user, size)
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (url, alt,
        size, size)
register.simple_tag(avatar)

def render_avatar(avt, size=80):
    if not avt.thumbnail_exists(size):
        avt.create_thumbnail(size)
    return """<img src="%s" alt="%s" width="%s" height="%s" />""" % (
        avt.avatar_url(size), str(avatar), size, size)
register.simple_tag(render_avatar)