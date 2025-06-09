from dataclasses import dataclass

@dataclass
class QuoteTreatment:
    quote_id: int
    treatment_id: int
    price_at_quote: float
    quantity: int = 1
    
    @property
    def subtotal(self) -> float:
        return self.price_at_quote * self.quantity