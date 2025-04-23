import re
from typing import Optional
from datetime import date, datetime, time

class Validators:
    @staticmethod
    def validate_email(email: str, required: bool = False) -> Optional[str]:
        if not email:
            return "El email es obligatorio" if required else None
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.fullmatch(pattern, email):
            return "Email inválido"
        return None

    @staticmethod
    def validate_cedula(cedula: str, country_code: str = 'VEN') -> Optional[str]:
        if not cedula:
            return "La cédula es obligatoria"
        if not cedula.isdigit():
            return "La cédula debe contener solo números"
        return None

    @staticmethod
    def validate_phone(phone: str, country_code: str = 'VEN') -> Optional[str]:
        if not phone:
            return None
        cleaned = re.sub(r'[^\d+]', '', phone)
        if country_code == 'VEN':
            if not cleaned.startswith('+'):
                cleaned = f"+58{cleaned.lstrip('0')}"
        return None

# Exporta las funciones al nivel del módulo
validate_email = Validators.validate_email
validate_phone = Validators.validate_phone
validate_cedula = Validators.validate_cedula