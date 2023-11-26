from base64 import b64decode
from datetime import timedelta
from random import randint

import pytest
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from mailinglist import models
from mailinglist.enum import SubmissionStatusEnum, SubscriptionStatusEnum


@pytest.fixture
def user_factory(db):
    def _user_factory(**kwargs):
        rand = randint(10000, 99999)
        user = get_user_model().objects.create(
            first_name="Test",
            last_name="User",
            email=f"user-{rand}@somedomain.test",
            username=f"testuser-{rand}",
            **kwargs,
        )
        return user

    return _user_factory


@pytest.fixture
def user(user_factory):
    user = user_factory()
    yield user
    user.delete()


@pytest.fixture
def denied_user(user_factory):
    user = user_factory()
    gdl, _ = models.GlobalDeny.objects.get_or_create(user=user)
    yield user
    gdl.delete()
    user.delete()


@pytest.fixture
def mailing_list(db):
    mailing_list = models.MailingList.objects.create(
        name="test list",
        slug="test-list",
        email="test@test.test",
        sender="Some Person",
    )
    yield mailing_list
    mailing_list.delete()


@pytest.fixture
def subscription(user, mailing_list):
    subscription = models.Subscription.objects.create(
        user=user,
        mailing_list=mailing_list,
        token="asdfasdfsadferrreasdfzxcvzxcv",
    )
    yield subscription
    subscription.delete()


@pytest.fixture
def denied_subscription(denied_user, mailing_list):
    subscription = models.Subscription.objects.create(
        user=denied_user,
        mailing_list=mailing_list,
        token="asdfasdfsadferrreasdfzxcvzxcv",
    )
    yield subscription
    subscription.delete()


@pytest.fixture
def message(mailing_list):
    rand = randint(10000, 99999)
    message = models.Message.objects.create(
        slug=f"test-{rand}",
        title="test message",
        mailing_list=mailing_list,
    )
    yield message
    message.delete()


@pytest.fixture
def message_part(message):
    message_part = models.MessagePart.objects.create(
        message=message,
        heading="test message part",
        order=0,
        text="""# This should render gloriously!

With paragraphs of _verbosely_ **exquisite** text!

* and lists
* of
* some
    * import
    * and
    * quality
""",
    )
    yield message_part
    message_part.delete()


@pytest.fixture
def fake_image():
    _image = "/9j/4AAQSkZJRgABAQEBLAEsAAD/2Q=="
    image_data = b64decode(_image)
    image_name = "testing.jpg"
    return ContentFile(image_data, image_name)


@pytest.fixture
def message_attachment(message, fake_image):
    message_attachment = models.MessageAttachment.objects.create(
        message=message,
        file=fake_image,
    )
    yield message_attachment
    message_attachment.delete()


@pytest.fixture
def submission(message):
    submission = models.Submission.objects.create(
        message=message,
    )
    yield submission
    submission.delete()


@pytest.fixture
def published_submission(message):
    submission = models.Submission.objects.create(
        message=message,
    )
    submission.published = now() - timedelta(minutes=1)
    submission.status = SubmissionStatusEnum.PENDING
    submission.save()
    yield submission
    submission.delete()


@pytest.fixture
def sent_submission(message):
    submission = models.Submission.objects.create(
        message=message,
    )
    submission.published = now() - timedelta(minutes=1)
    submission.status = SubmissionStatusEnum.PENDING
    submission.status = SubmissionStatusEnum.SENDING
    submission.status = SubmissionStatusEnum.SENT
    submission.save()
    yield submission
    submission.delete()


@pytest.fixture
def active_subscription(subscription):
    subscription.status = SubscriptionStatusEnum.SUBSCRIBED
    subscription.save()
    yield subscription
    subscription.status = SubscriptionStatusEnum.PENDING
    subscription.save()


@pytest.fixture
def active_denied_subscription(denied_subscription):
    denied_subscription.status = SubscriptionStatusEnum.SUBSCRIBED
    denied_subscription.save()
    yield denied_subscription
    denied_subscription.status = SubscriptionStatusEnum.PENDING
    denied_subscription.save()


@pytest.fixture
def address_file():
    _file = ContentFile(
        "first_name,last_name,email\nSeymore,Lastman,last@email.com", "somefile.csv"
    )
    _file.content_type = "text/csv"
    return _file
