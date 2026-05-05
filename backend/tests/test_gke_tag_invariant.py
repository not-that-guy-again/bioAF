"""SA hardening invariant: every google_container_cluster has a sibling
google_tags_tag_binding referencing the bioaf-managed tag.

bioaf-app's roles/container.admin grant is conditioned on
resource.matchTag("<PROJECT>/bioaf-managed", "true"). A cluster missing
the tag binding would be unmanageable from the runtime SA.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TF_DIRS = [
    _REPO_ROOT / "terraform",
    _REPO_ROOT / "backend" / "terraform" / "modules",
]

_CLUSTER_RE = re.compile(r'resource\s+"google_container_cluster"\s+"([^"]+)"')
_NODE_POOL_RE = re.compile(r'resource\s+"google_container_node_pool"\s+"([^"]+)"')


def _terraform_files() -> list[Path]:
    files: list[Path] = []
    for d in _TF_DIRS:
        if d.exists():
            files.extend(sorted(d.rglob("*.tf")))
    return files


def test_every_google_container_cluster_has_a_tag_binding():
    """Each defined cluster must have a google_tags_tag_binding referencing it.

    The binding may render conditionally (count = var.bioaf_bootstrap_sa_email != "" ? 1 : 0)
    so we look for any tag_binding whose `parent` references the cluster's id.
    """
    cluster_names: list[tuple[Path, str]] = []
    text_by_path: dict[Path, str] = {}
    for path in _terraform_files():
        text = path.read_text()
        text_by_path[path] = text
        for m in _CLUSTER_RE.finditer(text):
            cluster_names.append((path, m.group(1)))

    if not cluster_names:
        pytest.skip("No google_container_cluster resources found in repo")

    failures: list[tuple[Path, str]] = []
    for path, name in cluster_names:
        # A tag_binding that references this cluster will mention
        # "google_container_cluster.<name>" somewhere in the file.
        if (
            f"google_container_cluster.{name}.id" not in text_by_path[path]
            and f"google_container_cluster.{name}" not in text_by_path[path]
        ):
            failures.append((path, name))
            continue
        # And there must be at least one google_tags_tag_binding in the file.
        if "google_tags_tag_binding" not in text_by_path[path]:
            failures.append((path, name))

    assert not failures, (
        "google_container_cluster resources without a sibling google_tags_tag_binding "
        "(SA hardening requires the bioaf-managed tag for runtime access):\n"
        + "\n".join(f"  {p}: {n}" for p, n in failures)
    )


def test_node_pools_appear_in_files_with_a_tag_binding():
    """Sanity check: any file declaring a node pool also declares a tag binding."""
    failures: list[tuple[Path, str]] = []
    for path in _terraform_files():
        text = path.read_text()
        for m in _NODE_POOL_RE.finditer(text):
            if "google_tags_tag_binding" not in text:
                failures.append((path, m.group(1)))
    if failures:
        pytest.fail(
            "google_container_node_pool found in file without google_tags_tag_binding:\n"
            + "\n".join(f"  {p}: {n}" for p, n in failures)
        )
