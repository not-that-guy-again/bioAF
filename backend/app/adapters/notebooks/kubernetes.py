"""Kubernetes notebook adapter.

Supports local/mock mode for development and real K8s API for production.
Mode is controlled by the BIOAF_COMPUTE_MODE environment variable.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from app.adapters.base import NotebookProvider

logger = logging.getLogger("bioaf.adapters.notebooks.k8s")

# In-memory session store for local mode
_local_sessions: dict[str, dict] = {}


class KubernetesNotebookProvider(NotebookProvider):
    """Kubernetes notebook backend with local mode for development."""

    def __init__(self):
        self._mode = os.environ.get("BIOAF_COMPUTE_MODE", "local")

    @property
    def is_local(self) -> bool:
        return self._mode == "local"

    async def launch_session(self, session_spec: dict) -> dict:
        if self.is_local:
            return self._local_launch_session(session_spec)
        return await self._k8s_launch_session(session_spec)

    async def terminate_session(self, session_id: str) -> dict:
        if self.is_local:
            return self._local_terminate_session(session_id)
        return await self._k8s_terminate_session(session_id)

    async def get_session_status(self, session_id: str) -> dict:
        if self.is_local:
            return self._local_get_session_status(session_id)
        return await self._k8s_get_session_status(session_id)

    async def list_sessions(self, filters: dict | None = None) -> list[dict]:
        if self.is_local:
            return self._local_list_sessions(filters)
        return await self._k8s_list_sessions(filters)

    async def get_connection_command(self, session_id: str) -> str:
        namespace = "bioaf-interactive"
        return f"kubectl exec -it -n {namespace} pod/notebook-{session_id} -- /bin/bash"

    # -- Local mode implementations --

    def _local_launch_session(self, session_spec: dict) -> dict:
        session_id = f"local-{uuid.uuid4().hex[:12]}"
        session_type = session_spec.get("session_type", "jupyter")
        port = 8888 if session_type == "jupyter" else 8787

        session_data = {
            "session_id": session_id,
            "status": "running",
            "url": f"http://localhost:{port}",
            "session_type": session_type,
            "resource_profile": session_spec.get("resource_profile", "small"),
            "namespace": "bioaf-interactive",
            "node_pool": "bioaf-interactive",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _local_sessions[session_id] = session_data
        logger.info("Local mode: launched session %s (%s)", session_id, session_type)
        return session_data

    def _local_terminate_session(self, session_id: str) -> dict:
        if session_id in _local_sessions:
            _local_sessions[session_id]["status"] = "stopped"
            _local_sessions[session_id]["stopped_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Local mode: terminated session %s", session_id)
        return {
            "session_id": session_id,
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _local_get_session_status(self, session_id: str) -> dict:
        if session_id in _local_sessions:
            return _local_sessions[session_id]
        return {
            "session_id": session_id,
            "status": "unknown",
        }

    def _local_list_sessions(self, filters: dict | None = None) -> list[dict]:
        sessions = list(_local_sessions.values())
        if filters:
            if "status" in filters:
                sessions = [s for s in sessions if s.get("status") == filters["status"]]
            if "session_type" in filters:
                sessions = [s for s in sessions if s.get("session_type") == filters["session_type"]]
        return sessions

    # -- K8s API implementations (production) --

    async def _k8s_launch_session(self, session_spec: dict) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_terminate_session(self, session_id: str) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_get_session_status(self, session_id: str) -> dict:
        raise NotImplementedError("K8s production mode requires a running cluster")

    async def _k8s_list_sessions(self, filters: dict | None = None) -> list[dict]:
        raise NotImplementedError("K8s production mode requires a running cluster")
