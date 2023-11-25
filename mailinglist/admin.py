import logging

logger = logging.getLogger(__name__)
from functools import update_wrapper

from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.encoding import force_str
from django.views.decorators.clickjacking import xframe_options_sameorigin

from mailinglist import models
from mailinglist.admin_forms import ConfirmForm, ImportForm, SubmissionModelForm
from mailinglist.services import MessageService, SubmissionService, SubscriptionService


class ExtendibleModelAdminMixin:
    def _getobj(self, request, object_id):
        opts = self.model._meta

        try:
            obj = self.get_queryset(request).get(pk=unquote(object_id))
        except self.model.DoesNotExist:
            # Don't raise Http404 just yet, because we haven't checked
            # permissions yet. We don't want an unauthenticated user to
            # be able to determine whether a given object exists.
            obj = None

        if obj is None:
            raise Http404(
                f"{force_str(opts.verbose_name)} object with primary key "
                f"'{force_str(object_id)}' does not exist."
            )

        return obj

    def _wrap(self, view):
        def wrapper(*args, **kwargs):
            return self.admin_site.admin_view(view)(*args, **kwargs)

        return update_wrapper(wrapper, view)

    def _view_name(self, name):
        return f"{self.model._meta.app_label}_{self.model._meta.model_name}_{name}"


class ImmutableAdminMixin:
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ImmutableTabluarInline(ImmutableAdminMixin, admin.TabularInline):
    pass


@admin.register(models.MailingList)
class MailingListAdmin(admin.ModelAdmin):
    model = models.MailingList
    list_display = ("name", "slug", "visible")
    prepopulated_fields = {"slug": ("name",)}


class SubscriptionChangeInline(ImmutableTabluarInline):
    model = models.SubscriptionChange
    readonly_fields = ["from_status", "to_status", "changed"]


class SendingInline(ImmutableTabluarInline):
    model = models.Sending
    readonly_fields = ["submission", "sent"]


@admin.register(models.Subscription)
class SubscriptionAdmin(ExtendibleModelAdminMixin, admin.ModelAdmin):
    model = models.Subscription
    readonly_fields = ("token", "status")
    list_display = ("pk", "user", "mailing_list", "status")
    list_filter = ("mailing_list", "status")
    inlines = (SubscriptionChangeInline, SendingInline)
    actions = ("make_subscribed", "make_unsubscribed")

    def save_model(self, request, obj, form, change):
        if not change:
            SubscriptionService().subscribe(
                user=obj.user, mailing_list=obj.mailing_list
            )

    def has_change_permission(self, request, obj=None):
        return False

    def make_subscribed(self, request, queryset):
        # rows_updated = queryset.update(subscribed=True)
        service = SubscriptionService()
        rows_updated = 0
        for row in queryset:
            service._confirm_subscription(row)
            rows_updated += 1
        self.message_user(
            request, f"{rows_updated} users have been successfully subscribed."
        )

    make_subscribed.short_description = "Subscribe selected users"

    def make_unsubscribed(self, request, queryset):
        service = SubscriptionService()
        rows_updated = 0
        for row in queryset:
            service._confirm_unsubscription(row)
            rows_updated += 1
        self.message_user(
            request, f"{rows_updated} users have been successfully unsubscribed."
        )

    make_unsubscribed.short_description = "Unsubscribe selected users"

    """ Views """

    def subscribers_import(self, request):
        if not request.user.has_perm("mailinglist.add_subscription"):
            raise PermissionDenied()
        if request.POST:
            form = ImportForm(request.POST, request.FILES)
            if form.is_valid():
                request.session["addresses"] = form.get_addresses()
                request.session["mailing_list_pk"] = form.cleaned_data[
                    "mailing_list"
                ].pk

                confirm_url = reverse("admin:mailinglist_subscription_import_confirm")
                return HttpResponseRedirect(confirm_url)
        else:
            form = ImportForm()

        return render(
            request,
            "admin/mailinglist/subscription/import_form.html",
            {"form": form},
        )

    def subscribers_import_confirm(self, request):
        # If no addresses are in the session, start all over.

        if "addresses" not in request.session:
            import_url = reverse("admin:mailinglist_subscription_import")
            return HttpResponseRedirect(import_url)

        addresses = request.session["addresses"]
        mailing_list = models.MailingList.objects.get(
            pk=request.session["mailing_list_pk"]
        )

        logger.debug("Confirming addresses: %s", addresses)

        if request.POST:
            form = ConfirmForm(request.POST)
            if form.is_valid():
                try:
                    service = SubscriptionService()
                    for _user in addresses.values():
                        user = service.create_user(**_user)
                        service.force_subscribe(user=user, mailing_list=mailing_list)
                finally:
                    del request.session["addresses"]
                    del request.session["mailing_list_pk"]

                messages.success(
                    request,
                    f"{len(addresses)} subscriptions have been added.",
                )

                changelist_url = reverse("admin:mailinglist_subscription_changelist")
                return HttpResponseRedirect(changelist_url)
        else:
            form = ConfirmForm()

        return render(
            request,
            "admin/mailinglist/subscription/confirm_import_form.html",
            {"form": form, "subscribers": addresses},
        )

    """ URLs """

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path(
                "import/",
                self._wrap(self.subscribers_import),
                name=self._view_name("import"),
            ),
            path(
                "import/confirm/",
                self._wrap(self.subscribers_import_confirm),
                name=self._view_name("import_confirm"),
            ),
        ]

        return my_urls + urls


class UnchangingAdminMixin:
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.GlobalDeny)
class GlobalDenyAdmin(UnchangingAdminMixin, admin.ModelAdmin):
    model = models.GlobalDeny
    list_display = ("pk", "user", "created")
    date_hierarchy = "created"


class MessagePartInline(admin.StackedInline):
    model = models.MessagePart
    extra = 2


class MessageAttachmentInline(UnchangingAdminMixin, admin.TabularInline):
    model = models.MessageAttachment
    extra = 1
    fields = ("file",)


@admin.register(models.Message)
class MessageAdmin(ExtendibleModelAdminMixin, admin.ModelAdmin):
    model = models.Message
    prepopulated_fields = {"slug": ("title",)}
    list_display = ("title", "slug", "mailing_list", "created")
    inlines = (MessagePartInline, MessageAttachmentInline)

    """ Views """

    def preview(self, request, object_id):
        return render(
            request,
            "admin/mailinglist/preview.html",
            {
                "message": self._getobj(request, object_id),
                "attachments": models.MessageAttachment.objects.filter(
                    message_id=object_id
                ),
            },
        )

    @xframe_options_sameorigin
    def preview_html(self, request, object_id):
        message = self._getobj(request, object_id)
        html_body = MessageService().prepare_message_preview_html(message=message)
        return HttpResponse(html_body)

    @xframe_options_sameorigin
    def preview_text(self, request, object_id):
        message = self._getobj(request, object_id)
        body = MessageService().prepare_message_preview(message=message)
        return HttpResponse(body, content_type="text/plain")

    def submit(self, request, object_id):
        submission = SubmissionService().submit_message(
            self._getobj(request, object_id)
        )

        change_url = reverse(
            "admin:mailinglist_submission_change", args=[submission.id]
        )

        return HttpResponseRedirect(change_url)

    """ URLs """

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path(
                "<object_id>/preview/",
                self._wrap(self.preview),
                name=self._view_name("preview"),
            ),
            path(
                "<object_id>/preview/html/",
                self._wrap(self.preview_html),
                name=self._view_name("preview_html"),
            ),
            path(
                "<object_id>/preview/text/",
                self._wrap(self.preview_text),
                name=self._view_name("preview_text"),
            ),
            path(
                "<object_id>/submit/",
                self._wrap(self.submit),
                name=self._view_name("submit"),
            ),
        ]

        return my_urls + urls


@admin.register(models.Submission)
class SubmissionAdmin(ExtendibleModelAdminMixin, admin.ModelAdmin):
    form = SubmissionModelForm
    model = models.Submission
    list_display = ("__str__", "status", "published")
    readonly_fields = ("published", "status")
    exclude = ("sendings",)
    actions = ("publish",)

    def publish(self, request, queryset):
        service = SubmissionService()
        rows_updated = 0
        for row in queryset:
            service.publish(row)
            rows_updated += 1
        self.message_user(request, f"{rows_updated} submissions have been published.")

    def publish_view(self, request, object_id):
        service = SubmissionService()
        service.publish(self._getobj(request, object_id))

        messages.success(request, f"Submission {object_id} has been published.")

        changelist_url = reverse("admin:mailinglist_submission_changelist")
        return HttpResponseRedirect(changelist_url)

    def get_urls(self):
        urls = super().get_urls()

        my_urls = [
            path(
                "<object_id>/publish/",
                self._wrap(self.publish_view),
                name=self._view_name("publish"),
            ),
        ]

        return my_urls + urls
