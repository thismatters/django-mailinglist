import logging

logger = logging.getLogger(__name__)

import io
from csv import DictReader

from django import forms
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from mailinglist.models import Subscription


class AddressList:
    """List with unique addresses."""

    def __init__(self, mailing_list, ignore_errors=False):
        self.mailing_list = mailing_list
        self.ignore_errors = ignore_errors
        self.addresses = {}

    class OverLongEmailException(Exception):
        pass

    class InvalidEmailException(Exception):
        pass

    def _validate_email(self, email):
        try:
            email = check_field(
                field_name="email", value=email.lower(), ignore_errors=False
            )
        except forms.ValidationError as e:
            logger.warning(str(e))
            raise self.OverLongEmailException

        try:
            validate_email(email)
        except ValidationError:
            logger.warning(f"Entry '{email}' does not contain a valid e-mail address")
            raise self.InvalidEmailException

    def add(
        self,
        *,
        email,
        first_name=None,
        last_name=None,
        location="unknown location",
        **kwargs,
    ):
        """Add name to list."""

        logger.debug(f"Going to add {first_name} {last_name} <{email}>")
        try:
            self._validate_email(email)
        except self.OverLongEmailException:
            if not self.ignore_errors:
                raise forms.ValidationError(
                    f"Entry '{first_name} {last_name}' at {location} has an "
                    "overlong email address."
                )
            return
        except self.InvalidEmailException:
            if not self.ignore_errors:
                raise forms.ValidationError(
                    f"Entry '{first_name} {last_name}' at {location} does "
                    "not contain a valid email address."
                )
            return

        first_name = check_field(
            field_name="first_name", value=first_name, ignore_errors=self.ignore_errors
        )
        last_name = check_field(
            field_name="last_name", value=last_name, ignore_errors=self.ignore_errors
        )

        if email in self.addresses:
            logger.warning(
                f"Entry '{first_name} {last_name}' contains a duplicate entry "
                f"at {location}."
            )

            if not self.ignore_errors:
                raise forms.ValidationError(
                    f"The address file contains duplicate entries for '{email}'."
                )
            return

        if subscription_exists(self.mailing_list, email):
            logger.warning(f"Entry '{email}' is already subscribed to at {location}.")

            if not self.ignore_errors:
                raise forms.ValidationError("Some entries are already subscribed to.")
            return

        self.addresses[email] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }


def subscription_exists(mailing_list, email):
    """
    Return wheter or not a subscription exists.
    """
    qs = Subscription.objects.filter(
        mailing_list__id=mailing_list.id, user__email__iexact=email
    )

    return qs.exists()


def check_field(*, field_name, value, ignore_errors=False):
    """
    Check (length of) value address.
    """

    logger.debug(f"Checking {field_name} '{value}'")
    if value is None:
        return None

    max_length = (
        apps.get_model(settings.MAILINGLIST_USER_MODEL)
        ._meta.get_field(field_name)
        .max_length
    )

    # Get rid of leading/trailing spaces
    value = value.strip()

    if len(value) <= max_length or ignore_errors:
        return value[:max_length]
    else:
        raise forms.ValidationError(
            f"{field_name} value '{value}' too long, maximum length is "
            f"{max_length} characters."
        )


def parse_csv(csv_file, mailing_list, ignore_errors=False):
    """
    Parse addresses from CSV file-object into mailing list.

    Returns a dictionary mapping email addresses into Subscription objects.
    """
    address_list = AddressList(mailing_list, ignore_errors)
    _csv_file = io.StringIO(csv_file.read().decode())
    reader = DictReader(_csv_file)
    for idx, row in enumerate(reader):
        address_list.add(**row, location=f"line {idx}")

    return address_list.addresses
