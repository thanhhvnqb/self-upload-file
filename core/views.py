from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, HttpResponseForbidden
from django.conf import settings
from .models import Folder, File
from .forms import FolderForm, FileUploadForm
from django import forms
import os
import shutil
import zipfile
from io import BytesIO

@login_required
def dashboard(request, folder_id=None):
    if request.user.is_superuser and folder_id is None and request.GET.get('view') != 'personal':
        return redirect('admin_dashboard')

    folder = None
    if folder_id:
        if request.user.is_superuser:
            folder = get_object_or_404(Folder, id=folder_id)
        else:
            folder = get_object_or_404(Folder, id=folder_id, user=request.user)
        subfolders = folder.subfolders.all()
        files = folder.files.all()
    else:
        # For dashboard root, if standard user, show their root.
        # If admin is just visiting /dashboard/ (no ID), maybe just show their own root?
        # The issue reported is for specific folder ID access.
        # Let's keep root behavior as "my root" for now, unless specified otherwise.
        subfolders = Folder.objects.filter(user=request.user, parent__isnull=True)
        files = File.objects.filter(user=request.user, folder__isnull=True)
        
    context = {
        'folder': folder,
        'subfolders': subfolders,
        'files': files,
        'folder_form': FolderForm(),
        'upload_form': FileUploadForm(),
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def create_folder(request, folder_id=None):
    folder = None
    if folder_id:
        if request.user.is_superuser:
            folder = get_object_or_404(Folder, id=folder_id)
        else:
            folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    
    if request.method == 'POST':
        form = FolderForm(request.POST)
        if form.is_valid():
            new_folder = form.save(commit=False)
            new_folder.user = request.user
            new_folder.parent = folder
            new_folder.save()
            
    if folder:
        return redirect('folder_detail', folder_id=folder.id)
    return redirect('dashboard')

@login_required
def upload_file(request, folder_id=None):
    folder = None
    if folder_id:
        if request.user.is_superuser:
             folder = get_object_or_404(Folder, id=folder_id)
        else:
             folder = get_object_or_404(Folder, id=folder_id, user=request.user)
        
    if request.method == 'POST':
        files = request.FILES.getlist('file')
        for f in files:
            File.objects.create(
                user=request.user,
                folder=folder,
                file=f,
                name=f.name
            )
            
    if folder:
        return redirect('folder_detail', folder_id=folder.id)
    return redirect('dashboard')

@login_required
def delete_file(request, file_id):
    if request.user.is_superuser:
        file = get_object_or_404(File, id=file_id)
    else:
        file = get_object_or_404(File, id=file_id, user=request.user)
    folder_id = file.folder.id if file.folder else None
    file.delete()
    if folder_id:
        return redirect('folder_detail', folder_id=folder_id)
    return redirect('dashboard')

@login_required
def delete_folder(request, folder_id):
    if request.user.is_superuser:
        folder = get_object_or_404(Folder, id=folder_id)
    else:
        folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    parent_id = folder.parent.id if folder.parent else None
    folder.delete() # Cascade deletes subfolders and files
    if parent_id:
        return redirect('folder_detail', folder_id=parent_id)
    return redirect('dashboard')

@login_required
def download_file(request, file_id):
    file = get_object_or_404(File, id=file_id)
    # Check permission: owner or admin
    if file.user != request.user and not request.user.is_superuser:
        raise Http404
        
    file_path = file.file.path
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/octet-stream")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404

@login_required
def download_folder_zip(request, folder_id):
    # Determine if checking for own folder or admin checking any folder
    if request.user.is_superuser:
         folder = get_object_or_404(Folder, id=folder_id)
         # Mark as downloaded if admin
         if not folder.is_downloaded:
             folder.is_downloaded = True
             folder.save()
    else:
         folder = get_object_or_404(Folder, id=folder_id, user=request.user)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        _add_folder_to_zip(zip_file, folder, folder.name)
        
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename={folder.name}.zip'
    return response

def _add_folder_to_zip(zip_file, folder, current_path):
    # Add files in this folder
    for file in folder.files.all():
        if file.file:
            path_in_zip = os.path.join(current_path, file.name)
            try:
                zip_file.write(file.file.path, path_in_zip)
            except FileNotFoundError:
                pass # Skip missing files
            
    # Add subfolders recursively
    for subfolder in folder.subfolders.all():
        _add_folder_to_zip(zip_file, subfolder, os.path.join(current_path, subfolder.name))

@login_required
def rename_folder(request, folder_id):
    if request.user.is_superuser:
        folder = get_object_or_404(Folder, id=folder_id)
    else:
        folder = get_object_or_404(Folder, id=folder_id, user=request.user)
    if request.method == 'POST':
        form = FolderForm(request.POST, instance=folder)
        if form.is_valid():
            form.save()
            return redirect('folder_detail', folder_id=folder.parent.id) if folder.parent else redirect('dashboard')
    else:
        form = FolderForm(instance=folder)
    
    return render(request, 'core/rename.html', {'form': form, 'obj': folder, 'type': 'folder'})

@login_required
def rename_file(request, file_id):
    if request.user.is_superuser:
        file = get_object_or_404(File, id=file_id)
    else:
        file = get_object_or_404(File, id=file_id, user=request.user)
    
    # Simple form for file rename (just name)
    class FileRenameForm(forms.ModelForm):
        class Meta:
            model = File
            fields = ['name']
            widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}
            
    if request.method == 'POST':
        form = FileRenameForm(request.POST, instance=file)
        if form.is_valid():
            form.save()
            return redirect('folder_detail', folder_id=file.folder.id) if file.folder else redirect('dashboard')
    else:
        form = FileRenameForm(instance=file)
        
    return render(request, 'core/rename.html', {'form': form, 'obj': file, 'type': 'file'})

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
        
    # List all users who have folders or files
    # Or just list all root folders of all users?
    # Requirement: "admin có quyền quản lý, tải toàn bộ thư mục của toàn bộ user"
    # Admin View: List all users, click user -> see their root.
    
    # Simpler: List standard file manager but for ROOT of everything?
    # No, files belong to users.
    
    # We can fetch all root folders and orphan files.
    root_folders = Folder.objects.filter(parent__isnull=True).select_related('user')
    root_files = File.objects.filter(folder__isnull=True).select_related('user')
    
    context = {
        'root_folders': root_folders,
        'root_files': root_files,
        'is_admin_view': True
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
def download_all_zip(request):
    if not request.user.is_superuser:
        raise Http404

    root_folders = Folder.objects.filter(parent__isnull=True)
    
    # Create a temporary file for the master zip
    # We use a temp file to avoid loading everything into RAM
    import tempfile
    from django.http import FileResponse
    
    # Create a named temporary file that persists until we close and delete it manually
    # (or let FileResponse handle closing, but we need to ensure deletion)
    # Actually, with delete=True (default), it's deleted on close. 
    # But we need to close it after writing to read it? 
    # Or just seek(0)?
    # Windows has issues with opening same temp file twice, but this is Linux (Docker).
    # Best practice for Django FileResponse with temp file:
    # Use delete=False, then use background task or middleware to delete?
    # Or rely on OS to clean up /tmp?
    # Let's use delete=True and pass the open file handle to FileResponse.
    # FileResponse will close it, and then it is deleted.
    
    temp_file = tempfile.NamedTemporaryFile(delete=True) 
    
    with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as master_zip:
        used_names = set()
        for folder in root_folders:
            # Determine unique top-level folder name in zip
            base_name = folder.name
            candidate_name = base_name
            counter = 1
            while candidate_name in used_names:
                candidate_name = f"{base_name}_{counter}"
                counter += 1
            used_names.add(candidate_name)
            
            # Add folder contents directly to master zip
            _add_folder_to_zip(master_zip, folder, candidate_name)
            
            # Update status
            if not folder.is_downloaded:
                folder.is_downloaded = True
                folder.save()

    # Reset file pointer to beginning so it can be read
    temp_file.seek(0)
    
    response = FileResponse(temp_file, as_attachment=True, filename='all_folders.zip')
    return response

@login_required
def download_oldest_20_zip(request):
    if not request.user.is_superuser:
        raise Http404

    # Fetch 20 oldest root folders
    root_folders = Folder.objects.filter(parent__isnull=True).order_by('created_at')[:20]
    
    import tempfile
    from django.http import FileResponse
    
    temp_file = tempfile.NamedTemporaryFile(delete=True) 
    
    with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as master_zip:
        used_names = set()
        for folder in root_folders:
            base_name = folder.name
            candidate_name = base_name
            counter = 1
            while candidate_name in used_names:
                candidate_name = f"{base_name}_{counter}"
                counter += 1
            used_names.add(candidate_name)
            
            _add_folder_to_zip(master_zip, folder, candidate_name)
            
            if not folder.is_downloaded:
                folder.is_downloaded = True
                folder.save()

    temp_file.seek(0)
    
    response = FileResponse(temp_file, as_attachment=True, filename='oldest_20_folders.zip')
    return response

@login_required
def delete_downloaded_items(request):
    if not request.user.is_superuser:
        raise Http404
        
    if request.method == 'POST':
        # Delete all folders that are marked as downloaded
        deleted_count, _ = Folder.objects.filter(is_downloaded=True).delete()
        # Add message
        # from django.contrib import messages (ensure imported if not already)
    
    return redirect('admin_dashboard')

@login_required
def reset_download_status(request):
    if not request.user.is_superuser:
        raise Http404
        
    if request.method == 'POST':
        # Reset is_downloaded to False for all folders
        Folder.objects.update(is_downloaded=False)
        
    return redirect('admin_dashboard')
