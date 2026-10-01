"""
Views and DRF endpoints for Dashboards and Live Charts.
"""

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions

from apps.uploads.models import Upload, ColumnProfile, QualityReport, UploadStatus
from apps.dashboards.models import DashboardConfig
from apps.dashboards.serializers import (
    UploadStatusSerializer,
    ColumnProfileSerializer,
    QualityReportSerializer,
    DashboardConfigSerializer,
)
from apps.dashboards.aggregation import aggregate_chart_data, load_cleaned_dataframe


@login_required
def dashboard_view(request, upload_id):
    """
    Main interactive live analytics dashboard page.
    Renders KPI cards, dynamic filter controls, auto-suggested charts,
    and Chart.js 4 canvas elements.
    """
    upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

    if upload.status == UploadStatus.PROCESSING:
        return redirect("uploads:processing", upload_id=upload.id)
    elif upload.status == UploadStatus.FAILED:
        return redirect("uploads:list")

    profiles = upload.column_profiles.all().order_by("id")
    category_columns = profiles.filter(role="category")
    numeric_columns = profiles.filter(role="numeric")
    date_columns = profiles.filter(role="date")

    # Get sample unique values for category filters
    filter_categories = {}
    try:
        df = load_cleaned_dataframe(upload)
        for col in category_columns[:5]:
            vals = df[col.name_clean].dropna().unique().tolist()[:15]
            filter_categories[col.name_clean] = sorted([str(v) for v in vals])
    except Exception:
        pass

    # Retrieve existing saved dashboard configs for this upload
    saved_configs = DashboardConfig.objects.filter(upload=upload, owner=request.user)

    return render(
        request,
        "dashboards/dashboard.html",
        {
            "upload": upload,
            "profiles": profiles,
            "category_columns": category_columns,
            "numeric_columns": numeric_columns,
            "date_columns": date_columns,
            "filter_categories": filter_categories,
            "saved_configs": saved_configs,
        },
    )


# --- DRF REST API ENDPOINTS ---

class UploadStatusAPIView(APIView):
    """GET /api/uploads/<id>/status/ - Polled during L2 live processing."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)
        serializer = UploadStatusSerializer(upload)
        return Response(serializer.data)


class UploadReportAPIView(APIView):
    """GET /api/uploads/<id>/report/ - Full Data Quality Report JSON."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)
        if not hasattr(upload, "report"):
            return Response({"error": "Report not ready yet."}, status=status.HTTP_404_NOT_FOUND)
        serializer = QualityReportSerializer(upload.report)
        return Response(serializer.data)


class UploadColumnsAPIView(APIView):
    """GET /api/uploads/<id>/columns/ - Statistical column profiles."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)
        profiles = upload.column_profiles.all()
        serializer = ColumnProfileSerializer(profiles, many=True)
        return Response(serializer.data)


class ChartDataAPIView(APIView):
    """
    GET /api/uploads/<id>/chart-data/
    Computes server-side aggregated datasets for Chart.js 4.
    Query params: type, x, y, agg, bins, filters
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, upload_id):
        upload = get_object_or_404(Upload, id=upload_id, owner=request.user)

        chart_type = request.GET.get("type", "bar")
        x_col = request.GET.get("x")
        y_col = request.GET.get("y")
        agg = request.GET.get("agg", "mean")
        bins = int(request.GET.get("bins", 12))

        # Parse JSON filters if provided
        filters = {}
        raw_filters = request.GET.get("filters")
        if raw_filters:
            try:
                filters = json.loads(raw_filters)
            except Exception:
                pass

        try:
            chart_payload = aggregate_chart_data(
                upload=upload,
                chart_type=chart_type,
                x_col=x_col,
                y_col=y_col,
                agg_func=agg,
                bins=bins,
                filters=filters,
            )
            return Response(chart_payload)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DashboardConfigViewSet(viewsets.ModelViewSet):
    """CRUD API for saved dashboard layouts and widgets."""
    serializer_class = DashboardConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DashboardConfig.objects.filter(owner=self.request.user)
        upload_id = self.request.query_params.get("upload_id")
        if upload_id:
            qs = qs.filter(upload_id=upload_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
