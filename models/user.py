from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from utils.validators import Validators

@dataclass
class User:
    """
    Modelo que representa un usuario del sistema.
    
    Attributes:
        id: Identificador único del usuario (autogenerado)
        email: Correo electrónico (requerido, único, formato validado)
        password_hash: Hash de la contraseña (requerido para autenticación)
        is_active: Indica si el usuario está activo (default True)
        is_admin: Indica si el usuario es administrador (default False)
        created_at: Fecha de creación del registro (autogenerado)
        updated_at: Fecha de última actualización (autogenerado)
    """
    id: int
    email: str
    password_hash: str
    is_active: bool = True
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def validate(self) -> bool:
        """Valida los datos del usuario.
        
        Returns:
            bool: True si el usuario es válido
            
        Raises:
            ValueError: Si el email no es válido
        """
        if not Validators.validate_email(self.email):
            raise ValueError("Email inválido")
        return True

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convierte el objeto a diccionario para serialización.
        
        Args:
            include_sensitive: Incluir datos sensibles como password_hash
            
        Returns:
            dict: Diccionario con los datos del usuario
        """
        data = {
            "id": self.id,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data["password_hash"] = self.password_hash
            
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Crea una instancia de User desde un diccionario.
        
        Args:
            data: Diccionario con los datos del usuario
            
        Returns:
            User: Instancia del usuario
            
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
                email=data['email'],
                password_hash=data['password_hash'],
                is_active=data.get('is_active', True),
                is_admin=data.get('is_admin', False),
                created_at=created_at,
                updated_at=updated_at
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"Error parsing user data: {str(e)}")