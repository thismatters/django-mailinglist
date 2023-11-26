import importlib

from appconf import AppConf
from django.conf import settings  # noqa: F401
from django.core.exceptions import ImproperlyConfigured


def load_path_attr(path):
    """Gets the module path"""
    module, attr = path.rsplit(".", maxsplit=1)
    try:
        mod = importlib.import_module(module)
    except ImportError as e:
        raise ImproperlyConfigured("Error importing {0}: '{1}'".format(module, e))
    try:
        attr = getattr(mod, attr)
    except AttributeError:
        raise ImproperlyConfigured(
            "Module '{0}' does not define a '{1}'".format(module, attr)
        )
    return attr


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
        return load_path_attr(value)()

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
