from django import forms

from mailinglist import models
from mailinglist.enum import SubscriptionStatusEnum
from mailinglist.services import SubscriptionService


class SubscribeForm(forms.Form):
    """Basic subscription details."""

    email = forms.EmailField(label="Email:")
    first_name = forms.CharField(label="First name:")
    last_name = forms.CharField(label="Last name:", required=False)
    are_you_sure = forms.BooleanField(label="Are you sure?")


class SubscriptionForm(forms.Form):
    """Dynamically generates a series of checkboxes for each visible
    mailing list so that users can subscribe at their will. Also includes
    checkbox for global unsubscribe."""

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        subscriptions = user.subscriptions.filter(
            status=SubscriptionStatusEnum.SUBSCRIBED
        )
        self.user = user
        self.subscribed_lists = {
            s.mailing_list.pk: s for s in subscriptions if s.mailing_list
        }
        for mailing_list in models.MailingList.objects.filter(visible=True):
            self.fields[f"mailing-list_{mailing_list.pk}"] = forms.BooleanField(
                required=False,
                initial=mailing_list.pk in self.subscribed_lists,
                label=mailing_list.name,
            )
        self.fields["global-deny"] = forms.BooleanField(
            required=False,
            initial=hasattr(user, "mailinglist_deny"),
            label="Block all mailinglists from sending to me!",
        )

    def save(self, commit=True):
        if not commit:
            return
        if self.cleaned_data.get("global-deny", False):
            models.GlobalDeny.objects.get_or_create(user=self.user)
        else:
            models.GlobalDeny.objects.filter(user=self.user).delete()
        service = SubscriptionService()
        for mailing_list in models.MailingList.objects.filter(visible=True):
            wants = self.cleaned_data.get(f"mailing-list_{mailing_list.pk}", False)
            if wants and mailing_list.pk not in self.subscribed_lists:
                # create subscription
                service.subscribe(
                    user=self.user, mailing_list=mailing_list, force_confirm=True
                )
            if not wants and mailing_list.pk in self.subscribed_lists:
                service._confirm_unsubscription(self.subscribed_lists[mailing_list.pk])
