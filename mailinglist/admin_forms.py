from django import forms
from django.db.models import Q

from mailinglist.addressimport.parsers import parse_csv
from mailinglist.models import MailingList, Message, Submission


class ImportForm(forms.Form):
    def clean(self):
        # If there are validation errors earlier on, don't bother.
        if not (
            "address_file" in self.cleaned_data
            and "ignore_errors" in self.cleaned_data
            and "mailing_list" in self.cleaned_data
        ):
            return self.cleaned_data

        address_file = self.cleaned_data["address_file"]

        content_type = address_file.content_type
        allowed_types = (
            "text/plain",
            "text/comma-separated-values",
            "text/csv",
            "application/csv",
        )
        if content_type not in allowed_types:
            raise forms.ValidationError(
                f"File type '{content_type}' was not recognized."
            )

        ext = address_file.name.rsplit(".", 1)[-1].lower()
        parser = None
        if ext == "csv":
            parser = parse_csv
        if parser is None:
            raise forms.ValidationError(f"File extension '{ext}' was not recognized.")

        self.addresses = parser(
            address_file.file,
            self.cleaned_data["mailing_list"],
            self.cleaned_data["ignore_errors"],
        )

        if len(self.addresses) == 0:
            raise forms.ValidationError("No entries could found in this file.")

        return self.cleaned_data

    def get_addresses(self):
        return getattr(self, "addresses", {})

    mailing_list = forms.ModelChoiceField(
        label="Mailing List",
        queryset=MailingList.objects.all(),
    )
    address_file = forms.FileField(label="Address file")
    ignore_errors = forms.BooleanField(
        label="Ignore non-fatal errors", initial=True, required=False
    )


class ConfirmForm(forms.Form):
    def clean(self):
        value = self.cleaned_data.get("confirm", False)

        if not value:
            raise forms.ValidationError("You should confirm in order to continue.")
        return self.cleaned_data

    confirm = forms.BooleanField(
        label="Confirm import", initial=True, widget=forms.HiddenInput
    )


class SubmissionModelForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        submission = kwargs.get("instance")
        if submission is not None:
            self.fields[
                "exclude"
            ].queryset = submission.message.mailing_list.subscriptions.all()
            self.fields["message"].queryset = Message.objects.filter(
                Q(submission__isnull=True) | Q(submission=submission)
            )
        else:
            self.fields["message"].queryset = Message.objects.filter(
                submission__isnull=True
            )
