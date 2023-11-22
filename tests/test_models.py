def test_subscription_string(subscription):
    assert str(subscription) == f"{subscription.user} on {subscription.mailing_list}"


def test_message_string(message):
    assert str(message) == message.title


def test_message_subject(message):
    assert message.subject == f"[{message.mailing_list}] {message.title}"


def test_message_part_html(message_part):
    assert "<h1>This should render gloriously!</h1>" in message_part.html_text
    assert "<em>verbosely</em>" in message_part.html_text
    assert "<strong>exquisite</strong>" in message_part.html_text


def test_message_string(submission):
    assert (
        str(submission) == f"{submission.message} to {submission.message.mailing_list}"
    )
