from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, query: str, options: dict[str, Any]) -> dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex}"
        job = {
            "jobId": job_id,
            "status": "queued",
            "query": query,
            "options": options,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "result": None,
            "error": None,
        }
        self.save(job)
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        if not self.is_safe_id(job_id):
            return None
        path = self.root / f"{job_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, job: dict[str, Any]) -> None:
        job["updatedAt"] = utc_now()
        path = self.root / f"{job['jobId']}.json"
        path.write_text(json.dumps(job, indent=2), encoding="utf-8")

    def mark_running(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        job["status"] = "running"
        self.save(job)

    def mark_complete(self, job_id: str, result: dict[str, Any]) -> None:
        job = self.get(job_id)
        if not job:
            return
        job["status"] = "complete"
        job["result"] = result
        self.save(job)

    def mark_failed(self, job_id: str, error: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        job["status"] = "failed"
        job["error"] = error
        self.save(job)

    @staticmethod
    def is_safe_id(value: str) -> bool:
        return value.startswith("job_") and value.replace("job_", "").isalnum()

