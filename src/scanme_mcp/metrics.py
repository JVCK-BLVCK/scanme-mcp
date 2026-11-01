"""
Prometheus metrics used by the ScanMe Nuclei scanner.

Three types of metrics:
  Counter   — monotonically increasing number (total scans started)
  Gauge     — current value that can go up or down (active scans)
  Histogram — distribution of values (scan duration in seconds)

Why Prometheus?
  The de facto standard for infrastructure metrics.
  Works with Grafana for visualisation, AlertManager for alerting,
  and every cloud provider's monitoring stack.
  Pull-based model — Prometheus scrapes /metrics, you don't push data anywhere.
"""
from prometheus_client import Counter, Gauge, Histogram

# ___Scan lifecycle counters___

SCANS_TOTAL = Counter(
    "scanme_scans_total",
    "Total number of scans submitted",
    ["status"]   # label: completed, failed, timeout
)

SCANS_ACTIVE = Gauge(
    "scanme_scans_active",
    "Number of scans currently running"
)

# ___Scan Duration___
#
# Histogram buckets define the resolution of duration tracking.
# These buckets cover 1s, 30s, 1min, 2min, 5min, 10min — the realistic
# range for Nuclei scan durations.

SCAN_DURATION = Histogram(
    "scanme_scan_duration_seconds",
    "Duration of Nuclei scans in seconds",
    buckets=[1, 5, 15, 30, 60, 120, 300, 600]
)

# ___Finding statistics___

FINDINGS_TOTAL = Counter(
    "scanme_findings_total",
    "Total vulnerability findings discovered",
    ["severity"]   # label: critical, high, medium, low, info
)

# ___External API calls___ 

NVD_API_CALLS = Counter(
    "scanme_nvd_api_calls_total",
    "Total calls to NVD API for enrichment",
    ["status"]   # success, error, rate_limited
)

EPSS_API_CALLS = Counter(
    "scanme_epss_api_calls_total",
    "Total calls to EPSS API for enrichment",
    ["status"]
)

