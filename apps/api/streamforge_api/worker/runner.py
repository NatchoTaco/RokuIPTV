from __future__ import annotations

import logging
import time
import uuid

from streamforge_api.core.config import get_settings
from streamforge_api.core.logging import configure_logging
from streamforge_api.db.session import create_engine_from_settings, create_session_factory
from streamforge_api.services.source_import import SourceImportService


def run_once(worker_id: str | None = None) -> bool:
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    with session_factory() as db:
        service = SourceImportService(db, settings)
        service.queue_due_refreshes()
        return service.process_next_queued_job(worker_id=worker_id)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("streamforge.worker")
    worker_id = f"{uuid.uuid4()}"
    logger.info("worker.started", extra={"worker_id": worker_id})
    while True:
        processed = run_once(worker_id=worker_id)
        if not processed:
            time.sleep(settings.source_worker_poll_seconds)


if __name__ == "__main__":
    main()
