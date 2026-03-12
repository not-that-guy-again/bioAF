"""Nextflow config generator for K8s executor.

Generates a bioaf-nextflow.config file content for Nextflow pipelines
running on the GKE cluster with GCS output storage.
"""


def generate_nextflow_config(org_slug: str, namespace: str) -> str:
    """Generate Nextflow config content for the K8s executor.

    Args:
        org_slug: Organization slug for GCS bucket naming.
        namespace: Kubernetes namespace for pipeline jobs.

    Returns:
        Nextflow config string with K8s executor settings.
    """
    return f"""profiles {{
    bioaf_k8s {{
        process.executor = 'k8s'
        k8s.namespace = '{namespace}'
        k8s.serviceAccount = 'bioaf-pipeline-runner'
        process.publishDir = 'gs://bioaf-results-{org_slug}/'
        params.outdir = 'gs://bioaf-results-{org_slug}/'
        docker.enabled = true
    }}
}}
"""
