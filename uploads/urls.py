from django.urls import path
from . import views

app_name = 'uploads'

urlpatterns = [
    path('', views.UploadListView.as_view(), name='upload_list'),
    path('new/', views.UploadCreateView.as_view(), name='upload_create'),
    path('<int:pk>/', views.UploadDetailView.as_view(), name='upload_detail'),
    path('<int:pk>/delete/', views.UploadDeleteView.as_view(), name='upload_delete'),
    path('<int:pk>/errors/export/', views.DownloadErrorXlsxView.as_view(), name='export_errors'),
    path('templates/<str:dataset_type>/', views.DownloadTemplateView.as_view(), name='download_template'),
    path('api/<int:pk>/status/', views.UploadStatusApiView.as_view(), name='upload_status_api'),
]
