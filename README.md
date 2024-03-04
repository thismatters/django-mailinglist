Django Mailinglist
===================
[![PyPI](https://img.shields.io/pypi/v/django-mailinglist?color=156741&logo=python&logoColor=ffffff&style=for-the-badge)](https://pypi.org/project/django-mailinglist/)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/thismatters/django-mailinglist/test.yml?branch=main&color=156741&label=CI&logo=github&style=for-the-badge)](https://github.com/thismatters/django-mailinglist/actions)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-mailinglist?color=156741&logo=python&logoColor=white&style=for-the-badge)](https://pypi.org/project/django-mailinglist/)
[![PyPI - Django Version](https://img.shields.io/pypi/djversions/django-mailinglist?color=156741&logo=django&logoColor=ffffff&style=for-the-badge)](https://pypi.org/project/django-mailinglist/)
[![Codecov](https://img.shields.io/codecov/c/github/thismatters/django-mailinglist?color=156741&logo=codecov&logoColor=ffffff&style=for-the-badge)](https://codecov.io/gh/thismatters/django-mailinglist)
[![Read the Docs](https://img.shields.io/readthedocs/django-mailinglist?color=156741&logo=readthedocs&logoColor=ffffff&style=for-the-badge)](https://django-mailinglist.readthedocs.io/en/latest/)


`django-mailinglist` is a package for administering outgoing mailing lists to subscribers. This package aims to replace `django-newsletter` and takes inspiration (and a non-trivial amount of code) from it.

## Documentation

[Please refer to the full documentation](https://django-mailinglist.readthedocs.io/en/latest/).

## Installation

Use pip to install the package

```
pip install django-mailinglist
```

## Configuration

Add `mailinglist` to the `INSTALLED_APPS` list and create settings for `MAILINGLIST_BASE_URL` and `MAILINGLIST_DEFAULT_SENDER_EMAIL`:

```
INSTALLED_APPS = [
    ...
    "mailinglist",
    ...
]
MAILINGLIST_BASE_URL = "https://www.mygreatmailingeservice.lol"  # NO TRAILING SLASH PLEASE
MAILINGLIST_DEFAULT_SENDER_EMAIL = "prime_mover@mygreatmailingservice.lol"
```

Add urls to project so that archive, subscribe, and unsubscribe functionality will be available.

```
urlpatterns = [
    ...
    path("mailinglist/", include("mailinglist.urls", namespace="mailinglist")),
    ...
]
```


## Settings

Settings (and their defaults) are outlined below:

* (required) `MAILINGLIST_BASE_URL` : Specify the base url (including protocol! No trailing slash!) for linkbacks to the archive and unsubscribe links.
* (required) `MAILINGLIST_DEFAULT_SENDER_EMAIL` : The default email address for communication with subscribers.
* `MAILINGLIST_DEFAULT_SENDER_NAME = "Administrator` : The name or title of the person who will manage subscribers.
* `MAILINGLIST_USER_MODEL = settings.AUTH_USER_MODEL` : Specify the pool of potential subscribers; this doesn't have to be the same model that you use for authenticating users to your project.
* `MAILINGLIST_HOOKSET = "mailinglist.hooks.MailinglistDefaultHookset"` : You may provide a class which provides the hooks found in the package module to override certain behaviors (sending email mostly).
* `MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE = True` : Should new subscribers be sent an email to verify their email address?
* `MAILINGLIST_EMAIL_DELAY = 0.1` : Amount of seconds to wait between sending an individual email.
* `MAILINGLIST_BATCH_SIZE = 200` : The number of individual email which constitute a "batch".
* `MAILINGLIST_BATCH_DELAY = 10` : Amount of seconds to wait after completing a "batch".

## Functionality

This package takes many design cues from `django-newsletter`, chief among those are the data models. A major difference is in the `Subscription` model which sources user data from the model defined in `MAILINGLIST_USER_MODEL`, no email addresses are stored in `django-newsletter` models!

### Mailing List

Admin views are provided for managing mailing lists.
A mailing list must exist prior to any subscriptions or messages.

### Subscription

#### User data

You must provide your own form(s) for collecting and persisting user data.
Any subclass of the `AbstractUser` model will suffice for holding user data, but the only requirements (by default) for this package are a `get_full_name` method and `email` attribute.
The data used in messages is highly configurable by providing your own message templates.

#### Subscriptions proper

`django-mailinglist` provides a service class for managing subscriptions, as such the `Subscription` model **should not be used for creating subscriptions**.
Views are provided to illustrate the use of the service class, please reference `mailinglist/views.py` for patterns.
The provided admin forms also illustrate an appropriate pattern.
Adding a subscription for a user is done like so:
```
from mailinglist.services import SubscriptionService

SubscriptionService().subscribe(user=user, mailing_list=mailing_list)
```

The service code will send a subscription confirmation email to the user (by default), the user will find a link to click which will complete their subscription.
If the `MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE` setting is set `False` then no email will be sent, the user will immediately be subscribed; this is only recommended if you are already verifying email addresses as part of user registration.

Subscription change events are logged whenever a subscription is changed, a timestamp of each subscription or unsubscription is available in the admin.

#### Unsubscription

Unsubscribe links will go out with each email. These are personalized links which contain a token to unsubscribe that particular user _only_; when the user clicks the link they will be marked as unsubscribed and will no longer receive messages on that mailing list.

### Message

Messages belong to a certain mailing list and are comprised of message parts.
Message parts may have a heading and text.
The text supports [markdown](https://www.markdownguide.org/).


### Submission

Finally, submissions are the means by which a message is published and sent. An admin action exists to "publish" a submission, which will mark it as ready for sending

### Sending

The management command `process_submissions` will go through the sending action for all published submissions. Receiver lists are rendered at the time of sending to include all subscribed users and to exclude any users who have joined the global deny list. Each subscriber gets a message rendered solely for them which contains an unsubscribe link. Each sending is logged with a timestamp so that if a sending action is interrupted the process can be resumed without double-sending messages to any subscriber.

While sending, a delay can be configured between the sending of each email (`MAILINGLIST_EMAIL_DELAY`), also a delay can be configured between "batches" as well (`MAILINGLIST_BATCH_DELAY`, `MAILINGLIST_BATCH_SIZE`).

### Global Deny List

The author of this project feels strongly that people should be able to **opt-in** to being on mailing lists. They should also, if they wish, to opt-out of being on any mailing list. The `GlobalDeny` model exists to respect that right of users. When a `GlobalDeny` instance is associated with a user then that user will not receive messages on any mailing list to which they are subscribed, nor will they be able to be subscribed to any additional mailing lists. The user, when managing their subscriptions, will be able to join the global deny list. If a user is unsuccessful in unsubscribing from a mailing list they will be redirected to join the global deny list.

## Comparisons with `django-newsletter`

This project is a direct descendant of [`django-newsletter`](https://github.com/jazzband/django-newsletter) although not a fork. It borrows some amount of code from it (as well as the license), but in general is a full rewrite which uses a services architecture to keep the models thinner. The (subjectively appraised) differences between the architecture of this package and its predecessor are outlined below.

### Improvements

* Easier configuration: doesn't require installing and configuring additional apps, customized templates are not required, doesn't require the `sites` framework.
* More secure: doesn't leak user data in subscribe/unsubscribe flows; allows use of https.
* More private: doesn't store user data within its own models, project must provide a `User`-like model for storing subscriber user data.
* More compliant: outgoing messages adhere (accurately) to [RFC3269 on email header fields for mailing lists](https://datatracker.ietf.org/doc/html/rfc2369).
* Implicit send lists: when a message is published, it is sent to all subscribers (at time of processing) except those explicitly excluded from the submission.
* Send tracking: tracks each sending of a message to a subscriber so that interrupted sending jobs can be resumed.
* Lower friction user self-management: the unsubscribe link in outgoing message will immediately unsubscribe the recipient.
* Global unsubscribe: allows users to globally opt-out of receiving mailing list messages.
* Pluggable behavior: define your own email send and "user" creation functionality (if you like).

### Drawbacks

* No internationalization: Only English (for now).
* Worse subscriber import: Only CSV import is supported (for now).
* Worse documentation: There is a lot of room to grow here!
* No inline images (yet).

### Equivalent, but different

* Markdown instead of traditional rich text. It is the author's opinion that Markdown is superior to rich text because Markdown retains meaning as plain text, therefore your intent in formatting will be better conveyed in the plaintext version of the message.
