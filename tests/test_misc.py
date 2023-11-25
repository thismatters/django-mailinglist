import sys
import builtins
from unittest.mock import patch
from importlib import reload

import pytest
from django.core.management import call_command


@patch("mailinglist.services.SubmissionService.process_submissions")
def test_process_submissions_managment_command(p_process):
    call_command("process_submissions")
    p_process.assert_called_once_with()


@pytest.fixture
def hide_celery(monkeypatch):
    import_orig = builtins.__import__

    def mocked_import(name, *args, **kwargs):
        if name == "celery":
            raise ImportError()
        return import_orig(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mocked_import)


@pytest.mark.usefixtures("hide_celery")
def test_process_submissions_no_celery():
    from mailinglist import tasks

    assert not hasattr(tasks, "process_submissions")


@patch("mailinglist.services.SubmissionService.process_submissions")
def test_process_submissions_celery(p_process):
    reload(sys.modules["mailinglist.tasks"])
    from mailinglist import tasks

    assert hasattr(tasks, "process_submissions")
    tasks.process_submissions()
    p_process.assert_called_once_with()
