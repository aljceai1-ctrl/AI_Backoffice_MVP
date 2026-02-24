from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: str
    tenant_id: str
    timestamp: str
    actor_user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    metadata_json: dict | None = None

    class Config:
        from_attributes = True
