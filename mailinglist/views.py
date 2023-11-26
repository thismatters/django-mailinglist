from django.http import Http404
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import DetailView, FormView, ListView, TemplateView
from django.views.generic.detail import (
    SingleObjectMixin,
    SingleObjectTemplateResponseMixin,
)

from mailinglist import models
from mailinglist.conf import settings
from mailinglist.forms import SubscribeForm, SubscriptionForm
from mailinglist.services import SubscriptionService


class DetailFormView(
    SingleObjectTemplateResponseMixin,
    SingleObjectMixin,
    FormView,
):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)


class SubscribeFormMixin:
    form_class = SubscribeForm

    def get_initial(self):
        initial = super().get_initial()
        if not self.request.user.is_anonymous:
            initial.update(
                {
                    "email": self.request.user.email,
                    "first_name": self.request.user.first_name,
                    "last_name": self.request.user.last_name,
                }
            )
        return initial

    def form_valid(self, form):
        service = SubscriptionService()
        user = service.create_user(
            email=form.cleaned_data["email"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
        )
        service.subscribe(user=user, mailing_list=self.get_object())
        return super().form_valid(form)


class SubscribeView(SubscribeFormMixin, DetailFormView):
    """Allows users to subscrbe to a mailing list."""

    template_name = "mailinglist/web/subscribe.html"
    queryset = models.MailingList.objects.all()
    slug_url_kwarg = "mailing_list_slug"

    def get_success_url(self):
        return reverse("mailinglist:subscribe_success", kwargs=self.kwargs)


class GlobalDenyView(SubscribeFormMixin, FormView):
    """Allows users to subscrbe to the global deny list."""

    template_name = "mailinglist/web/global_unsubscribe.html"

    def get_success_url(self):
        return reverse("mailinglist:global_deny_success")

    def get_object(self):
        return None


class SubscribeSuccessView(DetailView):
    """Provides user with insight about subscription, namely whether or
    not they will need to confirm their email address"""

    template_name = "mailinglist/web/subscribe_success.html"
    queryset = models.MailingList.objects.all()
    slug_url_kwarg = "mailing_list_slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "requires_confirmation": settings.MAILINGLIST_CONFIRM_EMAIL_SUBSCRIBE,
            }
        )
        return context


class SubscriptionView(DetailFormView):
    """Allows the user to view what mailing lists they are subscribed to."""

    # Since the subscription might not point to a user who can log in to the
    #  site, we must not rely on `request.user`, we will use the subscription token
    #  as a bearer token and allow the other subscriptions that the
    #  `subscription.user` has.
    template_name = "mailinglist/web/subscriptions.html"
    form_class = SubscriptionForm
    queryset = models.Subscription.objects.all()
    slug_url_kwarg = "token"
    slug_field = "token"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        instance = self.get_object()
        kwargs.update({"user": instance.user})
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("mailinglist:subscriptions", kwargs=self.kwargs)


class IsSubscriptionMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _is_subcription = self.subscription is not None
        _is_global_unsubcription = False
        if _is_subcription and self.subscription.mailing_list is None:
            _is_global_unsubcription = True
        context.update(
            {
                "token": self.kwargs.get("token"),
                "is_global_unsubscription": _is_global_unsubcription,
                "is_subscription": _is_subcription,
            }
        )
        return context


class SubscribeConfirmView(IsSubscriptionMixin, TemplateView):
    """Reachable when user clicks on link in confirmation message, tells
    user that they are fully subscribed."""

    template_name = "mailinglist/web/subscribe_confirm.html"

    # Do not want _any_ subscription data leaking into the UI, so keep
    #   it a simple template view
    def get(self, request, *args, **kwargs):
        self.subscription = SubscriptionService().confirm_subscription(
            token=kwargs.get("token")
        )
        return super().get(request, *args, **kwargs)


class UnsubscribeView(IsSubscriptionMixin, TemplateView):
    """Reachable when user clicks unsubscribe link in any sent message.
    Deactivates user's subscription to the mailing list and provides link
    to user's subscriptions page"""

    # Do not want _any_ subscription data leaking into the UI, so keep
    #   it a simple template view
    template_name = "mailinglist/web/unsubscribe.html"

    def get(self, request, *args, **kwargs):
        self.subscription = SubscriptionService().unsubscribe(token=kwargs.get("token"))
        return super().get(request, *args, **kwargs)


class ArchivesView(ListView):
    """Allows user to browse messages published on a mailing list."""

    template_name = "mailinglist/web/archive/archives.html"
    queryset = models.MailingList.objects.filter(visible=True)


class ArchiveIndexView(DetailView):
    """Allows user to browse messages published on a mailing list."""

    template_name = "mailinglist/web/archive/index.html"
    queryset = models.MailingList.objects.filter(visible=True)
    slug_url_kwarg = "mailing_list_slug"


class ArchiveView(DetailView):
    """Allows user to view messages published on a mailing list."""

    template_name = "mailinglist/web/archive/message.html"
    queryset = models.Message.objects.filter(mailing_list__visible=True)

    def get_object(self, **kwargs):
        qs = super().get_queryset(**kwargs)
        try:
            return qs.get(
                slug=self.kwargs.get("message_slug"),
                mailing_list__slug=self.kwargs.get("mailing_list_slug"),
                submission__published__lte=now(),
            )
        except models.Message.DoesNotExist:
            raise Http404("No message like that")
