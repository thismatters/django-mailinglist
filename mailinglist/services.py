import time
from random import randint

from django.conf import settings
from django.template.loader import select_template
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from mailinglist import models
from mailinglist.conf import hookset
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


class TemplateSet:
    """Represents the templates needed for generating outgoing email."""

    def __init__(
        self, *, mailing_list: models.MailingList = None, action: str = "message"
    ):
        self.mailing_list = mailing_list
        self.action = action
        self._templates = None

    @property
    def templates(self):
        if self._templates is not None:
            return self._templates
        self._templates = {}
        self._templates["subject"] = self._get_template(_for=f"{self.action}_subject")
        self._templates["body"] = self._get_template(_for=self.action)
        if self.mailing_list is None or self.mailing_list.send_html:
            self._templates["html_body"] = self._get_template(
                _for=self.action, suffix="html"
            )
        return self._templates

    def _get_default_context(self):
        return {
            "mailing_list": self.mailing_list,
            "BASE_URL": settings.MAILINGLIST_BASE_URL,
            "DEFAULT_SENDER_NAME": settings.MAILINGLIST_DEFAULT_SENDER_NAME,
        }

    def _get_template(self, *, suffix="txt", _for="message"):
        _root = "mailinglist/email"
        slug = "global-deny"
        if self.mailing_list is not None:
            slug = self.mailing_list.slug
        return select_template(
            [
                f"{_root}/{slug}/{_for}.{suffix}",
                f"{_root}/{_for}.{suffix}",
            ]
        )

    def render_to_dict(self, context: dict):  # -> dict[str, str]:
        """Renders each template in the set and arranges the text into a
        dictionary, requires the context for the specific message and
        subscription"""

        rendered = {}
        _context = self._get_default_context()
        _context.update(context)
        for attr, template in self.templates.items():
            rendered[attr] = template.render(_context).strip()
        return rendered


class MessageService:
    """Composes email for sending"""

    def _urlify(self, path):
        return f"<{settings.MAILINGLIST_BASE_URL}{path}>"

    def _mailto(self, mailing_list, subject=None, appended=True):
        if mailing_list is None:
            return ""
        if subject is None:
            subject = mailing_list.slug
        buffer = ""
        if appended:
            buffer += ","

        buffer += f"<mailto: {mailing_list.email}?subject={subject}>"
        return buffer

    def _headers(self, *, subscription):
        """Provides necessary headers with correct formatting for good
        adherence to RFC2369.

        Reference
        ^^^^^^^^^
        https://datatracker.ietf.org/doc/html/rfc2369
        """
        _list = subscription.mailing_list
        _help_path = reverse(
            "mailinglist:subscriptions", kwargs={"token": subscription.token}
        )
        _unsubscribe_path = reverse(
            "mailinglist:unsubscribe", kwargs={"token": subscription.token}
        )
        _subscribe_path = reverse(
            "mailinglist:subscribe_confirm", kwargs={"token": subscription.token}
        )
        if subscription.mailing_list is None:
            _archive_path = reverse("mailinglist:archives")
        else:
            _archive_path = reverse(
                "mailinglist:archive_index", kwargs={"mailing_list_slug": _list.slug}
            )
        return {
            "List-Help": self._urlify(_help_path) + self._mailto(_list, subject="help"),
            "List-Unsubscribe": self._urlify(_unsubscribe_path)
            + self._mailto(_list, subject="unsubscribe"),
            "List-Subscribe": self._urlify(_subscribe_path),
            "List-Post": "NO",
            "List-Owner": self._mailto(_list, appended=False),
            "List-Archive": self._urlify(_archive_path),
        }

    def _prepare_kwargs(
        self,
        *,
        subscription: models.Subscription,
        template_set: TemplateSet,
        message: models.Message = None,
    ):  # -> dict:
        _kwargs = template_set.render_to_dict(
            context={"subscription": subscription, "message": message}
        )
        _kwargs.update(
            {
                "to": [subscription.user.email],
                "headers": self._headers(subscription=subscription),
            }
        )
        return _kwargs

    def prepare_message_kwargs(
        self,
        *,
        subscription: models.Subscription,
        template_set: TemplateSet,
        message: models.Message,
    ):  # -> dict:
        """Composes and structures outgoing message data for email sending"""
        return self._prepare_kwargs(
            message=message,
            subscription=subscription,
            template_set=template_set,
        )

    def prepare_confirmation_kwargs(
        self, *, subscription: models.Subscription, template_set: TemplateSet
    ):
        """Composes and structures outgoing message data for confirmation email"""
        return self._prepare_kwargs(
            subscription=subscription,
            template_set=template_set,
        )

    def _prepare_preview(self, *, message):
        template_set = TemplateSet(mailing_list=message.mailing_list)
        rendered = template_set.render_to_dict(
            context={"subscription": None, "message": message}
        )
        return rendered

    def prepare_message_preview(self, *, message):
        return self._prepare_preview(message=message)["body"]

    def prepare_message_preview_html(self, *, message):
        return self._prepare_preview(message=message).get("html_body", None)


class SubscriptionService:
    """Manages all subscription and unsubscribe events."""

    def _random_string(self, length):
        return get_random_string(
            length=length, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789-"
        )

    def _generate_token(self, *, user, mailing_list):
        _s = randint(0, len(user.email) - 1)
        _hash = str(hash(f"{user.email[0:_s]}{mailing_list}{user.email[_s:0]}"))
        _prefix = self._random_string(length=45 - len(_hash))
        return _prefix + _hash

    def _rotate_token(self, subscription):
        subscription.token = self._generate_token(
            user=subscription.user, mailing_list=subscription.mailing_list
        )
        subscription.save()

    def _new_subscription(self, *, user, mailing_list):
        token = self._generate_token(user=user, mailing_list=mailing_list)
        subscription = models.Subscription.objects.create(
            user=user,
            mailing_list=mailing_list,
            token=token,
        )
        return subscription

    def _update_subscription_status(self, *, subscription, to_status):
        if subscription.status == to_status:
            return subscription
        models.SubscriptionChange.objects.create(
            subscription=subscription,
            from_status=subscription.status,
            to_status=to_status,
        )
        subscription.status = to_status
        subscription.save()
        return subscription

    def _confirm_subscription(self, subscription):
        if subscription.mailing_list is None:
            models.GlobalDeny.objects.get_or_create(user=subscription.user)
        return self._update_subscription_status(
            subscription=subscription, to_status=SubscriptionStatusEnum.SUBSCRIBED
        )

    def _send_subscription_confirmation(self, subscription):
        sender = (
            f'"{settings.MAILINGLIST_DEFAULT_SENDER_NAME}" '
            f"<{settings.MAILINGLIST_DEFAULT_SENDER_EMAIL}>"
        )
        if subscription.mailing_list is not None:
            sender = subscription.mailing_list.sender_tag
        hookset.send_message(
            from_email=sender,
            **MessageService().prepare_confirmation_kwargs(
                subscription=subscription,
                template_set=TemplateSet(
                    mailing_list=subscription.mailing_list,
                    action="subscribe",
                ),
            ),
        )

    # Type hints get bothersome for this dynamic user model...
    def create_user(self, *, email: str, first_name: str, last_name: str):
        """Creates a "user" for a new subscription. This method calls
        the same-named method in the hookset to actually perform the action."""
        user = hookset.create_user(
            email=email, first_name=first_name, last_name=last_name
        )
        return user

    def _subscribe(self, *, user, mailing_list):
        try:
            subscription = models.Subscription.objects.get(
                user=user, mailing_list=mailing_list
            )
        except models.Subscription.DoesNotExist:
            subscription = self._new_subscription(user=user, mailing_list=mailing_list)
        return subscription

    def force_subscribe(
        self, *, user, mailing_list: models.MailingList
    ):  # -> models.Subscription:
        """Creates an active subscription skipping any confirmation email."""
        subscription = self._subscribe(user=user, mailing_list=mailing_list)
        self._confirm_subscription(subscription)
        return subscription

    def subscribe(
        self, *, user, mailing_list: models.MailingList, force_confirm=False
    ):  # -> models.Subscription:
        """Creates a subscription and sends the activation email (or just
        activates it based on settings)"""
        if models.GlobalDeny.objects.filter(user=user).exists():
            return
        subscription = self._subscribe(user=user, mailing_list=mailing_list)
        if subscription.status == SubscriptionStatusEnum.SUBSCRIBED:
            return subscription

        if mailing_list is None or (
            settings.MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE and not force_confirm
        ):
            self._send_subscription_confirmation(subscription)
        else:
            self._confirm_subscription(subscription)
        return subscription

    def confirm_subscription(self, *, token: str):  # -> models.Subscription:
        """Activates a subscription"""
        # get subscription
        try:
            subscription = models.Subscription.objects.get(token=token)
        except models.Subscription.DoesNotExist:
            # nothing to see here
            return None
        return self._confirm_subscription(subscription)

    def _confirm_unsubscription(self, subscription):
        return self._update_subscription_status(
            subscription=subscription, to_status=SubscriptionStatusEnum.UNSUBSCRIBED
        )

    def unsubscribe(self, *, token: str):  # -> models.Subscription:
        """Deactivates a subscription"""
        try:
            subscription = models.Subscription.objects.get(token=token)
        except models.Subscription.DoesNotExist:
            # nothing to see here
            return
        return self._confirm_unsubscription(subscription)


class SubmissionService:
    """Manages send activities for published submissions."""

    def _get_included_subscribers(self, submission):
        # get current list of subscribers
        subscriptions = (
            submission.message.mailing_list.subscriptions.filter(
                status=SubscriptionStatusEnum.SUBSCRIBED
            )
            # remove all global denies
            .filter(user__mailinglist_deny__isnull=True)
            # remove all excludes
            .exclude(pk__in=submission.exclude.all().values_list("id", flat=True))
        )
        return subscriptions

    def _send_message(self, *, message, subscription, template_set, **kwargs):
        hookset.send_message(
            from_email=subscription.mailing_list.sender_tag,
            **MessageService().prepare_message_kwargs(
                message=message, subscription=subscription, template_set=template_set
            ),
            **kwargs,
        )

    def _ensure_sent(self, *, subscription, submission, **kwargs):
        """Idempotent sending of message, returns ``True`` if email was
        actually sent (returns ``False`` if email was sent previously)."""
        # check if this has been sent already
        sending_kwargs = {
            "submission": submission,
            "subscription": subscription,
        }
        if models.Sending.objects.filter(**sending_kwargs).exists():
            return False
        # send email
        self._send_message(
            message=submission.message, subscription=subscription, **kwargs
        )
        # log sending of email
        models.Sending.objects.create(**sending_kwargs)
        return True

    def _rate_limit(self, total_send_count):
        batch_sleep = False
        if settings.MAILINGLIST_BATCH_DELAY is not None:
            if total_send_count % settings.MAILINGLIST_BATCH_SIZE == 0:
                batch_sleep = True
                time.sleep(settings.MAILINGLIST_BATCH_DELAY)
        if not batch_sleep and settings.MAILINGLIST_EMAIL_DELAY is not None:
            time.sleep(settings.MAILINGLIST_EMAIL_DELAY)

    def process_submission(
        self, submission: models.Submission, *, send_count: int = 0
    ):  # -> int:
        """Sends submitted message to each (non-excluded) subscriber,
        observing rate limits configured in settings."""
        submission.status = SubmissionStatusEnum.SENDING
        submission.save()
        subscriptions = self._get_included_subscribers(submission)
        template_set = TemplateSet(mailing_list=submission.message.mailing_list)
        attachments = list(submission.message.attachments.all())
        for subscription in subscriptions:
            did_send = self._ensure_sent(
                submission=submission,
                subscription=subscription,
                template_set=template_set,
                attachments=attachments,
            )
            if not did_send:
                continue
            send_count += 1
            self._rate_limit(send_count)
        submission.status = SubmissionStatusEnum.SENT
        submission.save()
        return send_count

    def _get_outstanding_submissions(self):
        sending_submissions = models.Submission.objects.filter(
            status=SubmissionStatusEnum.SENDING
        )
        published_submissions = models.Submission.objects.filter(
            status=SubmissionStatusEnum.PENDING,
            published__isnull=False,
            published__lte=now(),
        )
        return list(sending_submissions) + list(published_submissions)

    def process_submissions(self):  # -> None:
        """Finds all unsent published ``Submission`` instances and sends them."""
        send_count = 0
        for published_submission in self._get_outstanding_submissions():
            send_count = self.process_submission(
                published_submission, send_count=send_count
            )

    def publish(self, submission: models.Submission):  # -> None:
        """Mark a ``Submission`` for sending."""
        submission.published = now()
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()

    def submit_message(self, message: models.Message):  # -> models.Submission:
        """Creates a ``Submission`` instance for a given ``Message`` instance."""
        submission, _ = models.Submission.objects.get_or_create(message=message)
        return submission
