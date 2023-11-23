import pytest
from unittest.mock import call, patch, Mock
from django.http import Http404
from mailinglist import admin
from django.contrib import admin as admin_site
from django.contrib.auth.models import Permission

from django.shortcuts import reverse
from mailinglist.models import Subscription, Submission
from mailinglist.enum import SubmissionStatusEnum
from mailinglist import services


@pytest.fixture
def inner_mock():
    return Mock()


@pytest.fixture
def subscription_admin(inner_mock):
    return admin.SubscriptionAdmin(
        Subscription, Mock(admin_view=Mock(return_value=inner_mock))
    )


@pytest.fixture
def submission_admin(inner_mock):
    return admin.SubmissionAdmin(
        Submission, Mock(admin_view=Mock(return_value=inner_mock))
    )


@pytest.fixture
def subscription_import_response(admin_client, mailing_list, address_file):
    return admin_client.post(
        reverse("admin:mailinglist_subscription_import"),
        {
            "mailing_list": mailing_list.pk,
            "address_file": address_file,
            "ignore_errors": True,
        },
        follow=True,
    )


@pytest.fixture
def confirmed_subscription_import_response(admin_client, subscription_import_response):
    return admin_client.post(
        reverse("admin:mailinglist_subscription_import_confirm"),
        {"confirm": True},
        follow=True,
    )


class TestExtendibleModelAdminMixin:
    # mixin is too abstract, have to test concrete class
    @patch.object(admin.SubscriptionAdmin, "get_queryset")
    def test_get_object_missing(self, p_get_queryset):
        p_get_queryset.side_effect = Subscription.DoesNotExist
        with pytest.raises(Http404):
            admin.SubscriptionAdmin(Subscription, admin_site)._getobj(None, None)

    @patch.object(admin.SubscriptionAdmin, "get_queryset")
    def test_get_object_present(self, p_get_queryset):
        p_get_queryset.return_value = Mock(get=Mock(return_value="something"))
        assert (
            admin.SubscriptionAdmin(Subscription, admin_site)._getobj(None, "25")
            == "something"
        )

    def test_view_name(self):
        assert (
            admin.SubscriptionAdmin(Subscription, admin_site)._view_name("snut")
            == "mailinglist_subscription_snut"
        )

    def test_wrap(self, subscription_admin, inner_mock):
        _callable = subscription_admin._wrap(subscription_admin.subscribers_import)
        _callable("wild")
        inner_mock.assert_called_once_with("wild")


class TestImmutableAdminMixin:
    def test_add_permission(self):
        assert not admin.ImmutableAdminMixin().has_add_permission(None, None)

    def test_change_permission(self):
        assert not admin.ImmutableAdminMixin().has_change_permission(None, None)

    def test_delete_permission(self):
        assert not admin.ImmutableAdminMixin().has_delete_permission(None, None)


class TestUnchangingAdminMixin:
    def test_change_permission(self):
        assert not admin.UnchangingAdminMixin().has_change_permission(None, None)


class TestSubscriptionAdmin:
    @patch.object(services.SubscriptionService, "subscribe")
    def test_save_object_no_change(self, p_subscribe, subscription_admin, subscription):
        subscription_admin.save_model(None, subscription, None, False)
        p_subscribe.assert_called_once_with(
            user=subscription.user, mailing_list=subscription.mailing_list
        )

    @patch.object(services.SubscriptionService, "subscribe")
    def test_save_object(self, p_subscribe, subscription_admin, subscription):
        subscription_admin.save_model(None, subscription, None, True)
        p_subscribe.assert_not_called()

    def test_has_change_permission(self, subscription_admin):
        assert not subscription_admin.has_change_permission(None)

    @patch.object(services.SubscriptionService, "_confirm_subscription")
    @patch.object(admin.SubscriptionAdmin, "message_user")
    def test_make_subscribed(self, p_message, p_confirm, subscription_admin):
        subscription_admin.make_subscribed(None, ["a", "b", "c"])
        p_confirm.assert_has_calls([call("a"), call("b"), call("c")])
        p_message.assert_called_once_with(
            None, "3 users have been successfully subscribed."
        )

    @patch.object(services.SubscriptionService, "_confirm_unsubscription")
    @patch.object(admin.SubscriptionAdmin, "message_user")
    def test_make_unsubscribed(self, p_message, p_confirm, subscription_admin):
        subscription_admin.make_unsubscribed(None, ["a", "b", "c"])
        p_confirm.assert_has_calls([call("a"), call("b"), call("c")])
        p_message.assert_called_once_with(
            None, "3 users have been successfully unsubscribed."
        )

    def test_subscribers_import(self, subscription_import_response):
        assert b"<h1>Confirm import</h1>" in subscription_import_response.content
        assert (
            b"<li>&lt;last@email.com&gt; Seymore Lastman</li>"
            in subscription_import_response.content
        )

    def test_subscribers_import_confirm(self, confirmed_subscription_import_response):
        assert (
            b"1 subscriptions have been added."
            in confirmed_subscription_import_response.content
        )

    def test_subscribers_import_bad_post(self, admin_client, mailing_list):
        response = admin_client.post(
            reverse("admin:mailinglist_subscription_import"),
            {
                "mailing_list": mailing_list.pk,
                "ignore_errors": True,
            },
            follow=True,
        )
        print(response.content)
        assert (
            b'<ul class="errorlist"><li>This field is required.</li></ul>'
            in response.content
        )

    def test_subscribers_import_denied(self, admin_client, admin_user):
        admin_user.is_superuser = False
        admin_user.save()
        response = admin_client.get(reverse("admin:mailinglist_subscription_import"))

        assert response.status_code == 403

    def test_subscribers_import_tight_permission(self, admin_client, admin_user):
        admin_user.is_superuser = False
        admin_user.user_permissions.add(
            Permission.objects.get(codename="add_subscription")
        )
        admin_user.save()
        response = admin_client.get(reverse("admin:mailinglist_subscription_import"))

        assert response.status_code == 200

    def test_subscribers_import_get(self, admin_client):
        response = admin_client.get(
            reverse("admin:mailinglist_subscription_import"), follow=True
        )
        assert b"<h1>Import addresses</h1>" in response.content

    def test_subscribers_import_confirm_skipped(self, admin_client):
        response = admin_client.get(
            reverse("admin:mailinglist_subscription_import_confirm")
        )
        assert response.status_code == 302
        assert response.url == reverse("admin:mailinglist_subscription_import")

    def test_subscribers_import_confirm_bad_post(
        self, admin_client, subscription_import_response
    ):
        response = admin_client.post(
            reverse("admin:mailinglist_subscription_import_confirm"),
            {"confirm": False},
            follow=False,
        )
        print(response.content)
        assert b"<li>You should confirm in order to continue.</li>" in response.content


class TestMessageAdmin:
    def test_preview(self, admin_client, message, message_part):
        response = admin_client.get(
            reverse(
                "admin:mailinglist_message_preview", kwargs={"object_id": message.pk}
            )
        )
        assert response.status_code == 200
        print(response.content)
        assert (
            str.encode(
                f"<iframe src ='/admin/mailinglist/message/{message.pk}/preview/html/'"
            )
            in response.content
        )
        assert (
            str.encode(
                f"<iframe src ='/admin/mailinglist/message/{message.pk}/preview/text/'"
            )
            in response.content
        )

    def test_preview_no_html(self, admin_client, message, message_part):
        message.mailing_list.send_html = False
        message.mailing_list.save()
        response = admin_client.get(
            reverse(
                "admin:mailinglist_message_preview", kwargs={"object_id": message.pk}
            )
        )
        assert response.status_code == 200
        print(response.content)
        assert (
            str.encode(
                f"<iframe src ='/admin/mailinglist/message/{message.pk}/preview/html/'"
            )
            not in response.content
        )
        assert (
            str.encode(
                f"<iframe src ='/admin/mailinglist/message/{message.pk}/preview/text/'"
            )
            in response.content
        )

    def test_preview_html(self, admin_client, message, message_part):
        response = admin_client.get(
            reverse(
                "admin:mailinglist_message_preview_html",
                kwargs={"object_id": message.pk},
            )
        )
        assert response.status_code == 200
        print(response.content)
        assert b"<strong>exquisite</strong>" in response.content
        assert b"<li>and lists</li>" in response.content

    def test_preview_text(self, admin_client, message, message_part):
        response = admin_client.get(
            reverse(
                "admin:mailinglist_message_preview_text",
                kwargs={"object_id": message.pk},
            )
        )
        assert response.status_code == 200
        print(response.content)
        assert b"**exquisite**" in response.content
        assert b"* and lists" in response.content

    def test_submit(self, admin_client, message, message_part):
        assert not hasattr(message, "submission")
        response = admin_client.get(
            reverse(
                "admin:mailinglist_message_submit",
                kwargs={"object_id": message.pk},
            ),
            follow=False,
        )
        message.refresh_from_db()
        assert hasattr(message, "submission")
        assert response.status_code == 302
        assert response.url == reverse(
            "admin:mailinglist_submission_change", args=[message.submission.pk]
        )
        Submission.objects.filter(pk=message.submission.pk).delete()


class TestSubmissionAdmin:
    def test_submit(self, admin_client, submission):
        assert submission.status == SubmissionStatusEnum.NEW
        assert submission.published is None
        response = admin_client.get(
            reverse(
                "admin:mailinglist_submission_publish",
                kwargs={"object_id": submission.pk},
            ),
            follow=False,
        )
        submission.refresh_from_db()
        assert submission.status == SubmissionStatusEnum.PENDING
        assert submission.published is not None
        assert response.status_code == 302
        assert response.url == reverse("admin:mailinglist_submission_changelist")

    @patch.object(services.SubmissionService, "publish")
    @patch.object(admin.SubmissionAdmin, "message_user")
    def test_publish_action(self, p_message, p_publish, submission_admin):
        submission_admin.publish(None, ["a", "b", "c"])
        p_publish.assert_has_calls([call("a"), call("b"), call("c")])
        p_message.assert_called_once_with(None, "3 submissions have been published.")
