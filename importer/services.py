"""
Import processing service.

WHY A SEPARATE SERVICE?
------------------------
The Django view should stay thin (handle request/response only).
All the business logic -- reading files, validating rows, detecting
duplicates, and bulk inserting -- lives here so it is:
  * testable in isolation
  * reusable (views, management commands, background tasks)
  * easy to reason about

HOW BULK_CREATE() HELPS PERFORMANCE
-------------------------------------
Without bulk_create() we would run one INSERT for every valid row:

    for obj in valid_objects:
        Student.objects.create(...)        # rows x 1 query

With bulk_create(batch_size=1000) Django sends just ONE multi-row
INSERT for every 1000 rows, so 5000 valid records = only 5 INSERT
statements instead of 5000. That is the single biggest speed win for
large imports.
"""
import csv
import io
import math
import os
import re
import time
from datetime import datetime

import pandas as pd
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.utils import IntegrityError

from .forms import REQUIRED_COLUMNS
from .models import ImportError, ImportLog, Student

# Regex for an Indian 10-digit mobile number (may start with 6-9 or +91).
PHONE_RE = re.compile(r'^(\+91[- ]?|0)?[6-9]\d{9}$')


def normalize_columns(df):
    """
    Normalize column names: lowercase, strip whitespace/underscores so the
    file header can be sloppy and still pass validation.
    """
    mapping = {}
    for col in df.columns:
        norm = str(col).strip().lower().replace(' ', '_').replace('-', '_')
        mapping[col] = norm
    df = df.rename(columns=mapping)
    return df


def validate_required_columns(df):
    """Raise ValueError listing which required columns are missing."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}. "
                         f"Expected columns: {', '.join(REQUIRED_COLUMNS)}.")


def read_student_file(file):
    """
    Read an uploaded CSV or XLSX file into a Pandas DataFrame.

    Returns (dataframe, source_name). Raises ValueError for bad files.
    Handles encoding variants for CSV (some exports use utf-8-sig / latin-1).
    """
    _, ext = os.path.splitext(file.name) if file.name else (None, '')
    ext = ext.lower()

    name = file.name if file.name else 'uploaded_file'
    if ext == '.csv':
        # Read raw bytes -> decode -> StringIO so pandas handles encodings well
        raw = file.read()
        for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            raise ValueError('Could not decode the CSV file. Use UTF-8 encoding.')
        df = pd.read_csv(io.StringIO(text))
    elif ext == '.xlsx':
        df = pd.read_excel(file, engine='openpyxl')
    else:
        raise ValueError('Unsupported file type. Only .csv and .xlsx are allowed.')

    if df is None or df.empty:
        raise ValueError('The file contains no data rows.')

    # Drop completely empty rows (e.g. stray blank lines in Excel)
    df = df.dropna(how='all')
    if df.empty:
        raise ValueError('The file contains no data rows.')

    return df, name


def _cell_str(value):
    """
    Convert a pandas cell to a plain string, treating NaN as an empty string.

    IMPORTANT: pandas uses float('nan') for empty cells. `nan or ''` does NOT
    work because float(nan) is TRUTHY — so we must check for NaN explicitly.
    Without this, an empty city could silently become the string "nan" and a
    record would be inserted with a bogus value.
    """
    if value is None:
        return ''
    if isinstance(value, float) and math.isnan(value):
        return ''
    return str(value)


def validate_row(row):
    """
    Validate a single student row. Returns (errors, cleaned) where errors is a
    list of (field, error_message) tuples. An empty list means the row is valid.

    Every field is stripped of leading/trailing whitespace (so
    "  Mansi Sharma  " becomes "Mansi Sharma") before validation, and the
    cleaned values are returned to be used for the Student object.
    """
    errors = []

    # --- strip all values first ---
    name = _cell_str(row.get('name')).strip()
    email = _cell_str(row.get('email')).strip().lower()
    phone = _cell_str(row.get('phone')).strip()
    age = _cell_str(row.get('age')).strip()
    city = _cell_str(row.get('city')).strip()
    state = _cell_str(row.get('state')).strip()

    # --- name ---
    if not name:
        errors.append(('name', 'Name is required and cannot be empty.'))
    elif name.isspace():
        errors.append(('name', 'Name cannot contain only whitespace.'))

    # --- email ---
    if not email:
        errors.append(('email', 'Email is required.'))
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors.append(('email', f'"{email}" is not a valid email address.'))

    # --- phone (Indian 10-digit) ---
    if not phone:
        errors.append(('phone', 'Phone number is required.'))
    elif not PHONE_RE.match(phone):
        errors.append(('phone',
                       'Phone must be a valid Indian 10-digit number (e.g. 9876543210 or +91 9876543210).'))

    # --- age ---
    if not age:
        errors.append(('age', 'Age is required.'))
    else:
        try:
            age_value = float(age)
            if not age_value.is_integer() or age_value < 1 or age_value > 100:
                errors.append(('age', 'Age must be a whole number between 1 and 100.'))
            else:
                age = int(age_value)
        except ValueError:
            errors.append(('age', f'"{age}" is not a valid number for age.'))

    # --- city ---
    if not city or city.isspace():
        errors.append(('city', 'City is required and cannot contain only whitespace.'))

    # --- state ---
    if not state or state.isspace():
        errors.append(('state', 'State is required and cannot contain only whitespace.'))

    cleaned = {
        'name': name, 'email': email, 'phone': phone,
        'age': age, 'city': city, 'state': state,
    }
    return errors, cleaned


def json_safe_row(row):
    """
    Convert a pandas row into a plain dict whose values are safe to store in
    a Django JSONField. Pandas emits NaN (a float) and numpy int/float types,
    which json.dumps(allow_nan=True) would render as the *invalid* JSON token
    NaN -- that breaks the JSON_VALID check on MySQL/SQLite JSON columns.
    """
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, (int, float)):
            if isinstance(value, float) and math.isnan(value):
                result[key] = ''
            else:
                result[key] = value
        else:
            result[key] = str(value)
    return result


def process_import(uploaded_file):
    """
    Main import pipeline. Accepts an UploadedFile, returns an ImportLog.

    Steps:
      1. Read + normalize the DataFrame
      2. Validate required columns
      3. Loop every row: validate, detect in-file and in-DB duplicates,
         accumulate valid Student objects
      4. bulk_create() valid objects in batches of BATCH_SIZE
      5. Persist ImportLog + per-row ImportError details
      6. Return the log (view uses it to render the summary)

    The whole DB write is wrapped in a single transaction so we never leave
    the database in a half-written state if something unexpected happens.
    """
    BATCH_SIZE = 1000
    start = time.time()

    try:
        df, filename = read_student_file(uploaded_file)
        df = normalize_columns(df)
        validate_required_columns(df)

        total = len(df)
        success = 0
        failed = 0
        duplicates = 0

        valid_objects = []
        error_rows = []              # (row_number, field, msg, row_dict)
        seen_emails_in_file = set()  # duplicate detection inside the file

        # Pre-load all existing emails in the DB for O(1) duplicate lookup.
        # This avoids hitting the database once per row.
        existing_emails = set(Student.objects.values_list('email', flat=True))

        # ---- per-row processing ----
        for idx, row in df.iterrows():
            # +1 for zero-index, +1 for header row -> human row numbers
            row_num = idx + 2
            row_data = json_safe_row(row)

            row_errors, cleaned = validate_row(row)

            if row_errors:
                for field, msg in row_errors:
                    error_rows.append((row_num, field, msg, row_data))
                failed += 1
                continue

            email = cleaned['email']

            # 2) duplicate already in the database — check this BEFORE adding
            #    the email to the in-file seen set, otherwise a DB-duplicate's
            #    email would wrongly mark later rows as "duplicate inside file".
            if email in existing_emails:
                error_rows.append((row_num, 'email',
                                   'Email already exists in the database.',
                                   row_data))
                duplicates += 1
                continue

            # 1) duplicate inside this file
            if email in seen_emails_in_file:
                error_rows.append((row_num, 'email',
                                   'Duplicate email found inside the uploaded file.',
                                   row_data))
                duplicates += 1
                continue
            seen_emails_in_file.add(email)

            valid_objects.append(Student(
                name=cleaned['name'],
                email=cleaned['email'],
                phone=cleaned['phone'],
                age=cleaned['age'],
                city=cleaned['city'],
                state=cleaned['state'],
            ))
            success += 1

        # ----------------------------------------------------------------
        # BULK INSERT -- the performance-critical step.
        # one multi-row INSERT per BATCH_SIZE rows instead of one per row.
        # ----------------------------------------------------------------
        with transaction.atomic():
            log = ImportLog(
                uploaded_file=filename,
                total_records=total,
                successful_records=success,
                failed_records=failed,
                duplicate_records=duplicates,
            )
            log.save()

            if valid_objects:
                Student.objects.bulk_create(valid_objects, batch_size=BATCH_SIZE)

            # Persist error details in bulk too (same trick for speed)
            error_objs = [
                ImportError(
                    import_log=log,
                    row_number=rn,
                    field_name=field,
                    error_message=msg,
                    row_data=row_data,
                )
                for (rn, field, msg, row_data) in error_rows
            ]
            if error_objs:
                ImportError.objects.bulk_create(error_objs, batch_size=BATCH_SIZE)

            # Reaching here means the transaction commits cleanly as one unit.

        log.import_duration = round(time.time() - start, 2)
        log.save()
        return log

    except (ValueError, IntegrityError) as exc:
        # Validation-level error: missing columns, bad file, DB constraint hit.
        # If the failure happened while writing inside `atomic`, the transaction
        # was already rolled back -- so we record the failure in a fresh,
        # clean transaction and never write through a broken connection.
        return _record_failed_import(exc, 'file', uploaded_file, start)

    except Exception as exc:  # noqa: BLE001 -- never let the app crash
        # Unexpected exception -- still record it so the user knows what went wrong
        return _record_failed_import(exc, 'system', uploaded_file, start)


def _record_failed_import(exc, field_name, uploaded_file, start):
    """Create a new ImportLog (failed_records=1) + a single ImportError row."""
    log = ImportLog(
        uploaded_file=getattr(uploaded_file, 'name', 'uploaded_file'),
        total_records=0,
        successful_records=0,
        failed_records=1,
        duplicate_records=0,
        import_duration=round(time.time() - start, 2),
    )
    log.save()
    ImportError.objects.create(
        import_log=log,
        row_number=0,
        field_name=field_name,
        error_message=str(exc),
        row_data={},
    )
    return log


def build_error_csv(log_id):
    """
    Builds an in-memory CSV of the failed rows for this import.
    Returns (filename, csv_string).
    """
    errors = ImportError.objects.filter(import_log_id=log_id)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Row Number', 'Field', 'Value', 'Error Message'])
    for e in errors:
        value = ''
        if e.row_data:
            value = e.row_data.get(e.field_name, '')
        writer.writerow([e.row_number, e.field_name, value, e.error_message])
    buffer.seek(0)
    filename = f"import_errors_{log_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return filename, buffer.getvalue()