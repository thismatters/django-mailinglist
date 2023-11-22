from unittest.mock import patch
import pytest
from django.forms import ValidationError
from django.core.files.base import ContentFile
from mailinglist.admin_forms import ImportForm, ConfirmForm, SubmissionModelForm


class TestImportForm:
    def test_clean_missing_data_address_file(self, mailing_list):
        _data = {"ignore_errors": True, "mailing_list": mailing_list}
        form = ImportForm()
        form.cleaned_data = _data
        ret = form.clean()
        assert ret == _data
        assert not hasattr(form, "addresses")

    def test_clean_missing_data_ignore_errors(self, mailing_list):
        _data = {"address_file": True, "mailing_list": mailing_list}
        form = ImportForm()
        form.cleaned_data = _data
        ret = form.clean()
        assert not hasattr(form, "addresses")

    def test_clean_missing_data_ignore_errors(self):
        _data = {"address_file": True, "ignore_errors": True}
        form = ImportForm()
        form.cleaned_data = _data
        ret = form.clean()
        assert not hasattr(form, "addresses")

    def test_clean_bad_file_extension(self, mailing_list):
        _file = ContentFile(
            "first_name,last_name,email\nSeymore,Lastman,last@email.com", "somefile.bat"
        )
        _file.content_type = "text/csv"
        _data = {
            "address_file": _file,
            "ignore_errors": True,
            "mailing_list": mailing_list,
        }
        form = ImportForm()
        form.cleaned_data = _data
        with pytest.raises(ValidationError):
            ret = form.clean()
        assert not hasattr(form, "addresses")

    def test_clean_bad_file_content_type(self, mailing_list):
        _file = ContentFile(
            "first_name,last_name,email\nSeymore,Lastman,last@email.com", "somefile.csv"
        )
        _file.content_type = "text/excel"
        _data = {
            "address_file": _file,
            "ignore_errors": True,
            "mailing_list": mailing_list,
        }
        form = ImportForm()
        form.cleaned_data = _data
        with pytest.raises(ValidationError):
            ret = form.clean()
        assert not hasattr(form, "addresses")

    @patch("mailinglist.admin_forms.parse_csv")
    def test_clean_no_addresses(self, p_parse_csv, address_file, mailing_list):
        _data = {
            "address_file": address_file,
            "ignore_errors": True,
            "mailing_list": mailing_list,
        }
        form = ImportForm()

        form.cleaned_data = _data
        p_parse_csv.return_value = {}
        with pytest.raises(ValidationError):
            ret = form.clean()
        assert form.addresses == {}

    @patch("mailinglist.admin_forms.parse_csv")
    def test_clean(self, p_parse_csv, address_file, mailing_list):
        _data = {
            "address_file": address_file,
            "ignore_errors": True,
            "mailing_list": mailing_list,
        }
        form = ImportForm()

        form.cleaned_data = _data
        p_parse_csv.return_value = {"data": "values"}
        ret = form.clean()
        assert form.addresses == {"data": "values"}

    def test_get_addresses_default(self):
        form = ImportForm()
        assert form.get_addresses() == {}

    def test_get_addresses(self):
        form = ImportForm()
        form.addresses = {"data": "values"}
        assert form.get_addresses() == {"data": "values"}


class TestConfirmForm:
    def test_clean(self):
        form = ConfirmForm()
        form.cleaned_data = {"confirm": True}
        ret = form.clean()
        assert ret == {"confirm": True}

    def test_clean_bad(self):
        form = ConfirmForm()
        form.cleaned_data = {"confirm": False}
        with pytest.raises(ValidationError):
            ret = form.clean()


class TestSubmissionModelForm:
    def test_init_new(self, message):
        form = SubmissionModelForm()
        assert list(form.fields["message"].queryset) == [message]

    def test_init_no_messages(self, message, submission):
        form = SubmissionModelForm()
        assert list(form.fields["message"].queryset) == []

    def test_init_with_submission(self, message, submission, subscription):
        form = SubmissionModelForm(instance=submission)
        assert list(form.fields["message"].queryset) == [message]
        assert list(form.fields["exclude"].queryset) == [subscription]
