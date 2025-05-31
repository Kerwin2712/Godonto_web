from __future__ import annotations
from datetime import date, time, datetime
from dataclasses import dataclass
from typing import Optional, Tuple, Literal
from enum import Enum, auto
#print
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
    """
    id: int
    client_id: int
    client_name: str
    client_cedula: str
    date: date
    time: time
    status: str
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validación inicial después de la creación"""
        if not hasattr(self, 'status') or not self.status:
            self.status = "pending"

    def is_past_due(self) -> bool:
        """Verifica si la cita está vencida (fecha/hora pasada)."""
        appointment_datetime = datetime.combine(self.date, self.time)
        return appointment_datetime < datetime.now()

    def is_completed(self) -> bool:
        """Verifica si la cita está completada."""
        return self.status.lower() == "completed"

    def is_cancelled(self) -> bool:
        """Verifica si la cita está cancelada."""
        return self.status.lower() == "cancelled"

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para serialización.
        
        Returns:
            dict: Diccionario con los datos de la cita, con fechas en formato ISO.
        """
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "client_cedula": self.client_cedula,
            "date": self.date.isoformat(),
            "time": self.time.strftime("%H:%M"),
            "status": self.status,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Appointment':
        """Crea una instancia de Appointment desde un diccionario.
        
        Args:
            data: Diccionario con los datos de la cita
            
        Returns:
            Appointment: Instancia de la cita
            
        Raises:
            ValueError: Si los datos no son válidos
        """
        try:
            # Parseo de fechas
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
                status=data.get('status', 'pending'),
                notes=data.get('notes'),
                created_at=created_at,
                updated_at=updated_at
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error parsing appointment data: {str(e)}")

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida los datos de la cita.
        
        Returns:
            Tuple[bool, Optional[str]]: (True, None) si es válido, 
                                      (False, mensaje_error) si no
        """
        if not self.client_id:
            return False, "Se requiere un cliente"
            
        if not self.date:
            return False, "Se requiere una fecha"
            
        if not self.time:
            return False, "Se requiere una hora"
            
        # Validar que la fecha/hora no sea en el pasado
        if self.is_past_due() and not self.is_completed():
            return False, "No se pueden agendar citas en el pasado"
            
        # Validar estado
        valid_statuses = [s.name.lower() for s in AppointmentStatus]
        if self.status.lower() not in valid_statuses:
            return False, f"Estado de cita inválido. Válidos: {', '.join(valid_statuses)}"
            
        return True, None