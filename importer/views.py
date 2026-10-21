"""
Views for the Bulk Data Import System.

Thin views — they handle HTTP request/response only.
All heavy lifting is delegated to importer/services.py.
"""
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from .forms import StudentUploadForm
from .models import ImportError, ImportLog, Student
from .services import process_import, build_error_csv


def upload_view(request):
    """Show the upload page and, on POST, run the import pipeline."""
    form = StudentUploadForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            uploaded_file = form.cleaned_data['file']
            # Delegate the whole import to the service layer.
            log = process_import(uploaded_file)
            return render(request, 'importer/result.html', {'log': log})
        # Form invalid → render errors on the same page.
    return render(request, 'importer/upload.html', {'form': form})


def result_view(request, log_id):
    """Show the import summary for a past import + its error table."""
    log = get_object_or_404(ImportLog, id=log_id)
    errors = ImportError.objects.filter(import_log=log)

    # Percentages (guard against division by zero)
    total = log.total_records or 0
    success_pct = round(log.successful_records / total * 100, 2) if total else 0
    failed_pct = round(log.failed_records / total * 100, 2) if total else 0
    duplicate_pct = round(log.duplicate_records / total * 100, 2) if total else 0

    context = {
        'log': log,
        'errors': errors,
        'success_pct': success_pct,
        'failed_pct': failed_pct,
        'duplicate_pct': duplicate_pct,
    }
    return render(request, 'importer/result.html', context)


def error_csv_view(request, log_id):
    """Download a CSV report of all failed records for an import."""
    get_object_or_404(ImportLog, id=log_id)
    filename, content = build_error_csv(log_id)
    response = HttpResponse(content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def dashboard_view(request):
    """Admin-style dashboard with KPIs and recent imports."""
    from django.db.models import Sum

    total_students = Student.objects.count()
    total_imports = ImportLog.objects.count()

    # Aggregate totals across every import
    sums = ImportLog.objects.aggregate(
        total_records=Sum('total_records'),
        total_successful=Sum('successful_records'),
        total_failed=Sum('failed_records'),
        total_duplicates=Sum('duplicate_records'),
    )

    recent_imports = ImportLog.objects.all()[:8]

    context = {
        'total_students': total_students,
        'total_imports': total_imports,
        'total_records': sums['total_records'] or 0,
        'total_successful': sums['total_successful'] or 0,
        'total_failed': sums['total_failed'] or 0,
        'total_duplicates': sums['total_duplicates'] or 0,
        'recent_imports': recent_imports,
        'success_rate': round((sums['total_successful'] or 0) / (sums['total_records'] or 1) * 100, 2),
    }
    return render(request, 'importer/dashboard.html', context)


def records_view(request):
    """Page listing all successfully imported students with search/pagination/sort."""
    queryset = Student.objects.all()

    # --- search by name / email ---
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(email__icontains=q)
        )

    # --- sorting ---
    sort_map = {
        'name': 'name', '-name': '-name',
        'email': 'email', '-email': '-email',
        'age': 'age', '-age': '-age',
        'city': 'city', '-city': '-city',
        'state': 'state', '-state': '-state',
        'date': 'created_at', '-date': '-created_at',
    }
    sort = request.GET.get('sort', '-date')
    order_by = sort_map.get(sort, '-date')

    queryset = queryset.order_by(order_by)

    # --- pagination ---
    paginator = Paginator(queryset, 25)  # 25 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'current_q': q,
        'current_sort': sort,
    }
    return render(request, 'importer/records.html', context)