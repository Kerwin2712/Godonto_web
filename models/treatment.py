from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Treatment:
    id: int
    name: str
    price: float
    duration: timedelta
    description: str = None
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None