from datetime import datetime

from pydantic import BaseModel


class GitOpsRepoStatus(BaseModel):
    initialized: bool
    repo_url: str | None = None
    repo_name: str | None = None
    last_commit_sha: str | None = None
    last_commit_at: datetime | None = None
    status: str  # 'active', 'initializing', 'error', 'not_configured'


class GitCommit(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: datetime
    files_changed: int | None = None


class GitCommitDetail(BaseModel):
    sha: str
    message: str
    author: str
    timestamp: datetime
    diff: str
    files: list[str]


class GitCommitListResponse(BaseModel):
    commits: list[GitCommit]
    total: int
    page: int
    page_size: int


class GitOpsInitializeRequest(BaseModel):
    github_pat: str | None = None
