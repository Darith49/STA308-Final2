/**
 * University Data Portal - Interactive Chart.js and Live Status Engine
 */

window.portalCharts = {};

/**
 * Generic Chart Loader: Fetches { labels, datasets } from DRF API endpoint and renders Chart.js
 */
async function loadChart(canvasId, type, apiUrl, queryParams = {}, optionsOverride = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const url = new URL(apiUrl, window.location.origin);
    Object.keys(queryParams).forEach(key => {
        if (queryParams[key]) {
            url.searchParams.append(key, queryParams[key]);
        }
    });

    try {
        const response = await fetch(url.toString(), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!response.ok) {
            console.warn(`Failed to fetch chart data from ${url.toString()}: status ${response.status}`);
            return;
        }
        const data = await response.json();

        // Default Modern Aesthetics for Chart.js
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: type === 'doughnut' || type === 'pie' ? 'right' : 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        font: { family: "'Plus Jakarta Sans', sans-serif", size: 12, weight: 600 }
                    }
                },
                tooltip: {
                    backgroundColor: '#0f172a',
                    titleFont: { family: "'Plus Jakarta Sans', sans-serif", size: 13, weight: 700 },
                    bodyFont: { family: "'Plus Jakarta Sans', sans-serif", size: 12 },
                    padding: 10,
                    cornerRadius: 8,
                }
            },
            scales: (type === 'doughnut' || type === 'pie') ? {} : {
                x: {
                    grid: { display: false },
                    ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' },
                    ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                }
            }
        };

        const mergedOptions = { ...defaultOptions, ...optionsOverride };

        // If chart already exists, update data smoothly
        if (window.portalCharts[canvasId]) {
            const chart = window.portalCharts[canvasId];
            chart.data.labels = data.labels || [];
            chart.data.datasets = data.datasets || [];
            chart.update();
        } else {
            const ctx = canvas.getContext('2d');
            window.portalCharts[canvasId] = new Chart(ctx, {
                type: type,
                data: {
                    labels: data.labels || [],
                    datasets: data.datasets || []
                },
                options: mergedOptions
            });
        }
    } catch (err) {
        console.error(`Error loading chart ${canvasId}:`, err);
    }
}

/**
 * KPI Loader: Updates dashboard KPI summary cards
 */
async function loadKpiSummary(queryParams = {}) {
    const url = new URL('/api/kpis/', window.location.origin);
    Object.keys(queryParams).forEach(k => {
        if (queryParams[k]) url.searchParams.append(k, queryParams[k]);
    });

    try {
        const resp = await fetch(url.toString());
        if (!resp.ok) return;
        const kpis = await resp.json();

        const elTotalStudents = document.getElementById('kpi-total-students');
        if (elTotalStudents) elTotalStudents.textContent = kpis.total_students.toLocaleString();

        const elTotalCourses = document.getElementById('kpi-total-courses');
        if (elTotalCourses) elTotalCourses.textContent = kpis.total_courses.toLocaleString();

        const elAvgScore = document.getElementById('kpi-avg-score');
        if (elAvgScore) elAvgScore.textContent = `${kpis.average_score}%`;

        const elPassRate = document.getElementById('kpi-pass-rate');
        if (elPassRate) elPassRate.textContent = `${kpis.pass_rate}%`;

        const elUploadsMonth = document.getElementById('kpi-uploads-month');
        if (elUploadsMonth) elUploadsMonth.textContent = kpis.uploads_this_month;
    } catch (e) {
        console.error('Error fetching KPIs:', e);
    }
}

/**
 * Live Upload Status Poller
 */
function initUploadPoller(uploadId) {
    const statusBadge = document.getElementById('upload-status-badge');
    const progressBar = document.getElementById('upload-progress-bar');
    const progressText = document.getElementById('upload-progress-text');
    const processingAlert = document.getElementById('upload-processing-alert');

    if (!uploadId || !statusBadge) return;

    let pollInterval = setInterval(async () => {
        try {
            const resp = await fetch(`/uploads/api/${uploadId}/status/`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
            }
            if (progressText) {
                progressText.textContent = `${data.progress}% completed`;
            }

            if (data.status === 'done' || data.status === 'failed') {
                clearInterval(pollInterval);
                // Reload page to display full final report
                window.location.reload();
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 2000);
}

// Global hook
window.loadChart = loadChart;
window.loadKpiSummary = loadKpiSummary;
window.initUploadPoller = initUploadPoller;
