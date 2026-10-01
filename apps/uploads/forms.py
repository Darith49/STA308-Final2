from django import forms
from django.core.exceptions import ValidationError
from apps.uploads.models import DatasetType
from apps.uploads.validators import (
    validate_xlsx_file,
    compute_file_sha256,
    validate_duplicate_hash,
    validate_dataset_schema,
)


class UploadForm(forms.Form):
    dataset_type = forms.ChoiceField(
        choices=DatasetType.choices,
        initial=DatasetType.COURSES,
        widget=forms.Select(attrs={"class": "form-select", "id": "datasetTypeSelect"}),
        help_text="Select dataset type (Upload Order: Courses → Students → Grades → Attendance)."
    )

    file = forms.FileField(
        validators=[validate_xlsx_file],
        widget=forms.FileInput(attrs={
            "class": "form-control",
            "id": "fileInput",
            "accept": ".xlsx",
        }),
        help_text="Upload Microsoft Excel workbook (.xlsx). Max 20 MB."
    )

    # Advanced configurable cleaning pipeline parameters
    fuzzy_threshold = forms.IntegerField(
        initial=85,
        min_value=50,
        max_value=100,
        widget=forms.NumberInput(attrs={"class": "form-control", "id": "fuzzyThresholdInput"}),
        help_text="Categorical typo matching sensitivity (50-100%). Default: 85%."
    )

    outlier_method = forms.ChoiceField(
        choices=[
            ("iqr", "Tukey 1.5x IQR Rule (Recommended)"),
            ("zscore", "Modified Z-Score (Median Absolute Deviation > 3.5)"),
        ],
        initial="iqr",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Method used to detect statistical outliers."
    )

    missing_numeric_strategy = forms.ChoiceField(
        choices=[
            ("flag", "Flag in Quality Report (Preserve NaN - Default)"),
            ("median", "Impute with Column Median (Robust against outliers)"),
            ("mean", "Impute with Column Mean (Note: attenuates variance)"),
        ],
        initial="flag",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Statistical strategy for missing numeric values."
    )

    missing_category_strategy = forms.ChoiceField(
        choices=[
            ("flag", "Flag in Quality Report (Preserve NaN - Default)"),
            ("unknown", "Fill with 'Unknown' (Preserves row count)"),
        ],
        initial="flag",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Strategy for missing categorical values."
    )

    ambiguous_date_preference = forms.ChoiceField(
        choices=[
            ("DMY", "Day First (DD/MM/YYYY - International / UK)"),
            ("MDY", "Month First (MM/DD/YYYY - US Standard)"),
        ],
        initial="DMY",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Disambiguation rule for dual-numeric dates like 03/04/2024."
    )

    def clean(self):
        cleaned_data = super().clean()
        file_obj = cleaned_data.get("file")
        dataset_type = cleaned_data.get("dataset_type", DatasetType.GENERIC)

        if file_obj:
            # 1. Security & format checks
            validate_xlsx_file(file_obj)

            # 2. Check duplicate hash
            sha256 = compute_file_sha256(file_obj)
            validate_duplicate_hash(sha256)
            cleaned_data["sha256"] = sha256

            # 3. Check dataset schema & upload order prerequisites
            validate_dataset_schema(file_obj, dataset_type)

        return cleaned_data
