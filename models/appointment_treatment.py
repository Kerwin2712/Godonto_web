from dataclasses import dataclass

@dataclass
class AppointmentTreatment:
    appointment_id: int
    treatment_id: int
    price: float
    notes: str = None