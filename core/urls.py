from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('folder/<int:folder_id>/', views.dashboard, name='folder_detail'),
    
    path('create-folder/', views.create_folder, name='create_folder_root'),
    path('create-folder/<int:folder_id>/', views.create_folder, name='create_folder'),
    
    path('upload/', views.upload_file, name='upload_file_root'),
    path('upload/<int:folder_id>/', views.upload_file, name='upload_file'),
    
    path('file/delete/<int:file_id>/', views.delete_file, name='delete_file'),
    path('folder/delete/<int:folder_id>/', views.delete_folder, name='delete_folder'),
    
    path('file/rename/<int:file_id>/', views.rename_file, name='rename_file'),
    path('folder/rename/<int:folder_id>/', views.rename_folder, name='rename_folder'),
    
    path('file/download/<int:file_id>/', views.download_file, name='download_file'),
    path('folder/download/<int:folder_id>/', views.download_folder_zip, name='download_folder_zip'),
    
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]
