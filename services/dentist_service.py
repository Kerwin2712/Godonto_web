from core.database import get_db, Database
from models.dentist import Dentist
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DentistService:
    @staticmethod
    def get_dentist_by_id(dentist_id: int) -> Optional[Dentist]:
        """Obtiene un dentista por su ID."""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, name, phone, is_active, created_at, updated_at
                FROM dentists
                WHERE id = %s
                """,
                (dentist_id,)
            )
            row = cursor.fetchone()
            if row:
                return Dentist(
                    id=row[0],
                    name=row[1],
                    phone=row[2],
                    is_active=row[3],
                    created_at=row[4],
                    updated_at=row[5]
                )
            return None

    @staticmethod
    def get_all_dentists(search_term=None) -> List[Dentist]:
        """Obtiene todos los dentistas, opcionalmente filtrados por un término de búsqueda."""
        query = """
            SELECT id, name, phone, is_active, created_at, updated_at
            FROM dentists
            WHERE 1=1
        """
        params = []

        if search_term:
            query += """
                AND (
                    unaccent(name) ILIKE unaccent(%s) OR
                    unaccent(phone) ILIKE unaccent(%s)
                )
            """
            search_param = f"%{search_term}%"
            params = [search_param] * 2 # Mismo término para nombre y teléfono

        query += " ORDER BY name ASC" # Orden alfabético por nombre

        with Database.get_cursor() as cursor:
            cursor.execute(query, params)
            return [Dentist(*row) for row in cursor.fetchall()]

    @staticmethod
    def create_dentist(dentist_data: dict) -> Tuple[bool, str]:
        """Crea un nuevo dentista."""
        dentist = Dentist(
            id=0, # ID temporal, será autogenerado por la DB
            name=dentist_data['name'],
            phone=dentist_data.get('phone'),
            is_active=dentist_data.get('is_active', True)
        )
        is_valid, message = dentist.validate()
        if not is_valid:
            return False, message

        query = """
            INSERT INTO dentists (name, phone, is_active)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(query, (
                    dentist.name,
                    dentist.phone,
                    dentist.is_active
                ))
                new_id = cursor.fetchone()[0]
                logger.info(f"Dentista creado con ID: {new_id}")
                return True, "Dentista creado exitosamente."
        except Exception as e:
            logger.error(f"Error al crear dentista: {e}")
            return False, f"Error al crear dentista: {e}"

    @staticmethod
    def update_dentist(dentist_id: int, dentist_data: dict) -> Tuple[bool, str]:
        """Actualiza un dentista existente."""
        dentist = Dentist(
            id=dentist_id,
            name=dentist_data['name'],
            phone=dentist_data.get('phone'),
            is_active=dentist_data.get('is_active', True)
        )
        is_valid, message = dentist.validate()
        if not is_valid:
            return False, message

        query = """
            UPDATE dentists
            SET name = %s, phone = %s, is_active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id
        """
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(query, (
                    dentist.name,
                    dentist.phone,
                    dentist.is_active,
                    dentist_id
                ))
                if cursor.fetchone():
                    logger.info(f"Dentista con ID {dentist_id} actualizado.")
                    return True, "Dentista actualizado exitosamente."
                return False, "Dentista no encontrado."
        except Exception as e:
            logger.error(f"Error al actualizar dentista: {e}")
            return False, f"Error al actualizar dentista: {e}"

    @staticmethod
    def delete_dentist(dentist_id: int) -> Tuple[bool, str]:
        """Elimina un dentista por su ID."""
        # Antes de eliminar, verificar si el dentista tiene citas asociadas.
        if DentistService.has_appointments(dentist_id):
            return False, "No se puede eliminar el dentista porque tiene citas asociadas. Por favor, elimine o reasigne las citas primero."

        query = "DELETE FROM dentists WHERE id = %s RETURNING id"
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(query, (dentist_id,))
                if cursor.fetchone():
                    logger.info(f"Dentista con ID {dentist_id} eliminado.")
                    return True, "Dentista eliminado exitosamente."
                return False, "Dentista no encontrado."
        except Exception as e:
            logger.error(f"Error al eliminar dentista: {e}")
            return False, f"Error al eliminar dentista: {e}"

    @staticmethod
    def has_appointments(dentist_id: int) -> bool:
        """Verifica si el dentista tiene citas asociadas."""
        with get_db() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM appointments WHERE dentist_id = %s",
                (dentist_id,)
            )
            return cursor.fetchone()[0] > 0
