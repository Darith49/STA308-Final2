from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, FormView
from django.contrib import messages
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.db import transaction

from accounts.permissions import RoleRequiredMixin
from accounts.models import Role
from .models import Upload, UploadError, UploadStatus, AuditLog, DatasetType
from .forms import UploadForm
from .tasks import process_upload_task
from services.templates_xlsx import generate_template_xlsx
from services.importers import generate_error_xlsx

class UploadCreateView(RoleRequiredMixin, FormView):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]
    template_name = 'uploads/upload_form.html'
    form_class = UploadForm

    def form_valid(self, form):
        upload = form.save(commit=False)
        upload.uploaded_by = self.request.user
        upload.original_filename = self.request.FILES['file'].name
        upload.file_hash = form.cleaned_data['file_hash']
        upload.status = UploadStatus.PENDING
        upload.save()

        # Record audit log
        AuditLog.objects.create(
            user=self.request.user,
            action='UPLOAD_INITIATED',
            target=f"File: {upload.original_filename} ({upload.get_dataset_type_display()})",
            details={'upload_id': upload.id, 'file_hash': upload.file_hash}
        )

        # Trigger processing (async Celery if configured, synchronous fallback)
        try:
            from config.celery import app as celery_app
            if celery_app and hasattr(process_upload_task, 'delay'):
                process_upload_task.delay(upload.id)
            else:
                process_upload_task(upload.id)
        except Exception:
            process_upload_task(upload.id)

        messages.success(
            self.request,
            f"File '{upload.original_filename}' uploaded successfully. Cleaning pipeline initiated."
        )
        return redirect('uploads:upload_detail', pk=upload.id)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['dataset_types'] = DatasetType.choices
        return ctx


class UploadListView(RoleRequiredMixin, ListView):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]
    model = Upload
    template_name = 'uploads/upload_list.html'
    context_object_name = 'uploads'
    paginate_by = 20

    def get_queryset(self):
        qs = Upload.objects.select_related('uploaded_by').order_by('-uploaded_at')
        dtype = self.request.GET.get('dataset_type')
        status = self.request.GET.get('status')
        if dtype:
            qs = qs.filter(dataset_type=dtype)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['dataset_types'] = DatasetType.choices
        ctx['status_choices'] = UploadStatus.choices
        ctx['selected_type'] = self.request.GET.get('dataset_type', '')
        ctx['selected_status'] = self.request.GET.get('status', '')
        return ctx


class UploadDetailView(RoleRequiredMixin, DetailView):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]
    model = Upload
    template_name = 'uploads/upload_detail.html'
    context_object_name = 'upload'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        errors_qs = self.object.errors.all().order_by('row_number')
        ctx['total_errors'] = errors_qs.count()
        ctx['sample_errors'] = errors_qs[:50]
        ctx['has_more_errors'] = errors_qs.count() > 50
        # Check if user has permission to delete this upload
        ctx['can_delete'] = self.request.user.profile.can_delete_upload(self.object)
        return ctx


class UploadDeleteView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]

    def post(self, request, pk):
        upload = get_object_or_404(Upload, pk=pk)
        
        # Verify specific delete permission (Registrar can only delete own uploads)
        if not request.user.profile.can_delete_upload(upload):
            raise PermissionDenied("Registrars may only delete their own uploads. Admins can delete any upload.")

        with transaction.atomic():
            AuditLog.objects.create(
                user=request.user,
                action='UPLOAD_ROLLBACK_DELETE',
                target=f"Upload #{upload.id} ({upload.get_dataset_type_display()}) - {upload.original_filename}",
                details={
                    'dataset_type': upload.dataset_type,
                    'rows_ok': upload.rows_ok,
                    'file_hash': upload.file_hash
                }
            )
            # Delete upload: cascades to delete all imported rows from this upload
            upload.delete()

        messages.success(request, f"Upload #{pk} and all associated imported records were rolled back successfully.")
        return redirect('uploads:upload_list')


class DownloadTemplateView(View):
    def get(self, request, dataset_type):
        if dataset_type not in dict(DatasetType.choices):
            return HttpResponse("Invalid dataset type", status=400)
        
        content = generate_template_xlsx(dataset_type)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{dataset_type}_template.xlsx"'
        return response


class DownloadErrorXlsxView(RoleRequiredMixin, View):
    allowed_roles = [Role.ADMIN, Role.REGISTRAR]

    def get(self, request, pk):
        upload = get_object_or_404(Upload, pk=pk)
        content = generate_error_xlsx(upload)
        response = HttpResponse(
            content,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="upload_{upload.id}_cleaning_errors.xlsx"'
        return response


class UploadStatusApiView(View):
    def get(self, request, pk):
        upload = get_object_or_404(Upload, pk=pk)
        return JsonResponse({
            'id': upload.id,
            'status': upload.status,
            'progress': upload.progress_percent,
            'rows_in': upload.rows_in,
            'rows_ok': upload.rows_ok,
            'rows_rejected': upload.rows_rejected,
            'report': upload.report,
            'error_message': upload.error_message,
        })
