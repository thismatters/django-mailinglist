from django.db import models
from django.utils.timezone import now
from django_enumfield.enum import EnumField
from markdown import markdown

from mailinglist.conf import settings
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


class MailingList(models.Model):
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
        return f'"{self.sender}" <{self.email}>'

    @property
    def published_messages(self):
        return self.messages.filter(submission__published__lte=now()).distinct()


class GlobalDeny(models.Model):
    """Users with instances here will not receive mailing list messages"""

    user = models.OneToOneField(
        settings.MAILINGLIST_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mailinglist_deny",
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)


class Subscription(models.Model):
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
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    from_status = EnumField(SubscriptionStatusEnum, null=True, blank=True)
    to_status = EnumField(SubscriptionStatusEnum)
    changed = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    title = models.CharField(max_length=128)
    slug = models.SlugField()
    mailing_list = models.ForeignKey(
        MailingList, on_delete=models.CASCADE, related_name="messages"
    )
    created = models.DateTimeField(auto_now_add=True, editable=False)
    modified = models.DateTimeField(auto_now=True, editable=False)

    @property
    def subject(self):
        return f"[{self.mailing_list}] {self.title}"

    def __str__(self):
        return self.title

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "mailing_list"], name="unique_slug_per_mailing_list"
            )
        ]


class MessagePart(models.Model):
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
        constraints = [
            models.UniqueConstraint(
                fields=["message", "order"], name="unique_order_per_message"
            )
        ]


# TODO: attachments


class Submission(models.Model):
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
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT)
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    sent = models.DateTimeField(auto_now_add=True)
