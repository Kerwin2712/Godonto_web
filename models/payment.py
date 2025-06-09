from dataclasses import dataclass
from datetime import datetime

@dataclass
class Payment:
    id: int
    client_id: int
    amount: float
    payment_date: datetime
    method: str
    status: str  # pending/completed/failed/refunded
    appointment_id: int = None
    invoice_number: str = None
    notes: str = None
    created_at: datetime = None
    created_by: int = None  # ID de usuario