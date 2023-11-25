from django.core.management.base import BaseCommand

from mailinglist.services import SubmissionService


class Command(BaseCommand):
    help = "Send published submissions."

    def handle(self, *args, **options):
        SubmissionService().process_submissions()
