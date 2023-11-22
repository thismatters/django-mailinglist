import pytest
from mailinglist.conf import load_path_attr, MailinglistAppConf
from django.core.exceptions import ImproperlyConfigured


def test_load_path_attr():
    with pytest.raises(ImproperlyConfigured):
        load_path_attr("poopy.butthole")


def test_load_path_attr_other():
    with pytest.raises(ImproperlyConfigured):
        load_path_attr("mailinglist.butthole")


class TestMailinglistAppConf:
    def test_configure_default_sender_email(self):
        assert (
            MailinglistAppConf().configure_default_sender_email("something")
            == "something"
        )

    def test_configure_default_sender_email_fails(self):
        with pytest.raises(ImproperlyConfigured):
            MailinglistAppConf().configure_default_sender_email(None)

    def test_configure_base_url(self):
        assert MailinglistAppConf().configure_base_url("something") == "something"

    def test_configure_base_url_fails(self):
        with pytest.raises(ImproperlyConfigured):
            MailinglistAppConf().configure_base_url(None)
