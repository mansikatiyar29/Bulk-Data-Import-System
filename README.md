# Bulk Data Import System

A beginner-friendly but interview-ready **Django web application** that lets an
administrator upload a large **CSV or Excel (.xlsx)** file containing
student/customer records, validates every row, detects duplicates, inserts the
valid records into **MySQL** using `bulk_create()`, and shows a rich summary
with a detailed error report.

---

## Project Overview

The system solves a very common real-world problem: moving thousands of rows
from a spreadsheet into a relational database **without crashing**, **without
losing information about bad rows**, and **without slow row-by-row inserts**.

**What happens when you upload a file:**

1. The file is checked (type, size, emptiness, required columns).
2. Every row is validated server-side (name, email, Indian phone, age, city, state).
3. Duplicates are detected **inside the file** and **against existing database rows**.
4. Valid rows are inserted in **bulk** (`Student.objects.bulk_create(..., batch_size=1000)`).
5. Failed/duplicate rows are stored in an `ImportError` table with row number, field, and reason.
6. The user sees a summary (total / successful / failed / duplicates + percentages)
   and can download the failed rows as a CSV report.

---

## Technologies Used

| Technology   | Why                                                        |
|--------------|------------------------------------------------------------|
| **Python 3** | The application language.                                  |
| **Django**   | Web framework — ORM, forms, templates, security built in.  |
| **MySQL**    | Relational database for storing students & import logs.    |
| **Pandas**   | Reads CSV and Excel files into DataFrames for row iterating. |
| **OpenPyXL** | Reads `.xlsx` Excel files (used by Pandas under the hood). |
| **Bootstrap 5** | Responsive, modern UI via CDN (no extra template packages). |
| **JavaScript** | Small progressive-enhancement helper for the upload UI.   |

---

## Features

- **CSV / Excel upload** with type, size, and column validation.
- **Server-side validation** of every row:
  - Name — required, non-empty, no whitespace-only.
  - Email — required, valid format, lowercase-normalized.
  - Phone — required, valid **Indian 10-digit** mobile number.
  - Age — required, numeric whole number between 1 and 100.
  - City / State — required, no whitespace-only.
- **Whitespace stripping** (`"  Mansi Sharma  "` → `"Mansi Sharma"`).
- **Duplicate detection** in two layers:
  - Duplicates *inside the uploaded file* (tracked separately).
  - Duplicates *already in the database* (tracked separately).
- **Graceful error handling** — a bad row never crashes the app; it is marked
  failed and processing continues.
- **Performance-first bulk insertion** using `bulk_create()` with `batch_size=1000`.
- **Import summary page** (total/successful/failed/duplicates + percentages
  shown with Bootstrap progress bars).
- **Detailed error report** table (Row, Field, Value, Error) + CSV download.
- **Dashboard** with KPIs and recent imports.
- **Records page** with search, sorting, and pagination.
- **Security**: CSRF protection, extension whitelist, size limit, DB `unique`
  constraint on email, Django ORM everywhere, template auto-escaping.

---

## Project Structure

```
bulk_import_system/
│
├── manage.py
├── requirements.txt
├── generate_large_dataset.py     # utility (see "Large Dataset Testing")
├── sample_dataset.csv            # 30+ rows covering every validation case
│
├── bulk_import_system/           # Django project settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── importer/                     # the app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                  # upload form + file validation
│   ├── models.py                 # Student, ImportLog, ImportError
│   ├── services.py              ★ import pipeline (bulk_create lives here)
│   ├── urls.py
│   ├── views.py
│   ├── templatetags/importer_extras.py
│   └── migrations/
│
├── templates/
│   ├── base.html
│   └── importer/
│       ├── upload.html
│       ├── result.html
│       ├── records.html
│       └── dashboard.html
│
└── media/
    └── uploads/                  # saved uploaded files
```

---

## Installation

### 1. Requirements

- Python 3.10+
- MySQL 8.0+ running locally (or a remote instance)
- Git (optional)

### 2. Clone & enter the folder

```bash
git clone <your-repo-url>
cd bulk_import_system
```

### 3. Create & activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# On macOS/Linux:   source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note for Windows**: `mysqlclient` needs a MySQL C client build. If the
> install fails, install the pre-built wheel first:
> ```bash
> pip install mysqlclient (from wheels at https://pypi.org/project/mysqlclient/)
> ```
> or use **PyMySQL** (drop-in alternative for dev):
> ```bash
> pip install pymysql
> # then add to bulk_import_system/__init__.py:
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

### 5. Create the MySQL database

Connect to MySQL (e.g. `mysql -u root -p`) and run:

```sql
CREATE DATABASE bulk_import_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then update the credentials in `bulk_import_system/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'bulk_import_db',
        'USER': 'root',          # ← change
        'PASSWORD': 'root',      # ← change
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

### 6. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create an admin (optional)

```bash
python manage.py createsuperuser
```

### 8. Run the server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** — you land on the Dashboard.

---

## How Import Works

```
Upload File
     ↓
Validate File (type / size / empty)          ← importer/forms.py
     ↓
Read CSV / Excel (Pandas + OpenPyXL)         ← importer/services.py
     ↓
Normalize & Validate Columns (name,email,phone,age,city,state)
     ↓
Validate Rows (strip whitespace, check rules, 1–100 age, Indian phone)
     ↓
Duplicates: inside file  +  already in DB (email)   ← tracked separately
     ↓
Separate Valid / Invalid Data
     ↓
Student.objects.bulk_create(valid_objects, batch_size=1000)
     ↓
Persist ImportLog + per-row ImportError rows (in a DB transaction)
     ↓
Generate Import Summary (total/successful/failed/duplicates + %)
     ↓
Display Errors in a report table + CSV download
```

---

## Why `bulk_create()` matters

Without bulk insertion, 10,000 valid rows would generate **10,000 separate
`INSERT` statements** (slow round-trips to MySQL one row at a time):

```python
for obj in valid_objects:
    Student.objects.create(**obj)   # 10,000 queries → slow
```

With `bulk_create()`:

```python
Student.objects.bulk_create(valid_objects, batch_size=1000)
```

Django sends a **single multi-row `INSERT` per 1000 rows**, so the same 10,000
records need only **10 INSERT statements**. That is the difference between a
few seconds and a much longer wait, and it is the exact technique used in
production-grade import tools.

**Why `transaction.atomic()`?** All writes for one import (the `ImportLog`, the
students, and the error rows) are committed together. If anything unexpected
fails halfway, the whole batch rolls back instead of leaving the database in a
half-written state.

---

## Sample Dataset

`sample_dataset.csv` contains **36 rows** covering every scenario:

- valid records (unique emails, valid phones/ages)
- invalid email (`abc.com`)
- non-Indian / short phone numbers
- invalid ages (`-5`, `150`, `"twenty"`)
- duplicate emails **inside the file** (`rahul.verma@gmail.com`, `priya.singh@gmail.com`)
- a duplicate email that may already exist in the DB on a second upload
- empty / whitespace-only name, city, email, and age

Upload it from the **Upload Import** page to see the validation working.

---

## Large Dataset Testing

Generate a 10,000-row CSV (configurable):

```bash
python generate_large_dataset.py          # 10,000 records
python generate_large_dataset.py 50000    # 50,000 records
```

Then upload `large_dataset.csv`. Watch the **import time** on the result page —
with `bulk_create()` a 10,000-row file should import in a couple of seconds.

---

## Pages

| Page        | URL                      | What it shows                                   |
|-------------|--------------------------|-------------------------------------------------|
| Dashboard   | `/`                      | KPIs + recent imports table                     |
| Upload      | `/upload/`               | File picker, required columns, size limit       |
| Result      | `/result/<id>/`          | Summary cards, progress bars, error table       |
| Records     | `/records/`              | All students — search, sort, pagination         |
| Errors CSV  | `/errors/<id>/csv/`      | Downloadable failed-row report                  |
| Django Admin| `/admin/`                | Manage students / logs / errors                 |

---

## Security Measures

- **CSRF protection** — every form includes `{% csrf_token %}` and the
  `CsrfViewMiddleware` validates it on POST.
- **File extension whitelist** — only `.csv` / `.xlsx` (checked in the form).
- **File size limit** — 5 MB, enforced server-side (never trust the client).
- **Empty-file check** — a 0-byte upload is rejected.
- **Missing-column check** — files without the exact required columns are rejected.
- **Server-side row validation** — every field validated before insert.
- **Database-level `unique` on email** — the DB itself refuses duplicates.
- **Django ORM everywhere** — parameterized queries prevent SQL injection.
- **Template auto-escaping** — Django escapes HTML so stored data cannot inject
  XSS into the UI.
- **Failed rows never crash the app** — each error is captured and stored, the
  request always completes with a summary.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `mysqlclient` won't install on Windows | Install a wheel or use PyMySQL (see step 4). |
| `Access denied` connecting to MySQL | Check USER / PASSWORD in `settings.py`. |
| File too large to upload | Bump `MAX_UPLOAD_SIZE` in `importer/forms.py` and the `Accept` attribute. |
| CSV shows `UnicodeDecodeError` | The service already tries utf-8-sig → utf-8 → latin-1 automatically. Save as UTF-8 CSV. |

---

## How I Explain This Project in an Interview

### 2-Minute Pitch (say this naturally)

> "I built a **Bulk Data Import System** with Django and MySQL. The problem it
> solves is real: companies often need to push thousands of student or customer
> records from a spreadsheet into a database — and they can't afford the import
> to crash or to silently lose bad rows.
>
> The flow is: the user uploads a **CSV or Excel** file. Django validates the
> file itself — type, size, whether it's empty, and whether it has the required
> columns. Then, for **every row**, the system validates each field server-side:
> name, email format, a valid **Indian 10-digit phone number**, an age between 1
> and 100, and non-empty city/state — stripping whitespace before checking.
>
> I detect duplicates in two places: **inside the file** and **against existing
> rows in the database**. Valid rows are collected as Django model objects and
> inserted all at once using `bulk_create()` with `batch_size=1000`. Invalid and
> duplicate rows never crash the app — each one is written to an `ImportError`
> table with the row number, field, value, and reason, so the user sees a clear
> error report and can download it as a CSV.
>
> Finally, the system shows an import summary — total, successful, failed,
> duplicates, percentages, and import time — on a dashboard with a records page
> that supports search, sorting, and pagination.
>
> The key engineering decision was **performance**: instead of 10,000 separate
> `INSERT` queries for 10,000 rows, `bulk_create()` sends just ~10 multi-row
> INSERTs, which made a 10,000-record file import in a couple of seconds."

### Likely Interview Questions & Answers

**1. Why did you choose Django?**
Django gives me everything a production web app needs out of the box — an ORM,
a forms system with built-in validation, template rendering, an admin panel,
and security features like CSRF protection and auto-escaping. It lets me focus
on the import business logic instead of reinventing HTTP, sessions, and
security. The `bulk_create()` ORM method is also exactly what I needed for the
performance goal.

**2. Why did you use MySQL?**
It's one of the most widely used relational databases in industry, it's what
most companies and the recruiter's team already run, and it gives me strong
guarantees that matter for imports — like a `UNIQUE` constraint on email that
blocks duplicates at the database level, and transaction support via
`transaction.atomic()` so a failed import never leaves partial data.

**3. Why did you use Pandas?**
Pandas reads both CSV and Excel into a **DataFrame**, which makes iterating row
by row, normalizing column names, and handling NaN/empty cells much cleaner
than hand-parsing files. It also robustly handles different encodings, which is
a common real-world problem with CSVs exported from various tools.

**4. Why did you use OpenPyXL?**
It's the engine Pandas uses under the hood to read `.xlsx` Excel files. I
mention it because it shows I understand *how* the Excel reading actually
happens — `.xlsx` files are ZIP containers of XML, and OpenPyXL parses that
format. It's the standard Python library for Excel and supports `.xlsx`.

**5. How does the file upload work?**
The form uses `enctype="multipart/form-data"`, the file is bound to a Django
`FileField`, and the form's `clean_file()` method validates extension, size,
and emptiness **server-side** before I ever touch it. If valid, the file goes
to the service layer, which reads it into a DataFrame.

**6. How do you validate each record?**
I wrote a `validate_row()` function that strips every field's whitespace, then
checks each rule — required name, valid email via Django's `validate_email`,
Indian 10-digit phone via regex, numeric age in 1–100, and non-blank city/state.
It returns a list of `(field, message)` errors. Only rows with no errors become
Student objects.

**7. How do you handle invalid records?**
I never stop the import because of one bad row. Each invalid row is stored in
the `ImportError` table with its row number, the failing field, the bad value,
and a human-readable message, then processing continues. At the end, the user
sees all of these in an error report and can download them as CSV.

**8. How do you detect duplicate records?**
Two layers. First, I keep a `set` of emails seen inside the current file, so a
second occurrence is flagged as an in-file duplicate. Second, I preload all
existing emails from the database into a set for O(1) lookup, so a row whose
email already exists is flagged before insertion. I also set `unique=True` on
email in the model, so the database itself is the final guard.

**9. What is `bulk_create()`?**
It's a Django ORM method that inserts many model objects in a **single (or few)
multi-row INSERT** statements, instead of running one query per object. You give
it a list of unsaved model instances.

**10. Why is `bulk_create()` faster than `objects.create()` in a loop?**
Because each `objects.create()` is a round-trip to the database — one network
call and one query per row. With 10,000 rows that's 10,000 queries and 10,000
round-trips. `bulk_create()` builds one multi-row `INSERT` per batch, so the
same data needs only a handful of queries. Database round-trips are expensive;
`bulk_create()` amortizes that cost.

**11. How did you optimize the database operation?**
Mainly with `bulk_create(valid_objects, batch_size=1000)`. I also avoid
per-row DB hits during duplicate checking by loading all existing emails into a
Python set once, and I bulk-insert the `ImportError` rows the same way. I add
indexes on frequently queried columns (name, email, city).

**12. How do you handle 10,000 or 100,000 records?**
The script reads the file into a DataFrame and processes it row by row in
Python, collecting valid objects — that's O(n) in memory, fine for these sizes.
Then `batch_size=1000` splits the insert into manageable chunks so we don't
send an enormous single query or lock the DB for too long. For even larger data
you'd add chunked reading so you don't hold the whole file in memory.

**13. What happens if one record fails?**
It's caught per-row, recorded in `ImportError`, and the import continues. Only
fully valid, non-duplicate rows get inserted. The request always completes with
a summary rather than crashing.

**14. How do you handle database exceptions?**
The service catches `ValueError` and `IntegrityError` (for example, a unique
constraint violation) and also a generic `Exception` as a safety net. It records
the failure in an `ImportLog` plus an error row, and returns cleanly — the app
never bubbles up a raw 500 because of a data problem.

**15. Where did you use transactions?**
I wrap the entire DB write — creating the `ImportLog`, `bulk_create` of students,
and bulk-creating the `ImportError` rows — inside `transaction.atomic()`. That
way, if anything fails halfway, the whole batch rolls back to a consistent state
instead of leaving half-written data. Transactions are useful because they give
atomicity: all-or-nothing for a group of related writes.

**16. How does Django ORM interact with MySQL?**
Django's ORM translates Python method calls into SQL and parameterized queries.
For `bulk_create`, it runs multi-row `INSERT` statements. Parameterized queries
prevent SQL injection. Django also auto-generates migrations that create the
MySQL tables, unique constraints, and indexes.

**17. What security measures did you implement?**
CSRF protection on forms, file-extension whitelist (only `.csv`/`.xlsx`),
server-side file-size limit, empty-file and missing-column checks, stripping
whitespace before validation, `unique=True` on email at the DB level, using the
Django ORM with parameterized queries instead of raw SQL, Django template
auto-escaping to prevent XSS, and never trusting uploaded data.

**18. How does CSRF protection work?**
Django's `CsrfViewMiddleware` generates a token, sends it to the browser as a
hidden field/cookie, and on every POST checks that the submitted token matches.
Because an attacker's site can't read our cookie or token, a cross-site request
without the correct token is rejected. Every form here uses `{% csrf_token %}`.

**19. How would you improve this project in the future?**
I'd process large files with a background task (Celery) so the request doesn't
block, add user authentication/authorization so only admins can import, stream
or chunk the file reading to bound memory, add more configurable validation
rules, and write a full automated test suite with `pytest`/Django's test client.

**20. What was the most challenging part?**
Handling edge cases in real data: pandas represents empty cells as `NaN`
(a float), so a blank value could silently become the string `"nan"` and get
inserted as a bogus record. I had to explicitly detect `NaN` and treat it as an
empty string, and normalize numpy types before storing them in a JSON field so
the stored error data stayed valid. Getting that right across all the sample
file's bad rows taught me a lot about real-world data cleaning.