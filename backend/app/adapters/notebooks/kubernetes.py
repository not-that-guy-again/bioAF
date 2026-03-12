"""Kubernetes notebook adapter.

Supports local/mock mode for development and real K8s API for production.
Mode is controlled by the BIOAF_COMPUTE_MODE environment variable.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from app.adapters.base import NotebookProvider
from app.services.session_persistence import (
    generate_sync_in_command,
    generate_sync_out_command,
)

logger = logging.getLogger("bioaf.adapters.notebooks.k8s")

# In-memory session store for local mode
_local_sessions: dict[str, dict] = {}

DEFAULT_NOTEBOOK_NAMESPACE = "bioaf-notebooks"
HOME_DIR = "/home/jovyan"


class KubernetesNotebookProvider(NotebookProvider):
    """Kubernetes notebook backend with local mode for development."""

    def __init__(self):
        self._mode = os.environ.get("BIOAF_COMPUTE_MODE", "local")
        self._namespace_ready = False

    @property
    def is_local(self) -> bool:
        return self._mode == "local"

    async def launch_session(self, session_spec: dict) -> dict:
        if self.is_local:
            return self._local_launch_session(session_spec)
        return await self._k8s_launch_session(session_spec)

    async def terminate_session(self, session_id: str, **kwargs) -> dict:
        if self.is_local:
            return self._local_terminate_session(session_id)
        return await self._k8s_terminate_session(session_id=session_id, **kwargs)

    async def get_session_status(self, session_id: str, **kwargs) -> dict:
        if self.is_local:
            return self._local_get_session_status(session_id)
        return await self._k8s_get_session_status(session_id=session_id, **kwargs)

    async def list_sessions(self, filters: dict | None = None) -> list[dict]:
        if self.is_local:
            return self._local_list_sessions(filters)
        return await self._k8s_list_sessions(filters)

    async def get_connection_command(self, session_id: str) -> str:
        namespace = DEFAULT_NOTEBOOK_NAMESPACE
        return f"kubectl exec -it -n {namespace} pod/bioaf-notebook-{session_id} -- /bin/bash"

    # -- K8s client helpers --

    def _get_k8s_core_client(self):
        """Get a Kubernetes CoreV1Api client. Tests mock this method."""
        from kubernetes import client, config

        config.load_incluster_config()
        return client.CoreV1Api()

    def _get_k8s_rbac_client(self):
        """Get a Kubernetes RbacAuthorizationV1Api client. Tests mock this method."""
        from kubernetes import client, config

        config.load_incluster_config()
        return client.RbacAuthorizationV1Api()

    # -- Namespace setup --

    async def ensure_notebook_namespace(
        self, namespace: str = DEFAULT_NOTEBOOK_NAMESPACE
    ) -> None:
        """Ensure the notebook namespace and service account exist."""
        from kubernetes import client
        from kubernetes.client.rest import ApiException

        if self._namespace_ready:
            return

        core_v1 = self._get_k8s_core_client()
        rbac_v1 = self._get_k8s_rbac_client()

        try:
            core_v1.read_namespace(name=namespace)
            logger.info("Namespace %s already exists, skipping setup", namespace)
            self._namespace_ready = True
            return
        except ApiException as e:
            if e.status != 404:
                raise

        core_v1.create_namespace(
            body=client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=namespace,
                    labels={"bioaf.io/managed": "true"},
                )
            )
        )
        logger.info("Created namespace %s", namespace)

        core_v1.create_namespaced_service_account(
            namespace=namespace,
            body=client.V1ServiceAccount(
                metadata=client.V1ObjectMeta(
                    name="bioaf-notebook-runner",
                    labels={"bioaf.io/managed": "true"},
                )
            ),
        )
        logger.info("Created service account bioaf-notebook-runner in %s", namespace)

        rbac_v1.create_namespaced_role_binding(
            namespace=namespace,
            body=client.V1RoleBinding(
                metadata=client.V1ObjectMeta(
                    name="bioaf-notebook-runner-binding",
                    labels={"bioaf.io/managed": "true"},
                ),
                role_ref=client.V1RoleRef(
                    api_group="rbac.authorization.k8s.io",
                    kind="ClusterRole",
                    name="edit",
                ),
                subjects=[
                    client.RbacV1Subject(
                        kind="ServiceAccount",
                        name="bioaf-notebook-runner",
                        namespace=namespace,
                    )
                ],
            ),
        )
        logger.info("Created role binding in %s", namespace)
        self._namespace_ready = True

    # -- K8s API implementations (production) --

    async def _k8s_launch_session(self, session_spec: dict) -> dict:
        """Launch a notebook pod on the GKE interactive node pool."""
        session_id = session_spec.get("session_id", 0)
        session_type = session_spec.get("session_type", "jupyter")
        user_id = session_spec.get("user_id", 0)
        namespace = DEFAULT_NOTEBOOK_NAMESPACE

        await self.ensure_notebook_namespace(namespace)

        pod_name = f"bioaf-notebook-{session_id}"
        service_name = f"bioaf-notebook-svc-{session_id}"
        gcs_home_prefix = f"gs://bioaf-working/notebooks/{user_id}/"

        # Determine container command based on session type
        if session_type == "jupyter":
            container_port = 8888
            container_command = [
                "jupyter", "lab",
                "--ip=0.0.0.0",
                f"--port={container_port}",
                "--no-browser",
                "--NotebookApp.token=''",
                "--NotebookApp.password=''",
            ]
        else:
            container_port = 8787
            container_command = [
                "rserver",
                "--www-address=0.0.0.0",
                f"--www-port={container_port}",
                "--auth-none=1",
            ]

        # Build GCS sync init container
        sync_in_cmd = generate_sync_in_command(gcs_home_prefix, HOME_DIR)
        init_container = {
            "name": "gcs-sync-in",
            "image": "google/cloud-sdk:slim",
            "command": sync_in_cmd,
            "volumeMounts": [{"name": "home", "mountPath": HOME_DIR}],
        }

        # Build notebook container
        image = session_spec.get("image", "bioaf-scrna:latest")
        notebook_container = {
            "name": "notebook",
            "image": image,
            "command": container_command,
            "ports": [{"containerPort": container_port}],
            "volumeMounts": [{"name": "home", "mountPath": HOME_DIR}],
            "resources": {
                "requests": {
                    "cpu": str(session_spec.get("cpu_cores", 2)),
                    "memory": f"{session_spec.get('memory_gb', 4)}Gi",
                },
                "limits": {
                    "cpu": str(session_spec.get("cpu_cores", 2)),
                    "memory": f"{session_spec.get('memory_gb', 4)}Gi",
                },
            },
        }

        # Pod manifest
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {
                    "bioaf.io/session": str(session_id),
                    "bioaf.io/user": str(user_id),
                    "bioaf.io/type": session_type,
                    "bioaf.io/pool": "interactive",
                },
            },
            "spec": {
                "nodeSelector": {"bioaf.io/pool": "interactive"},
                "tolerations": [
                    {
                        "key": "bioaf.io/pool",
                        "value": "interactive",
                        "effect": "NoSchedule",
                    }
                ],
                "serviceAccountName": "bioaf-notebook-runner",
                "initContainers": [init_container],
                "containers": [notebook_container],
                "volumes": [
                    {"name": "home", "emptyDir": {"sizeLimit": "10Gi"}},
                ],
                "restartPolicy": "Never",
            },
        }

        core_client = self._get_k8s_core_client()
        core_client.create_namespaced_pod(namespace=namespace, body=pod_manifest)
        logger.info("Created pod %s in %s", pod_name, namespace)

        # Create Service
        service_manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "bioaf.io/session": str(session_id),
                },
            },
            "spec": {
                "selector": {"bioaf.io/session": str(session_id)},
                "ports": [
                    {
                        "port": container_port,
                        "targetPort": container_port,
                        "protocol": "TCP",
                    }
                ],
                "type": "ClusterIP",
            },
        }
        core_client.create_namespaced_service(
            namespace=namespace, body=service_manifest
        )
        logger.info("Created service %s in %s", service_name, namespace)

        # Wait for pod readiness (poll up to 5 minutes)
        for _ in range(60):
            pod = core_client.read_namespaced_pod(name=pod_name, namespace=namespace)
            if pod.status.phase == "Running":
                conditions = pod.status.conditions or []
                ready = any(
                    c.type == "Ready" and c.status == "True" for c in conditions
                )
                if ready:
                    break
            if pod.status.phase in ("Failed", "Unknown"):
                logger.error("Pod %s entered %s phase", pod_name, pod.status.phase)
                return {
                    "session_id": session_id,
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "status": "error",
                    "access_url": None,
                    "gcs_home_prefix": gcs_home_prefix,
                }
            await asyncio.sleep(5)

        access_url = (
            f"http://{service_name}.{namespace}.svc.cluster.local:{container_port}"
        )

        return {
            "session_id": session_id,
            "pod_name": pod_name,
            "namespace": namespace,
            "status": "running",
            "access_url": access_url,
            "gcs_home_prefix": gcs_home_prefix,
        }

    async def _k8s_terminate_session(
        self,
        session_id: int | str = 0,
        pod_name: str = "",
        namespace: str = DEFAULT_NOTEBOOK_NAMESPACE,
        gcs_home_prefix: str = "",
    ) -> dict:
        """Sync to GCS, then delete pod and service."""
        from kubernetes.stream import stream

        core_client = self._get_k8s_core_client()

        # Sync home directory to GCS before termination
        if gcs_home_prefix and pod_name:
            try:
                sync_cmd = generate_sync_out_command(HOME_DIR, gcs_home_prefix)
                stream(
                    core_client.connect_get_namespaced_pod_exec,
                    name=pod_name,
                    namespace=namespace,
                    command=sync_cmd,
                    stderr=True,
                    stdin=False,
                    stdout=True,
                    tty=False,
                )
                logger.info("GCS sync-out complete for pod %s", pod_name)
            except Exception as e:
                logger.warning("GCS sync-out failed for pod %s: %s", pod_name, e)

        # Delete pod
        try:
            core_client.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info("Deleted pod %s", pod_name)
        except Exception as e:
            logger.warning("Failed to delete pod %s: %s", pod_name, e)

        # Delete service
        service_name = f"bioaf-notebook-svc-{session_id}"
        try:
            core_client.delete_namespaced_service(
                name=service_name, namespace=namespace
            )
            logger.info("Deleted service %s", service_name)
        except Exception as e:
            logger.warning("Failed to delete service %s: %s", service_name, e)

        return {
            "session_id": session_id,
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _k8s_get_session_status(
        self,
        session_id: int | str = 0,
        pod_name: str = "",
        namespace: str = DEFAULT_NOTEBOOK_NAMESPACE,
    ) -> dict:
        """Query K8s API for pod status."""
        core_client = self._get_k8s_core_client()

        try:
            pod = core_client.read_namespaced_pod(name=pod_name, namespace=namespace)
        except Exception:
            return {
                "session_id": session_id,
                "status": "unknown",
                "pod_name": pod_name,
            }

        phase = pod.status.phase
        if phase == "Running":
            conditions = pod.status.conditions or []
            ready = any(
                c.type == "Ready" and c.status == "True" for c in conditions
            )
            status = "running" if ready else "starting"
        elif phase == "Pending":
            status = "starting"
        elif phase in ("Failed", "Unknown"):
            status = "error"
        elif phase == "Succeeded":
            status = "stopped"
        else:
            status = "unknown"

        return {
            "session_id": session_id,
            "status": status,
            "pod_name": pod_name,
            "namespace": namespace,
        }

    async def _k8s_list_sessions(
        self, filters: dict | None = None
    ) -> list[dict]:
        """List notebook pods in the namespace."""
        core_client = self._get_k8s_core_client()
        namespace = DEFAULT_NOTEBOOK_NAMESPACE

        label_selector = "bioaf.io/pool=interactive"
        if filters and "session_type" in filters:
            label_selector += f",bioaf.io/type={filters['session_type']}"

        pod_list = core_client.list_namespaced_pod(
            namespace=namespace,
            label_selector=label_selector,
        )

        sessions = []
        for pod in pod_list.items:
            labels = pod.metadata.labels or {}
            phase = pod.status.phase
            status = "running" if phase == "Running" else "starting"
            if phase in ("Failed", "Unknown"):
                status = "error"

            sessions.append(
                {
                    "session_id": labels.get("bioaf.io/session", ""),
                    "pod_name": pod.metadata.name,
                    "session_type": labels.get("bioaf.io/type", ""),
                    "user_id": labels.get("bioaf.io/user", ""),
                    "status": status,
                    "namespace": namespace,
                }
            )
        return sessions

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
            _local_sessions[session_id]["stopped_at"] = datetime.now(
                timezone.utc
            ).isoformat()
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
                sessions = [
                    s for s in sessions if s.get("status") == filters["status"]
                ]
            if "session_type" in filters:
                sessions = [
                    s
                    for s in sessions
                    if s.get("session_type") == filters["session_type"]
                ]
        return sessions
