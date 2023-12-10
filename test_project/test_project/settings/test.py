from .base import *  # noqa: F401, F403

INSTALLED_APPS.remove("django_extensions")

MAILINGLIST_USER_MODEL = "auth.User"
