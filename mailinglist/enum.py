from django_enumfield.enum import Enum


class SubscriptionStatusEnum(Enum):
    PENDING = 0
    SUBSCRIBED = 1
    UNSUBSCRIBED = 2

    __default__ = PENDING


class SubmissionStatusEnum(Enum):
    NEW = 0
    PENDING = 1
    SENDING = 2
    SENT = 3

    __default__ = NEW

    __transitions__ = {
        SENT: (SENDING,),
        SENDING: (PENDING,),
        PENDING: (NEW,),
    }
