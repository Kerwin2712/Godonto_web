from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from utils.validators import Validators # Asumiendo que tienes un módulo de validadores

@dataclass
class Dentist:
    """
    Modelo que representa un dentista en el sistema odontológico.

    Attributes:
        id: Identificador único del dentista (autogenerado).
        name: Nombre completo del dentista (requerido, mínimo 3 caracteres).
        phone: Número de teléfono (opcional, formato validado).
        is_active: Booleano que indica si el dentista está activo (por defecto True).
        created_at: Fecha de creación del registro (autogenerado).
        updated_at: Fecha de última actualización (autogenerado).
    """
    id: int
    name: str
    phone: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida los datos del dentista.

        Returns:
            Tuple[bool, Optional[str]]: (True, None) si es válido,
                                      (False, mensaje_error) si no.
        """
        if not self.name or len(self.name.strip()) < 3:
            return False, "El nombre del dentista debe tener al menos 3 caracteres."

        if self.phone and (phone_error := Validators.validate_phone(self.phone)):
            return False, phone_error

        return True, None

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para serialización.

        Returns:
            dict: Diccionario con los datos del dentista.
        """
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Dentist':
        """Crea una instancia de Dentist desde un diccionario.

        Args:
            data: Diccionario con los datos del dentista.

        Returns:
            Dentist: Instancia del dentista.

        Raises:
            ValueError: Si los datos no son válidos.
        """
        try:
            created_at = (datetime.fromisoformat(data['created_at'])
                          if data.get('created_at') else None)
            updated_at = (datetime.fromisoformat(data['updated_at'])
                          if data.get('updated_at') else None)

            return cls(
                id=data['id'],
                name=data['name'],
                phone=data.get('phone'),
                is_active=data.get('is_active', True), # Por defecto True si no se especifica
                created_at=created_at,
                updated_at=updated_at
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error al analizar los datos del dentista: {str(e)}")

    def get_full_info(self) -> str:
        """Devuelve información completa del dentista formateada.

        Returns:
            str: Información formateada del dentista.
        """
        info_parts = [
            f"Nombre: {self.name}"
        ]

        if self.phone:
            info_parts.append(f"Teléfono: {self.phone}")
        info_parts.append(f"Activo: {'Sí' if self.is_active else 'No'}")

        return " | ".join(info_parts)
