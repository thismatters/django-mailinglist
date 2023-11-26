from unittest.mock import patch, Mock
import pytest
from mailinglist.hooks import MailinglistDefaultHookset
from django.core.exceptions import ValidationError


class FileNameyThingy:
    def __init__(self, name):
        self.name = name


class TestMailinglistDefaultHookset:
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
