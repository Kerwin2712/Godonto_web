# services/history_service.py
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from core.database import get_db, Database
from models.client import Client
from models.appointment import Appointment
from models.treatment import Treatment
import logging

logger = logging.getLogger(__name__)

class HistoryService:
    @staticmethod
    def get_suggested_and_completed_treatments(client_id: int) -> List[Dict]:
        """
        Obtiene una lista unificada de tratamientos asociados al cliente,
        marcando su estado como 'completed' si están en client_treatments
        o 'pending' si vienen de citas/presupuestos y no están completados.
        """
        all_treatments = {} # Usando un diccionario para rastrear la unicidad por treatment_id

        with get_db() as cursor:
            # Obtener tratamientos de client_treatments (tratamientos explícitamente completados/registrados)
            cursor.execute(
                """
                SELECT ct.treatment_id, t.name, t.price, ct.notes, ct.id as client_treatment_record_id, ct.treatment_date
                FROM client_treatments ct
                JOIN treatments t ON ct.treatment_id = t.id
                WHERE ct.client_id = %s
                """,
                (client_id,)
            )
            for row in cursor.fetchall():
                treatment_id = row[0]
                all_treatments[treatment_id] = {
                    "id": treatment_id,
                    "name": row[1],
                    "price": float(row[2]),
                    "notes": row[3],
                    "status": "completed", # Implícitamente completado si está en client_treatments
                    "source": "historial_directo",
                    "client_treatment_record_id": row[4], # ID del registro en client_treatments
                    "treatment_date": row[5]
                }

            # Obtener tratamientos de appointment_treatments (potencialmente pendientes)
            cursor.execute(
                """
                SELECT DISTINCT at.treatment_id, t.name, t.price
                FROM appointment_treatments at
                JOIN appointments a ON at.appointment_id = a.id
                JOIN treatments t ON at.treatment_id = t.id
                WHERE a.client_id = %s
                """,
                (client_id,)
            )
            for row in cursor.fetchall():
                treatment_id = row[0]
                if treatment_id not in all_treatments: # Solo añadir si no está ya presente (completado o de cita)
                    all_treatments[treatment_id] = {
                        "id": treatment_id,
                        "name": row[1],
                        "price": float(row[2]),
                        "notes": "Asociado a cita (Pendiente)",
                        "status": "pending",
                        "source": "cita",
                        "client_treatment_record_id": None, # No hay registro directo en client_treatment todavía
                        "treatment_date": None # No hay fecha específica para este estado "pendiente"
                    }

            # Obtener tratamientos de quote_treatments (potencialmente pendientes)
            cursor.execute(
                """
                SELECT DISTINCT qt.treatment_id, t.name, t.price
                FROM quote_treatments qt
                JOIN quotes q ON qt.quote_id = q.id
                JOIN treatments t ON qt.treatment_id = t.id
                WHERE q.client_id = %s
                """,
                (client_id,)
            )
            for row in cursor.fetchall():
                treatment_id = row[0]
                if treatment_id not in all_treatments: # Solo añadir si no está ya presente (completado o de cita/presupuesto)
                    all_treatments[treatment_id] = {
                        "id": treatment_id,
                        "name": row[1],
                        "price": float(row[2]),
                        "notes": "Asociado a presupuesto (Pendiente)",
                        "status": "pending",
                        "source": "presupuesto",
                        "client_treatment_record_id": None,
                        "treatment_date": None
                    }
        
        # Ordenar los tratamientos: pendientes primero, luego completados, y finalmente por nombre
        sorted_treatments = sorted(
            all_treatments.values(),
            key=lambda x: (0 if x['status'] == 'pending' else 1, x['name'])
        )
        return sorted_treatments

    @staticmethod
    def get_client_full_history(client_id: int) -> Dict:
        """
        Obtiene el historial completo de un cliente, incluyendo datos personales,
        registros médicos, tratamientos unificados (pendientes y completados),
        citas y presupuestos.
        """
        history_data = {
            "client_info": None,
            "medical_records": [],
            "all_client_treatments": [], # Nueva clave para tratamientos unificados
            "appointments": [],
            "quotes": []
        }

        with get_db() as cursor:
            # 1. Obtener información del cliente
            cursor.execute(
                """
                SELECT id, name, cedula, phone, email, address, created_at, updated_at
                FROM clients
                WHERE id = %s
                """,
                (client_id,)
            )
            client_row = cursor.fetchone()
            if client_row:
                history_data["client_info"] = Client(
                    id=client_row[0],
                    name=client_row[1],
                    cedula=client_row[2],
                    phone=client_row[3],
                    email=client_row[4],
                    address=client_row[5],
                    created_at=client_row[6],
                    updated_at=client_row[7]
                )
            else:
                return history_data # Cliente no encontrado

            # 2. Obtener registros de historial médico general (medical_history)
            cursor.execute(
                """
                SELECT id, record_date, description, treatment_details, notes, created_by,
                       reason_for_visit, diagnosis, procedures_performed, prescription, next_appointment_date,
                       created_at, updated_at
                FROM medical_history
                WHERE client_id = %s
                ORDER BY record_date DESC
                """,
                (client_id,)
            )
            history_data["medical_records"] = [
                {
                    "id": row[0],
                    "record_date": row[1],
                    "description": row[2],
                    "treatment_details": row[3],
                    "notes": row[4],
                    "created_by": row[5],
                    "reason_for_visit": row[6],
                    "diagnosis": row[7],
                    "procedures_performed": row[8],
                    "prescription": row[9],
                    "next_appointment_date": row[10],
                    "created_at": row[11],
                    "updated_at": row[12]
                } for row in cursor.fetchall()
            ]

            # 3. Obtener citas del cliente y sus tratamientos asociados
            cursor.execute(
                """
                SELECT a.id, a.date, a.time, a.status, a.notes,
                       ARRAY_AGG(JSON_BUILD_OBJECT('id', t.id, 'name', t.name, 'price', at.price)) FILTER (WHERE t.id IS NOT NULL) AS treatments_list
                FROM appointments a
                LEFT JOIN appointment_treatments at ON a.id = at.appointment_id
                LEFT JOIN treatments t ON at.treatment_id = t.id
                WHERE a.client_id = %s
                GROUP BY a.id, a.date, a.time, a.status, a.notes
                ORDER BY a.date DESC, a.time DESC
                """,
                (client_id,)
            )
            appointments_raw = cursor.fetchall()
            for app_row in appointments_raw:
                app_dict = {
                    "id": app_row[0],
                    "date": app_row[1],
                    "time": app_row[2].strftime('%H:%M') if app_row[2] else None,
                    "status": app_row[3],
                    "notes": app_row[4],
                    "treatments": app_row[5] if app_row[5] else []
                }
                history_data["appointments"].append(app_dict)

            # 4. Obtener presupuestos del cliente y sus tratamientos asociados
            cursor.execute(
                """
                SELECT q.id, q.quote_date, q.total_amount, q.status, q.notes,
                       ARRAY_AGG(JSON_BUILD_OBJECT('id', t.id, 'name', t.name, 'quantity', qt.quantity, 'price', qt.price_at_quote)) FILTER (WHERE t.id IS NOT NULL) AS treatments_list
                FROM quotes q
                LEFT JOIN quote_treatments qt ON q.id = qt.quote_id
                LEFT JOIN treatments t ON qt.treatment_id = t.id
                WHERE q.client_id = %s
                GROUP BY q.id, q.quote_date, q.total_amount, q.status, q.notes
                ORDER BY q.quote_date DESC
                """,
                (client_id,)
            )
            quotes_raw = cursor.fetchall()
            for quote_row in quotes_raw:
                quote_dict = {
                    "id": quote_row[0],
                    "quote_date": quote_row[1],
                    "total_amount": float(quote_row[2]),
                    "status": quote_row[3],
                    "notes": quote_row[4],
                    "treatments": quote_row[5] if quote_row[5] else []
                }
                history_data["quotes"].append(quote_dict)
        
        # 5. Obtener tratamientos unificados (pendientes y completados)
        history_data["all_client_treatments"] = HistoryService.get_suggested_and_completed_treatments(client_id)

        return history_data

    @staticmethod
    def add_client_treatment(client_id: int, treatment_id: int, notes: Optional[str] = None, treatment_date: Optional[date] = None) -> Tuple[bool, str]:
        """
        Añade un tratamiento directamente al historial del cliente (client_treatments).
        Si el tratamiento ya existe para el cliente en client_treatments, lo actualiza.
        """
        try:
            if treatment_date is None:
                treatment_date = date.today()

            with get_db() as cursor:
                # Comprobar si el tratamiento ya existe para este cliente en client_treatments
                cursor.execute(
                    """
                    SELECT id FROM client_treatments
                    WHERE client_id = %s AND treatment_id = %s
                    """,
                    (client_id, treatment_id)
                )
                existing_id = cursor.fetchone()

                if existing_id:
                    # Actualizar el registro existente (por ejemplo, notas, fecha)
                    record_id = existing_id[0]
                    cursor.execute(
                        """
                        UPDATE client_treatments
                        SET notes = %s, treatment_date = %s, updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                        """,
                        (notes, treatment_date, record_id)
                    )
                    return True, f"Tratamiento de historial actualizado exitosamente (ID: {record_id})."
                else:
                    # Insertar nuevo registro
                    cursor.execute(
                        """
                        INSERT INTO client_treatments (client_id, treatment_id, treatment_date, notes, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        RETURNING id
                        """,
                        (client_id, treatment_id, treatment_date, notes)
                    )
                    new_id = cursor.fetchone()[0]
                    return True, f"Tratamiento de historial añadido exitosamente (ID: {new_id})."
        except Exception as e:
            logger.error(f"Error al añadir/actualizar tratamiento de historial: {str(e)}")
            return False, f"Error al añadir/actualizar tratamiento de historial: {str(e)}"
    
    @staticmethod
    def delete_client_treatment(client_treatment_id: int) -> Tuple[bool, str]:
        """
        Elimina un tratamiento de la tabla client_treatments.
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    "DELETE FROM client_treatments WHERE id = %s RETURNING id",
                    (client_treatment_id,)
                )
                if cursor.fetchone():
                    return True, "Tratamiento de historial eliminado exitosamente."
                else:
                    return False, "No se encontró el tratamiento de historial para eliminar."
        except Exception as e:
            logger.error(f"Error al eliminar tratamiento de historial {client_treatment_id}: {str(e)}")
            return False, f"Error al eliminar tratamiento de historial: {str(e)}"

    @staticmethod
    def add_medical_record(
        client_id: int,
        description: str,
        treatment_details: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[int] = None,
        record_date: Optional[datetime] = None,
        reason_for_visit: Optional[str] = None,
        diagnosis: Optional[str] = None,
        procedures_performed: Optional[str] = None,
        prescription: Optional[str] = None,
        next_appointment_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Añade un nuevo registro de historial médico a la tabla medical_history.
        """
        try:
            if record_date is None:
                record_date = datetime.now()

            with get_db() as cursor:
                cursor.execute(
                    """
                    INSERT INTO medical_history (
                        client_id, record_date, description, treatment_details, notes, created_by,
                        reason_for_visit, diagnosis, procedures_performed, prescription, next_appointment_date,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (
                        client_id, record_date, description, treatment_details, notes, created_by,
                        reason_for_visit, diagnosis, procedures_performed, prescription, next_appointment_date
                    )
                )
                new_id = cursor.fetchone()[0]
                return True, f"Registro médico añadido exitosamente (ID: {new_id})."
        except Exception as e:
            logger.error(f"Error al añadir registro médico: {str(e)}")
            return False, f"Error al añadir registro médico: {str(e)}"
    
    @staticmethod
    def update_medical_record(
        record_id: int,
        description: Optional[str] = None,
        treatment_details: Optional[str] = None,
        notes: Optional[str] = None,
        reason_for_visit: Optional[str] = None,
        diagnosis: Optional[str] = None,
        procedures_performed: Optional[str] = None,
        prescription: Optional[str] = None,
        next_appointment_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Actualiza un registro de historial médico existente en la tabla medical_history.
        """
        try:
            updates = []
            params = []

            if description is not None:
                updates.append("description = %s")
                params.append(description)
            if treatment_details is not None:
                updates.append("treatment_details = %s")
                params.append(treatment_details)
            if notes is not None:
                updates.append("notes = %s")
                params.append(notes)
            if reason_for_visit is not None:
                updates.append("reason_for_visit = %s")
                params.append(reason_for_visit)
            if diagnosis is not None:
                updates.append("diagnosis = %s")
                params.append(diagnosis)
            if procedures_performed is not None:
                updates.append("procedures_performed = %s")
                params.append(procedures_performed)
            if prescription is not None:
                updates.append("prescription = %s")
                params.append(prescription)
            if next_appointment_date is not None:
                updates.append("next_appointment_date = %s")
                params.append(next_appointment_date)
            
            if not updates:
                return False, "No hay campos para actualizar."

            set_clause = ", ".join(updates)
            params.append(record_id) # Añadir record_id para la cláusula WHERE

            with get_db() as cursor:
                cursor.execute(
                    f"""
                    UPDATE medical_history
                    SET {set_clause}, updated_at = NOW()
                    WHERE id = %s
                    RETURNING id
                    """,
                    params
                )
                if cursor.fetchone():
                    return True, "Registro médico actualizado exitosamente."
                else:
                    return False, "No se encontró el registro médico para actualizar."
        except Exception as e:
            logger.error(f"Error al actualizar registro médico {record_id}: {str(e)}")
            return False, f"Error al actualizar registro médico: {str(e)}"

    @staticmethod
    def delete_medical_record(record_id: int) -> Tuple[bool, str]:
        """
        Elimina un registro de historial médico de la tabla medical_history.
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    "DELETE FROM medical_history WHERE id = %s RETURNING id",
                    (record_id,)
                )
                if cursor.fetchone():
                    return True, "Registro médico eliminado exitosamente."
                else:
                    return False, "No se encontró el registro médico para eliminar."
        except Exception as e:
            logger.error(f"Error al eliminar registro médico {record_id}: {str(e)}")
            return False, f"Error al eliminar registro médico: {str(e)}"
