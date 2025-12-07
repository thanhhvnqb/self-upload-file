from django import forms
from .models import Folder, File

class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tên thư mục'})
        }

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].widget.attrs.update({'multiple': True})
