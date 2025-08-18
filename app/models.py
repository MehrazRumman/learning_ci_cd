from pydantic import BaseModel
from datetime import datetime

class HealthResponse(BaseModel):
    message: str
    status: str
    timestamp: datetime
    version: str
