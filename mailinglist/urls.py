from django.urls import path
from django.views.generic import TemplateView

from mailinglist import views

app_name = "mailinglist"

urlpatterns = [
    path(
        "global_deny/",
        views.GlobalDenyView.as_view(),
        name="global_deny",
    ),
    path(
        "global_deny/success/",
        TemplateView.as_view(
            template_name="mailinglist/web/global_unsubscribe_success.html"
        ),
        name="global_deny_success",
    ),
    path(
        "subscribe/<slug:mailing_list_slug>/",
        views.SubscribeView.as_view(),
        name="subscribe",
    ),
    path(
        "subscribe/<slug:mailing_list_slug>/success/",
        views.SubscribeSuccessView.as_view(),
        name="subscribe_success",
    ),
    path(
        "subscribe/<slug:token>/confirm/",
        views.SubscribeConfirmView.as_view(),
        name="subscribe_confirm",
    ),
    path(
        "subscriptions/<slug:token>/",
        views.SubscriptionView.as_view(),
        name="subscriptions",
    ),
    path(
        "unsubscribe/<slug:token>/",
        views.UnsubscribeView.as_view(),
        name="unsubscribe",
    ),
    path(
        "archive/",
        views.ArchivesView.as_view(),
        name="archives",
    ),
    path(
        "archive/<slug:mailing_list_slug>/",
        views.ArchiveIndexView.as_view(),
        name="archive_index",
    ),
    path(
        "archive/<slug:mailing_list_slug>/<slug:message_slug>/",
        views.ArchiveView.as_view(),
        name="archive",
    ),
]
