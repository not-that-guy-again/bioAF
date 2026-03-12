"""GCP credential injection helper for Terraform subprocess calls.

Reads GCP configuration from a platform_config dict and produces:
- A dict of environment variables to pass to subprocess calls
- An async cleanup callable that removes any temporary files

Supports two credential sources:
- vm_default: uses the VM's attached service account via ADC
- service_account_key: writes the JSON key to a temp file and sets
  GOOGLE_APPLICATION_CREDENTIALS
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable, Coroutine


class GCPCredentialInjector:
    """Build subprocess environment variables for Terraform GCP operations."""

    @staticmethod
    async def build_env(config: dict) -> tuple[dict, Callable[[], Coroutine]]:
        """Build env dict and cleanup callable from platform_config values.

        Args:
            config: Dict containing GCP config keys such as those from
                    platform_config: gcp_credential_source, gcp_project_id,
                    gcp_region, gcp_zone, gcp_service_account_key.

        Returns:
            (env, cleanup) where env is a dict of environment variables to
            merge into the subprocess environment, and cleanup is an async
            callable that removes temporary files.

        Raises:
            ValueError: If credential_source is service_account_key but no key
                        JSON is present in config.
        """
        credential_source = config.get("gcp_credential_source", "vm_default")
        project_id = config.get("gcp_project_id", "")
        region = config.get("gcp_region", "us-central1")
        zone = config.get("gcp_zone", "us-central1-a")

        env: dict[str, str] = {
            "TF_VAR_project_id": project_id,
            "TF_VAR_region": region,
            "TF_VAR_zone": zone,
        }

        if credential_source == "service_account_key":
            sa_key = config.get("gcp_service_account_key")
            if not sa_key:
                raise ValueError(
                    "gcp_credential_source is 'service_account_key' but no service_account_key value found in config"
                )

            # Write key to a named temp file
            fd, key_path = tempfile.mkstemp(suffix=".json", prefix="bioaf_sa_")
            try:
                os.write(fd, sa_key.encode())
            finally:
                os.close(fd)

            env["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

            async def _cleanup_sa() -> None:
                p = Path(key_path)
                if p.exists():
                    p.unlink()

            return env, _cleanup_sa

        else:
            # vm_default: ADC picks up VM's service account automatically
            async def _noop_cleanup() -> None:
                pass

            return env, _noop_cleanup
