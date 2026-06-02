from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class LinkStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    SLOW = "slow"

class LinkConfig(BaseModel):
    url: str
    name: str
    category: str = "geral"

class CheckResult(BaseModel):
    url: str
    name: str
    status: LinkStatus
    status_code: int | None = None
    response_time_ms: float | None = None
    error_message: str | None = None
    checked_at: datetime = None

    def model_post_init(self, __context):
        if self.checked_at is None:
            self.checked_at = datetime.now()
