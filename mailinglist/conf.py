import importlib

from appconf import AppConf
from appconf.utils import import_attribute
from django.conf import settings  # noqa: F401
from django.core.exceptions import ImproperlyConfigured


class MailinglistAppConf(AppConf):
    BASE_URL = None
    DEFAULT_SENDER_EMAIL = None
    DEFAULT_SENDER_NAME = "Administrator"
    USER_MODEL = settings.AUTH_USER_MODEL
    HOOKSET = "mailinglist.hooks.MailinglistDefaultHookset"
    CONFIRM_EMAIL_SUBSCRIBE = True
    EMAIL_DELAY = 0.1
    BATCH_DELAY = 10  # seconds
    BATCH_SIZE = 100

    def configure_hookset(self, value):
        return import_attribute(value)()

    def configure_default_sender_email(self, value):
        if value is None:
            raise ImproperlyConfigured(
                "Must configure MAILINGLIST_DEFAULT_SENDER_EMAIL"
            )
        return value

    def configure_base_url(self, value):
        if value is None:
            raise ImproperlyConfigured("Must configure MAILINGLIST_BASE_URL")
        return value


class HookProxy:
    def __getattr__(self, attr):
        return getattr(settings.MAILINGLIST_HOOKSET, attr)


hookset = HookProxy()
