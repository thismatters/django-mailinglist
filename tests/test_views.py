from unittest.mock import patch, Mock
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.test import override_settings

from mailinglist import enum, models, views


def setup_view(view, request, *args, **kwargs):
    """Mimic as_view() returned callable, but returns view instance.

    args and kwargs are the same you would pass to ``reverse()``

    """
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view


class TestDetailFormView:
    # can't test the view class itself because it is too abstract
    @patch.object(views.SubscribeView, "get_object")
    def test_get(self, p_get_object, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        p_get_object.return_value = "great object"
        view = setup_view(views.SubscribeView(), request)
        view.get(request)
        assert view.object == "great object"


class TestSubscribeFormMixin:
    # can't test the mixin class itself because it is too abstract
    def test_initial_anon(self, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.SubscribeView(), request)
        initial = view.get_initial()
        assert initial == {}

    def test_initial(self, rf, user):
        request = rf.get("/fake-path")
        request.user = user
        view = setup_view(views.SubscribeView(), request)
        initial = view.get_initial()
        assert initial == {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }


class TestGlobalDenyView:
    def test_get_success_url(self, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.GlobalDenyView(), request)
        assert view.get_success_url() == "/mailinglist/global_deny/success/"

    def test_get_object(self, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.GlobalDenyView(), request)
        assert view.get_object() is None


class TestSubscribeSuccessView:
    @override_settings(MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE=True)
    def test_get_context_data(self, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.SubscribeSuccessView(), request)
        view.object = None
        assert view.get_context_data()["requires_confirmation"]

    @override_settings(MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE=False)
    def test_get_context_data_nay(self, rf):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.SubscribeSuccessView(), request)
        view.object = None
        assert not view.get_context_data()["requires_confirmation"]


class TestSubscriptionView:
    def test_get_success_url(self, rf, subscription):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.SubscriptionView(), request, token=subscription.token)
        assert (
            view.get_success_url()
            == f"/mailinglist/subscriptions/{subscription.token}/"
        )

    def test_form_valid(self, rf, subscription):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        form = Mock()
        view = setup_view(views.SubscriptionView(), request, token=subscription.token)
        view.form_valid(form)
        form.save.assert_called_once()

    def test_get_form_kwargs(self, rf, subscription):
        request = rf.get("/fake-path")
        request.user = AnonymousUser()
        view = setup_view(views.SubscriptionView(), request, token=subscription.token)
        assert view.get_form_kwargs()["user"] == subscription.user


class TestSubscribeView:
    def test_post_form_empty(self, client, mailing_list):
        assert not models.Subscription.objects.all().exists()
        response = client.post(
            reverse(
                "mailinglist:subscribe", kwargs={"mailing_list_slug": mailing_list.slug}
            ),
        )
        assert not models.Subscription.objects.all().exists()
        assert not response.context["form"].is_valid()

    def test_post(self, client, mailing_list):
        assert not models.Subscription.objects.all().exists()
        client.post(
            reverse(
                "mailinglist:subscribe", kwargs={"mailing_list_slug": mailing_list.slug}
            ),
            {
                "email": "test@test.test",
                "first_name": "Testy",
                "last_name": "McTestface",
                "are_you_sure": True,
            },
        )
        assert models.Subscription.objects.all().exists()
        subscription = models.Subscription.objects.first()
        assert subscription.mailing_list == mailing_list
        assert subscription.user.email == "test@test.test"
        assert subscription.user.first_name == "Testy"
        assert subscription.user.last_name == "McTestface"

    def test_post_first_name_only(self, client, mailing_list):
        assert not models.Subscription.objects.all().exists()
        client.post(
            reverse(
                "mailinglist:subscribe", kwargs={"mailing_list_slug": mailing_list.slug}
            ),
            {
                "email": "test@test.test",
                "first_name": "Testy",
                "last_name": "",
                "are_you_sure": True,
            },
        )
        assert models.Subscription.objects.all().exists()
        subscription = models.Subscription.objects.first()
        assert subscription.user.email == "test@test.test"
        assert subscription.user.first_name == "Testy"
        assert subscription.user.last_name == ""

    def test_post_bad_email(self, client, mailing_list):
        assert not models.Subscription.objects.all().exists()
        response = client.post(
            reverse(
                "mailinglist:subscribe", kwargs={"mailing_list_slug": mailing_list.slug}
            ),
            {
                "email": "notanemailaddress.com",
                "first_name": "Testy",
                "last_name": "",
                "are_you_sure": True,
            },
        )
        assert not models.Subscription.objects.all().exists()
        assert not response.context["form"].is_valid()

    def test_post_not_sure(self, client, mailing_list):
        assert not models.Subscription.objects.all().exists()
        response = client.post(
            reverse(
                "mailinglist:subscribe", kwargs={"mailing_list_slug": mailing_list.slug}
            ),
            {
                "email": "test@test.test",
                "first_name": "Testy",
                "last_name": "McTestface",
                "are_you_sure": False,
            },
        )
        assert not models.Subscription.objects.all().exists()
        assert not response.context["form"].is_valid()


class TestSubscribeConfirmView:
    def test_good_subscribe(self, client, mailing_list, subscription):
        client.get(
            reverse(
                "mailinglist:subscribe_confirm", kwargs={"token": subscription.token}
            )
        )
        subscription.refresh_from_db()
        assert subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED

    def test_good_subscribe_global_unsubscribe(
        self, client, mailing_list, subscription
    ):
        subscription.mailing_list = None
        subscription.save()
        client.get(
            reverse(
                "mailinglist:subscribe_confirm", kwargs={"token": subscription.token}
            )
        )
        subscription.refresh_from_db()
        assert hasattr(subscription.user, "mailinglist_deny")
        assert subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED

    def test_bad_subscribe(self, client, mailing_list, subscription):
        response = client.get(
            reverse(
                "mailinglist:subscribe_confirm",
                kwargs={"token": subscription.token + "a"},
            )
        )
        subscription.refresh_from_db()
        assert subscription.status == enum.SubscriptionStatusEnum.PENDING
        assert b"token in the URL is invalid! Sorry." in response.content


class TestUnsubscribeView:
    def test_good_unsubscribe(self, client, mailing_list, active_subscription):
        client.get(
            reverse(
                "mailinglist:unsubscribe", kwargs={"token": active_subscription.token}
            )
        )
        active_subscription.refresh_from_db()
        assert active_subscription.status == enum.SubscriptionStatusEnum.UNSUBSCRIBED

    def test_bad_unsubscribe(self, client, mailing_list, active_subscription):
        response = client.get(
            reverse(
                "mailinglist:subscribe_confirm",
                kwargs={"token": active_subscription.token + "a"},
            )
        )
        active_subscription.refresh_from_db()
        assert active_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED
        assert b"token in the URL is invalid! Sorry." in response.content


class TestArchiveIndexView:
    def test_archive_visibility(self, client, mailing_list):
        # should be visible by default
        response = client.get(
            reverse(
                "mailinglist:archive_index",
                kwargs={"mailing_list_slug": mailing_list.slug},
            )
        )
        assert b"Archive of test list" in response.content

    def test_archive_invisibility(self, client, mailing_list):
        mailing_list.visible = False
        mailing_list.save()
        response = client.get(
            reverse(
                "mailinglist:archive_index",
                kwargs={"mailing_list_slug": mailing_list.slug},
            )
        )
        assert response.status_code == 404

    def test_archive_message_invisibility(
        self, client, submission, message, mailing_list
    ):
        # should be visible by default
        response = client.get(
            reverse(
                "mailinglist:archive_index",
                kwargs={"mailing_list_slug": mailing_list.slug},
            )
        )
        assert b"test message" not in response.content

    def test_archive_message_visibility(
        self, client, published_submission, message, mailing_list
    ):
        response = client.get(
            reverse(
                "mailinglist:archive_index",
                kwargs={"mailing_list_slug": mailing_list.slug},
            )
        )
        assert b"test message" in response.content


class TestArchiveView:
    def test_message_visibility(
        self, client, published_submission, message, mailing_list
    ):
        response = client.get(
            reverse(
                "mailinglist:archive",
                kwargs={
                    "mailing_list_slug": mailing_list.slug,
                    "message_slug": message.slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"test message" in response.content

    def test_message_invisibility_mailinglist(
        self, client, published_submission, message, mailing_list
    ):
        mailing_list.visible = False
        mailing_list.save()
        response = client.get(
            reverse(
                "mailinglist:archive",
                kwargs={
                    "mailing_list_slug": mailing_list.slug,
                    "message_slug": message.slug,
                },
            )
        )
        assert response.status_code == 404

    def test_message_invisibility_unpublished(
        self, client, submission, message, mailing_list
    ):
        response = client.get(
            reverse(
                "mailinglist:archive",
                kwargs={
                    "mailing_list_slug": mailing_list.slug,
                    "message_slug": message.slug,
                },
            )
        )
        assert response.status_code == 404
