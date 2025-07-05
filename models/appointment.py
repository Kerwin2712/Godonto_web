from __future__ import annotations
from datetime import date, time, datetime
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from enum import Enum, auto

class AppointmentStatus(Enum):
    PENDING = auto()
    COMPLETED = auto()
    CANCELLED = auto()

    @classmethod
    def from_string(cls, value: str) -> 'AppointmentStatus':
        try:
            return cls[value.upper()]
        except KeyError:
            raise ValueError(f"Invalid status: {value}")

@dataclass
class Appointment:
    """
    Modelo que representa una cita en el sistema odontológico.
    
    Attributes:
        id: Identificador único de la cita (autogenerado)
        client_id: ID del cliente asociado (requerido)
        client_name: Nombre del cliente (denormalizado para eficiencia)
        client_cedula: Cédula del cliente (formato validado)
        date: Fecha de la cita (requerida, no puede ser en pasado)
        time: Hora de la cita (requerida)
        status: Estado de la cita (pending/completed/cancelled)
        notes: Notas adicionales (opcional)
        created_at: Fecha de creación del registro (autogenerado)
        updated_at: Fecha de última actualización (autogenerado)
        dentist_id: ID del dentista asociado (opcional)
        dentist_name: Nombre del dentista asociado (denormalizado para eficiencia en UI) # ¡NUEVO!
    """
    id: int
    client_id: int
    client_name: str
    client_cedula: str
    date: date
    time: time
    status: AppointmentStatus = AppointmentStatus.PENDING
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    dentist_id: Optional[int] = None
    dentist_name: Optional[str] = None # ¡Añadido!

    def __post_init__(self):
        """Validación inicial después de la creación y conversión de estado."""
        if isinstance(self.status, str):
            self.status = AppointmentStatus.from_string(self.status)

    def is_past_due(self) -> bool:
        """Verifica si la cita está vencida (fecha/hora pasada)."""
        appointment_datetime = datetime.combine(self.date, self.time)
        return appointment_datetime < datetime.now()

    def is_completed(self) -> bool:
        return self.status == AppointmentStatus.COMPLETED

    def is_cancelled(self) -> bool:
        return self.status == AppointmentStatus.CANCELLED

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para serialización."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "client_cedula": self.client_cedula,
            "date": self.date.isoformat(),
            "time": self.time.strftime("%H:%M"),
            "status": self.status.name.lower(), # Guardar como string
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "dentist_id": self.dentist_id,
            "dentist_name": self.dentist_name, # Incluir en dict
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Appointment':
        """Crea una instancia de Appointment desde un diccionario."""
        try:
            date_obj = date.fromisoformat(data['date']) if isinstance(data['date'], str) else data['date']
            time_str = data['time'] if isinstance(data['time'], str) else data['time'].strftime("%H:%M")
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            
            created_at = (datetime.fromisoformat(data['created_at']) 
                         if data.get('created_at') else None)
            updated_at = (datetime.fromisoformat(data['updated_at']) 
                         if data.get('updated_at') else None)
            
            return cls(
                id=data['id'],
                client_id=data['client_id'],
                client_name=data['client_name'],
                client_cedula=data['client_cedula'],
                date=date_obj,
                time=time_obj,
                status=AppointmentStatus.from_string(data.get('status', 'pending')), # Convertir a Enum
                notes=data.get('notes'),
                created_at=created_at,
                updated_at=updated_at,
                dentist_id=data.get('dentist_id'),
                dentist_name=data.get('dentist_name'), # Leer de dict
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error parsing appointment data: {str(e)}")

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida los datos de la cita."""
        if not self.client_id:
            return False, "Se requiere un cliente."
            
        if not self.date:
            return False, "Se requiere una fecha."
            
        if not self.time:
            return False, "Se requiere una hora."

        if not self.dentist_id: # ¡NUEVO! Validar que se haya seleccionado un dentista
            return False, "Se requiere seleccionar un dentista."
            
        # Validar que la fecha/hora no sea en el pasado
        if self.is_past_due() and not self.is_completed():
            return False, "No se pueden agendar citas en el pasado."
            
        # Validar estado
        if not isinstance(self.status, AppointmentStatus): # Asegurar que es un Enum
             return False, "El estado de la cita es inválido."
            
        return True, None
