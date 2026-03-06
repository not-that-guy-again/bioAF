from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.bootstrap import router as bootstrap_router
from app.api.components import router as components_router
from app.api.health import router as health_router
from app.api.terraform import router as terraform_router
from app.api.users import router as users_router
from app.api.experiments import router as experiments_router
from app.api.samples import router as samples_router
from app.api.batches import router as batches_router
from app.api.projects import router as projects_router
from app.api.templates import router as templates_router
from app.api.audit import router as audit_router
from app.api.compute import router as compute_router
from app.api.notebooks import router as notebooks_router
from app.api.quotas import router as quotas_router
from app.api.pipelines import router as pipelines_router
from app.api.pipeline_runs import router as pipeline_runs_router
from app.api.files import router as files_router
from app.api.datasets import router as datasets_router
from app.api.documents import router as documents_router
from app.api.storage import router as storage_router
from app.api.cellxgene import router as cellxgene_router
from app.api.qc_dashboards import router as qc_dashboards_router
from app.api.plots import router as plots_router
from app.api.search import router as search_router
from app.api.gitops import router as gitops_router
from app.api.packages import router as packages_router
from app.api.environments import router as environments_router
from app.api.template_notebooks import router as template_notebooks_router
from app.api.notifications import router as notifications_router
from app.api.backups import router as backups_router
from app.api.costs import router as costs_router
from app.api.upgrades import router as upgrades_router
from app.api.access_logs import router as access_logs_router
from app.api.activity_feed import router as activity_feed_router
from app.api.vocabularies import router as vocabularies_router
from app.api.pipeline_run_reviews import router as pipeline_run_reviews_router
from app.api.references import router as references_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(bootstrap_router)
api_router.include_router(users_router)
api_router.include_router(components_router)
api_router.include_router(terraform_router)
api_router.include_router(experiments_router)
api_router.include_router(samples_router)
api_router.include_router(batches_router)
api_router.include_router(projects_router)
api_router.include_router(templates_router)
api_router.include_router(audit_router)
api_router.include_router(compute_router)
api_router.include_router(notebooks_router)
api_router.include_router(quotas_router)
api_router.include_router(pipelines_router)
api_router.include_router(pipeline_runs_router)
api_router.include_router(files_router)
api_router.include_router(datasets_router)
api_router.include_router(documents_router)
api_router.include_router(storage_router)
api_router.include_router(cellxgene_router)
api_router.include_router(qc_dashboards_router)
api_router.include_router(plots_router)
api_router.include_router(search_router)
api_router.include_router(gitops_router)
api_router.include_router(packages_router)
api_router.include_router(environments_router)
api_router.include_router(template_notebooks_router)
api_router.include_router(notifications_router)
api_router.include_router(backups_router)
api_router.include_router(costs_router)
api_router.include_router(upgrades_router)
api_router.include_router(access_logs_router)
api_router.include_router(activity_feed_router)
api_router.include_router(vocabularies_router)
api_router.include_router(pipeline_run_reviews_router)
api_router.include_router(references_router)
