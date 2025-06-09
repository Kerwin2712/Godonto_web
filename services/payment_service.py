from datetime import datetime
from typing import Optional, List, Tuple
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    @staticmethod
    def create_payment(client_id: int, amount: float, method: str, notes: Optional[str] = None) -> Tuple[bool, str]:
        """
        Registra un pago para un cliente.
        Args:
            client_id (int): ID del cliente.
            amount (float): Monto del pago.
            method (str): Método de pago.
            notes (Optional[str]): Notas adicionales sobre el pago.
        Returns:
            Tuple[bool, str]: (True, mensaje_exito) o (False, mensaje_error).
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    """
                    INSERT INTO payments (client_id, amount, method, notes, payment_date, created_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, amount, method, notes) # Asegurarse de que 'notes' se incluye aquí
                )
                payment_id = cursor.fetchone()[0]
                return True, f"Pago registrado exitosamente (ID: {payment_id})"
        except Exception as e:
            logger.error(f"Error al crear pago: {e}")
            return False, f"Error al crear pago: {str(e)}"

    
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
                    'method': row[2], # Corregido para que coincida con la columna 'method'
                    'notes': row[3],  # Asegurado que se mapea 'notes'
                    'payment_date': row[4], # Corregido para que coincida con la columna 'payment_date'
                    'created_at': row[5]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_client_debts(client_id: int) -> List[dict]:
        """
        Obtiene todas las deudas de un cliente.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de deudas.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, amount, description, due_date, created_at
                FROM debts
                WHERE client_id = %s
                ORDER BY due_date DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'amount': float(row[1]),
                    'description': row[2],
                    'debt_date': row[3],
                    'created_at': row[4]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_payment_summary(client_id: int) -> dict: # Cambiado de float a dict para consistencia
        """
        Obtiene el resumen de pagos y deudas de un cliente.
        Args:
            client_id (int): ID del cliente.
        Returns:
            dict: Diccionario con el total de pagos, total de deudas y saldo pendiente.
        """
        total_payments = PaymentService.get_total_payments_for_client(client_id)
        total_debts = PaymentService.get_total_debts_for_client(client_id)
        return {
            'total_payments': total_payments,
            'total_debt': total_debts,
            'balance': total_payments - total_debts
        }
    
    @staticmethod
    def get_payments_by_client(client_id: int) -> List[dict]:
        """
        Obtiene todos los pagos de un cliente.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de pagos.
        """
        # Esta función es un duplicado de get_client_payments.
        # Se mantiene por si hay referencias en otras partes del código,
        # pero idealmente se debería usar solo una versión.
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
    def create_debt(client_id: int, amount: float, description: Optional[str] = None) -> Tuple[bool, str]:
        """
        Registra una deuda para un cliente.
        Args:
            client_id (int): ID del cliente.
            amount (float): Monto de la deuda.
            description (Optional[str]): Descripción de la deuda.
        Returns:
            Tuple[bool, str]: (True, mensaje_exito) o (False, mensaje_error).
        """
        try:
            with get_db() as cursor:
                cursor.execute(
                    """
                    INSERT INTO debts (client_id, amount, description, due_date, created_at, updated_at)
                    VALUES (%s, %s, %s, NOW(), NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, amount, description)
                )
                debt_id = cursor.fetchone()[0]
                return True, f"Deuda registrada exitosamente (ID: {debt_id})"
        except Exception as e:
            logger.error(f"Error al crear deuda: {e}")
            return False, f"Error al crear deuda: {str(e)}"

    @staticmethod
    def delete_debt_by_description_and_client(client_id: int, description_prefix: str) -> bool:
        """
        Elimina deudas de un cliente que coincidan con un prefijo de descripción.
        Útil para limpiar deudas de tratamientos antes de re-insertar.
        """
        logger.info(f"Intentando eliminar deuda para client_id: {client_id}, description_prefix: '{description_prefix}'")
        try:
            with get_db() as cursor:
                cursor.execute(
                    "DELETE FROM debts WHERE client_id = %s AND description ILIKE %s",
                    (client_id, f"{description_prefix}%")
                )
                if cursor.rowcount > 0:
                    logger.info(f"Se eliminaron {cursor.rowcount} registros de deuda para client_id: {client_id}, description_prefix: '{description_prefix}'")
                    return True
                else:
                    logger.warning(f"No se encontraron registros de deuda para eliminar con client_id: {client_id}, description_prefix: '{description_prefix}'")
                    return False
        except Exception as e:
            logger.error(f"Error al eliminar deuda por descripción y cliente ({client_id}, '{description_prefix}%'): {e}")
            return False

    @staticmethod
    def get_debts_by_client(client_id: int) -> List[dict]:
        """
        Obtiene todas las deudas de un cliente.
        Args:
            client_id (int): ID del cliente.
        Returns:
            List[dict]: Lista de deudas.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, amount, description, debt_date, created_at
                FROM debts
                WHERE client_id = %s
                ORDER BY debt_date DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'amount': float(row[1]),
                    'description': row[2],
                    'debt_date': row[3],
                    'created_at': row[4]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_total_debts_for_client(client_id: int) -> float:
        """
        Calcula el total de deudas pendientes de un cliente.
        """
        with get_db() as cursor:
            cursor.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM debts WHERE client_id = %s",
                (client_id,)
            )
            return float(cursor.fetchone()[0])
