from datetime import datetime, time, date, timedelta
from typing import List, Optional, Tuple
from core.database import get_db
from models.appointment import Appointment
from services.payment_service import PaymentService
from utils.validators import Validators
from utils.date_utils import is_working_hours, is_future_datetime
from .observable import Observable
import logging
logger = logging.getLogger(__name__)
#print

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
        """Actualiza los estados de la cita

        Args:
            appointment_id (int): identificador de la cita
            new_status (str): estado de la cita

        Returns:
            bool: _description_
        """
        with get_db() as cursor:
            cursor.execute(
                "UPDATE appointments SET status = %s WHERE id = %s",
                (new_status, appointment_id)
            )
            if cursor.rowcount > 0:
                notify_all('APPOINTMENT_STATUS_CHANGED', {
                    'id': appointment_id,
                    'status': new_status
                })
                return True
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
            
            with get_db() as cursor:
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
                
                # Agregar tratamientos si existen
                if treatments:
                    total_debt = 0.0
                    for treatment in treatments:
                        # Asegúrate de que 'id' y 'price' estén presentes en el diccionario de tratamiento
                        if 'id' in treatment and 'price' in treatment:
                            cursor.execute(
                                """
                                INSERT INTO appointment_treatments 
                                (appointment_id, treatment_id, price, notes)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (appointment_id, treatment['id'], treatment['price'], 
                                f"Tratamiento: {treatment.get('name', 'Desconocido')}") # Usar .get para seguridad
                            )
                            total_debt += float(treatment['price']) * treatment.get('quantity', 1)
                        else:
                            logger.warning(f"Tratamiento incompleto, no se pudo añadir a la cita: {treatment}")
                    
                    # Crear deuda asociada si hay tratamientos con costo
                    if total_debt > 0:
                        PaymentService().create_debt(
                            client_id=client_id,
                            amount=total_debt,
                            description=f"Tratamientos para cita #{appointment_id}"
                        )

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
                SELECT t.id, t.name, at.price, at.notes
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
                    'notes': row[3]
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
    def update_appointment(self, appointment_id: int, treatments: List[dict] = None, **kwargs) -> Tuple[bool, str]:
        """Actualiza una cita existente"""
        valid_fields = ['client_id', 'date', 'time', 'notes', 'status']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
        
        if not updates and not treatments: # Permitir actualización si solo se cambian tratamientos
            return False, "No hay campos válidos para actualizar"
            
        try:
            with get_db() as cursor:
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
                    
                    total_debt = 0.0
                    for treatment in treatments:
                        if 'id' in treatment and 'price' in treatment:
                            cursor.execute(
                                """
                                INSERT INTO appointment_treatments 
                                (appointment_id, treatment_id, price, notes)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (appointment_id, treatment['id'], treatment['price'], 
                                f"Tratamiento: {treatment.get('name', 'Desconocido')}")
                            )
                            total_debt += float(treatment['price']) * treatment.get('quantity', 1)
                        else:
                            logger.warning(f"Tratamiento incompleto, no se pudo añadir a la cita: {treatment}")
                    
                    # Actualizar deuda asociada (esto es una simplificación, en un caso real
                    # podrías querer ajustar la deuda existente en lugar de solo crear una nueva)
                    # Por simplicidad, aquí se crea una nueva deuda por los nuevos tratamientos
                    # o se podría buscar la deuda existente y actualizarla.
                    # Para una gestión de deuda más robusta, se necesitaría un enfoque más sofisticado.
                    # Por ahora, eliminaremos las deudas anteriores de tratamientos de esta cita y crearemos una nueva
                    PaymentService().delete_debt_by_description_and_client(
                        client_id=updates.get('client_id', self.get_appointment_by_id(appointment_id).client_id), # Asegura que tenemos el client_id
                        description_prefix=f"Tratamientos para cita #{appointment_id}"
                    )
                    if total_debt > 0:
                        PaymentService().create_debt(
                            client_id=updates.get('client_id', self.get_appointment_by_id(appointment_id).client_id),
                            amount=total_debt,
                            description=f"Tratamientos para cita #{appointment_id}"
                        )


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
            while current_time <= end_time:
                slots.append((
                    current_time,
                    current_time not in booked_times
                ))
                # Añadir 30 minutos
                # Esto puede causar problemas al pasar de 23:30 a 00:00 del día siguiente.
                # Una forma más robusta sería usar timedelta.
                current_datetime = datetime.combine(date.today(), current_time) # Usar una fecha dummy para timedelta
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
            return []  # Devuelve lista vacía en lugar de None
    
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
        """Elimina una cita por su ID"""
        with get_db() as cursor:
            cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
            return cursor.rowcount > 0
        

# Funciones de conveniencia para mantener compatibilidad
def create_appointment(*args, **kwargs):
    return AppointmentService.create_appointment(*args, **kwargs)

def get_appointment_by_id(*args, **kwargs):
    return AppointmentService.get_appointment_by_id(*args, **kwargs)

def update_appointment(*args, **kwargs):
    return AppointmentService.update_appointment(*args, **kwargs)

def search_available_slots(*args, **kwargs):
    return AppointmentService.search_available_slots(*args, **kwargs)

def validate_appointment_time(*args, **kwargs):
    return AppointmentService.validate_appointment_time(*args, **kwargs)

def search_clients(*args, **kwargs):  # ¡Añade esta línea!
    return AppointmentService.search_clients(*args, **kwargs)

def get_appointments(*args, **kwargs):
    return AppointmentService.get_appointments(*args, **kwargs)

def count_appointments(*args, **kwargs):
    return AppointmentService.count_appointments(*args, **kwargs)

def delete_appointment(*args, **kwargs):
    return AppointmentService.delete_appointment(*args, **kwargs)

def get_appointment_treatments(*args, **kwargs):
    return AppointmentService.get_appointment_treatments(*args, **kwargs)
