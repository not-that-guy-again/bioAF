from datetime import datetime

from pydantic import BaseModel


class PackageSearchResult(BaseModel):
    name: str
    version: str
    description: str | None = None
    source: str
    channel: str | None = None
    homepage: str | None = None


class PackageSearchResponse(BaseModel):
    results: list[PackageSearchResult]
    total: int
    query: str


class DependencyNode(BaseModel):
    name: str
    version: str
    source: str
    action: str  # 'install', 'update', 'already_installed'


class DependencyTree(BaseModel):
    package: str
    version: str
    dependencies: list[DependencyNode]
    total_new_packages: int
    estimated_disk_bytes: int | None = None


class PackageInstallRequest(BaseModel):
    environment: str
    package_name: str
    version: str | None = None
    source: str
    pinned: bool = False


class PackageRemoveRequest(BaseModel):
    environment: str
    package_name: str
    source: str


class PackageUpdateRequest(BaseModel):
    environment: str
    package_name: str
    new_version: str
    source: str


class InstalledPackageResponse(BaseModel):
    name: str
    version: str | None = None
    source: str
    pinned: bool
    installed_at: datetime

    model_config = {"from_attributes": True}


class PackageDetail(BaseModel):
    name: str
    version: str | None = None
    source: str
    pinned: bool
    installed_at: datetime
    available_versions: list[str] | None = None
    description: str | None = None
