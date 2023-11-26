from django.conf import settings

from mailinglist.hooks import MailinglistDefaultHookset


class MyCustomHookset(MailinglistDefaultHookset):
    # be sure you inherit the default hookset!
    def create_user(self, *, email, first_name, last_name):
        user_model = apps.get_model(settings.MAILINGLIST_USER_MODEL)
        # if the email field on your user model were encrypted then you
        #   wouldn't be able to `get` the instance directly.
        _email = email.lower()
        for user in user_model.objects.all():
            if user.email == _email:
                return user
        user = user_model.objects.create(
            username=f"user{hash(email)}",
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        return user
