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
    
    # Create a temporary file for the master zip to avoid high memory usage
    import tempfile
    
    # We will write the master zip to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_master_zip:
        with zipfile.ZipFile(temp_master_zip, 'w', zipfile.ZIP_DEFLATED) as master_zip:
            used_names = set()
            for folder in root_folders:
                # Create in-memory zip for this folder
                folder_buffer = BytesIO()
                with zipfile.ZipFile(folder_buffer, 'w', zipfile.ZIP_DEFLATED) as folder_zip:
                    _add_folder_to_zip(folder_zip, folder, folder.name)
                
                # Determine unique filename
                base_name = folder.name
                candidate_name = base_name
                counter = 1
                while candidate_name in used_names:
                    candidate_name = f"{base_name}_{counter}"
                    counter += 1
                used_names.add(candidate_name)
                
                zip_name = f"{candidate_name}.zip"
                master_zip.writestr(zip_name, folder_buffer.getvalue())
                
                # Update status
                if not folder.is_downloaded:
                    folder.is_downloaded = True
                    folder.save()
                    
        temp_master_zip.seek(0)
        # Read content to return (warning: if very large, this is still memory heavy, 
        # but better than holding everything in RAM twice during construction)
        # For true scalability, we'd use FileResponse with a generator or stream from disk.
        # Given constraints, we'll read it back or pass the file handle.
        
        # Re-open for reading
        
    # Serve the file
    # We use FileResponse for efficiency if possible or open it
    # We need to make sure it's deleted after. 
    # Simpler for now: Read into memory and return, then delete temp. 
    # (Not ideal for GBs of data, but fine for prototype)
    with open(temp_master_zip.name, 'rb') as f:
        data = f.read()
    
    os.unlink(temp_master_zip.name)
    
    response = HttpResponse(data, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=all_folders.zip'
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
