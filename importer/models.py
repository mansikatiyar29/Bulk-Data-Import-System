"""
Models for the Bulk Data Import System.

SECURITY & DESIGN NOTES:
- The `unique=True` constraint on Student.email is enforced at the database level
  (a DB unique index), so not only the app but the database itself refuses
  duplicate emails. This is our last line of defence against duplicates.
- Indexes (db_index=True) speed up lookups on frequently queried columns.
- ImportError is intentionally a separate model so we can show exactly which
  rows failed and why, without ever crashing the request.
"""
from django.db import models


class Student(models.Model):
    """
    A single student / customer record imported from CSV or Excel.
    """
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, unique=True)
    phone = models.CharField(max_length=15)
    age = models.IntegerField()
    city = models.CharField(max_length=150)
    state = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'id']
        indexes = [
            # Useful for searching / sorting on these columns
            models.Index(fields=['name'], name='student_name_idx'),
            models.Index(fields=['email'], name='student_email_idx'),
            models.Index(fields=['city'], name='student_city_idx'),
        ]

    def __str__(self):
        return self.name


class ImportLog(models.Model):
    """
    One row per upload — stores a summary of what happened.
    """
    uploaded_file = models.FileField(upload_to='uploads/')
    total_records = models.PositiveIntegerField(default=0)
    successful_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    duplicate_records = models.PositiveIntegerField(default=0)
    import_duration = models.FloatField(default=0.0)  # seconds
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-imported_at']

    def __str__(self):
        return f"{self.uploaded_file.name} @ {self.imported_at}"


class ImportError(models.Model):
    """
    Stores per-row validation errors for a given import so we can render
    a detailed error report table afterwards.
    """
    import_log = models.ForeignKey(
        ImportLog,
        on_delete=models.CASCADE,
        related_name='errors',
    )
    row_number = models.PositiveIntegerField()      # row in the source file
    field_name = models.CharField(max_length=100)    # e.g. 'email', 'age'
    error_message = models.TextField()               # human readable reason
    row_data = models.JSONField(default=dict, blank=True)  # original raw row

    class Meta:
        ordering = ['row_number']
        indexes = [
            models.Index(fields=['import_log'], name='import_error_log_idx'),
        ]

    def __str__(self):
        return f"Row {self.row_number}: {self.field_name} — {self.error_message}"