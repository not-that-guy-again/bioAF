from datetime import datetime

from pydantic import BaseModel

from app.schemas.package import InstalledPackageResponse, PackageInstallRequest


class UserSummary(BaseModel):
    id: int
    name: str | None = None
    email: str


class EnvironmentResponse(BaseModel):
    id: int
    name: str
    env_type: str
    description: str | None = None
    is_default: bool
    package_count: int
    jupyter_kernel_name: str | None = None
    status: str
    last_synced_at: datetime | None = None
    created_by: UserSummary | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentListResponse(BaseModel):
    environments: list[EnvironmentResponse]
    total: int


class EnvironmentDetailResponse(BaseModel):
    id: int
    name: str
    env_type: str
    description: str | None = None
    is_default: bool
    jupyter_kernel_name: str | None = None
    status: str
    packages: list[InstalledPackageResponse]
    last_synced_at: datetime | None = None
    created_by: UserSummary | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentCreateRequest(BaseModel):
    name: str
    description: str | None = None
    packages: list[PackageInstallRequest] = []
    clone_from: str | None = None


class EnvironmentChangeResponse(BaseModel):
    id: int
    change_type: str
    package_name: str | None = None
    old_version: str | None = None
    new_version: str | None = None
    git_commit_sha: str | None = None
    commit_message: str | None = None
    reconciled: bool
    reconciled_at: datetime | None = None
    error_message: str | None = None
    user: UserSummary | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentHistoryResponse(BaseModel):
    changes: list[EnvironmentChangeResponse]
    total: int
    page: int
    page_size: int


class EnvironmentRollbackRequest(BaseModel):
    target_change_id: int


class EnvironmentDiff(BaseModel):
    added: list[str]
    removed: list[str]
    changed: list[dict]
