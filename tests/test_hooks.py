from unittest.mock import patch, Mock
import pytest
from mailinglist.hooks import MailinglistDefaultHookset
from django.core.exceptions import ValidationError
from django.test import override_settings


class FileNameyThingy:
    def __init__(self, name):
        self.name = name


class TestMailinglistDefaultHookset:
    def test_create_user(self, db):
        user = MailinglistDefaultHookset().create_user(
            email="test@email.com",
            first_name="testy",
            last_name="mctestface",
        )
        assert user.email == "test@email.com"
        assert user.first_name == "testy"
        assert user.last_name == "mctestface"

    def test_create_user_exists(self, user):
        _user = MailinglistDefaultHookset().create_user(
            email=user.email,
            first_name=user.first_name + "asdfsadf",
            last_name=user.last_name + "zxcvzxcv",
        )
        assert _user.pk == user.pk
        assert _user.first_name == user.first_name  # didn't get updated
        assert _user.last_name == user.last_name  # didn't get updated

    @override_settings(MAILINGLIST_USER_MODEL="custom.override")
    @patch("django.apps.apps.get_model")
    def test_create_user_other_model(self, p_get_model):
        _user_model = Mock()
        _user_model.objects.get.return_value = "asdf"
        p_get_model.return_value = _user_model
        user = MailinglistDefaultHookset().create_user(
            email="test@email.com",
            first_name="testy",
            last_name="mctestface",
        )
        p_get_model.assert_called_once_with("custom.override")
        assert user == "asdf"

    @patch("mailinglist.hooks.EmailMultiAlternatives")
    def test_send_message(self, p_email_alternatives, message_attachment):
        _message = Mock()
        p_email_alternatives.return_value = _message
        MailinglistDefaultHookset().send_message(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            html_body="good <strong>strong</strong> body here!",
            attachments=[message_attachment],
            headers={"header": "yes"},
        )
        p_email_alternatives.assert_called_once_with(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            headers={"header": "yes"},
        )
        _message.attach_file.assert_called_once_with(message_attachment.file.path)
        _message.attach_alternative.assert_called_once_with(
            "good <strong>strong</strong> body here!", "text/html"
        )
        _message.send.assert_called_once_with()

    @patch("mailinglist.hooks.EmailMultiAlternatives")
    def test_send_message_no_attachments(self, p_email_alternatives):
        _message = Mock()
        p_email_alternatives.return_value = _message
        MailinglistDefaultHookset().send_message(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            html_body="good <strong>strong</strong> body here!",
            headers={"header": "yes"},
        )
        p_email_alternatives.assert_called_once_with(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            headers={"header": "yes"},
        )
        _message.attach_file.assert_not_called()
        _message.attach_alternative.assert_called_once_with(
            "good <strong>strong</strong> body here!", "text/html"
        )
        _message.send.assert_called_once_with()

    @patch("mailinglist.hooks.EmailMultiAlternatives")
    def test_send_message_no_html(self, p_email_alternatives, message_attachment):
        _message = Mock()
        p_email_alternatives.return_value = _message
        MailinglistDefaultHookset().send_message(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            attachments=[message_attachment],
            headers={"header": "yes"},
        )
        p_email_alternatives.assert_called_once_with(
            to="someone@email.com",
            body="good strong body here!",
            subject="[mailinglist] subject or whatever",
            from_email="loving@it.com",
            headers={"header": "yes"},
        )
        _message.attach_file.assert_called_once_with(message_attachment.file.path)
        _message.attach_alternative.assert_not_called()
        _message.send.assert_called_once_with()

    def test_message_attachment_file_validator_bad(self):
        with pytest.raises(ValidationError):
            MailinglistDefaultHookset().message_attachment_file_validator(
                FileNameyThingy(name="file.exe")
            )

    def test_message_attachment_file_validator_jpg(self):
        MailinglistDefaultHookset().message_attachment_file_validator(
            FileNameyThingy("long/path/t/o/file.jpg")
        )

    def test_message_attachment_file_validator_jpeg(self):
        MailinglistDefaultHookset().message_attachment_file_validator(
            FileNameyThingy("long/path/t/o/file.jpeg")
        )

    def test_message_attachment_file_validator_pdf(self):
        MailinglistDefaultHookset().message_attachment_file_validator(
            FileNameyThingy("long/path/t/o/file.pdf")
        )
