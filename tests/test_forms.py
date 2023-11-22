from mailinglist import enum, forms, models


class TestSubscriptionForm:
    def test_initial_not_subscribed(self, subscription):
        form = forms.SubscriptionForm(user=subscription.user)
        _list_key = f"mailing-list_{subscription.mailing_list.pk}"
        assert _list_key in form.fields
        assert not form.fields[_list_key].initial

    def test_initial_subscribed(self, active_subscription):
        form = forms.SubscriptionForm(user=active_subscription.user)
        _list_key = f"mailing-list_{active_subscription.mailing_list.pk}"
        assert _list_key in form.fields
        assert form.fields[_list_key].initial

    def test_initial_global_deny(self, denied_subscription):
        form = forms.SubscriptionForm(user=denied_subscription.user)
        _list_key = f"mailing-list_{denied_subscription.mailing_list.pk}"
        assert _list_key in form.fields
        assert not form.fields[_list_key].initial
        assert form.fields["global-deny"].initial

    def test_can_subscribe(self, subscription):
        assert subscription.status == enum.SubscriptionStatusEnum.PENDING
        _list_key = f"mailing-list_{subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(user=subscription.user, data={_list_key: True})
        form.is_valid()
        form.save()
        subscription.refresh_from_db()
        assert subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED

    def test_can_unsubscribe(self, active_subscription):
        assert active_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED
        _list_key = f"mailing-list_{active_subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(
            user=active_subscription.user, data={_list_key: False}
        )
        form.is_valid()
        form.save()
        active_subscription.refresh_from_db()
        assert active_subscription.status == enum.SubscriptionStatusEnum.UNSUBSCRIBED

    def test_nothing_changes(self, active_subscription):
        assert active_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED
        _list_key = f"mailing-list_{active_subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(
            user=active_subscription.user, data={_list_key: True}
        )
        form.is_valid()
        form.save()
        active_subscription.refresh_from_db()
        assert active_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED

    def test_can_global_deny(self, active_subscription, user):
        assert active_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED
        _list_key = f"mailing-list_{active_subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(
            user=active_subscription.user, data={_list_key: True, "global-deny": True}
        )
        form.is_valid()
        form.save()
        assert models.GlobalDeny.objects.filter(user=user).exists()

    def test_can_un_global_deny(self, active_denied_subscription, denied_user):
        assert (
            active_denied_subscription.status == enum.SubscriptionStatusEnum.SUBSCRIBED
        )
        assert models.GlobalDeny.objects.filter(user=denied_user).exists()
        _list_key = f"mailing-list_{active_denied_subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(
            user=active_denied_subscription.user,
            data={_list_key: True, "global-deny": False},
        )
        form.is_valid()
        form.save()
        assert not models.GlobalDeny.objects.filter(user=denied_user).exists()

    def test_can_subscribe_nothing_happens(self, subscription):
        assert subscription.status == enum.SubscriptionStatusEnum.PENDING
        _list_key = f"mailing-list_{subscription.mailing_list.pk}"
        form = forms.SubscriptionForm(user=subscription.user, data={_list_key: False})
        form.is_valid()
        form.save(commit=False)
        subscription.refresh_from_db()
        assert subscription.status == enum.SubscriptionStatusEnum.PENDING

    def test_no_mailing_lists(self, user):
        form = forms.SubscriptionForm(user=user)
        assert len(form.fields) == 1
        assert "global-deny" in form.fields

    def test_no_mailing_lists_can_global_deny(self, user):
        assert not models.GlobalDeny.objects.filter(user=user).exists()
        form = forms.SubscriptionForm(user=user, data={"global-deny": True})
        assert len(form.fields) == 1
        assert "global-deny" in form.fields
        form.is_valid()
        form.save()
        assert models.GlobalDeny.objects.filter(user=user).exists()
