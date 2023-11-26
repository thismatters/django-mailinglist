from pathlib import Path

from django.db import models
from django.utils.timezone import now
from django_enumfield.enum import EnumField
from markdown import markdown

from mailinglist.conf import hookset, settings
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


class MailingList(models.Model):
    """The fundamental model for sending messages. A mailing list can be
    subscribed to by users and is required for composing (and therefore
    sending) messages"""

    name = models.CharField(max_length=128)
    slug = models.SlugField(db_index=True, unique=True)
    email = models.EmailField(help_text="Sender e-mail")
    sender = models.CharField(max_length=200, help_text="Sender name")
    visible = models.BooleanField(default=True, db_index=True)
    send_html = models.BooleanField(
        default=True,
        help_text="Whether or not to send HTML versions of e-mails.",
    )

    def __str__(self):
        return self.name

    @property
    def sender_tag(self):
        """Mailing list sender formatted in the standard way for email addresses::
        "FirstName LastName" <email>
        """
        return f'"{self.sender}" <{self.email}>'

    @property
    def published_messages(self):
        """All messages that have been published to this mailing list prior to now"""
        return self.messages.filter(submission__published__lte=now()).distinct()


class GlobalDeny(models.Model):
    """Users with instances here will not receive mailing list messages."""

    user = models.OneToOneField(
        settings.MAILINGLIST_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailinglist_deny",
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)


class Subscription(models.Model):
    """The means by which a user subscribes to receive mailing list messages.
    **Do not create instances of this yourself, use the methods in
    ``mailinglist.services.SubscriptionService`` for managing subscriptions!**"""

    user = models.ForeignKey(
        settings.MAILINGLIST_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    # token used for verification of subscription events
    token = models.CharField(max_length=45)
    mailing_list = models.ForeignKey(
        MailingList,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        null=True,
    )
    status = EnumField(SubscriptionStatusEnum)

    def __str__(self):
        return f"{self.user} on {self.mailing_list}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "mailing_list"], name="unique_user_per_mailing_list"
            )
        ]


class SubscriptionChange(models.Model):
    """Tracks changes to subscriptions so that subscriptions/unsubscriptions
    can be audited. Instances of this model are managed by
    ``mailinglist.services.SubscriptionService``."""

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    from_status = EnumField(SubscriptionStatusEnum, null=True, blank=True)
    to_status = EnumField(SubscriptionStatusEnum)
    changed = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    """The messages which will be sent to subscribed users. Comprised of
    ``MessagePart`` and ``MessageAttachment`` instances."""

    title = models.CharField(max_length=128)
    slug = models.SlugField()
    mailing_list = models.ForeignKey(
        MailingList, on_delete=models.CASCADE, related_name="messages"
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "mailing_list"], name="unique_slug_per_mailing_list"
            )
        ]


class MessagePart(models.Model):
    """The text content of a ``Message``."""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="message_parts"
    )
    heading = models.CharField(max_length=128)
    order = models.PositiveSmallIntegerField()
    text = models.TextField()
    # TODO: images!

    @property
    def html_text(self):
        return markdown(self.text)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "order"], name="unique_order_per_message"
            )
        ]


def attachment_upload_to(instance, filename):
    return Path(
        "mailinglist-static",
        "attachments",
        str(instance.message.pk),
        filename,
    )


def hookset_validation_wrapper(value):
    # Model field validators are referenced in migration files. This wrapper
    #  allows the hookset to be dynamic without causing chaos in the migration
    #  file.
    hookset.message_attachment_file_validator(value)


class MessageAttachment(models.Model):
    """The file content of a ``Message``"""

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(
        upload_to=attachment_upload_to,
        verbose_name="attachment",
        validators=[hookset_validation_wrapper],
    )
    filename = models.CharField(max_length=256, null=False)

    def __str__(self):
        return f"{self.filename} on {self.message.title}"

    def save(self, **kwargs):
        # The file name may be mangled by name collisions upon save,
        #   capture the original filename prior to the first save.
        if not self.pk:
            self.filename = str(self.file)
        super().save(**kwargs)


class Submission(models.Model):
    """The means by which ``Message`` instances are published and sent."""

    message = models.OneToOneField(
        Message, on_delete=models.PROTECT, related_name="submission"
    )
    exclude = models.ManyToManyField(
        Subscription,
        blank=True,
        help_text=(
            "Subscriptions to exclude from mailing, all other "
            "subscribers will receive message"
        ),
    )
    published = models.DateTimeField(null=True, blank=True)
    status = EnumField(SubmissionStatusEnum)
    sendings = models.ManyToManyField(
        Subscription, through="Sending", related_name="sendings"
    )

    def __str__(self):
        return f"{self.message} to {self.message.mailing_list}"


class Sending(models.Model):
    """Tracks the sending of each ``Submission`` to each individual
    ``Subscription``. Provided for audit, as well as to allow interruped
    send jobs to be resumed without double-sending to any users."""

    submission = models.ForeignKey(Submission, on_delete=models.PROTECT)
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    sent = models.DateTimeField(auto_now_add=True)
