from unittest.mock import patch, call
from django.core.exceptions import ValidationError
import pytest
import io

from mailinglist.addressimport.parsers import AddressList, parse_csv


@pytest.fixture
def address_list(mailing_list):
    return AddressList(mailing_list=mailing_list)


@pytest.fixture
def address_list_quiet(mailing_list):
    return AddressList(mailing_list=mailing_list, ignore_errors=True)


class TestAddressList:
    def test_add(self, address_list):
        address_list.add(email="test@good.test", first_name="Test", last_name="Good")
        assert "test@good.test" in address_list.addresses
        assert address_list.addresses["test@good.test"] == {
            "email": "test@good.test",
            "first_name": "Test",
            "last_name": "Good",
        }

    def test_add_bad_email_quiet(self, address_list_quiet):
        address_list_quiet.add(email="bad_email", first_name="Test", last_name="Good")
        assert "bad_email" not in address_list_quiet.addresses

    def test_add_bad_email(self, address_list):
        with pytest.raises(ValidationError):
            address_list.add(email="bad_email", first_name="Test", last_name="Good")
        assert "bad_email" not in address_list.addresses

    def test_add_email_overlong_quiet(self, address_list_quiet):
        address_list_quiet.add(
            email="long@email.com" + ("m" * 300), first_name="Test", last_name="Good"
        )
        assert "long@email.com" not in address_list_quiet.addresses

    def test_add_email_overlong(self, address_list):
        with pytest.raises(ValidationError):
            address_list.add(
                email="long@email.com" + ("m" * 300),
                first_name="Test",
                last_name="Good",
            )
        assert not address_list.addresses

    def test_add_first_name_overlong_quiet(self, address_list_quiet):
        address_list_quiet.add(
            email="long@email.com",
            first_name="Test" + ("m" * 300),
            last_name="Good",
        )
        assert "long@email.com" in address_list_quiet.addresses
        assert len(address_list_quiet.addresses["long@email.com"]["first_name"]) < 300

    def test_add_first_name_overlong(self, address_list):
        with pytest.raises(ValidationError):
            address_list.add(
                email="long@email.com",
                first_name="Test" + ("m" * 300),
                last_name="Good",
            )

    def test_add_last_name_overlong_quiet(self, address_list_quiet):
        address_list_quiet.add(
            email="long@email.com",
            first_name="Test",
            last_name="Good" + ("m" * 300),
        )
        assert "long@email.com" in address_list_quiet.addresses
        assert len(address_list_quiet.addresses["long@email.com"]["last_name"]) < 300

    def test_add_last_name_overlong(self, address_list):
        with pytest.raises(ValidationError):
            address_list.add(
                email="long@email.com",
                first_name="Test",
                last_name="Good" + ("m" * 300),
            )
        assert not address_list.addresses

    def test_add_no_last_name(self, address_list):
        address_list.add(
            email="good@email.com",
            first_name="Test",
            last_name=None,
        )
        assert "good@email.com" in address_list.addresses
        assert address_list.addresses["good@email.com"] == {
            "email": "good@email.com",
            "first_name": "Test",
            "last_name": None,
        }

    def test_add_duplicate_quiet(self, address_list_quiet):
        address_list_quiet.add(
            email="good@email.com",
            first_name="Test",
            last_name=None,
        )
        address_list_quiet.add(
            email="good@email.com",
            first_name="Other",
            last_name="Test",
        )
        assert "good@email.com" in address_list_quiet.addresses
        assert address_list_quiet.addresses["good@email.com"] == {
            "email": "good@email.com",
            "first_name": "Test",
            "last_name": None,
        }

    def test_add_duplicate(self, address_list):
        address_list.add(
            email="good@email.com",
            first_name="Test",
            last_name=None,
        )
        with pytest.raises(ValidationError):
            address_list.add(
                email="good@email.com",
                first_name="Other",
                last_name="Test",
            )

    def test_add_duplicate_subscription(self, address_list, subscription):
        with pytest.raises(ValidationError):
            address_list.add(
                email=subscription.user.email,
                first_name="Test",
                last_name=None,
            )

    def test_add_duplicate_subscription_quiet(self, address_list_quiet, subscription):
        address_list_quiet.add(
            email=subscription.user.email,
            first_name="Test",
            last_name=None,
        )
        assert subscription.user.email not in address_list_quiet.addresses


class TestParseCsv:
    @patch.object(AddressList, "add")
    def test_parse(self, p_add, mailing_list):
        _file = io.BytesIO(
            b"""first_name,last_name,email
test,person,person@person.us
another,human,identity@real.yes"""
        )
        parse_csv(_file, mailing_list)
        p_add.assert_has_calls(
            [
                call(
                    first_name="test",
                    last_name="person",
                    email="person@person.us",
                    location="line 0",
                ),
                call(
                    first_name="another",
                    last_name="human",
                    email="identity@real.yes",
                    location="line 1",
                ),
            ]
        )
