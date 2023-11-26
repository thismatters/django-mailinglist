========
Settings
========

Required Settings
-----------------

Base URL
^^^^^^^^

To ease linking back to the site for archive and subscription management functionalities a base url (including protocol and without trailing slash) must be provided::

    MAILINGLIST_BASE_URL = "https://my-mailinglist-is-the-best.com"

Default Sender Email
^^^^^^^^^^^^^^^^^^^^

This package needs an email address to be the sender for global unsubscribe functionalities::

    MAILINGLIST_DEFAULT_SENDER_EMAIL = "admin@my-mailinglist-is-the-best.com"


Optional Settings
-----------------

.. _user_model_setting:

User model
^^^^^^^^^^

``django-mailinglist`` does not store user data. It relies on the project providing a model which provides the following attributes:
    * ``first_name``
    * ``last_name``
    * ``email``

Any subclass of ``django.contrib.auth.models.AbstractUser`` will be more than sufficient. The default configuration is that the app will use the ``AUTH_USER_MODEL`` configured in settings::

    MAILINGLIST_USER_MODEL = settings.AUTH_USER_MODEL

It is advisable that you **not** change this setting once set, your database thanks you.

If you need row-level encryption on any of the user data the author recommends using `django-cryptography <https://github.com/georgemarshall/django-cryptography>`_ to accomplish that; in that event you will also need to provide a "hook" for creating users (described below).


Hookset
^^^^^^^

This package allows you to customize certain funcationalities to best suit your project and its unique concerns. These methods are collected in a "Hookset" class which can be specified as a setting::

    MAILINGLIST_HOOKSET = "mailinglist.hooks.MailinglistDefaultHookset"

If you wish to customize the particular way that email is sent, or change which file types can be attached to messages, or if you have encrypted user data then you may need to provide your own hookset. The ``test_project`` included in the repo shows how this can be done.

Default Sender Name
^^^^^^^^^^^^^^^^^^^

You may provide a name to accompany the default sender email described above::

    MAILINGLIST_DEFAULT_SENDER_NAME = "Administrator"


Confirm Subscribe
^^^^^^^^^^^^^^^^^

When a new user subscribes to a mailing list they will (by default) be sent an email to verify their email address and intent to join the mailing list. If you would prefer these messages not be sent (for example, you already verify email addresses for your users) then this setting will allow you to change the behavior::

    MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE = True

Regardless of this setting, whenever subscribers are added in bulk via admin, no subscription confirmation will be sent!

Send Rate Limiting
^^^^^^^^^^^^^^^^^^

These three settings control the delay between sending messages. To control the sleep time between each individual email use::

    MAILINGLIST_EMAIL_DELAY = 0.1  # seconds

It is also possible to sleep after sending some number of individual email. To contol the batch size use::

    MAILINGLIST_BATCH_SIZE = 200

And finally, to contol the amount of time to sleep after sending a batch use::

    MAILINGLIST_BATCH_DELAY = 10

