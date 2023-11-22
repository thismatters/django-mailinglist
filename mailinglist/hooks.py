from django.apps import apps
from django.conf import settings
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

    def send_message(self, *, to, body, subject, from_email, html_body=None):
        msg = EmailMultiAlternatives(
            to=to, body=body, subject=subject, from_email=from_email
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
