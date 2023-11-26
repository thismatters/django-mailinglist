from unittest.mock import patch
from mailinglist.models import hookset_validation_wrapper


def test_subscription_string(subscription):
    assert str(subscription) == f"{subscription.user} on {subscription.mailing_list}"


def test_message_string(message):
    assert str(message) == message.title


def test_message_part_html(message_part):
    assert "<h1>This should render gloriously!</h1>" in message_part.html_text
    assert "<em>verbosely</em>" in message_part.html_text
    assert "<strong>exquisite</strong>" in message_part.html_text


def test_submission_string(submission):
    assert (
        str(submission) == f"{submission.message} to {submission.message.mailing_list}"
    )


def test_message_attachment_string(message_attachment):
    assert (
        str(message_attachment)
        == f"{message_attachment.filename} on {message_attachment.message.title}"
    )


def test_message_attachment_file_name(message_attachment):
    assert message_attachment.filename == "testing.jpg"


def test_message_attachment_save(message_attachment):
    message_attachment.filename = "something_else.jpg"
    message_attachment.save()
    message_attachment.refresh_from_db()
    assert message_attachment.filename == "something_else.jpg"


@patch("mailinglist.models.hookset.message_attachment_file_validator")
def test_hookset_validation_wrapper(p_validator):
    hookset_validation_wrapper(True)
    p_validator.assert_called_once_with(True)
