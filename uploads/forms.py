from django import forms
from .models import Upload, DatasetType
from .validators import validate_excel_file, compute_file_hash

class UploadForm(forms.ModelForm):
    allow_duplicate = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Upload
        fields = ['dataset_type', 'file']
        widgets = {
            'dataset_type': forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'dataset_type_select'}),
            'file': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'id': 'file_input', 'accept': '.xlsx'}),
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data.get('file')
        if uploaded_file:
            validate_excel_file(uploaded_file)
        return uploaded_file

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = cleaned_data.get('file')
        allow_duplicate = cleaned_data.get('allow_duplicate')

        if uploaded_file:
            f_hash = compute_file_hash(uploaded_file)
            cleaned_data['file_hash'] = f_hash
            # Check duplicate detection
            existing = Upload.objects.filter(file_hash=f_hash).first()
            if existing and not allow_duplicate:
                self.add_error(
                    'file',
                    forms.ValidationError(
                        f"Duplicate file detected: An identical file was already imported on "
                        f"{existing.uploaded_at.strftime('%Y-%m-%d %H:%M')} (Upload #{existing.id}). "
                        f"If you wish to re-process this file, check the 'Force Re-upload' option below.",
                        code='duplicate_hash'
                    )
                )
        return cleaned_data
