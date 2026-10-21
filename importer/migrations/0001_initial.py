import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ImportLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uploaded_file', models.FileField(upload_to='uploads/')),
                ('total_records', models.PositiveIntegerField(default=0)),
                ('successful_records', models.PositiveIntegerField(default=0)),
                ('failed_records', models.PositiveIntegerField(default=0)),
                ('duplicate_records', models.PositiveIntegerField(default=0)),
                ('import_duration', models.FloatField(default=0.0)),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-imported_at'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(max_length=15)),
                ('age', models.IntegerField()),
                ('city', models.CharField(max_length=150)),
                ('state', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-created_at', 'id'],
                'indexes': [models.Index(fields=['name'], name='student_name_idx'), models.Index(fields=['email'], name='student_email_idx'), models.Index(fields=['city'], name='student_city_idx')],
            },
        ),
        migrations.CreateModel(
            name='ImportError',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row_number', models.PositiveIntegerField()),
                ('field_name', models.CharField(max_length=100)),
                ('error_message', models.TextField()),
                ('row_data', models.JSONField(blank=True, default=dict)),
                ('import_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='errors', to='importer.importlog')),
            ],
            options={
                'ordering': ['row_number'],
                'indexes': [models.Index(fields=['import_log'], name='import_error_log_idx')],
            },
        ),
    ]
