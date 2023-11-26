import os

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives


class MailinglistDefaultHookset:
    def create_user(self, *, email, first_name, last_name):
        user_model = apps.get_model(settings.MAILINGLIST_USER_MODEL)
        try:
            user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            user = user_model.objects.create(
                username=f"user{hash(email)}",
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
        return user

    def send_message(
        self,
        *,
        to,
        body,
        subject,
        from_email,
        html_body=None,
        attachments=None,
        headers=None,
    ):
        message = EmailMultiAlternatives(
            to=to,
            body=body,
            subject=subject,
            from_email=from_email,
            headers=headers,
        )
        _attachments = attachments or []

        for attachment in _attachments:
            message.attach_file(attachment.file.path)

        if html_body is not None:
            message.attach_alternative(html_body, "text/html")
        message.send()

    def message_attachment_file_validator(self, value):
        valid_file_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]
        ext = os.path.splitext(value.name)[-1]
        if ext.lower() not in valid_file_extensions:
            raise ValidationError(
                f"File must have "
                f"{' or '.join([f'{e!r}' for e in valid_file_extensions]) } "
                "as its extension"
            )
