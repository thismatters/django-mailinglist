import time
from random import randint

from django.template.loader import select_template
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from mailinglist import models
from mailinglist.conf import hookset, settings
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


class MessageService:
    def _get_template(self, *, mailing_list, suffix="txt", _for="message"):
        _root = "mailinglist/email"
        slug = "global-deny"
        if mailing_list is not None:
            slug = mailing_list.slug
        return select_template(
            [
                f"{_root}/{slug}/{_for}.{suffix}",
                f"{_root}/{_for}.{suffix}",
            ]
        )

    def _prepare(self, *, subscription, message=None, suffix="txt", _for="message"):
        if message is not None:
            mailing_list = message.mailing_list
        else:
            mailing_list = subscription.mailing_list

        template = self._get_template(
            mailing_list=mailing_list, suffix=suffix, _for=_for
        )
        context = {
            "subscription": subscription,
            "message": message,
            "BASE_URL": settings.MAILINGLIST_BASE_URL,
            "DEFAULT_SENDER_NAME": settings.MAILINGLIST_DEFAULT_SENDER_NAME,
        }
        return template.render(context).strip()

    def prepare_message_subject(self, *, message, subscription):
        return self._prepare(
            message=message,
            subscription=subscription,
            _for="message_subject",
        )

    def prepare_message_body(self, *, message, subscription):
        return self._prepare(
            message=message,
            subscription=subscription,
            suffix="txt",
        )

    def prepare_message_html_body(self, *, message, subscription):
        return self._prepare(
            message=message,
            subscription=subscription,
            suffix="html",
        )

    def prepare_message_kwargs(self, *, message, subscription):
        return {
            "subject": self.prepare_message_subject(
                message=message, subscription=subscription
            ),
            "body": self.prepare_message_body(
                message=message, subscription=subscription
            ),
            "html_body": self.prepare_message_html_body(
                message=message, subscription=subscription
            ),
        }

    def prepare_confirmation_subject(self, *, subscription):
        return self._prepare(
            subscription=subscription,
            _for="subscribe_subject",
        )

    def prepare_confirmation_body(self, *, subscription):
        return self._prepare(
            subscription=subscription,
            _for="subscribe",
        )

    def prepare_confirmation_html_body(self, *, subscription):
        return self._prepare(
            subscription=subscription,
            suffix="html",
            _for="subscribe",
        )

    def prepare_confirmation_kwargs(self, *, subscription):
        return {
            "subject": self.prepare_confirmation_subject(subscription=subscription),
            "body": self.prepare_confirmation_body(subscription=subscription),
            "html_body": self.prepare_confirmation_html_body(subscription=subscription),
        }


class SubscriptionService:
    def _random_string(self, length):
        return get_random_string(
            length=length, allowed_chars="abcdefghijklmnopqrstuvwxyz0123456789-"
        )

    def _generate_token(self, *, user, mailing_list):
        # TODO: this might go into the hookset
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
            to=[subscription.user.email],
            from_email=sender,
            **MessageService().prepare_confirmation_kwargs(subscription=subscription),
        )

    def create_user(self, *, email, first_name, last_name):
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

    def force_subscribe(self, *, user, mailing_list):
        subscription = self._subscribe(user=user, mailing_list=mailing_list)
        self._confirm_subscription(subscription)
        return subscription

    def subscribe(self, *, user, mailing_list, force_confirm=False):
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

    def confirm_subscription(self, *, token):
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

    def unsubscribe(self, *, token):
        try:
            subscription = models.Subscription.objects.get(token=token)
        except models.Subscription.DoesNotExist:
            # nothing to see here
            return
        return self._confirm_unsubscription(subscription)


class SubmissionService:
    def _get_included_subscribers(self, submission):
        # get current list of subscribers
        subscriptions = (
            submission.message.mailing_list.subscriptions.filter(
                status=SubscriptionStatusEnum.SUBSCRIBED
            )
            # remove all global denies
            .filter(user__mailinglist_deny__isnull=True)
            # remove all excludes
            .difference(submission.exclude.all())
        )
        return subscriptions

    def _send_message(self, message, subscription):
        hookset.send_message(
            to=[subscription.user.email],
            from_email=subscription.mailing_list.sender_tag,
            **MessageService().prepare_message_kwargs(
                message=message, subscription=subscription
            ),
        )

    def _ensure_sent(self, *, subscription, submission):
        """Idempotent sending of message, returns ``True`` if email was
        actually sent (returns ``False`` if email was sent previously)."""
        # check if this has been sent already
        kwargs = {
            "submission": submission,
            "subscription": subscription,
        }
        if models.Sending.objects.filter(**kwargs).exists():
            return False
        # send email
        self._send_message(message=submission.message, subscription=subscription)
        # log sending of email
        models.Sending.objects.create(**kwargs)
        return True

    def _rate_limit(self, total_send_count):
        batch_sleep = False
        if settings.MAILINGLIST_BATCH_DELAY is not None:
            if total_send_count % settings.MAILINGLIST_BATCH_SIZE == 0:
                batch_sleep = True
                time.sleep(settings.MAILINGLIST_BATCH_DELAY)
        if not batch_sleep and settings.MAILINGLIST_EMAIL_DELAY is not None:
            time.sleep(settings.MAILINGLIST_EMAIL_DELAY)

    def process_submission(self, submission, *, send_count=0):
        submission.status = SubmissionStatusEnum.SENDING
        submission.save()
        subscriptions = self._get_included_subscribers(submission)
        for subscription in subscriptions:
            did_send = self._ensure_sent(
                submission=submission, subscription=subscription
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

    def process_submissions(self):
        send_count = 0
        for published_submission in self._get_outstanding_submissions():
            send_count = self.process_submission(
                published_submission, send_count=send_count
            )

    def publish(self, submission):
        submission.published = now()
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()

    def submit_message(self, message):
        submission, _ = models.Submission.objects.get_or_create(message=message)
        return submission
