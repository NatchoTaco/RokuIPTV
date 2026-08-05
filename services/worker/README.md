# Worker Service

Milestone 2 runs the playlist import worker from the API package:

```sh
python -m streamforge_api.worker.runner
```

Docker Compose starts this as the `worker` service. It polls for queued playlist imports, queues due source refreshes, writes progress to `playlist_import_jobs`, stores import history, and preserves raw channels in `raw_channels`.
