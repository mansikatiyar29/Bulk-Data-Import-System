"""
Forms for the Bulk Data Import System.

SECURITY:
- File extension validation happens in the form AND again in the service layer
  (defence in depth). Browsers can be tricked; the server never trusts them.
- File size is validated so a giant file cannot exhaust server memory.
"""
import os

from django import forms

from .models import Student

# Maximum upload size (5 MB). Change as needed.
MAX_UPLOAD_SIZE = 5 * 1024 * 1024

# Only these extensions are ever accepted.
ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}

# Columns that must exist in the uploaded file.
REQUIRED_COLUMNS = ['name', 'email', 'phone', 'age', 'city', 'state']


class StudentUploadForm(forms.Form):
    """
    Handles the uploaded CSV / Excel file.

    Error messages are user-friendly because they are shown directly
    on the upload page.
    """
    file = forms.FileField(
        label='Upload CSV / Excel File',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control form-control-lg',
            'accept': '.csv,.xlsx',
        }),
    )

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise forms.ValidationError('Please choose a file to upload.')

        # --- Empty file check ---
        if file.size == 0:
            raise forms.ValidationError('The uploaded file is empty.')

        # --- File size check (server-side, do not trust the client) ---
        if file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f'File is too large. Maximum allowed size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.'
            )

        # --- Extension check ---
        _, ext = os.path.splitext(file.name)
        if ext.lower() not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                'Unsupported file type. Only .csv and .xlsx files are allowed.'
            )

        return file