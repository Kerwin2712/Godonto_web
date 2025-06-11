from datetime import datetime
from typing import Optional, List, Tuple
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    def _update_client_credit_balance(client_id: int, amount: float, cursor) -> None:
        """
        Actualiza el saldo a favor del cliente en la tabla client_credits.
        amount puede ser positivo (añadir crédito) o negativo (usar crédito).
        Se requiere el cursor de la transacción existente.
        """
        cursor.execute(
            """
            INSERT INTO client_credits (client_id, amount, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (client_id) DO UPDATE
            SET amount = client_credits.amount + EXCLUDED.amount, updated_at = NOW()
            """,
            (client_id, amount)
        )
        logger.info(f"Saldo a favor del cliente {client_id} actualizado por: {amount}. Nuevo saldo calculado en DB.")


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
        # Fetchone puede devolver None si no hay entrada, COALESCE lo maneja, pero es bueno estar seguro
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
                # Priorizamos las deudas más antiguas o con fecha de vencimiento más cercana
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
                    # Convertir a float para las operaciones aritméticas
                    debt_total_amount = float(debt_total_amount_decimal)
                    debt_paid_amount = float(debt_paid_amount_decimal)

                    debt_remaining_to_pay = debt_total_amount - debt_paid_amount

                    if remaining_amount <= 0:
                        break # No hay más monto del pago para aplicar

                    if debt_remaining_to_pay <= remaining_amount:
                        # El pago cubre completamente esta deuda
                        amount_to_apply_to_this_debt = debt_remaining_to_pay
                        new_debt_status = 'paid'
                        new_debt_paid_amount = debt_total_amount
                        paid_at_clause = ', paid_at = NOW()' # Se marca como pagada ahora
                    else:
                        # El pago cubre parcialmente esta deuda
                        amount_to_apply_to_this_debt = remaining_amount
                        new_debt_status = 'pending' # Sigue pendiente
                        new_debt_paid_amount = debt_paid_amount + remaining_amount
                        paid_at_clause = '' # No se marca como pagada completamente

                    # Actualizar la deuda
                    cursor.execute(
                        f"""
                        UPDATE debts
                        SET paid_amount = %s, status = %s, updated_at = NOW(){paid_at_clause}
                        WHERE id = %s
                        """,
                        (new_debt_paid_amount, new_debt_status, debt_id)
                    )

                    # Registrar la aplicación del pago a la deuda específica
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
                
                # 4. Registrar el saldo a favor si queda un monto restante
                if remaining_amount > 0.001: # Usar una pequeña tolerancia para flotantes
                    PaymentService._update_client_credit_balance(client_id, remaining_amount, cursor)
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). Aplicados ${total_applied_to_debts:,.2f} a {applied_debts_count} deudas. ${remaining_amount:,.2f} registrados como saldo a favor."
                elif applied_debts_count > 0:
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). Aplicados ${total_applied_to_debts:,.2f} a {applied_debts_count} deudas pendientes."
                else:
                    return True, f"Pago registrado exitosamente (ID: {payment_id}). No se encontraron deudas pendientes para cubrir."

        except Exception as e:
            logger.error(f"Error al crear pago y aplicar a deudas: {e}")
            return False, f"Error al crear pago y aplicar a deudas: {str(e)}"
    
    @staticmethod
    def create_debt(client_id: int, amount: float, description: Optional[str] = None, due_date: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Registra una deuda para un cliente, intentando usar el saldo a favor del cliente primero.
        """
        try:
            with get_db() as cursor:
                # Obtener el saldo a favor actual del cliente
                current_credit = PaymentService._get_client_credit_balance(client_id, cursor)
                
                initial_status = 'pending'
                paid_amount_on_creation = 0.0
                message_suffix = ""

                # Columnas y valores base para la inserción
                sql_columns = ["client_id", "amount", "description", "due_date", "status", "paid_amount", "created_at", "updated_at"]
                sql_placeholders = ["%s", "%s", "%s", "%s", "%s", "%s", "NOW()", "NOW()"]
                sql_values = [client_id, amount, description, due_date, initial_status, paid_amount_on_creation]

                if current_credit > 0.001: # Si hay saldo a favor
                    if current_credit >= amount:
                        # El crédito cubre la deuda completamente
                        paid_amount_on_creation = amount
                        initial_status = 'paid'
                        PaymentService._update_client_credit_balance(client_id, -amount, cursor) # Usar el crédito
                        
                        # Añadir 'paid_at' y su valor (NOW()) a la consulta
                        if "paid_at" not in sql_columns: # Evitar duplicados
                            sql_columns.append("paid_at")
                            sql_placeholders.append("NOW()")
                            # No se añade a sql_values porque NOW() se inserta directamente en SQL
                        
                        sql_values[sql_columns.index("status")] = initial_status # Actualizar el estado en los valores
                        sql_values[sql_columns.index("paid_amount")] = paid_amount_on_creation # Actualizar monto pagado

                        message_suffix = f" Cubierta completamente con saldo a favor (${amount:,.2f} usados)."
                        logger.info(f"Deuda de {amount} para cliente {client_id} cubierta completamente con saldo a favor.")
                    else:
                        # El crédito cubre parcialmente la deuda
                        paid_amount_on_creation = current_credit
                        initial_status = 'pending' # Sigue siendo pendiente por el resto
                        PaymentService._update_client_credit_balance(client_id, -current_credit, cursor) # Usar todo el crédito

                        sql_values[sql_columns.index("status")] = initial_status # Actualizar el estado en los valores
                        sql_values[sql_columns.index("paid_amount")] = paid_amount_on_creation # Actualizar monto pagado

                        message_suffix = f" Cubierta parcialmente con saldo a favor (${current_credit:,.2f} usados). Pendiente: ${amount - current_credit:,.2f}."
                        logger.info(f"Deuda de {amount} para cliente {client_id} cubierta parcialmente con saldo a favor de {current_credit}.")
                
                # Construir la parte de la consulta SQL
                column_str = ", ".join(sql_columns)
                placeholder_str = ", ".join(sql_placeholders)

                # Insertar la nueva deuda con el monto pagado y estado inicial
                cursor.execute(
                    f"""
                    INSERT INTO debts ({column_str})
                    VALUES ({placeholder_str})
                    RETURNING id
                    """,
                    tuple(sql_values) # Pasar valores como una tupla
                )
                debt_id = cursor.fetchone()[0]
                return True, f"Deuda registrada exitosamente (ID: {debt_id}).{message_suffix}"
        except Exception as e:
            logger.error(f"Error al crear deuda: {e}")
            return False, f"Error al crear deuda: {str(e)}"

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
                SELECT id, amount, method, notes, payment_date, created_at
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
                    'created_at': row[5]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_client_debts(client_id: int) -> List[dict]:
        """
        Obtiene todas las deudas de un cliente, incluyendo el monto pagado.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de deudas.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, amount, description, due_date, created_at, status, paid_amount
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
                    'paid_amount': float(row[6])
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
                'remaining_debt_balance': total_pending_debts, # Este es el saldo de deudas a pagar
                'client_credit_balance': client_credit_balance # Saldo a favor
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
            
    # El método create_debt ya está modificado arriba
    # delete_debt_by_description_and_client no necesita cambios
    # get_debts_by_client no necesita cambios
    # get_total_debts_for_client no necesita cambios
