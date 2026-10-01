from django import forms
from apps.uploads.validators import validate_xlsx_file


class UploadForm(forms.Form):
    file = forms.FileField(
        validators=[validate_xlsx_file],
        widget=forms.FileInput(attrs={
            "class": "form-control",
            "id": "fileInput",
            "accept": ".xlsx",
        }),
        help_text="Upload clean or messy Microsoft Excel workbook (.xlsx). Max 20 MB."
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
