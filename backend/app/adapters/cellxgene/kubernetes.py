"""Kubernetes cellxgene adapter.

Supports local/mock mode for development and real K8s API for production.
Mode is controlled by the BIOAF_COMPUTE_MODE environment variable.

When running outside the cluster (e.g., Docker Compose on a VM), the adapter
builds a K8s client from platform_config credentials (gke_cluster_endpoint,
gke_cluster_ca_cert, GCP service account key).
"""

import asyncio
import base64
import json as _json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone

from kubernetes import client, config

from app.adapters.base import CellxgeneProvider

logger = logging.getLogger("bioaf.adapters.cellxgene.k8s")


def _get_gcp_token(service_account_key_json: str) -> str:
    """Exchange a GCP service account key for an access token."""
    from google.oauth2 import service_account
    import google.auth.transport.requests

    key_data = _json.loads(service_account_key_json)
    credentials = service_account.Credentials.from_service_account_info(
        key_data,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


# In-memory instance store for local mode
_local_instances: dict[int, dict] = {}

DEFAULT_CELLXGENE_NAMESPACE = "bioaf-cellxgene"


class KubernetesCellxgeneProvider(CellxgeneProvider):
    """Kubernetes cellxgene backend with local mode for development."""

    _TOKEN_TTL_SECONDS = 2700  # 45 minutes

    def __init__(self, session_factory=None):
        self._mode = os.environ.get("BIOAF_COMPUTE_MODE", "local")
        self._session_factory = session_factory
        self._api_client: client.ApiClient | None = None
        self._client_created_at: float = 0.0
        self._cluster_config: dict | None = None
        self._namespace_ready = False

    @property
    def is_local(self) -> bool:
        return self._mode == "local"

    async def deploy(self, publication_id: int, gcs_uri: str, dataset_name: str) -> dict:
        if self.is_local:
            return self._local_deploy(publication_id, gcs_uri, dataset_name)
        return await self._k8s_deploy(publication_id, gcs_uri, dataset_name)

    async def teardown(self, publication_id: int) -> dict:
        if self.is_local:
            return self._local_teardown(publication_id)
        return await self._k8s_teardown(publication_id)

    async def get_status(self, publication_id: int) -> dict:
        if self.is_local:
            return self._local_get_status(publication_id)
        return await self._k8s_get_status(publication_id)

    # -- Cluster config --

    async def load_cluster_config(self, force: bool = False) -> dict:
        """Read GKE cluster config from platform_config.

        Caches the result. Re-reads when forced or when the cached endpoint
        is missing/null so newly deployed clusters are picked up.
        """
        if self._cluster_config is not None and not force:
            endpoint = self._cluster_config.get("gke_cluster_endpoint", "")
            if endpoint and endpoint != "null":
                return self._cluster_config

        from sqlalchemy import text as sa_text

        if not self._session_factory:
            self._cluster_config = {}
            return self._cluster_config

        async with self._session_factory() as session:
            result = await session.execute(
                sa_text(
                    "SELECT key, value FROM platform_config "
                    "WHERE key IN ("
                    "  'gke_cluster_endpoint', 'gke_cluster_ca_cert',"
                    "  'gcp_credential_source', 'gcp_service_account_key',"
                    "  'gke_cluster_name', 'gcp_project_id', 'gcp_zone'"
                    ")"
                )
            )
            self._cluster_config = {r[0]: r[1] for r in result.fetchall()}

        if force:
            self._api_client = None

        return self._cluster_config

    def _build_out_of_cluster_client(self) -> client.ApiClient:
        """Build a K8s ApiClient using platform_config credentials."""
        cfg = self._cluster_config or {}

        endpoint = cfg.get("gke_cluster_endpoint", "")
        ca_cert_b64 = cfg.get("gke_cluster_ca_cert", "")
        sa_key = cfg.get("gcp_service_account_key", "")

        if not endpoint or endpoint == "null":
            raise RuntimeError("No GKE cluster endpoint in platform_config. Deploy the compute stack first.")

        if not endpoint.startswith("https://"):
            endpoint = f"https://{endpoint}"

        token = _get_gcp_token(sa_key)

        ca_cert_bytes = base64.b64decode(ca_cert_b64)
        ca_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
        ca_file.write(ca_cert_bytes)
        ca_file.close()

        configuration = client.Configuration()
        configuration.host = endpoint
        configuration.ssl_ca_cert = ca_file.name
        configuration.api_key = {"authorization": f"Bearer {token}"}

        self._client_created_at = time.monotonic()
        return client.ApiClient(configuration)

    def _is_token_expired(self) -> bool:
        if self._client_created_at == 0.0:
            return False
        return (time.monotonic() - self._client_created_at) > self._TOKEN_TTL_SECONDS

    async def _get_api_client_async(self) -> client.ApiClient:
        """Get or create a K8s ApiClient, trying incluster first."""
        if self._api_client is not None and not self._is_token_expired():
            return self._api_client

        if self._is_token_expired():
            logger.info("GCP access token approaching expiry, refreshing K8s client")
            self._api_client = None

        try:
            config.load_incluster_config()
            self._api_client = client.ApiClient()
            logger.info("Using incluster K8s config")
        except Exception:
            logger.info("Not running in cluster, using platform_config credentials")
            await self.load_cluster_config(force=True)
            try:
                self._api_client = self._build_out_of_cluster_client()
                logger.info(
                    "K8s client built for endpoint %s",
                    (self._cluster_config or {}).get("gke_cluster_endpoint"),
                )
            except Exception:
                logger.exception("Failed to build out-of-cluster K8s client")
                raise

        return self._api_client

    def _get_api_client(self) -> client.ApiClient:
        """Get or create a K8s ApiClient (sync version)."""
        if self._api_client is not None and not self._is_token_expired():
            return self._api_client

        if self._is_token_expired():
            logger.info("GCP access token approaching expiry, refreshing K8s client")
            self._api_client = None

        try:
            config.load_incluster_config()
            self._api_client = client.ApiClient()
            logger.info("Using incluster K8s config")
        except Exception:
            logger.info("Not running in cluster, using platform_config credentials")
            try:
                self._api_client = self._build_out_of_cluster_client()
                logger.info(
                    "K8s client built for endpoint %s",
                    (self._cluster_config or {}).get("gke_cluster_endpoint"),
                )
            except Exception:
                logger.exception("Failed to build out-of-cluster K8s client")
                raise

        return self._api_client

    def _get_k8s_core_client(self):
        return client.CoreV1Api(api_client=self._get_api_client())

    def _get_k8s_apps_client(self):
        return client.AppsV1Api(api_client=self._get_api_client())

    def _get_k8s_rbac_client(self):
        return client.RbacAuthorizationV1Api(api_client=self._get_api_client())

    # -- Namespace setup --

    async def ensure_cellxgene_namespace(
        self, namespace: str = DEFAULT_CELLXGENE_NAMESPACE, gcp_sa_email: str = ""
    ) -> None:
        """Ensure the cellxgene namespace and service account exist."""
        from kubernetes.client.rest import ApiException

        if self._namespace_ready:
            return

        core_v1 = self._get_k8s_core_client()
        rbac_v1 = self._get_k8s_rbac_client()

        try:
            core_v1.read_namespace(name=namespace)
            logger.info("Namespace %s already exists, skipping setup", namespace)
            if gcp_sa_email:
                self._patch_sa_annotation(core_v1, namespace, gcp_sa_email)
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

        sa_annotations = {}
        if gcp_sa_email:
            sa_annotations["iam.gke.io/gcp-service-account"] = gcp_sa_email

        core_v1.create_namespaced_service_account(
            namespace=namespace,
            body=client.V1ServiceAccount(
                metadata=client.V1ObjectMeta(
                    name="bioaf-cellxgene-runner",
                    labels={"bioaf.io/managed": "true"},
                    annotations=sa_annotations or None,
                )
            ),
        )
        logger.info("Created service account bioaf-cellxgene-runner in %s", namespace)

        rbac_v1.create_namespaced_role_binding(
            namespace=namespace,
            body=client.V1RoleBinding(
                metadata=client.V1ObjectMeta(
                    name="bioaf-cellxgene-runner-binding",
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
                        name="bioaf-cellxgene-runner",
                        namespace=namespace,
                    )
                ],
            ),
        )
        logger.info("Created role binding in %s", namespace)
        self._namespace_ready = True

    @staticmethod
    def _patch_sa_annotation(core_v1, namespace: str, gcp_sa_email: str) -> None:
        try:
            sa = core_v1.read_namespaced_service_account(name="bioaf-cellxgene-runner", namespace=namespace)
            current = (sa.metadata.annotations or {}).get("iam.gke.io/gcp-service-account", "")
            if current != gcp_sa_email:
                core_v1.patch_namespaced_service_account(
                    name="bioaf-cellxgene-runner",
                    namespace=namespace,
                    body={"metadata": {"annotations": {"iam.gke.io/gcp-service-account": gcp_sa_email}}},
                )
                logger.info("Patched Workload Identity annotation on bioaf-cellxgene-runner")
        except Exception:
            logger.warning("Could not patch SA annotation for Workload Identity")

    # -- K8s API implementations --

    async def _k8s_deploy(self, publication_id: int, gcs_uri: str, dataset_name: str) -> dict:
        """Deploy a cellxgene pod on the GKE cluster."""
        await self._get_api_client_async()

        namespace = DEFAULT_CELLXGENE_NAMESPACE
        await self.ensure_cellxgene_namespace(namespace)

        name = f"cellxgene-{publication_id}"
        apps_v1 = self._get_k8s_apps_client()
        core_v1 = self._get_k8s_core_client()

        deployment = client.V1Deployment(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={
                    "bioaf.io/managed": "true",
                    "bioaf.io/publication": str(publication_id),
                },
            ),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        service_account_name="bioaf-cellxgene-runner",
                        node_selector={"bioaf.io/pool": "interactive"},
                        tolerations=[
                            client.V1Toleration(
                                key="bioaf.io/pool",
                                value="interactive",
                                effect="NoSchedule",
                            )
                        ],
                        containers=[
                            client.V1Container(
                                name="cellxgene",
                                image="cellxgene:latest",
                                args=["launch", "--host", "0.0.0.0", gcs_uri],
                                ports=[client.V1ContainerPort(container_port=5005)],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "1", "memory": "4Gi"},
                                    limits={"cpu": "2", "memory": "8Gi"},
                                ),
                            )
                        ],
                    ),
                ),
            ),
        )
        apps_v1.create_namespaced_deployment(namespace=namespace, body=deployment)
        logger.info("Created cellxgene deployment %s in %s", name, namespace)

        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=name,
                namespace=namespace,
                labels={
                    "bioaf.io/managed": "true",
                    "bioaf.io/publication": str(publication_id),
                },
            ),
            spec=client.V1ServiceSpec(
                selector={"app": name},
                ports=[client.V1ServicePort(port=80, target_port=5005)],
                type="ClusterIP",
            ),
        )
        core_v1.create_namespaced_service(namespace=namespace, body=service)
        logger.info("Created cellxgene service %s in %s", name, namespace)

        # Poll for readiness in background
        asyncio.create_task(self._poll_deployment_ready(publication_id, name, namespace))

        return {
            "publication_id": publication_id,
            "pod_name": name,
            "namespace": namespace,
            "status": "starting",
            "access_url": None,
        }

    async def _poll_deployment_ready(self, publication_id: int, name: str, namespace: str) -> None:
        """Background: poll for deployment readiness, then update the DB."""
        try:
            apps_v1 = self._get_k8s_apps_client()

            for _ in range(60):
                try:
                    dep = apps_v1.read_namespaced_deployment_status(name=name, namespace=namespace)
                    if dep.status.ready_replicas and dep.status.ready_replicas >= 1:
                        logger.info("Cellxgene deployment %s is ready", name)
                        await self._update_publication_status(publication_id, "published")
                        return
                except Exception:
                    pass
                await asyncio.sleep(5)

            logger.error("Cellxgene deployment %s not ready after 5 min", name)
            await self._update_publication_status(publication_id, "failed")
        except Exception:
            logger.exception("Background poll failed for cellxgene %s", name)
            await self._update_publication_status(publication_id, "failed")

    async def _update_publication_status(self, publication_id: int, status: str) -> None:
        if not self._session_factory:
            logger.warning("No session_factory, cannot update publication %s in DB", publication_id)
            return

        try:
            async with self._session_factory() as db:
                from sqlalchemy import text

                now = datetime.now(timezone.utc)
                if status == "published":
                    await db.execute(
                        text(
                            "UPDATE cellxgene_publications SET status = :status, published_at = :now WHERE id = :id"
                        ),
                        {"status": status, "now": now, "id": publication_id},
                    )
                else:
                    await db.execute(
                        text("UPDATE cellxgene_publications SET status = :status WHERE id = :id"),
                        {"status": status, "id": publication_id},
                    )
                await db.commit()
                logger.info("Updated publication %s: status=%s", publication_id, status)
        except Exception:
            logger.exception("Failed to update publication %s in DB", publication_id)

    async def _k8s_teardown(self, publication_id: int) -> dict:
        """Delete the cellxgene deployment and service."""
        await self._get_api_client_async()

        name = f"cellxgene-{publication_id}"
        namespace = DEFAULT_CELLXGENE_NAMESPACE

        apps_v1 = self._get_k8s_apps_client()
        core_v1 = self._get_k8s_core_client()

        try:
            apps_v1.delete_namespaced_deployment(name=name, namespace=namespace)
            logger.info("Deleted cellxgene deployment %s", name)
        except Exception as e:
            logger.warning("Failed to delete cellxgene deployment %s: %s", name, e)

        try:
            core_v1.delete_namespaced_service(name=name, namespace=namespace)
            logger.info("Deleted cellxgene service %s", name)
        except Exception as e:
            logger.warning("Failed to delete cellxgene service %s: %s", name, e)

        return {
            "publication_id": publication_id,
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _k8s_get_status(self, publication_id: int) -> dict:
        """Query K8s API for deployment status."""
        await self._get_api_client_async()

        name = f"cellxgene-{publication_id}"
        namespace = DEFAULT_CELLXGENE_NAMESPACE
        apps_v1 = self._get_k8s_apps_client()

        try:
            dep = apps_v1.read_namespaced_deployment_status(name=name, namespace=namespace)
            ready = dep.status.ready_replicas or 0
            status = "running" if ready >= 1 else "starting"
        except Exception:
            return {
                "publication_id": publication_id,
                "status": "unknown",
                "pod_name": name,
            }

        return {
            "publication_id": publication_id,
            "status": status,
            "pod_name": name,
            "namespace": namespace,
        }

    # -- Local mode implementations --

    def _local_deploy(self, publication_id: int, gcs_uri: str, dataset_name: str) -> dict:
        instance = {
            "publication_id": publication_id,
            "pod_name": f"cellxgene-{publication_id}",
            "namespace": DEFAULT_CELLXGENE_NAMESPACE,
            "status": "running",
            "access_url": f"http://localhost:5005/cellxgene/{publication_id}/",
            "gcs_uri": gcs_uri,
            "dataset_name": dataset_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _local_instances[publication_id] = instance
        logger.info("Local mode: deployed cellxgene %s for %s", publication_id, dataset_name)
        return instance

    def _local_teardown(self, publication_id: int) -> dict:
        if publication_id in _local_instances:
            _local_instances[publication_id]["status"] = "stopped"
            _local_instances[publication_id]["stopped_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("Local mode: torn down cellxgene %s", publication_id)
        return {
            "publication_id": publication_id,
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
        }

    def _local_get_status(self, publication_id: int) -> dict:
        if publication_id in _local_instances:
            return _local_instances[publication_id]
        return {
            "publication_id": publication_id,
            "status": "unknown",
        }
