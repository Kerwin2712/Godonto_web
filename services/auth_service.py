from core.database import Database
from models.user import User
from core.database import get_db
import bcrypt
#print
class AuthService:
    @staticmethod
    def authenticate(email: str, password: str) -> User:
        """Autentica un usuario de forma síncrona"""
        with Database.get_cursor() as cursor:
            cursor.execute(
                "SELECT id, email, password_hash FROM users WHERE email = %s",
                (email,)
            )
            user_data = cursor.fetchone()
            
            if user_data and verify_password(password, user_data[2]):
                return User(id=user_data[0], email=user_data[1])
            return None

def authenticate_user(username: str, password: str) -> bool:
    """
    Autentica un usuario contra la base de datos.
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
    Returns:
        bool: True si las credenciales son válidas
    """
    try:
        with get_db() as cursor:
            cursor.execute(
                "SELECT password_hash FROM users WHERE email = %s",
                (username,)
            )
            if result := cursor.fetchone():
                stored_hash = result[0].encode('utf-8')
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        return False
    except Exception as e:
        #print(f"Error en autenticación: {str(e)}")
        return False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash"""
    # Implementar lógica de verificación (usando bcrypt o similar)
    pass