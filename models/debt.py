from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class Debt:
    id: int
    client_id: int
    amount: float
    status: str  # pending/paid/canceled
    description: str = None
    due_date: date = None
    paid_amount: float = 0.0
    paid_at: datetime = None
    created_at: datetime = None
    updated_at: datetime = None