from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple, List, TYPE_CHECKING
from utils.validators import Validators
from models.appointment import Appointment
from models.debt import Debt
from models.quote import Quote

#print
@dataclass
class Client:
    """
    Modelo que representa un cliente en el sistema odontológico.
    
    Attributes:
        id: Identificador único del cliente (autogenerado)
        name: Nombre completo del cliente (requerido, mínimo 3 caracteres)
        cedula: Cédula o documento de identidad (requerido, formato validado)
        phone: Número de teléfono (opcional, formato validado)
        email: Correo electrónico (opcional, formato validado)
        address: Dirección física (opcional)
        created_at: Fecha de creación del registro (autogenerado)
        updated_at: Fecha de última actualización (autogenerado)
    """
    id: int
    name: str
    cedula: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    appointments: List[Appointment] = None
    debts: List[Debt] = None
    quotes: List[Quote] = None

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Valida los datos del cliente.
        
        Returns:
            Tuple[bool, Optional[str]]: (True, None) si es válido, 
                                      (False, mensaje_error) si no
        """
        if not self.name or len(self.name.strip()) < 3:
            return False, "El nombre debe tener al menos 3 caracteres"
            
        if cedula_error := Validators.validate_cedula(self.cedula):
            return False, cedula_error
            
        if self.phone and (phone_error := Validators.validate_phone(self.phone)):
            return False, phone_error
            
        if self.email and (email_error := Validators.validate_email(self.email)):
            return False, email_error
            
        return True, None

    def to_dict(self) -> dict:
        """Convierte el objeto a diccionario para serialización.
        
        Returns:
            dict: Diccionario con los datos del cliente
        """
        return {
            "id": self.id,
            "name": self.name,
            "cedula": self.cedula,
            "phone": self.phone,
            "email": self.email,
            "address": self.address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Client':
        """Crea una instancia de Client desde un diccionario.
        
        Args:
            data: Diccionario con los datos del cliente
            
        Returns:
            Client: Instancia del cliente
            
        Raises:
            ValueError: Si los datos no son válidos
        """
        try:
            created_at = (datetime.fromisoformat(data['created_at']) 
                        if data.get('created_at') else None)
            updated_at = (datetime.fromisoformat(data['updated_at']) 
                        if data.get('updated_at') else None)
            
            return cls(
                id=data['id'],
                name=data['name'],
                cedula=data['cedula'],
                phone=data.get('phone'),
                email=data.get('email'),
                address=data.get('address'),
                created_at=created_at,
                updated_at=updated_at
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error parsing client data: {str(e)}")

    def get_full_info(self) -> str:
        """Devuelve información completa del cliente formateada.
        
        Returns:
            str: Información formateada del cliente
        """
        info_parts = [
            f"Nombre: {self.name}",
            f"Cédula: {self.cedula}"
        ]
        
        if self.phone:
            info_parts.append(f"Teléfono: {self.phone}")
        if self.email:
            info_parts.append(f"Email: {self.email}")
        if self.address:
            info_parts.append(f"Dirección: {self.address}")
            
        return " | ".join(info_parts)