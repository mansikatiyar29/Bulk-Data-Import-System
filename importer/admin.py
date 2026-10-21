from django.contrib import admin
from .models import Student, ImportLog, ImportError


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'age', 'city', 'state', 'created_at')
    search_fields = ('name', 'email', 'city', 'state')
    list_filter = ('state', 'city')


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'uploaded_file', 'total_records', 'successful_records',
                    'failed_records', 'duplicate_records', 'imported_at')


@admin.register(ImportError)
class ImportErrorAdmin(admin.ModelAdmin):
    list_display = ('id', 'import_log', 'row_number', 'field_name', 'error_message')
    list_filter = ('field_name', 'import_log')
    search_fields = ('error_message',)