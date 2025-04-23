from core.database import Database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self):
        pass
    
    def create_payment(self, client_id, amount, method, status='completed', invoice_number=None, notes=None, appointment_id=None):
        """Crea un nuevo pago y aplica el monto a las deudas pendientes"""
        try:
            with Database.get_cursor() as cursor:
                # 1. Registrar el pago
                payment_query = """
                    INSERT INTO payments (
                        client_id,
                        appointment_id, 
                        amount, 
                        method, 
                        status, 
                        invoice_number, 
                        notes,
                        payment_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                payment_params = (
                    client_id,
                    appointment_id, 
                    float(amount),  # Asegurar que es float
                    method, 
                    status, 
                    invoice_number, 
                    notes,
                    datetime.now()
                )
                cursor.execute(payment_query, payment_params)
                payment_id = cursor.fetchone()[0]
                
                # 2. Obtener deudas pendientes ordenadas por antigüedad (primero las más viejas)
                debts_query = """
                    SELECT id, amount 
                    FROM debts 
                    WHERE client_id = %s AND status = 'pending'
                    ORDER BY created_at ASC
                    FOR UPDATE  -- Bloquea los registros para evitar condiciones de carrera
                """
                cursor.execute(debts_query, (client_id,))
                debts = cursor.fetchall()
                
                remaining_amount = float(amount)  # Convertir a float explícitamente
                
                # 3. Aplicar el pago a las deudas
                for debt in debts:
                    if remaining_amount <= 0:
                        break
                        
                    debt_id, debt_amount = debt
                    # Convertir debt_amount a float si es Decimal
                    debt_amount_float = float(debt_amount) if hasattr(debt_amount, 'to_eng_string') else debt_amount
                    amount_to_apply = min(remaining_amount, debt_amount_float)
                    
                    # Actualizar la deuda
                    if amount_to_apply == debt_amount_float:
                        # Pagar la deuda completa
                        update_query = """
                            UPDATE debts 
                            SET status = 'paid', 
                                paid_amount = %s,
                                paid_at = %s
                            WHERE id = %s
                        """
                        cursor.execute(update_query, (float(debt_amount_float), datetime.now(), debt_id))
                    else:
                        # Reducir el monto de la deuda
                        update_query = """
                            UPDATE debts 
                            SET amount = amount - %s,
                                paid_amount = COALESCE(paid_amount, 0) + %s
                            WHERE id = %s
                        """
                        cursor.execute(update_query, (float(amount_to_apply), float(amount_to_apply), debt_id))
                    
                    # Registrar la transacción de pago de deuda
                    debt_payment_query = """
                        INSERT INTO debt_payments (
                            payment_id,
                            debt_id,
                            amount_applied
                        )
                        VALUES (%s, %s, %s)
                    """
                    cursor.execute(debt_payment_query, (payment_id, debt_id, float(amount_to_apply)))
                    
                    remaining_amount -= float(amount_to_apply)  # Asegurar operación entre floats
                
                return payment_id
                
        except Exception as e:
            logger.error(f"Error al crear pago: {str(e)}")
            raise
    
    def create_debt(self, client_id, amount, description):
        """Crea una deuda para un cliente"""
        try:
            query = """
                INSERT INTO debts (
                    client_id, 
                    amount, 
                    description, 
                    status, 
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            params = (
                client_id, 
                amount, 
                description,
                'pending',
                datetime.now()
            )
            
            with Database.get_cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error al crear deuda: {str(e)}")
            raise
    
    def get_client_payments(self, client_id):
        """Obtiene los pagos de un cliente con formato para la UI"""
        try:
            query = """
                SELECT 
                    p.id,
                    p.amount,
                    p.method,
                    p.status,
                    p.payment_date as date,
                    p.notes,
                    p.appointment_id,
                    a.date as appointment_date
                FROM payments p
                LEFT JOIN appointments a ON p.appointment_id = a.id
                WHERE p.client_id = %s
                ORDER BY p.payment_date DESC
                LIMIT 10
            """
            
            with Database.get_cursor() as cursor:
                cursor.execute(query, (client_id,))
                results = cursor.fetchall()
                return [{
                    'id': r[0],
                    'amount': float(r[1]),
                    'method': r[2],
                    'status': r[3],
                    'date': r[4].strftime('%d/%m/%Y %H:%M') if r[4] else '',
                    'notes': r[5],
                    'appointment_id': r[6],
                    'appointment_date': r[7].strftime('%d/%m/%Y') if r[7] else 'Sin cita'
                } for r in results]
                
        except Exception as e:
            logger.error(f"Error al obtener pagos del cliente: {str(e)}")
            return []
    
    def get_client_debts(self, client_id):
        """Obtiene las deudas de un cliente con formato para la UI"""
        try:
            query = """
                SELECT 
                    id,
                    amount,
                    description,
                    status,
                    created_at as date,
                    (CURRENT_DATE - created_at::date) as days_pending
                FROM debts
                WHERE client_id = %s
                ORDER BY created_at DESC
                LIMIT 10
            """
            
            with Database.get_cursor() as cursor:
                cursor.execute(query, (client_id,))
                results = cursor.fetchall()
                return [{
                    'id': r[0],
                    'amount': float(r[1]),
                    'description': r[2],
                    'status': r[3],
                    'date': r[4].strftime('%d/%m/%Y') if r[4] else '',
                    'days_pending': int(r[5]),  # Convertir a entero explícitamente
                    'status_color': 'red' if r[5] > 30 else 'orange' if r[5] > 7 else 'blue'
                } for r in results]
                
        except Exception as e:
            logger.error(f"Error al obtener deudas del cliente: {str(e)}")
            return []
    
    def get_appointment_payments(self, appointment_id):
        """Obtiene los pagos asociados a una cita específica"""
        try:
            query = """
                SELECT 
                    id,
                    amount,
                    method,
                    status,
                    payment_date,
                    invoice_number
                FROM payments
                WHERE appointment_id = %s
                ORDER BY payment_date DESC
            """
            
            with Database.get_cursor() as cursor:
                cursor.execute(query, (appointment_id,))
                results = cursor.fetchall()
                return [{
                    'id': r[0],
                    'amount': float(r[1]),
                    'method': r[2],
                    'status': r[3],
                    'date': r[4].strftime('%d/%m/%Y %H:%M') if r[4] else '',
                    'invoice': r[5]
                } for r in results]
                
        except Exception as e:
            logger.error(f"Error al obtener pagos de cita: {str(e)}")
            return []
    
    def mark_debt_as_paid(self, debt_id):
        """Marca una deuda como pagada"""
        try:
            query = """
                UPDATE debts
                SET status = 'paid', paid_at = %s
                WHERE id = %s
                RETURNING id
            """
            
            with Database.get_cursor() as cursor:
                cursor.execute(query, (datetime.now(), debt_id))
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error al marcar deuda como pagada: {str(e)}")
            raise
    
    def get_payment_summary(self, client_id):
        """Obtiene un resumen financiero del cliente"""
        try:
            summary = {
                'total_paid': 0,
                'total_debt': 0,
                'balance': 0,
                'last_payment': None
            }
            
            with Database.get_cursor() as cursor:
                # Total pagos (incluyendo los aplicados a deudas)
                payments_query = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE client_id = %s AND status = 'completed'
                """
                cursor.execute(payments_query, (client_id,))
                summary['total_paid'] = float(cursor.fetchone()[0] or 0)
                
                # Deudas pendientes (solo el saldo pendiente)
                debts_query = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM debts
                    WHERE client_id = %s AND status = 'pending'
                """
                cursor.execute(debts_query, (client_id,))
                summary['total_debt'] = float(cursor.fetchone()[0] or 0)
                
                summary['balance'] = summary['total_paid'] - (summary['total_debt'] + 
                                    self.get_total_paid_to_debts(client_id))
                
                # Último pago
                last_payment_query = """
                    SELECT amount, payment_date
                    FROM payments
                    WHERE client_id = %s
                    ORDER BY payment_date DESC
                    LIMIT 1
                """
                cursor.execute(last_payment_query, (client_id,))
                last_payment = cursor.fetchone()
                
                if last_payment:
                    summary['last_payment'] = {
                        'amount': float(last_payment[0]),
                        'date': last_payment[1].strftime('%d/%m/%Y %H:%M') if last_payment[1] else 'N/A'
                    }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error al obtener resumen financiero: {str(e)}")
            return {
                'total_paid': 0,
                'total_debt': 0,
                'balance': 0,
                'last_payment': None
            }

    def get_total_paid_to_debts(self, client_id):
        """Obtiene el total pagado a deudas"""
        with Database.get_cursor() as cursor:
            query = """
                SELECT COALESCE(SUM(paid_amount), 0)
                FROM debts
                WHERE client_id = %s AND status = 'paid'
            """
            cursor.execute(query, (client_id,))
            return float(cursor.fetchone()[0] or 0)