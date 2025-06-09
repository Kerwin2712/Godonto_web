from typing import List, Optional, Tuple
from datetime import timedelta, datetime
import logging
from models.treatment import Treatment
# Asume que tienes un módulo core.database con get_db o Database.get_cursor
# Si tu conexión a la base de datos es diferente, ajusta esta importación.
from core.database import get_db, Database 

logger = logging.getLogger(__name__)

class TreatmentService:
    @staticmethod
    def create_treatment_if_not_exists(name: str, price: float) -> int:
        """
        Crea un nuevo tratamiento si no existe, o devuelve el ID existente.
        Returns: ID del tratamiento
        """
        try:
            # Buscar tratamiento por nombre
            # search_treatments retorna una lista de tuplas (id, name, price)
            # Necesitamos convertir a objetos Treatment para consistencia o adaptar la lógica
            found_treatments_data = TreatmentService.search_treatments(search_term=name)
            
            # Convierte las tuplas a objetos Treatment para el chequeo
            found_treatments = [
                Treatment(id=t[0], name=t[1], price=float(t[2]), description="", duration="00:00:00", is_active=True) 
                for t in found_treatments_data
            ]

            if found_treatments:
                # Comprobar si hay una coincidencia exacta por nombre
                for t in found_treatments:
                    if t.name.lower() == name.lower():
                        return t.id
            
            # Si no existe o no hay coincidencia exacta, crear nuevo tratamiento
            # Se llama a create_treatment con los argumentos esperados,
            # y se espera un ID o None, no la tupla (bool, str) que el otro create_treatment devolverá.
            # Esto puede requerir un ajuste si quieres que create_treatment_if_not_exists también
            # se alinee con el nuevo retorno de create_treatment.
            # Por ahora, se asume que create_treatment sigue devolviendo un ID.
            new_id, _ = TreatmentService.create_treatment( # Modificado para capturar el ID y descartar el mensaje
                name=name,
                description=f"Tratamiento creado automáticamente: {name}",
                price=price,
                duration="00:30:00", # Duración por defecto
                is_active=True
            )
            return new_id
        except Exception as e:
            logger.error(f"Error al crear tratamiento (if_not_exists): {e}")
            raise
    
    @staticmethod
    def search_treatments(search_term: str) -> List[Tuple[int, str, float]]: # Cambiado a float
        """
        Busca tratamiento por nombre.
        Returns:
            List[Tuple[id, name, price]]
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, price 
                    FROM treatments 
                    WHERE unaccent(name) ILIKE %s
                    LIMIT 10
                    """,
                    (f"%{search_term}%", )
                )
                return cursor.fetchall()
        except Exception as e: # Captura la excepción general
            logger.error(f"Error al buscar tratamientos: {e}") # Mensaje de error más específico
            return [] # Retorna una lista vacía en caso de error
    
    @staticmethod
    def create_treatment(name: str, price: float, 
                         description: Optional[str] = None, # Ahora opcional
                         duration: str = "00:30:00",      # Duración por defecto
                         is_active: bool = True) -> Tuple[Optional[int], str]: # Cambiado el tipo de retorno
        """
        Crea un nuevo tratamiento en la base de datos.
        Args:
            name (str): Nombre del tratamiento.
            price (float): Precio del tratamiento.
            description (Optional[str]): Descripción del tratamiento (opcional).
            duration (str): Duración del tratamiento en formato 'HH:MM:SS' o 'INTERVAL' (con valor por defecto).
            is_active (bool): Si el tratamiento está activo (con valor por defecto).
        Returns:
            Tuple[Optional[int], str]: (ID del nuevo tratamiento o None, mensaje de éxito/error).
        """
        try:
            query = """
                INSERT INTO treatments (name, description, price, duration, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id;
            """
            with get_db() as cursor:
                cursor.execute(query, (name, description, price, duration, is_active))
                new_id = cursor.fetchone()[0]
                return new_id, "Tratamiento creado exitosamente."
        except Exception as e:
            logger.error(f"Error al crear tratamiento: {e}")
            return None, f"Error al crear tratamiento: {str(e)}"

    @staticmethod
    def get_treatment_by_id(treatment_id: int) -> Optional[Treatment]:
        """
        Obtiene un tratamiento por su ID.
        Args:
            treatment_id (int): El ID del tratamiento a buscar.
        Returns:
            Optional[Treatment]: El objeto Treatment si se encuentra, None en caso contrario.
        """
        try:
            query = """
                SELECT id, name, description, price, duration, is_active, created_at, updated_at
                FROM treatments
                WHERE id = %s;
            """
            with get_db() as cursor:
                cursor.execute(query, (treatment_id,))
                row = cursor.fetchone()
                if row:
                    return Treatment(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        price=float(row[3]), # Convertir a float
                        duration=row[4],
                        is_active=row[5],
                        created_at=row[6],
                        updated_at=row[7]
                    )
            return None
        except Exception as e:
            logger.error(f"Error al obtener tratamiento por ID {treatment_id}: {e}")
            return None

    @staticmethod
    def get_all_treatments(active_only: bool = False, search_term: Optional[str] = None) -> List[Treatment]: # Cambiado active_only a False por defecto para la vista de administración
        """
        Lista todos los tratamientos, con opciones de filtrado.
        Args:
            active_only (bool): Si es True, solo lista tratamientos activos.
            search_term (Optional[str]): Término para buscar en el nombre o descripción del tratamiento.
        Returns:
            List[Treatment]: Una lista de objetos Treatment.
        """
        try:
            query = """
                SELECT id, name, description, price, duration, is_active, created_at, updated_at
                FROM treatments
                WHERE 1=1
            """
            params = []

            if active_only:
                query += " AND is_active = TRUE"
            
            if search_term:
                query += " AND (unaccent(name) ILIKE unaccent(%s) OR unaccent(description) ILIKE unaccent(%s))"
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            query += " ORDER BY name ASC;"

            with get_db() as cursor:
                cursor.execute(query, params)
                return [
                    Treatment(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        price=float(row[3]),
                        duration=row[4],
                        is_active=row[5],
                        created_at=row[6],
                        updated_at=row[7]
                    ) for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error al obtener todos los tratamientos: {e}")
            return []

    @staticmethod
    def update_treatment(treatment_id: int, name: str, price: float) -> Tuple[bool, str]: # Simplificado para la vista
        """
        Actualiza los detalles de un tratamiento existente (nombre y precio).
        Args:
            treatment_id (int): El ID del tratamiento a actualizar.
            name (str): Nuevo nombre del tratamiento.
            price (float): Nuevo precio del tratamiento.
        Returns:
            Tuple[bool, str]: (True, mensaje_exito) o (False, mensaje_error).
        """
        try:
            query = """
                UPDATE treatments
                SET name = %s, price = %s, updated_at = NOW()
                WHERE id = %s;
            """
            with get_db() as cursor:
                cursor.execute(query, (name, price, treatment_id))
                if cursor.rowcount > 0:
                    return True, "Tratamiento actualizado exitosamente."
                else:
                    return False, "No se encontró el tratamiento para actualizar o no hubo cambios."
        except Exception as e:
            logger.error(f"Error al actualizar tratamiento {treatment_id}: {e}")
            return False, f"Error al actualizar tratamiento: {str(e)}"

    @staticmethod
    def delete_treatment(treatment_id: int) -> Tuple[bool, str]: # Cambiado el tipo de retorno
        """
        Elimina un tratamiento por su ID.
        Debido a la restricción ON DELETE RESTRICT en quote_treatments,
        este método fallará si el tratamiento está asociado a algún presupuesto.
        Args:
            treatment_id (int): El ID del tratamiento a eliminar.
        Returns:
            Tuple[bool, str]: (True, mensaje_exito) o (False, mensaje_error).
        """
        try:
            with get_db() as cursor:
                # Verificar si el tratamiento está en uso en quote_treatments
                cursor.execute(
                    "SELECT COUNT(*) FROM quote_treatments WHERE treatment_id = %s;",
                    (treatment_id,)
                )
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"No se puede eliminar el tratamiento {treatment_id} porque está asociado a presupuestos.")
                    return False, "No se puede eliminar el tratamiento porque está asociado a presupuestos."
                
                # Verificar en appointment_treatments
                cursor.execute(
                    "SELECT COUNT(*) FROM appointment_treatments WHERE treatment_id = %s;",
                    (treatment_id,)
                )
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"No se puede eliminar el tratamiento {treatment_id} porque está asociado a citas.")
                    return False, "No se puede eliminar el tratamiento porque está asociado a citas."

                # Si no está en uso, proceder con la eliminación
                query = "DELETE FROM treatments WHERE id = %s;"
                cursor.execute(query, (treatment_id,))
                if cursor.rowcount > 0:
                    return True, "Tratamiento eliminado exitosamente."
                else:
                    return False, "No se encontró el tratamiento para eliminar."
        except Exception as e:
            logger.error(f"Error al eliminar tratamiento {treatment_id}: {e}")
            return False, f"Error al eliminar tratamiento: {str(e)}"

def search_treatment(*args, **kwargs):
    # Esta función parece ser un wrapper para TreatmentService.search_treatments
    # Si TreatmentService.search_treatments devuelve objetos Treatment, este wrapper
    # podría necesitar ajustarse si se usa en otros lugares que esperan tuplas.
    return TreatmentService.search_treatments(*args, **kwargs)
