from mailinglist.services import SubmissionService

try:
    from celery import shared_task
except ImportError:
    pass
else:

    @shared_task
    def process_submissions():
        SubmissionService().process_submissions()
