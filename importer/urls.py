from django.urls import path
from . import views

app_name = 'importer'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('upload/', views.upload_view, name='upload'),
    path('result/<int:log_id>/', views.result_view, name='result'),
    path('errors/<int:log_id>/csv/', views.error_csv_view, name='error_csv'),
    path('records/', views.records_view, name='records'),
]