from typing import Literal

SourceState = Literal["healthy", "importing", "warning", "offline", "failed", "disabled", "pending"]
SourceType = Literal["m3u_url", "m3u_upload", "demo_playlist"]
ImportJobState = Literal["queued", "running", "succeeded", "failed"]
PlaylistImportState = Literal["queued", "running", "completed", "warning", "failed"]

SOURCE_STATUS_LABELS: dict[str, str] = {
    "healthy": "Healthy",
    "importing": "Importing",
    "warning": "Warning",
    "offline": "Offline",
    "failed": "Failed",
    "disabled": "Disabled",
    "pending": "Pending",
}
