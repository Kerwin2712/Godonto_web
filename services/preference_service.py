import logging
from core.database import get_db
from datetime import datetime

logger = logging.getLogger(__name__)

class PreferenceService:
    @staticmethod
    def get_user_theme(user_id: int) -> str:
        """
        Obtiene el modo de tema guardado para un usuario.
        Retorna 'light' si no se encuentra o hay un error.
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT theme_mode FROM user_preferences WHERE user_id = %s",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    logger.info(f"Tema encontrado para el usuario {user_id}: {result[0]}")
                    return result[0]
                else:
                    logger.info(f"No se encontró preferencia de tema para el usuario {user_id}. Usando 'light' por defecto.")
                    return 'light' # Tema por defecto si no se encuentra preferencia
        except Exception as e:
            logger.error(f"Error al obtener la preferencia de tema para el usuario {user_id}: {e}")
            return 'light' # Fallback en caso de error

    @staticmethod
    def save_user_theme(user_id: int, theme_mode: str) -> bool:
        """
        Guarda o actualiza el modo de tema para un usuario.
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    """
                    INSERT INTO user_preferences (user_id, theme_mode, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET theme_mode = EXCLUDED.theme_mode, updated_at = NOW()
                    """,
                    (user_id, theme_mode)
                )
                logger.info(f"Preferencia de tema '{theme_mode}' guardada para el usuario {user_id}.")
                return True
        except Exception as e:
            logger.error(f"Error al guardar la preferencia de tema para el usuario {user_id}: {e}")
            return False

