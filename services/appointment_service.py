import psycopg2
from datetime import datetime, time, date, timedelta
from typing import List, Optional, Tuple
from core.database import get_db
from models.appointment import Appointment
from services.payment_service import PaymentService # Importa PaymentService
from utils.validators import Validators
from utils.date_utils import is_working_hours, is_future_datetime
from .observable import Observable
import logging
from services.history_service import HistoryService # Importar HistoryService
from services.quote_service import QuoteService # Importar QuoteService

logger = logging.getLogger(__name__)

# Define or import the notify_all function
def notify_all(event_type: str, data: dict):
    """
    Mock implementation of notify_all.
    Replace this with the actual implementation or import it from the correct module.
    """
    logger.info(f"Notification sent: {event_type} with data {data}")

class AppointmentService(Observable):
    @staticmethod
    def delete_client_appointments(client_id: int) -> bool:
        """Elimina todas las citas de un cliente"""
        with get_db() as cursor:
            cursor.execute(
                "DELETE FROM appointments WHERE client_id = %s",
                (client_id,)
            )
            return cursor.rowcount > 0
    
    @staticmethod
    def update_appointment_status(appointment_id, new_status):
        """Actualiza los estados de la cita y, si se completa, marca los tratamientos asociados en el historial.

        Args:
            appointment_id (int): identificador de la cita
            new_status (str): estado de la cita ('pending', 'completed', 'cancelled')

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario.
        """
        try:
            with get_db() as cursor: # Usamos un cursor para esta operación también
                # Obtener el client_id antes de la actualización
                cursor.execute(
                    "SELECT client_id FROM appointments WHERE id = %s",
                    (appointment_id,)
                )
                client_id_row = cursor.fetchone()
                if not client_id_row:
                    logger.warning(f"Cita con ID {appointment_id} no encontrada para actualizar estado.")
                    return False
                client_id = client_id_row[0]

                cursor.execute(
                    "UPDATE appointments SET status = %s WHERE id = %s",
                    (new_status, appointment_id)
                )
                if cursor.rowcount > 0:
                    notify_all('APPOINTMENT_STATUS_CHANGED', {
                        'id': appointment_id,
                        'status': new_status
                    })

                    # Si la cita se marca como 'completed', actualizar los tratamientos en el historial del cliente
                    if new_status == 'completed':
                        treatments = AppointmentService.get_appointment_treatments(appointment_id)
                        for treatment in treatments:
                            success, msg = HistoryService.add_client_treatment(
                                client_id=client_id,
                                treatment_id=treatment['id'],
                                notes=f"Completado a través de cita ID: {appointment_id} - Originalmente: {treatment.get('notes', 'N/A')}",
                                treatment_date=date.today(), # Usa la fecha actual para el registro de completado
                                appointment_id=appointment_id, # Pasa el ID de la cita
                                quantity_to_mark_completed=treatment.get('quantity', 1), # Pasa la cantidad de la cita
                                cursor=cursor # Pasa el cursor
                            )
                            if not success:
                                logger.error(f"Error al marcar tratamiento {treatment['name']} (ID: {treatment['id']}) como completado para cliente {client_id}: {msg}")
                                # No revertimos toda la operación si falla un tratamiento individual,
                                # pero registramos el error.
                    return True
            return False
        except Exception as e:
            logger.error(f"Error al actualizar estado de cita {appointment_id}: {str(e)}")
            return False
    
    @staticmethod
    def create_appointment(client_id: int, 
                        appointment_date: date, 
                        appointment_time: time,
                        treatments: List[dict] = None, # Ahora acepta una lista de diccionarios de tratamientos
                        notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Crea una nueva cita en el sistema
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Validar datos antes de crear
            appointment_dt = datetime.combine(appointment_date, appointment_time)
            
            # Validar horario laboral
            if not is_working_hours(appointment_time):
                return False, "Fuera del horario laboral (07:30 - 19:30)"
                
            # Validar que sea en el futuro
            if not is_future_datetime(appointment_dt):
                return False, "No se pueden agendar citas en el pasado"
            
            with get_db() as cursor: # Inicia la transacción para la cita y sus deudas
                # Obtener datos del cliente
                cursor.execute(
                    "SELECT name, cedula FROM clients WHERE id = %s",
                    (client_id,)
                )
                client_data = cursor.fetchone()
                if not client_data:
                    return False, "Cliente no encontrado"
                
                client_name, client_cedula = client_data

                # Crear cita
                cursor.execute(
                    """
                    INSERT INTO appointments 
                    (client_id, client_name, client_cedula, date, time, status, notes, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, 'pending', %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, client_name, client_cedula, appointment_date, appointment_time, notes)
                )
                appointment_id = cursor.fetchone()[0]
                
                # Crear una descripción de deuda combinada para todos los tratamientos de la cita
                debt_description_parts = []
                total_debt_amount = 0.0

                # Agregar tratamientos si existen
                if treatments:
                    for treatment in treatments:
                        # Asegúrate de que 'id' y 'price' estén presentes en el diccionario de tratamiento
                        if 'id' in treatment and 'price' in treatment:
                            # Insertar tratamiento asociado a la cita
                            quantity = treatment.get('quantity', 1) # Obtener la cantidad del tratamiento
                            item_total = float(treatment['price']) * quantity
                            total_debt_amount += item_total
                            
                            debt_description_parts.append(f"{treatment.get('name', 'Desconocido')} ({quantity}x)")

                            cursor.execute(
                                """
                                INSERT INTO appointment_treatments 
                                (appointment_id, treatment_id, price, notes, quantity)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (appointment_id, treatment['id'], treatment['price'], 
                                f"Tratamiento: {treatment.get('name', 'Desconocido')}", quantity) # Usar .get para seguridad
                            )
                            
                            # Al crear una cita, también se añade el tratamiento al historial del cliente
                            # inicialmente con completed_quantity = 0, y total_quantity = quantity
                            HistoryService.add_client_treatment(
                                client_id=client_id,
                                treatment_id=treatment['id'],
                                notes=f"Asociado a cita ID: {appointment_id}",
                                treatment_date=appointment_date, # Fecha de la cita como fecha de origen
                                appointment_id=appointment_id,
                                quantity_to_mark_completed=0, # Inicialmente, no hay cantidad completada
                                cursor=cursor # Pasa el cursor
                            )
                        else:
                            logger.warning(f"Tratamiento incompleto, no se pudo añadir a la cita: {treatment}")
                
                return True, f"Cita creada exitosamente (ID: {appointment_id})"
                
        except Exception as e:
            logger.error(f"Error al crear cita: {str(e)}")
            return False, f"Error al crear cita: {str(e)}"

    @staticmethod
    def get_appointment_treatments(appointment_id: int) -> List[dict]:
        """Obtiene tratamientos asociados a una cita"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT t.id, t.name, at.price, at.notes, at.quantity
                FROM appointment_treatments at
                JOIN treatments t ON at.treatment_id = t.id
                WHERE at.appointment_id = %s
                """,
                (appointment_id,)
            )
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'price': float(row[2]),
                    'notes': row[3],
                    'quantity': row[4] # Incluir la cantidad
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_appointment_by_id(appointment_id: int) -> Optional[Appointment]:
        """Obtiene una cita por su ID"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT a.id, a.client_id, c.name, c.cedula, 
                       a.date, a.time, a.status, a.notes, 
                       a.created_at, a.updated_at
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                WHERE a.id = %s
                """,
                (appointment_id,)
            )
            if result := cursor.fetchone():
                return Appointment(*result)
            return None

    @staticmethod
    def update_appointment(appointment_id: int, treatments: List[dict] = None, **kwargs) -> Tuple[bool, str]:
        """Actualiza una cita existente"""
        valid_fields = ['client_id', 'date', 'time', 'notes', 'status']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
        
        if not updates and not treatments: # Permitir actualización si solo se cambian tratamientos
            return False, "No hay campos válidos para actualizar"
            
        try:
            with get_db() as cursor: # Inicia la transacción para la actualización
                # Obtener client_id si no se pasa en kwargs
                client_id = kwargs.get('client_id')
                if client_id is None:
                    # Si no se pasó client_id, recuperarlo de la cita existente
                    current_appointment = AppointmentService.get_appointment_by_id(appointment_id)
                    if current_appointment:
                        client_id = current_appointment.client_id
                    else:
                        return False, "Cita no encontrada."


                # Actualizar campos de la cita principal
                if updates:
                    set_clause = ", ".join([f"{field} = %s" for field in updates.keys()])
                    values = list(updates.values())
                    values.append(appointment_id)
                    
                    cursor.execute(
                        f"""
                        UPDATE appointments 
                        SET {set_clause}, updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                        """,
                        values
                    )
                    
                    if cursor.rowcount == 0:
                        return False, "Cita no encontrada"
                
                # Actualizar tratamientos asociados
                if treatments is not None: # Solo si se pasa una lista de tratamientos
                    # Eliminar tratamientos existentes para esta cita
                    cursor.execute(
                        "DELETE FROM appointment_treatments WHERE appointment_id = %s",
                        (appointment_id,)
                    )
                    
                    # Eliminar deudas anteriores asociadas a esta cita antes de crear las nuevas
                    cursor.execute(
                        """
                        DELETE FROM debts
                        WHERE appointment_id = %s;
                        """,
                        (appointment_id,)
                    )

                    # Eliminar tratamientos de historial asociados a esta cita
                    HistoryService.delete_client_treatments_by_appointment(appointment_id, cursor)
                    
                    # Crear una descripción de deuda combinada para todos los tratamientos de la cita
                    debt_description_parts = []
                    total_debt_amount = 0.0

                    for treatment in treatments:
                        if 'id' in treatment and 'price' in treatment:
                            quantity = treatment.get('quantity', 1)
                            item_total = float(treatment['price']) * quantity
                            total_debt_amount += item_total
                            
                            debt_description_parts.append(f"{treatment.get('name', 'Desconocido')} ({quantity}x)")

                            cursor.execute(
                                """
                                INSERT INTO appointment_treatments 
                                (appointment_id, treatment_id, price, notes, quantity)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (appointment_id, treatment['id'], treatment['price'], 
                                f"Tratamiento: {treatment.get('name', 'Desconocido')}", quantity)
                            )
                            # Añadir el tratamiento al historial del cliente (si no existe ya)
                            HistoryService.add_client_treatment(
                                client_id=client_id,
                                treatment_id=treatment['id'],
                                notes=f"Asociado a cita ID: {appointment_id}",
                                treatment_date=kwargs.get('date', date.today()), # Usar la nueva fecha si se actualiza, sino hoy
                                appointment_id=appointment_id,
                                quantity_to_mark_completed=0, # No se completa al actualizar la cita
                                cursor=cursor # Pasa el cursor
                            )

                else:
                    logger.warning(f"Tratamiento incompleto, no se pudo añadir a la cita: {treatment}")
                            
                return True, "Cita actualizada exitosamente"
                
        except Exception as e:
            logger.error(f"Error al actualizar cita: {str(e)}")
            return False, f"Error al actualizar cita: {str(e)}"

    @staticmethod
    def search_available_slots(date: date) -> List[Tuple[time, bool]]:
        """Busca horarios disponibles para una fecha dada"""
        slots = []
        start_time = time(7, 30)
        end_time = time(19, 30)
        
        with get_db() as cursor:
            # Obtener citas existentes para la fecha
            cursor.execute(
                "SELECT time FROM appointments WHERE date = %s AND status = 'pending'",
                (date,)
            )
            booked_times = {t[0] for t in cursor.fetchall()}
            
            # Generar slots cada 30 minutos
            current_time = start_time
            current_datetime = datetime.combine(date.today(), current_time) # Initialize current_datetime
            while current_time <= end_time:
                slots.append((
                    current_time,
                    current_time not in booked_times
                ))
                # Añadir 30 minutos
                current_datetime += timedelta(minutes=30)
                current_time = current_datetime.time()
                
        return slots

    @staticmethod
    def validate_appointment_time(date: date, time: time, exclude_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Valida si un horario de cita es válido
        Args:
            exclude_id: ID de cita a excluir (para actualizaciones)
        """
        appointment_dt = datetime.combine(date, time)
        
        # Validar horario laboral
        if not is_working_hours(time):
            return False, "Fuera del horario laboral (07:30 - 19:30)"
            
        # Validar que sea en el futuro
        if not is_future_datetime(appointment_dt):
            return False, "No se pueden agendar citas en el pasado"
            
        # Validar colisión con otras citas
        with get_db() as cursor:
            query = """
                SELECT id FROM appointments 
                WHERE date = %s AND time = %s AND status = 'pending'
            """
            params = [date, time]
            
            if exclude_id:
                query += " AND id != %s"
                params.append(exclude_id)
                
            cursor.execute(query, params)
            if cursor.fetchone():
                return False, "Horario ya reservado"
                
        return True, "Horario disponible"
    
    @staticmethod
    def search_clients(search_term: str) -> List[Tuple[int, str, str]]:
        """
        Busca clientes por nombre o cédula.
        Returns:
            List[Tuple[id, name, cedula]]
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, name, cedula 
                FROM clients 
                WHERE unaccent(name) ILIKE %s OR cedula ILIKE %s
                LIMIT 10
                """,
                (f"%{search_term}%", f"%{search_term}%")
            )
            return cursor.fetchall()
    
    @staticmethod
    def get_upcoming_appointments(limit: int = 5) -> List[Appointment]:
        """Versión más robusta con manejo de errores"""
        try:
            with get_db() as cursor:
                cursor.execute("""
                    SELECT a.id, a.client_id, c.name, c.cedula, 
                        a.date, a.time, a.status, a.notes,
                        a.created_at, a.updated_at
                    FROM appointments a
                    JOIN clients c ON a.client_id = c.id
                    WHERE a.date >= CURRENT_DATE
                    AND a.status = 'pending'
                    ORDER BY a.date ASC, a.time ASC
                    LIMIT %s
                """, (limit,))
                
                results = cursor.fetchall()
                if not results:
                    return []
                    
                appointments = []
                for row in results:
                    try:
                        appointments.append(Appointment(*row))
                    except Exception as e:
                        logger.error(f"Error al crear Appointment: {str(e)}")
                        continue
                        
                return appointments
                
        except Exception as e:
            logger.error(f"Error en get_upcoming_appointments: {str(e)}")
            return []
    
    @staticmethod
    def get_appointments(limit: int = 10, offset: int = 0, filters: dict = None) -> List[Appointment]:
        """Obtiene citas paginadas con filtros"""
        filters = filters or {}
        query = """
            SELECT a.id, a.client_id, c.name, c.cedula, 
                a.date, a.time, a.status, a.notes,
                a.created_at, a.updated_at
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            WHERE 1=1
        """
        params = []
    
        # Aplicar filtros
        if filters.get('date_from'):
            query += " AND a.date >= %s"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            query += " AND a.date <= %s"
            params.append(filters['date_to'])
        if filters.get('status'):
            query += " AND a.status = %s"
            params.append(filters['status'])
        if filters.get('search_term'):
            query += " AND (unaccent(c.name) ILIKE %s OR c.cedula ILIKE %s OR a.notes ILIKE %s)"
            params.extend([f"%{filters['search_term']}%"] * 3)
        
        query += " ORDER BY a.date DESC, a.time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        with get_db() as cursor:
            cursor.execute(query, params)
            return [Appointment(*row) for row in cursor.fetchall()]

    @staticmethod
    def count_appointments(filters: dict = None) -> int:
        """Cuenta el total de citas que coinciden con los filtros"""
        filters = filters or {}
        query = "SELECT COUNT(*) FROM appointments a JOIN clients c ON a.client_id = c.id WHERE 1=1"
        params = []
        
        # Aplicar filtros (igual que en get_appointments)
        if filters.get('date_from'):
            query += " AND a.date >= %s"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            query += " AND a.date <= %s"
            params.append(filters['date_to'])
        if filters.get('status'):
            query += " AND a.status = %s"
            params.append(filters['status'])
        if filters.get('search_term'):
            query += " AND (c.name ILIKE %s OR c.cedula ILIKE %s OR a.notes ILIKE %s)"
            params.extend([f"%{filters['search_term']}%"] * 3)
        
        with get_db() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    @staticmethod
    def delete_appointment(appointment_id: int) -> bool:
        """
        Elimina una cita por su ID y todas las deudas y tratamientos de historial asociados a ella.
        """
        try:
            with get_db() as cursor:
                # Iniciar una transacción
                cursor.execute("BEGIN;") 
                
                # Paso 1: Eliminar los tratamientos de historial asociados a esta cita
                HistoryService.delete_client_treatments_by_appointment(appointment_id, cursor)

                # Paso 2: Eliminar las deudas asociadas a esta cita
                cursor.execute(
                    """
                    DELETE FROM debts
                    WHERE appointment_id = %s;
                    """,
                    (appointment_id,)
                )
                logger.info(f"Eliminadas {cursor.rowcount} deudas asociadas a la cita {appointment_id}.")

                # Paso 3: Eliminar los tratamientos de la tabla appointment_treatments
                cursor.execute(
                    """
                    DELETE FROM appointment_treatments
                    WHERE appointment_id = %s;
                    """,
                    (appointment_id,)
                )
                logger.info(f"Eliminados {cursor.rowcount} tratamientos de appointment_treatments para la cita {appointment_id}.")


                # Paso 4: Eliminar la cita
                cursor.execute(
                    """
                    DELETE FROM appointments
                    WHERE id = %s;
                    """,
                    (appointment_id,)
                )
                if cursor.rowcount > 0:
                    cursor.execute("COMMIT;") # Confirmar la transacción
                    logger.info(f"Cita con ID {appointment_id} eliminada con éxito.")
                    return True
                else:
                    cursor.execute("ROLLBACK;") # Revertir si la cita no se encontró
                    logger.warning(f"No se encontró la cita con ID {appointment_id} para eliminar.")
                    return False
        except Exception as e:
            cursor.execute("ROLLBACK;") # Revertir en caso de error
            logger.error(f"Error al eliminar cita con ID {appointment_id} y sus deudas asociadas: {e}")
            return False

# Funciones de conveniencia para mantener compatibilidad
def create_appointment(*args, **kwargs):
    # Asegúrate de que se pase la instancia de AppointmentService si es un método de instancia
    return AppointmentService.create_appointment(*args, **kwargs)

def get_appointment_by_id(*args, **kwargs):
    return AppointmentService.get_appointment_by_id(*args, **kwargs)

def update_appointment(*args, **kwargs):
    # Asegúrate de que se pase la instancia de AppointmentService si es un método de instancia
    return AppointmentService.update_appointment(*args, **kwargs)

def search_available_slots(*args, **kwargs):
    return AppointmentService.search_available_slots(*args, **kwargs)

def validate_appointment_time(*args, **kwargs):
    return AppointmentService.validate_appointment_time(*args, **kwargs)

def search_clients(*args, **kwargs):
    return AppointmentService.search_clients(*args, **kwargs)

def get_appointments(*args, **kwargs):
    return AppointmentService.get_appointments(*args, **kwargs)

def count_appointments(*args, **kwargs):
    return AppointmentService.count_appointments(*args, **kwargs)

def delete_appointment(*args, **kwargs):
    return AppointmentService.delete_appointment(*args, **kwargs)

def get_appointment_treatments(*args, **kwargs):
    return AppointmentService.get_appointment_treatments(*args, **kwargs)
