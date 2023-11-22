from datetime import timedelta
from unittest.mock import Mock, patch, call

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils.timezone import now

from mailinglist import models, services
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


class TestMessageService:
    @patch("mailinglist.services.select_template")
    def test_get_template(self, p_select_template, mailing_list):
        services.MessageService()._get_template(mailing_list=mailing_list)
        p_select_template.assert_called_once_with(
            [
                f"mailinglist/email/{mailing_list.slug}/message.txt",
                "mailinglist/email/message.txt",
            ]
        )

    @patch("mailinglist.services.select_template")
    def test_get_template_no_mailing_list(self, p_select_template):
        services.MessageService()._get_template(mailing_list=None)
        p_select_template.assert_called_once_with(
            [
                "mailinglist/email/global-deny/message.txt",
                "mailinglist/email/message.txt",
            ]
        )

    @patch.object(services.MessageService, "_get_template")
    def test_prepare(self, p_get_template, subscription):
        _render = Mock(return_value="  Blah blah Blahh!1! ")
        p_get_template.return_value = Mock(render=_render)
        ret = services.MessageService()._prepare(subscription=subscription)
        p_get_template.assert_called_once_with(
            mailing_list=subscription.mailing_list, suffix="txt", _for="message"
        )
        _render.assert_called_once_with(
            {
                "subscription": subscription,
                "message": None,
                "BASE_URL": "http://ilocalhost:8000",
                "DEFAULT_SENDER_NAME": "Administrator",
            }
        )
        assert "Blah blah Blahh!1!" == ret

    @patch.object(services.MessageService, "_get_template")
    def test_prepare_no_mailing_list(self, p_get_template, subscription):
        subscription.mailing_list = None
        subscription.save()
        _render = Mock(return_value="  Blah blah Blahh!1! ")
        p_get_template.return_value = Mock(render=_render)
        ret = services.MessageService()._prepare(subscription=subscription)
        p_get_template.assert_called_once_with(
            mailing_list=None, suffix="txt", _for="message"
        )
        _render.assert_called_once_with(
            {
                "subscription": subscription,
                "message": None,
                "BASE_URL": "http://ilocalhost:8000",
                "DEFAULT_SENDER_NAME": "Administrator",
            }
        )
        assert "Blah blah Blahh!1!" == ret

    @patch.object(services.MessageService, "_get_template")
    def test_prepare_message(self, p_get_template, subscription, message):
        subscription.mailing_list = None
        subscription.save()
        _render = Mock(return_value="  Blah blah Blahh!1! ")
        p_get_template.return_value = Mock(render=_render)
        ret = services.MessageService()._prepare(
            subscription=subscription, message=message
        )
        p_get_template.assert_called_once_with(
            mailing_list=message.mailing_list, suffix="txt", _for="message"
        )
        _render.assert_called_once_with(
            {
                "subscription": subscription,
                "message": message,
                "BASE_URL": "http://ilocalhost:8000",
                "DEFAULT_SENDER_NAME": "Administrator",
            }
        )
        assert "Blah blah Blahh!1!" == ret

    @patch.object(services.MessageService, "_prepare")
    def test_prepare_message_kwargs(self, p_prepare, subscription, message):
        p_prepare.return_value = "generic return"
        ret = services.MessageService().prepare_message_kwargs(
            subscription=subscription, message=message
        )
        assert ret == {
            "subject": "generic return",
            "body": "generic return",
            "html_body": "generic return",
        }
        p_prepare.assert_has_calls(
            [
                call(
                    message=message, subscription=subscription, _for="message_subject"
                ),
                call(message=message, subscription=subscription, suffix="txt"),
                call(message=message, subscription=subscription, suffix="html"),
            ]
        )


class TestSubmissionService:
    def test_get_included_subscribers(self, active_subscription, submission):
        subscriptions = services.SubmissionService()._get_included_subscribers(
            submission
        )
        assert active_subscription in subscriptions

    def test_get_included_subscribers_excluded(self, active_subscription, submission):
        submission.exclude.add(active_subscription)
        subscriptions = services.SubmissionService()._get_included_subscribers(
            submission
        )
        assert active_subscription not in subscriptions

    def test_get_included_subscribers_global_deny(
        self, active_denied_subscription, submission
    ):
        subscriptions = services.SubmissionService()._get_included_subscribers(
            submission
        )
        assert active_denied_subscription not in subscriptions

    @override_settings(
        MAILINGLIST_EMAIL_DELAY=2,
        MAILINGLIST_BATCH_SIZE=200,
        MAILINGLIST_BATCH_DELAY=3,
    )
    @patch("time.sleep")
    def test_rate_limit(self, p_sleep):
        services.SubmissionService()._rate_limit(99)
        p_sleep.assert_called_once_with(2)

    @override_settings(
        MAILINGLIST_EMAIL_DELAY=2,
        MAILINGLIST_BATCH_SIZE=200,
        MAILINGLIST_BATCH_DELAY=3,
    )
    @patch("time.sleep")
    def test_rate_limit_batch(self, p_sleep):
        services.SubmissionService()._rate_limit(400)
        p_sleep.assert_called_once_with(3)

    @override_settings(
        MAILINGLIST_EMAIL_DELAY=2,
        MAILINGLIST_BATCH_SIZE=200,
        MAILINGLIST_BATCH_DELAY=None,
    )
    @patch("time.sleep")
    def test_rate_limit_batch_no_delay(self, p_sleep):
        services.SubmissionService()._rate_limit(400)
        p_sleep.assert_called_once_with(2)

    @override_settings(
        MAILINGLIST_EMAIL_DELAY=None,
        MAILINGLIST_BATCH_SIZE=200,
        MAILINGLIST_BATCH_DELAY=None,
    )
    @patch("time.sleep")
    def test_rate_limit_no_delay(self, p_sleep):
        services.SubmissionService()._rate_limit(400)
        p_sleep.assert_not_called()

    @patch.object(services.SubmissionService, "_send_message")
    def test_ensure_sent(self, p_send_message, active_subscription, submission):
        assert not models.Sending.objects.filter(
            submission=submission, subscription=active_subscription
        ).exists()
        did_send = services.SubmissionService()._ensure_sent(
            subscription=active_subscription, submission=submission
        )
        p_send_message.assert_called_once_with(
            message=submission.message, subscription=active_subscription
        )
        assert models.Sending.objects.filter(
            submission=submission, subscription=active_subscription
        ).exists()
        assert did_send
        models.Sending.objects.filter(
            submission=submission, subscription=active_subscription
        ).delete()

    @patch.object(services.SubmissionService, "_send_message")
    def test_ensure_sent_already_sent(
        self, p_send_message, active_subscription, submission
    ):
        models.Sending.objects.create(
            submission=submission, subscription=active_subscription
        )
        did_send = services.SubmissionService()._ensure_sent(
            subscription=active_subscription, submission=submission
        )
        p_send_message.assert_not_called()
        assert not did_send
        models.Sending.objects.filter(
            submission=submission, subscription=active_subscription
        ).delete()

    @patch.object(services.SubmissionService, "_send_message")
    def test_ensure_sent_send_failure(
        self, p_send_message, active_subscription, submission
    ):
        p_send_message.side_effect = Exception("boom")
        with pytest.raises(Exception):
            services.SubmissionService()._ensure_sent(
                subscription=active_subscription, submission=submission
            )
        assert not models.Sending.objects.filter(
            submission=submission, subscription=active_subscription
        ).exists()

    def test_get_outstanding_submissions_sending(self, submission):
        submission.status = SubmissionStatusEnum.PENDING
        submission.status = SubmissionStatusEnum.SENDING
        submission.save()
        outstanding = services.SubmissionService()._get_outstanding_submissions()
        assert submission in outstanding

    def test_get_outstanding_submissions_pending(self, submission):
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()
        outstanding = services.SubmissionService()._get_outstanding_submissions()
        assert submission not in outstanding

    def test_get_outstanding_submissions_pending_future(self, submission):
        submission.status = SubmissionStatusEnum.PENDING
        submission.published = now() + timedelta(hours=1)
        submission.save()
        outstanding = services.SubmissionService()._get_outstanding_submissions()
        assert submission not in outstanding

    def test_get_outstanding_submissions_pending_ready(self, submission):
        submission.status = SubmissionStatusEnum.PENDING
        submission.published = now() - timedelta(hours=1)
        submission.save()
        outstanding = services.SubmissionService()._get_outstanding_submissions()
        assert submission in outstanding

    def test_get_outstanding_submissions_not_submitted(self, submission):
        outstanding = services.SubmissionService()._get_outstanding_submissions()
        assert submission not in outstanding

    @patch.object(services.SubmissionService, "_rate_limit")
    @patch.object(services.SubmissionService, "_ensure_sent")
    def test_process_submission(
        self, p_ensure_sent, p_rate_limit, submission, active_subscription
    ):
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()
        p_ensure_sent.return_value = True
        _send_count = services.SubmissionService().process_submission(submission)
        p_ensure_sent.assert_called_once_with(
            submission=submission, subscription=active_subscription
        )
        p_rate_limit.assert_called_once_with(1)
        submission.refresh_from_db()
        assert submission.status == SubmissionStatusEnum.SENT
        assert _send_count == 1

    @patch.object(services.SubmissionService, "_rate_limit")
    @patch.object(services.SubmissionService, "_ensure_sent")
    def test_process_submission_send_count(
        self, p_ensure_sent, p_rate_limit, submission, active_subscription
    ):
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()
        p_ensure_sent.return_value = True
        _send_count = services.SubmissionService().process_submission(
            submission, send_count=2
        )
        p_ensure_sent.assert_called_once_with(
            submission=submission, subscription=active_subscription
        )
        p_rate_limit.assert_called_once_with(3)
        submission.refresh_from_db()
        assert submission.status == SubmissionStatusEnum.SENT
        assert _send_count == 3

    @patch.object(services.SubmissionService, "_rate_limit")
    @patch.object(services.SubmissionService, "_ensure_sent")
    def test_process_submission_not_send(
        self, p_ensure_sent, p_rate_limit, submission, active_subscription
    ):
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()
        p_ensure_sent.return_value = False
        _send_count = services.SubmissionService().process_submission(submission)
        p_ensure_sent.assert_called_once_with(
            submission=submission, subscription=active_subscription
        )
        p_rate_limit.assert_not_called()
        submission.refresh_from_db()
        assert submission.status == SubmissionStatusEnum.SENT
        assert _send_count == 0

    @patch.object(services.SubmissionService, "_get_included_subscribers")
    def test_process_submission_interrupt(self, p_get_included_subscribers, submission):
        p_get_included_subscribers.side_effect = Exception
        submission.status = SubmissionStatusEnum.PENDING
        submission.save()
        with pytest.raises(Exception):
            services.SubmissionService().process_submission(submission)
        submission.refresh_from_db()
        assert submission.status == SubmissionStatusEnum.SENDING

    @patch.object(services.SubmissionService, "process_submission")
    @patch.object(services.SubmissionService, "_get_outstanding_submissions")
    def test_process_submissions(
        self, p_get_outstanding_submissions, p_process_submission
    ):
        p_get_outstanding_submissions.return_value = [1, 2, 3]
        p_process_submission.return_value = 0
        services.SubmissionService().process_submissions()
        p_process_submission.assert_has_calls(
            [call(1, send_count=0), call(2, send_count=0), call(3, send_count=0)]
        )

    def test_publish(self, submission):
        assert submission.published is None
        assert submission.status == SubmissionStatusEnum.NEW
        services.SubmissionService().publish(submission)
        submission.refresh_from_db()
        assert submission.published is not None
        assert submission.status == SubmissionStatusEnum.PENDING

    def test_submit_message(self, message):
        assert not hasattr(message, "submission")
        services.SubmissionService().submit_message(message)
        message.refresh_from_db()
        assert hasattr(message, "submission")
        assert message.submission.status == SubmissionStatusEnum.NEW
        message.submission.delete()

    def test_submit_message_already_submitted(self, message, submission):
        assert hasattr(message, "submission")
        _submission = services.SubmissionService().submit_message(message)
        message.refresh_from_db()
        assert hasattr(message, "submission")
        assert submission == _submission
        assert message.submission.status == SubmissionStatusEnum.NEW
        assert models.Submission.objects.filter(message=message).count() == 1

    @patch.object(services.MessageService, "prepare_message_kwargs")
    @patch.object(services.hookset, "send_message")
    def test_send_message(
        self, p_send_message, p_prepare_message_kwargs, message, subscription
    ):
        p_prepare_message_kwargs.return_value = {"stuff": "yeah"}
        services.SubmissionService()._send_message(message, subscription)
        p_send_message.assert_called_once_with(
            to=[subscription.user.email],
            from_email=subscription.mailing_list.sender_tag,
            stuff="yeah",
        )


class TestSubscriptionService:
    @patch("mailinglist.services.randint", Mock(return_value=3))
    def test_rotate_token(self, subscription):
        _old_token = subscription.token
        services.SubscriptionService()._rotate_token(subscription)
        subscription.refresh_from_db()
        _hash = str(
            hash(
                f"{subscription.user.email[0:3]}"
                f"{subscription.mailing_list.name}"
                f"{subscription.user.email[3:0]}"
            )
        )

        assert subscription.token.endswith(_hash)
        assert _old_token != subscription.token

    @patch("mailinglist.services.randint", Mock(return_value=3))
    def test_new_subscription(self, mailing_list, user):
        subscription = services.SubscriptionService()._new_subscription(
            user=user, mailing_list=mailing_list
        )
        _hash = str(hash(f"{user.email[0:3]}{mailing_list.name}{user.email[3:0]}"))
        assert subscription.token.endswith(_hash)
        assert subscription.status == SubscriptionStatusEnum.PENDING

    def test_update_subscription_status_no_change(self, active_subscription):
        assert active_subscription.status == SubscriptionStatusEnum.SUBSCRIBED
        qs = models.SubscriptionChange.objects.filter(subscription=active_subscription)
        assert qs.count() == 0
        services.SubscriptionService()._update_subscription_status(
            subscription=active_subscription,
            to_status=SubscriptionStatusEnum.SUBSCRIBED,
        )
        active_subscription.refresh_from_db()
        assert active_subscription.status == SubscriptionStatusEnum.SUBSCRIBED
        assert qs.count() == 0

    def test_update_subscription_status_subscribe(self, subscription):
        assert subscription.status != SubscriptionStatusEnum.SUBSCRIBED
        qs = models.SubscriptionChange.objects.filter(subscription=subscription)
        assert qs.count() == 0
        services.SubscriptionService()._update_subscription_status(
            subscription=subscription,
            to_status=SubscriptionStatusEnum.SUBSCRIBED,
        )
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatusEnum.SUBSCRIBED
        assert qs.count() == 1
        assert qs[0].to_status == SubscriptionStatusEnum.SUBSCRIBED

    def test_update_subscription_status_unsubscribe(self, subscription):
        assert subscription.status != SubscriptionStatusEnum.UNSUBSCRIBED
        qs = models.SubscriptionChange.objects.filter(subscription=subscription)
        assert qs.count() == 0
        services.SubscriptionService()._update_subscription_status(
            subscription=subscription,
            to_status=SubscriptionStatusEnum.UNSUBSCRIBED,
        )
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatusEnum.UNSUBSCRIBED
        assert qs.count() == 1
        assert qs[0].to_status == SubscriptionStatusEnum.UNSUBSCRIBED

    @patch.object(services.SubscriptionService, "_send_subscription_confirmation")
    def test_subscribe(self, p_confirm, user, mailing_list):
        subscription = services.SubscriptionService().subscribe(
            user=user, mailing_list=mailing_list
        )
        assert subscription.status == SubscriptionStatusEnum.PENDING
        p_confirm.assert_called_once_with(subscription)

    @patch.object(services.SubscriptionService, "_send_subscription_confirmation")
    def test_subscribe_force_confirm(self, p_confirm, user, mailing_list):
        subscription = services.SubscriptionService().subscribe(
            user=user, mailing_list=mailing_list, force_confirm=True
        )
        assert subscription.status == SubscriptionStatusEnum.SUBSCRIBED
        p_confirm.assert_not_called()

    @patch.object(services.SubscriptionService, "_new_subscription")
    def test_subscribe_exists(self, p_new_subscription, active_subscription):
        services.SubscriptionService().subscribe(
            user=active_subscription.user, mailing_list=active_subscription.mailing_list
        )
        active_subscription.refresh_from_db()
        p_new_subscription.assert_not_called()
        assert active_subscription.status == SubscriptionStatusEnum.SUBSCRIBED

    def test_subscribe_deny(self, denied_user, mailing_list):
        subscription = services.SubscriptionService().subscribe(
            user=denied_user, mailing_list=mailing_list
        )
        assert subscription is None
        assert not models.Subscription.objects.filter(user=denied_user).exists()

    @override_settings(MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE=False)
    def test_subscribe_noconfirm(self, user, mailing_list):
        subscription = services.SubscriptionService().subscribe(
            user=user, mailing_list=mailing_list
        )
        assert subscription.status == SubscriptionStatusEnum.SUBSCRIBED

    def test_unsubscribe(self, active_subscription):
        assert active_subscription.status != SubscriptionStatusEnum.UNSUBSCRIBED
        services.SubscriptionService().unsubscribe(token=active_subscription.token)
        active_subscription.refresh_from_db()
        assert active_subscription.status == SubscriptionStatusEnum.UNSUBSCRIBED

    def test_unsubscribe_bad_token(self, active_subscription):
        assert active_subscription.status != SubscriptionStatusEnum.UNSUBSCRIBED
        ret = services.SubscriptionService().unsubscribe(
            token=active_subscription.token + "a"
        )
        assert ret is None
        active_subscription.refresh_from_db()
        assert active_subscription.status == SubscriptionStatusEnum.SUBSCRIBED

    def test_confirm_subscription(self, subscription):
        assert subscription.status != SubscriptionStatusEnum.SUBSCRIBED
        services.SubscriptionService().confirm_subscription(token=subscription.token)
        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatusEnum.SUBSCRIBED

    @override_settings(
        MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE=False,
        MAILINGLIST_BASE_URL="https://www.trustworthymailer.lol",
    )
    @patch.object(services.hookset, "send_message")
    def test_new_subscription_no_mailing_list(self, p_send, user):
        assert not models.GlobalDeny.objects.filter(user=user).exists()
        subscription = services.SubscriptionService().subscribe(
            user=user, mailing_list=None
        )
        confirm_url = reverse(
            "mailinglist:subscribe_confirm", kwargs={"token": subscription.token}
        )
        full_url = f"https://www.trustworthymailer.lol{confirm_url}"
        # sends email with token always!
        p_send.assert_called_once()
        assert full_url in p_send.call_args.kwargs["body"]
        assert full_url in p_send.call_args.kwargs["html_body"]
        assert not models.GlobalDeny.objects.filter(user=user).exists()
        # token redeems by putting user in global deny
        services.SubscriptionService().confirm_subscription(token=subscription.token)
        assert models.GlobalDeny.objects.filter(user=user).exists()

    def test_force_subscribe(self, user, mailing_list):
        assert not user.subscriptions.all().exists()
        subscription = services.SubscriptionService().force_subscribe(
            user=user, mailing_list=mailing_list
        )
        assert user.subscriptions.all().exists()
        assert subscription.user == user
        assert subscription.mailing_list == mailing_list
        assert subscription.status == SubscriptionStatusEnum.SUBSCRIBED
