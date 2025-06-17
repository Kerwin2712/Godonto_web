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
        o 'pending' si vienen de citas/presupuestos y no están completados,
        incluyendo las cantidades.
        """
        all_treatments_map = {} # Usando un diccionario para rastrear la unicidad por (treatment_id, source_id, source_type)

        with get_db() as cursor:
            # ORIGINALMENTE: 1. Obtener tratamientos de client_treatments (tratamientos ya completados)
            # Esta sección se comenta o elimina si solo se quieren ver tratamientos de presupuestos
            # cursor.execute(
            #     """
            #     SELECT
            #         ct.id AS client_treatment_record_id,
            #         ct.treatment_id,
            #         t.name,
            #         t.price,
            #         ct.notes,
            #         ct.treatment_date,
            #         ct.completed_quantity,
            #         ct.total_quantity,
            #         ct.appointment_id,
            #         ct.quote_id
            #     FROM client_treatments ct
            #     JOIN treatments t ON ct.treatment_id = t.id
            #     WHERE ct.client_id = %s
            #     """,
            #     (client_id,)
            # )
            # for row in cursor.fetchall():
            #     treatment_id = row[1]
            #     source_id = None
            #     source_type = "historial_directo"

            #     if row[8] is not None: # appointment_id
            #         source_id = row[8]
            #         source_type = "cita"
            #     elif row[9] is not None: # quote_id
            #         source_id = row[9]
            #         source_type = "presupuesto"

            #     unique_key = (treatment_id, source_id, source_type, row[0]) # Añadir record_id para unicidad aún mayor

            #     all_treatments_map[unique_key] = {
            #         "id": treatment_id,
            #         "name": row[2],
            #         "price": float(row[3]),
            #         "notes": row[4],
            #         "status": "completed",
            #         "source": source_type,
            #         "client_treatment_record_id": row[0],
            #         "treatment_date": row[5],
            #         "completed_quantity": row[6],
            #         "total_quantity": row[7],
            #         "appointment_id": row[8],
            #         "quote_id": row[9]
            #     }

            # ORIGINALMENTE: 2. Obtener tratamientos de appointment_treatments (potencialmente pendientes)
            # Esta sección se comenta o elimina si solo se quieren ver tratamientos de presupuestos
            # cursor.execute(
            #     """
            #     SELECT
            #         at.treatment_id,
            #         t.name,
            #         t.price,
            #         at.quantity,
            #         a.id AS appointment_id
            #     FROM appointment_treatments at
            #     JOIN appointments a ON at.appointment_id = a.id
            #     JOIN treatments t ON at.treatment_id = t.id
            #     WHERE a.client_id = %s -- No filtrar por status, la vista unificada se encarga
            #     """,
            #     (client_id,)
            # )
            # for row in cursor.fetchall():
            #     treatment_id = row[0]
            #     total_expected_quantity = row[3]
            #     appointment_id = row[4]

            #     unique_key = (treatment_id, appointment_id, "cita", None) # None para client_treatment_record_id

            #     if unique_key in all_treatments_map and all_treatments_map[unique_key]["status"] == "completed" and \
            #        all_treatments_map[unique_key]["completed_quantity"] >= total_expected_quantity:
            #         continue

            #     cursor.execute(
            #         """
            #         SELECT COALESCE(SUM(completed_quantity), 0)
            #         FROM client_treatments
            #         WHERE client_id = %s AND treatment_id = %s AND appointment_id = %s
            #         """,
            #         (client_id, treatment_id, appointment_id)
            #     )
            #     completed_qty_for_source = cursor.fetchone()[0]

            #     status = "pending"
            #     if completed_qty_for_source >= total_expected_quantity:
            #         status = "completed"

            #     all_treatments_map[unique_key] = {
            #         "id": treatment_id,
            #         "name": row[1],
            #         "price": float(row[2]),
            #         "notes": f"Asociado a cita #{appointment_id}",
            #         "status": status,
            #         "source": "cita",
            #         "client_treatment_record_id": None,
            #         "treatment_date": None,
            #         "total_quantity": total_expected_quantity,
            #         "completed_quantity": completed_qty_for_source,
            #         "appointment_id": appointment_id,
            #         "quote_id": None
            #     }

            # 3. Obtener tratamientos de quote_treatments (potencialmente pendientes)
            cursor.execute(
                """
                SELECT
                    qt.treatment_id,
                    t.name,
                    t.price,
                    qt.quantity,
                    q.id AS quote_id
                FROM quote_treatments qt
                JOIN quotes q ON qt.quote_id = q.id
                JOIN treatments t ON qt.treatment_id = t.id
                WHERE q.client_id = %s
                """,
                (client_id,)
            )
            for row in cursor.fetchall():
                treatment_id = row[0]
                total_expected_quantity = row[3]
                quote_id = row[4]

                unique_key = (treatment_id, quote_id, "presupuesto", None)

                # Si este tratamiento ya está en el mapa como completado (desde client_treatments),
                # no lo añadimos de nuevo como "pendiente" a menos que la cantidad esperada sea mayor.
                # Esta lógica se mantiene por si en el futuro decides reintroducir client_treatments,
                # pero para este caso, puedes asumirla menos relevante si solo te enfocas en presupuestos.
                if unique_key in all_treatments_map and all_treatments_map[unique_key]["status"] == "completed" and \
                   all_treatments_map[unique_key]["completed_quantity"] >= total_expected_quantity:
                    continue

                # Obtener la cantidad ya completada para este tratamiento y presupuesto
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(completed_quantity), 0)
                    FROM client_treatments
                    WHERE client_id = %s AND treatment_id = %s AND quote_id = %s
                    """,
                    (client_id, treatment_id, quote_id)
                )
                completed_qty_for_source = cursor.fetchone()[0]

                status = "pending"
                if completed_qty_for_source >= total_expected_quantity:
                    status = "completed"

                all_treatments_map[unique_key] = {
                    "id": treatment_id,
                    "name": row[1],
                    "price": float(row[2]),
                    "notes": f"Asociado a presupuesto #{quote_id}",
                    "status": status,
                    "source": "presupuesto",
                    "client_treatment_record_id": None,
                    "treatment_date": None,
                    "total_quantity": total_expected_quantity,
                    "completed_quantity": completed_qty_for_source,
                    "appointment_id": None,
                    "quote_id": quote_id
                }

        # Filtrar y ordenar los tratamientos finales.
        final_treatments = []
        for key, treatment_data in all_treatments_map.items():
            final_treatments.append(treatment_data)

        # Ordenar los tratamientos: pendientes primero, luego completados, y finalmente por nombre
        sorted_treatments = sorted(
            final_treatments,
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
                       ARRAY_AGG(JSON_BUILD_OBJECT('id', t.id, 'name', t.name, 'price', at.price, 'quantity', at.quantity)) FILTER (WHERE t.id IS NOT NULL) AS treatments_list
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
        # Aquí se llama a la función modificada para obtener solo los tratamientos de presupuestos
        history_data["all_client_treatments"] = HistoryService.get_suggested_and_completed_treatments(client_id)

        return history_data

    @staticmethod
    def add_client_treatment(
        client_id: int,
        treatment_id: int,
        notes: Optional[str] = None,
        treatment_date: Optional[date] = None,
        appointment_id: Optional[int] = None,
        quote_id: Optional[int] = None, # Añadir quote_id para identificar fuente
        quantity_to_mark_completed: int = 1 # Cantidad a marcar como completada
    ) -> Tuple[bool, str]:
        """
        Añade/actualiza un tratamiento en el historial del cliente (client_treatments),
        incrementando la cantidad completada.
        """
        try:
            if treatment_date is None:
                treatment_date = date.today()

            with get_db() as cursor:
                # Determinar la cantidad total esperada del tratamiento
                total_expected_quantity = 1 # Valor predeterminado para tratamientos directos
                source_identifier_clause = ""
                source_identifier_params = []

                if appointment_id is not None:
                    # Obtener cantidad del tratamiento de appointment_treatments
                    cursor.execute(
                        "SELECT quantity FROM appointment_treatments WHERE appointment_id = %s AND treatment_id = %s",
                        (appointment_id, treatment_id)
                    )
                    result = cursor.fetchone()
                    if result:
                        total_expected_quantity = result[0]
                    source_identifier_clause = " AND appointment_id = %s AND quote_id IS NULL"
                    source_identifier_params = [appointment_id]
                elif quote_id is not None:
                    # Obtener cantidad del tratamiento de quote_treatments
                    cursor.execute(
                        "SELECT quantity FROM quote_treatments WHERE quote_id = %s AND treatment_id = %s",
                        (quote_id, treatment_id)
                    )
                    result = cursor.fetchone()
                    if result:
                        total_expected_quantity = result[0]
                    source_identifier_clause = " AND quote_id = %s AND appointment_id IS NULL"
                    source_identifier_params = [quote_id]
                else: # Tratamiento directo, sin cita o presupuesto asociado
                    source_identifier_clause = " AND appointment_id IS NULL AND quote_id IS NULL"
                    total_expected_quantity = quantity_to_mark_completed # Para directos, total es lo que se marca


                # Buscar un registro existente para actualizar
                query_check_existing = f"""
                    SELECT id, completed_quantity, total_quantity
                    FROM client_treatments
                    WHERE client_id = %s AND treatment_id = %s {source_identifier_clause}
                """
                params_check_existing = [client_id, treatment_id] + source_identifier_params
                cursor.execute(query_check_existing, tuple(params_check_existing))
                existing_record = cursor.fetchone()

                if existing_record:
                    record_id = existing_record[0]
                    current_completed_qty = existing_record[1]
                    current_total_qty = existing_record[2]

                    new_completed_qty = current_completed_qty + quantity_to_mark_completed

                    # No permitir que completed_quantity exceda el total_quantity existente o el recién determinado
                    final_total_qty = max(current_total_qty, total_expected_quantity) # Asegura que total_qty no disminuya
                    if new_completed_qty > final_total_qty:
                        new_completed_qty = final_total_qty

                    cursor.execute(
                        """
                        UPDATE client_treatments
                        SET notes = %s, treatment_date = %s, completed_quantity = %s, total_quantity = %s, updated_at = NOW()
                        WHERE id = %s
                        RETURNING id
                        """,
                        (notes, treatment_date, new_completed_qty, final_total_qty, record_id)
                    )
                    return True, f"Tratamiento de historial actualizado. Cantidad completada: {new_completed_qty} de {final_total_qty}."
                else:
                    # Insertar nuevo registro
                    cursor.execute(
                        """
                        INSERT INTO client_treatments (
                            client_id, treatment_id, treatment_date, notes,
                            created_at, updated_at, appointment_id, quote_id,
                            completed_quantity, total_quantity
                        )
                        VALUES (%s, %s, %s, %s, NOW(), NOW(), %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            client_id, treatment_id, treatment_date, notes,
                            appointment_id, quote_id,
                            quantity_to_mark_completed, total_expected_quantity
                        )
                    )
                    new_id = cursor.fetchone()[0]
                    return True, f"Tratamiento de historial añadido. Cantidad completada: {quantity_to_mark_completed} de {total_expected_quantity}."
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
    def delete_client_treatments_by_appointment(appointment_id: int, cursor) -> bool:
        """
        Elimina todos los registros de tratamientos de historial asociados a un appointment_id.
        Se espera que se le pase un cursor de una transacción existente (del AppointmentService).
        """
        try:
            cursor.execute(
                """
                DELETE FROM client_treatments
                WHERE appointment_id = %s;
                """,
                (appointment_id,)
            )
            logger.info(f"Eliminados {cursor.rowcount} registros de historial para cita {appointment_id}.")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar tratamientos de historial para cita {appointment_id}: {e}")
            raise # Re-lanza la excepción para que la transacción principal pueda hacer rollback


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
