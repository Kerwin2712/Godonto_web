from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List
from .quote_treatment import QuoteTreatment

@dataclass
class Quote:
    id: int
    client_id: int
    quote_date: date
    total_amount: float
    status: str  # pending/approved/rejected/expired/invoiced
    user_id: Optional[int] = None
    expiration_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    treatments: List['QuoteTreatment'] = None  # Relación 1:N