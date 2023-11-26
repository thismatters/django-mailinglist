============
Installation
============

Use pip to install the package ::

    pip install django-mailinglist

Configuration
-------------

Update your settings to add ``mailinglist`` to the ``INSTALLED_APPS`` list and create settings for ``MAILINGLIST_BASE_URL`` and ``MAILINGLIST_DEFAULT_SENDER_EMAIL``::

    INSTALLED_APPS = [
        ...
        "mailinglist",
        ...
    ]
    MAILINGLIST_BASE_URL = "https://www.mygreatmailingeservice.lol"  # NO TRAILING SLASH PLEASE
    MAILINGLIST_DEFAULT_SENDER_EMAIL = "prime_mover@mygreatmailingservice.lol"

Add urls to project so that archive, subscribe, and unsubscribe functionality will be available::

    urlpatterns = [
        ...
        path("mailinglist/", include("mailinglist.urls", namespace="mailinglist")),
        ...
    ]

This package requires that you provide your own user model for holding sensitive user data. Before going any further, consider whether it is appropriate to use your actual user table (``AUTH_USER_MODEL``) or to provide a dedicated model for holding this data. If you need a dedicated model, establish that and set the ``MAILINGLIST_USER_MODEL`` setting (see :ref:`user_model_setting`). Changing this setting later will be unpleasant.

Once you are certain about your user model you can create the necessary database tables using::

    python manage.py migrate

