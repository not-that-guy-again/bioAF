from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    event_type: str
    title: str
    message: str | None
    severity: str
    read: bool
    read_at: datetime | None
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    total: int
    page: int
    page_size: int


class UnreadCountResponse(BaseModel):
    count: int


class NotificationPreferenceItem(BaseModel):
    event_type: str
    channel: str
    enabled: bool = True


class NotificationPreferenceResponse(BaseModel):
    id: int
    event_type: str
    channel: str
    enabled: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesUpdate(BaseModel):
    preferences: list[NotificationPreferenceItem]


class NotificationRuleItem(BaseModel):
    event_type: str
    channel: str
    role_filter: str | None = None
    mandatory: bool = False
    enabled: bool = True


class NotificationRuleResponse(BaseModel):
    id: int
    event_type: str
    channel: str
    role_filter: str | None
    mandatory: bool
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationRulesUpdate(BaseModel):
    rules: list[NotificationRuleItem]


class SlackWebhookCreate(BaseModel):
    name: str
    webhook_url: str
    channel_name: str | None = None
    event_types: list[str] = []
    enabled: bool = True


class SlackWebhookUpdate(BaseModel):
    name: str | None = None
    webhook_url: str | None = None
    channel_name: str | None = None
    event_types: list[str] | None = None
    enabled: bool | None = None


class SlackWebhookResponse(BaseModel):
    id: int
    name: str
    webhook_url: str
    channel_name: str | None
    event_types_json: list
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TestDeliveryRequest(BaseModel):
    channel: str


class TestDeliveryResponse(BaseModel):
    channel: str
    status: str
    detail: str | None = None
    webhooks: list[dict] | None = None
