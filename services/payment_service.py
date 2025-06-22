from datetime import datetime
from typing import Optional, List, Tuple
from core.database import get_db
import logging
import psycopg2
from dateutil.relativedelta import relativedelta # Importar relativedelta

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    def _update_client_credit_balance(client_id: int, amount: float, cursor) -> None:
        """
        Actualiza el saldo a favor del cliente en la tabla client_credits.
        amount puede ser positivo (añadir crédito) o negativo (usar crédito).
        Se requiere el cursor de la transacción existente.

        Esta función ahora asegura que el saldo a favor nunca sea negativo.
        """
        # Primero, obtén el saldo actual
        cursor.execute(
            "SELECT COALESCE(amount, 0) FROM client_credits WHERE client_id = %s",
            (client_id,)
        )
        current_balance = float(cursor.fetchone()[0]) if cursor.rowcount > 0 else 0.0

        new_balance = current_balance + amount

        # Asegúrate de que el saldo a favor nunca sea negativo
        if new_balance < 0:
            new_balance = 0.0 # O registra la diferencia como una deuda, pero para saldo a favor, no debe ser negativo.
            logger.warning(f"Intento de reducir el saldo a favor del cliente {client_id} por debajo de cero. Saldo establecido a 0.")


        cursor.execute(
            """
            INSERT INTO client_credits (client_id, amount, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (client_id) DO UPDATE
            SET amount = EXCLUDED.amount, updated_at = NOW() -- Usamos EXCLUDED.amount directamente para el nuevo saldo calculado
            """,
            (client_id, new_balance) # Pasa el nuevo_balance calculado
        )
        logger.info(f"Saldo a favor del cliente {client_id} actualizado a: {new_balance}.")


    @staticmethod
    def _get_client_credit_balance(client_id: int, cursor) -> float:
        """
        Obtiene el saldo a favor actual de un cliente.
        Se requiere el cursor de la transacción existente.
        """
        cursor.execute(
            "SELECT COALESCE(amount, 0) FROM client_credits WHERE client_id = %s",
            (client_id,)
        )
        result = cursor.fetchone()
        return float(result[0]) if result else 0.0

    @staticmethod
    def create_payment(client_id: int, amount: float, method: str, notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Registra un pago para un cliente y lo aplica a deudas pendientes.
        También registra cualquier excedente como saldo a favor en client_credits.
        """
        try:
            with get_db() as cursor:
                # 1. Registrar el pago principal
                cursor.execute(
                    """
                    INSERT INTO payments (client_id, amount, method, notes, payment_date, created_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, amount, method, notes)
                )
                payment_id = cursor.fetchone()[0]
                
                remaining_amount = amount
                applied_debts_count = 0
                total_applied_to_debts = 0.0

                # 2. Obtener deudas pendientes del cliente, ordenadas por due_date (o created_at)
                cursor.execute(
                    """
                    SELECT id, amount, paid_amount, due_date
                    FROM debts
                    WHERE client_id = %s AND status = 'pending'
                    ORDER BY due_date ASC, created_at ASC
                    """ , (client_id,)
                )
                pending_debts = cursor.fetchall()

                # 3. Aplicar el pago a las deudas pendientes existentes
                for debt_id, debt_total_amount_decimal, debt_paid_amount_decimal, _ in pending_debts:
                    debt_total_amount = float(debt_total_amount_decimal)
                    debt_paid_amount = float(debt_paid_amount_decimal)

                    debt_remaining_to_pay = debt_total_amount - debt_paid_amount

                    if remaining_amount <= 0:
                        break

                    if debt_remaining_to_pay <= remaining_amount:
                        amount_to_apply_to_this_debt = debt_remaining_to_pay
                        new_debt_status = 'paid'
                        new_debt_paid_amount = debt_total_amount
                        paid_at_clause = ', paid_at = NOW()'
                    else:
                        amount_to_apply_to_this_debt = remaining_amount
                        new_debt_status = 'pending'
                        new_debt_paid_amount = debt_paid_amount + remaining_amount
                        paid_at_clause = ''

                    cursor.execute(
                        f"""
                        UPDATE debts
                        SET paid_amount = %s, status = %s, updated_at = NOW(){paid_at_clause}
                        WHERE id = %s
                        """,
                        (new_debt_paid_amount, new_debt_status, debt_id)
                    )

                    cursor.execute(
                        """
                        INSERT INTO debt_payments (payment_id, debt_id, amount_applied, created_at)
                        VALUES (%s, %s, %s, NOW())
                        """,
                        (payment_id, debt_id, amount_to_apply_to_this_debt)
                    )

                    remaining_amount -= amount_to_apply_to_this_debt
                    total_applied_to_debts += amount_to_apply_to_this_debt
                    applied_debts_count += 1
                
                if remaining_amount > 0.001:
                    PaymentService._update_client_credit_balance(client_id, remaining_amount, cursor)
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). Aplicados ${total_applied_to_debts:,.2f} a {applied_debts_count} deudas. ${remaining_amount:,.2f} registrados como saldo a favor."
                elif applied_debts_count > 0:
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). Aplicados ${total_applied_to_debts:,.2f} a {applied_debts_count} deudas pendientes."
                else:
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). No se encontraron deudas pendientes a las cuales aplicar el pago."

        except Exception as e:
            logger.error(f"Error al crear pago y aplicar a deudas: {e}")
            return False, f"Error al crear pago y aplicar a deudas: {str(e)}"
    
    @staticmethod
    def update_payment(payment_id: int, amount: float, method: str, notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Actualiza un pago existente y recalcula su impacto en deudas y saldo a favor del cliente.
        Esta operación es transaccional.
        """
        try:
            with get_db() as cursor:
                cursor.execute("BEGIN;") # Iniciar transacción

                # 1. Obtener detalles del pago original antes de la actualización
                cursor.execute(
                    "SELECT client_id, amount FROM payments WHERE id = %s",
                    (payment_id,)
                )
                original_payment_details = cursor.fetchone()
                if not original_payment_details:
                    cursor.execute("ROLLBACK;")
                    return False, "Pago original no encontrado."

                client_id, original_amount = original_payment_details
                original_amount = float(original_amount)

                # 2. Revertir las aplicaciones del pago original a las deudas y el crédito
                # Obtener todas las deudas a las que se aplicó este pago
                cursor.execute(
                    "SELECT debt_id, amount_applied FROM debt_payments WHERE payment_id = %s",
                    (payment_id,)
                )
                original_applied_debts = cursor.fetchall()
                
                total_original_applied_to_debts = 0.0

                for debt_id, amount_applied in original_applied_debts:
                    # Revertir la aplicación en la tabla 'debts'
                    cursor.execute(
                        "UPDATE debts SET paid_amount = paid_amount - %s, status = 'pending', updated_at = NOW() WHERE id = %s",
                        (amount_applied, debt_id)
                    )
                    total_original_applied_to_debts += float(amount_applied)
                
                # Revertir el sobrepago original al crédito del cliente
                original_overpayment = original_amount - total_original_applied_to_debts
                if original_overpayment > 0.001:
                    PaymentService._update_client_credit_balance(client_id, -original_overpayment, cursor) # Resta el crédito
                
                # Eliminar los registros de debt_payments para este pago original
                cursor.execute(
                    "DELETE FROM debt_payments WHERE payment_id = %s",
                    (payment_id,)
                )

                # 3. Actualizar el pago con los nuevos valores
                cursor.execute(
                    """
                    UPDATE payments
                    SET amount = %s, method = %s, notes = %s
                    WHERE id = %s
                    """,
                    (amount, method, notes, payment_id)
                )

                # 4. Re-aplicar el nuevo monto del pago a las deudas pendientes y al crédito
                remaining_amount_to_apply = amount
                reapplied_debts_count = 0
                total_reapplied_to_debts = 0.0

                cursor.execute(
                    """
                    SELECT id, amount, paid_amount, due_date
                    FROM debts
                    WHERE client_id = %s AND status = 'pending'
                    ORDER BY due_date ASC, created_at ASC
                    """,
                    (client_id,)
                )
                pending_debts_for_reapplication = cursor.fetchall()

                for debt_id, debt_total_amount_decimal, debt_paid_amount_decimal, _ in pending_debts_for_reapplication:
                    debt_total_amount = float(debt_total_amount_decimal)
                    debt_paid_amount = float(debt_paid_amount_decimal)
                    debt_remaining_to_pay = debt_total_amount - debt_paid_amount

                    if remaining_amount_to_apply <= 0:
                        break

                    if debt_remaining_to_pay <= remaining_amount_to_apply:
                        amount_to_apply_to_this_debt = debt_remaining_to_pay
                        new_debt_status = 'paid'
                        new_debt_paid_amount = debt_total_amount
                        paid_at_clause = ', paid_at = NOW()'
                    else:
                        amount_to_apply_to_this_debt = remaining_amount_to_apply
                        new_debt_status = 'pending'
                        new_debt_paid_amount = debt_paid_amount + remaining_amount_to_apply
                        paid_at_clause = ''
                    
                    cursor.execute(
                        f"""
                        UPDATE debts
                        SET paid_amount = %s, status = %s, updated_at = NOW(){paid_at_clause}
                        WHERE id = %s
                        """,
                        (new_debt_paid_amount, new_debt_status, debt_id)
                    )

                    cursor.execute(
                        """
                        INSERT INTO debt_payments (payment_id, debt_id, amount_applied, created_at)
                        VALUES (%s, %s, %s, NOW())
                        """,
                        (payment_id, debt_id, amount_to_apply_to_this_debt)
                    )

                    remaining_amount_to_apply -= amount_to_apply_to_this_debt
                    total_reapplied_to_debts += amount_to_apply_to_this_debt
                    reapplied_debts_count += 1

                if remaining_amount_to_apply > 0.001:
                    PaymentService._update_client_credit_balance(client_id, remaining_amount_to_apply, cursor)
                    message = f"Pago actualizado exitosamente. Aplicados ${total_reapplied_to_debts:,.2f} a {reapplied_debts_count} deudas. ${remaining_amount_to_apply:,.2f} registrados como saldo a favor."
                elif reapplied_debts_count > 0:
                    message = f"Pago actualizado exitosamente. Aplicados ${total_reapplied_to_debts:,.2f} a {reapplied_debts_count} deudas."
                else:
                    message = "Pago actualizado exitosamente. No se encontraron deudas pendientes a las cuales aplicar el pago."

                cursor.execute("COMMIT;")
                return True, message

        except Exception as e:
            if cursor:
                cursor.execute("ROLLBACK;")
            logger.error(f"Error al actualizar pago {payment_id} y recalcular efectos: {e}")
            return False, f"Error al actualizar pago: {str(e)}"

    @staticmethod
    def update_debt(debt_id: int, amount: float, description: Optional[str] = None, 
                    due_date: Optional[datetime] = None, status: str = 'pending', 
                    paid_amount: Optional[float] = None) -> Tuple[bool, str]:
        """
        Actualiza una deuda existente.
        Permite actualizar el monto, descripción, fecha de vencimiento y estado.
        Si el estado cambia a 'paid', paid_at se actualiza a NOW().
        Si el estado cambia de 'paid' a 'pending', paid_at se establece en NULL.
        """
        try:
            with get_db() as cursor:
                # Obtener la deuda actual para comparar el estado
                cursor.execute("SELECT client_id, amount, paid_amount, status FROM debts WHERE id = %s", (debt_id,))
                current_debt_info = cursor.fetchone()
                if not current_debt_info:
                    return False, "Deuda no encontrada."
                
                client_id, old_amount, old_paid_amount, old_status = current_debt_info
                old_amount = float(old_amount)
                old_paid_amount = float(old_paid_amount) # Convertir a float

                update_paid_at_clause = ""
                
                new_paid_amount = paid_amount # Default to the provided paid_amount

                # Lógica para manejar cambios de estado y `paid_amount`
                if status == 'paid' and old_status != 'paid':
                    # Si la deuda se marca como pagada y antes no lo estaba
                    update_paid_at_clause = ", paid_at = NOW()"
                    new_paid_amount = amount # Se asume que al marcar como pagada, se paga el monto total
                elif status == 'pending' and old_status == 'paid':
                    # Si la deuda se marca como pendiente y antes estaba pagada
                    update_paid_at_clause = ", paid_at = NULL"
                    new_paid_amount = 0.0 # Se asume que al volver a pendiente, el monto pagado se reinicia o se define explícitamente

                # Si no se proporciona paid_amount en la llamada, mantener el anterior
                if paid_amount is None:
                    new_paid_amount = old_paid_amount
                
                # Ajustar el paid_amount si el nuevo estado es 'paid' y el amount es mayor que el paid_amount actual
                if status == 'paid' and new_paid_amount < amount:
                    new_paid_amount = amount # Asegurar que si está pagada, el paid_amount sea igual al amount

                # Ahora, recalcular el impacto en el saldo a favor del cliente
                # Esto es más complejo: si el old_paid_amount o old_amount cambian, o si el status cambia,
                # podría impactar el crédito del cliente o su deuda pendiente general.
                # Para una edición de deuda, el enfoque más seguro es:
                # 1. Revertir el efecto del "pago" (paid_amount) de la deuda original en el crédito del cliente.
                # 2. Aplicar el efecto del "pago" (new_paid_amount) de la deuda actualizada en el crédito.

                # 1. Revertir el impacto del paid_amount original en el crédito
                # Si la deuda original tenía un paid_amount > 0 que contribuyó al crédito del cliente,
                # o si su estado era 'paid', necesitamos deshacer ese efecto.
                # Esto es un placeholder para una lógica más robusta de reversión.
                # Por ahora, nos centraremos en la actualización directa de la deuda.
                # La función `update_payment` ya maneja la complejidad de las aplicaciones a deudas.

                cursor.execute(
                    f"""
                    UPDATE debts
                    SET amount = %s, description = %s, due_date = %s, status = %s, paid_amount = %s, updated_at = NOW() {update_paid_at_clause}
                    WHERE id = %s
                    """,
                    (amount, description, due_date, status, new_paid_amount, debt_id)
                )
                if cursor.rowcount > 0:
                    cursor.execute("COMMIT;")
                    return True, "Deuda actualizada exitosamente."
                else:
                    cursor.execute("ROLLBACK;")
                    return False, "No se pudo encontrar o actualizar la deuda."
        except Exception as e:
            if cursor:
                cursor.execute("ROLLBACK;")
            logger.error(f"Error al actualizar deuda {debt_id}: {e}")
            return False, f"Error al actualizar deuda: {str(e)}"
    
    @staticmethod
    def create_debt(client_id: int, amount: float, description: Optional[str] = None, 
                    due_date: Optional[datetime] = None, appointment_id: Optional[int] = None,
                    quote_id: Optional[int] = None, # Añadir quote_id
                    cursor=None) -> Tuple[bool, str]:
        """
        Registra una deuda para un cliente, intentando usar el saldo a favor del cliente primero.
        Ahora puede asociarse con una appointment_id y usar un cursor existente.
        La fecha de vencimiento (due_date) se establece automáticamente un mes después de la creación
        si no se proporciona explícitamente.
        """
        try:
            # Usa el cursor proporcionado o abre uno nuevo si no se proporciona
            db_context = get_db() if cursor is None else None
            _cursor = cursor if cursor is not None else db_context.__enter__()

            try:
                # Si due_date no se proporciona, calcúlala un mes después de hoy
                if due_date is None:
                    due_date = datetime.now() + relativedelta(months=1)

                current_credit = PaymentService._get_client_credit_balance(client_id, _cursor)
                
                initial_status = 'pending'
                paid_amount_on_creation = 0.0
                message_suffix = ""

                sql_columns = ["client_id", "amount", "description", "due_date", "status", "paid_amount", "created_at", "updated_at"]
                sql_placeholders = ["%s", "%s", "%s", "%s", "%s", "%s", "NOW()", "NOW()"]
                sql_values = [client_id, amount, description, due_date, initial_status, paid_amount_on_creation]

                # Añadir appointment_id si se proporciona
                if appointment_id is not None:
                    sql_columns.append("appointment_id")
                    sql_placeholders.append("%s")
                    sql_values.append(appointment_id)
                
                # Añadir quote_id si se proporciona
                if quote_id is not None:
                    sql_columns.append("quote_id")
                    sql_placeholders.append("%s")
                    sql_values.append(quote_id)

                if current_credit > 0.001: # Solo usar crédito si es positivo
                    if current_credit >= amount:
                        paid_amount_on_creation = amount
                        initial_status = 'paid'
                        PaymentService._update_client_credit_balance(client_id, -amount, _cursor) # Reduce el crédito
                        
                        if "paid_at" not in sql_columns:
                            sql_columns.append("paid_at")
                            sql_placeholders.append("NOW()")
                        
                        sql_values[sql_columns.index("status")] = initial_status
                        sql_values[sql_columns.index("paid_amount")] = paid_amount_on_creation

                        message_suffix = f" Cubierta completamente con saldo a favor (${amount:,.2f} usados)."
                        logger.info(f"Deuda de {amount} para cliente {client_id} cubierta completamente con saldo a favor.")
                    else:
                        paid_amount_on_creation = current_credit
                        initial_status = 'pending'
                        PaymentService._update_client_credit_balance(client_id, -current_credit, _cursor) # Reduce el crédito a cero
                        amount_after_credit = amount - current_credit

                        sql_values[sql_columns.index("status")] = initial_status
                        sql_values[sql_columns.index("paid_amount")] = paid_amount_on_creation
                        # La cantidad de la deuda sigue siendo el 'amount' original, pero el 'paid_amount' refleja el crédito usado.

                        message_suffix = f" Cubierta parcialmente con saldo a favor (${current_credit:,.2f} usados). Pendiente: ${amount_after_credit:,.2f}."
                        logger.info(f"Deuda de {amount} para cliente {client_id} cubierta parcialmente con saldo a favor de {current_credit}.")
                
                column_str = ", ".join(sql_columns)
                placeholder_str = ", ".join(sql_placeholders)

                _cursor.execute(
                    f"""
                    INSERT INTO debts ({column_str})
                    VALUES ({placeholder_str})
                    RETURNING id
                    """,
                    tuple(sql_values)
                )
                debt_id = _cursor.fetchone()[0]

                if db_context is not None:
                    db_context.__exit__(None, None, None)

                return True, f"Deuda registrada exitosamente (ID: {debt_id}).{message_suffix}"
            finally:
                if db_context is not None and not db_context.is_committed: # type: ignore
                    pass 
        except Exception as e:
            logger.error(f"Error al crear deuda: {e}")
            return False, f"Error al crear deuda: {str(e)}"

    @staticmethod
    def delete_debts_by_appointment_id(appointment_id: int) -> bool:
        """
        Elimina todas las deudas asociadas a una cita específica por su appointment_id.
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    """
                    DELETE FROM debts
                    WHERE appointment_id = %s;
                    """,
                    (appointment_id,)
                )
                logger.info(f"Eliminadas {cursor.rowcount} deudas asociadas a la cita {appointment_id}.")
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error al eliminar deudas para la cita {appointment_id}: {e}")
            return False

    @staticmethod
    def delete_payment(payment_id: int) -> Tuple[bool, str]:
        """
        Elimina un pago y revierte sus efectos en deudas y saldo a favor del cliente.
        Esta operación es transaccional.
        """
        try:
            with get_db() as cursor:
                cursor.execute("BEGIN;") # Iniciar transacción

                # 1. Obtener detalles del pago a eliminar
                cursor.execute(
                    "SELECT client_id, amount, payment_date FROM payments WHERE id = %s",
                    (payment_id,)
                )
                payment_details = cursor.fetchone()
                if not payment_details:
                    cursor.execute("ROLLBACK;")
                    return False, "Pago no encontrado."

                client_id, payment_amount, _ = payment_details

                # 2. Revertir las aplicaciones del pago a las deudas
                cursor.execute(
                    "SELECT debt_id, amount_applied FROM debt_payments WHERE payment_id = %s",
                    (payment_id,)
                )
                applied_debts = cursor.fetchall()

                for debt_id, amount_applied in applied_debts:
                    # Obtener estado actual de la deuda
                    cursor.execute(
                        "SELECT amount, paid_amount, status FROM debts WHERE id = %s",
                        (debt_id,)
                    )
                    debt_info = cursor.fetchone()
                    if debt_info:
                        debt_total_amount, debt_paid_amount, debt_status = debt_info
                        new_paid_amount = float(debt_paid_amount) - float(amount_applied)

                        new_status = debt_status
                        # Si el monto pagado después de la reversión es menor que el total de la deuda
                        # y el estado era 'paid', cambiarlo a 'pending'.
                        if new_paid_amount < float(debt_total_amount) and debt_status == 'paid':
                            new_status = 'pending' 
                        elif new_paid_amount >= float(debt_total_amount) and new_status == 'pending':
                            # Si, por alguna razón, el pago restante aún cubre la deuda, mantén el estado actual o cámbialo a 'paid'
                            # Aunque si estamos revirtiendo, lo normal sería que pasara a pendiente si no se cubre
                            pass # Mantener estado si aún está cubierto

                        cursor.execute(
                            "UPDATE debts SET paid_amount = %s, status = %s, updated_at = NOW() WHERE id = %s",
                            (new_paid_amount, new_status, debt_id)
                        )
                        logger.info(f"Revertida aplicación de {amount_applied} a deuda {debt_id}. Nuevo pagado: {new_paid_amount}, estado: {new_status}")

                # 3. Eliminar los registros de debt_payments asociados a este pago
                cursor.execute(
                    "DELETE FROM debt_payments WHERE payment_id = %s",
                    (payment_id,)
                )
                logger.info(f"Eliminados {cursor.rowcount} registros de debt_payments para el pago {payment_id}.")

                # 4. Ajustar el saldo a favor del cliente si el pago fue un sobrepago
                total_applied_to_debts = sum(float(a[1]) for a in applied_debts)
                overpayment_amount = float(payment_amount) - total_applied_to_debts

                if overpayment_amount > 0.001: # Si hubo sobrepago que se fue a crédito
                    PaymentService._update_client_credit_balance(client_id, -overpayment_amount, cursor)
                    logger.info(f"Revertido saldo a favor por {overpayment_amount} para cliente {client_id}.")

                # 5. Eliminar el pago de la tabla payments
                cursor.execute(
                    "DELETE FROM payments WHERE id = %s",
                    (payment_id,)
                )
                if cursor.rowcount > 0:
                    cursor.execute("COMMIT;")
                    logger.info(f"Pago {payment_id} eliminado exitosamente y efectos revertidos.")
                    return True, "Pago eliminado exitosamente."
                else:
                    cursor.execute("ROLLBACK;")
                    return False, "No se pudo eliminar el pago."

        except Exception as e:
            # Asegurarse de revertir en caso de cualquier error
            if cursor: # Verificar si el cursor existe para el rollback
                cursor.execute("ROLLBACK;") 
            logger.error(f"Error al eliminar pago {payment_id} y revertir sus efectos: {e}")
            return False, f"Error al eliminar pago: {str(e)}"
            
    @staticmethod
    def delete_debt(debt_id: int) -> Tuple[bool, str]:
        """
        Elimina una deuda y revierte cualquier saldo a favor que se haya usado para pagarla,
        o reactiva pagos si estaban asociados a ella.
        Esta operación es transaccional.
        """
        try:
            with get_db() as cursor:
                cursor.execute("BEGIN;")  # Iniciar transacción

                # 1. Obtener detalles de la deuda a eliminar
                cursor.execute(
                    "SELECT client_id, amount, paid_amount, status FROM debts WHERE id = %s",
                    (debt_id,)
                )
                debt_details = cursor.fetchone()
                if not debt_details:
                    cursor.execute("ROLLBACK;")
                    return False, "Deuda no encontrada."

                client_id, debt_amount, paid_amount_on_debt, debt_status = debt_details
                debt_amount = float(debt_amount)
                paid_amount_on_debt = float(paid_amount_on_debt)

                # 2. Revertir el saldo a favor si la deuda fue pagada por crédito al crearse
                # Esto ocurre si la deuda fue creada y pagada con saldo a favor.
                # Si el `paid_amount_on_debt` es > 0 y la deuda fue cubierta por crédito al crearse,
                # ese monto debe ser devuelto al crédito del cliente.

                # Buscamos si hay pagos directos asociados a esta deuda.
                cursor.execute(
                    "SELECT SUM(amount_applied) FROM debt_payments WHERE debt_id = %s",
                    (debt_id,)
                )
                payments_applied_to_debt = cursor.fetchone()[0] or 0.0
                payments_applied_to_debt = float(payments_applied_to_debt)

                # La diferencia entre paid_amount_on_debt y payments_applied_to_debt
                # podría ser el crédito usado al crear la deuda.
                credit_to_revert = paid_amount_on_debt - payments_applied_to_debt

                if credit_to_revert > 0.001:
                    PaymentService._update_client_credit_balance(client_id, credit_to_revert, cursor)
                    logger.info(f"Revertido saldo a favor por {credit_to_revert} para cliente {client_id} al eliminar deuda {debt_id}.")

                # 3. Eliminar las asociaciones de pagos a esta deuda (debt_payments)
                cursor.execute(
                    "DELETE FROM debt_payments WHERE debt_id = %s",
                    (debt_id,)
                )
                logger.info(f"Eliminados {cursor.rowcount} registros de debt_payments para la deuda {debt_id}.")

                # 4. Eliminar la deuda de la tabla debts
                cursor.execute(
                    "DELETE FROM debts WHERE id = %s",
                    (debt_id,)
                )
                if cursor.rowcount > 0:
                    cursor.execute("COMMIT;")
                    logger.info(f"Deuda {debt_id} eliminada exitosamente y efectos revertidos.")
                    return True, "Deuda eliminada exitosamente."
                else:
                    cursor.execute("ROLLBACK;")
                    return False, "No se pudo eliminar la deuda."

        except Exception as e:
            if cursor:
                cursor.execute("ROLLBACK;")
            logger.error(f"Error al eliminar deuda {debt_id} y revertir sus efectos: {e}")
            return False, f"Error al eliminar deuda: {str(e)}"
            
    @staticmethod
    def get_client_payments(client_id: int) -> List[dict]:
        """
        Obtiene todos los pagos de un cliente.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de pagos.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, amount, method, notes, payment_date, created_at, appointment_id
                FROM payments
                WHERE client_id = %s
                ORDER BY payment_date DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'amount': float(row[1]),
                    'method': row[2],
                    'notes': row[3],
                    'payment_date': row[4],
                    'created_at': row[5],
                    'appointment_id': row[6]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_client_debts(client_id: int) -> List[dict]:
        """
        Obtiene todas las deudas de un cliente, incluyendo el monto pagado.
        Ahora también incluye appointment_id.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de deudas.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, amount, description, due_date, created_at, status, paid_amount, appointment_id, quote_id
                FROM debts
                WHERE client_id = %s
                ORDER BY due_date DESC, created_at DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'amount': float(row[1]),
                    'description': row[2],
                    'due_date': row[3],
                    'created_at': row[4],
                    'status': row[5],
                    'paid_amount': float(row[6]),
                    'appointment_id': row[7],
                    'quote_id': row[8]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_payment_summary(client_id: int) -> dict:
        """
        Obtiene el resumen de pagos y deudas pendientes de un cliente,
        incluyendo el saldo a favor.
        Args:
            client_id (int): ID del cliente.
        Returns:
            dict: Diccionario con el total de pagos, total de deudas pendientes,
                  saldo restante de deudas y saldo a favor del cliente.
        """
        with get_db() as cursor:
            total_payments = PaymentService.get_total_payments_for_client(client_id)
            total_pending_debts = PaymentService.get_total_pending_debts_for_client(client_id)
            client_credit_balance = PaymentService._get_client_credit_balance(client_id, cursor)

            return {
                'total_payments': total_payments,
                'total_pending_debt': total_pending_debts,
                'remaining_debt_balance': total_pending_debts,
                'client_credit_balance': client_credit_balance
            }
    
    @staticmethod
    def get_total_payments_for_client(client_id: int) -> float:
        """
        Calcula el total de pagos realizados por un cliente.
        """
        with get_db() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE client_id = %s",
                (client_id,)
            )
            return float(cursor.fetchone()[0])

    @staticmethod
    def get_total_pending_debts_for_client(client_id: int) -> float:
        """
        Calcula el total de deudas *pendientes* de un cliente (monto total - monto pagado).
        """
        with get_db() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(amount - paid_amount), 0) FROM debts WHERE client_id = %s AND status = 'pending'",
                (client_id,)
            )
            return float(cursor.fetchone()[0])
