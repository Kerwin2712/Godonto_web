from core.database import get_db, Database
from models.client import Client  # Asegúrate de tener este modelo
from typing import List, Optional
import logging
#print
logger = logging.getLogger(__name__)

class ClientService:
    @staticmethod
    def get_client_by_id(client_id: int) -> Optional[Client]: # Añadido este método
        """Obtiene un cliente por su ID."""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, name, cedula, phone, email, created_at, updated_at
                FROM clients
                WHERE id = %s
                """,
                (client_id,)
            )
            row = cursor.fetchone()
            if row:
                return Client(
                    id=row[0],
                    name=row[1],
                    cedula=row[2],
                    phone=row[3],
                    email=row[4],
                    created_at=row[5],
                    updated_at=row[6]
                )
            return None # Retornar None si el cliente no se encuentra
    
    @staticmethod
    def has_payments_or_debts(client_id: int) -> bool:
        """Verifica si el cliente tiene pagos o deudas asociadas"""
        with get_db() as cursor:
            # Verificar pagos
            cursor.execute(
                "SELECT COUNT(*) FROM payments WHERE client_id = %s",
                (client_id,)
            )
            has_payments = cursor.fetchone()[0] > 0
            
            # Verificar deudas
            cursor.execute(
                "SELECT COUNT(*) FROM debts WHERE client_id = %s",
                (client_id,)
            )
            has_debts = cursor.fetchone()[0] > 0
            
            return has_payments or has_debts
    
    @staticmethod
    def get_client_quotes(client_id: int) -> List[dict]:
        """Obtiene presupuestos de un cliente"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, quote_date, expiration_date, total_amount, status
                FROM quotes
                WHERE client_id = %s
                ORDER BY quote_date DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'quote_date': row[1],
                    'expiration_date': row[2],
                    'total_amount': float(row[3]),
                    'status': row[4]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_client_appointments(client_id: int) -> List[dict]:
        """Obtiene citas de un cliente"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT id, date, hour, status, notes
                FROM appointments
                WHERE client_id = %s
                ORDER BY date DESC, hour DESC
                """,
                (client_id,)
            )
            return [
                {
                    'id': row[0],
                    'date': row[1],
                    'time': row[2].strftime('%H:%M'),
                    'status': row[3],
                    'notes': row[4]
                } for row in cursor.fetchall()
            ]
    
    @staticmethod
    def delete_client_with_dependencies(client_id: int) -> bool:
        """Elimina un cliente y todos sus registros asociados (pagos, deudas, citas)"""
        with Database.get_cursor() as cursor:
            try:
                # 1. Eliminar registros en debt_payments (si existe esta tabla)
                #cursor.execute(
                #    "DELETE FROM debt_payments WHERE payment_id IN "
                #    "(SELECT id FROM payments WHERE client_id = %s)",
                #    (client_id,)
                #)
                
                # 2. Eliminar deudas
                cursor.execute(
                    "DELETE FROM debts WHERE client_id = %s",
                    (client_id,)
                )
                
                # 3. Eliminar pagos
                cursor.execute(
                    "DELETE FROM payments WHERE client_id = %s",
                    (client_id,)
                )
                
                # 4. Eliminar citas
                cursor.execute(
                    "DELETE FROM appointments WHERE client_id = %s",
                    (client_id,)
                )
                
                # 5. Finalmente eliminar el cliente
                cursor.execute(
                    "DELETE FROM clients WHERE id = %s RETURNING id",
                    (client_id,)
                )
                return cursor.fetchone() is not None
                
            except Exception as e:
                logger.error(f"Error al eliminar cliente con dependencias: {str(e)}")
                raise
    
    @staticmethod
    def has_appointments(client_id: int) -> bool:
        """Verifica si el cliente tiene citas asociadas"""
        with get_db() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM appointments WHERE client_id = %s",
                (client_id,)
            )
            return cursor.fetchone()[0] > 0
    
    @staticmethod
    def delete_client(client_id: int) -> bool:
        """Elimina un cliente por su ID"""
        with Database.get_cursor() as cursor:
            cursor.execute(
                "DELETE FROM clients WHERE id = %s RETURNING id",
                (client_id,)
            )
            return cursor.fetchone() is not None
    
    @staticmethod
    def get_recent_clients(limit: int = 5) -> List[Client]:
        """Obtiene los clientes más recientes"""
        with get_db() as cursor:
            cursor.execute("""
                SELECT id, name, cedula, phone, email, created_at, updated_at
                FROM clients
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            clients = []
            for row in cursor.fetchall():
                clients.append(Client(
                    id=row[0],
                    name=row[1],
                    cedula=row[2],
                    phone=row[3],
                    email=row[4],
                    created_at=row[5],
                    updated_at=row[6]
                ))
            return clients
    
    @staticmethod
    def get_all_clients(search_term=None) -> List[Client]:
        query = """
            SELECT id, name, cedula, phone, email, created_at, updated_at 
            FROM clients
            WHERE 1=1
        """
        params = []
        
        if search_term:
            query += """
                AND (
                    unaccent(name) ILIKE unaccent(%s) OR 
                    unaccent(cedula) ILIKE unaccent(%s) OR 
                    unaccent(phone) ILIKE unaccent(%s) OR 
                    unaccent(email) ILIKE unaccent(%s)
                )
            """
            search_param = f"%{search_term}%"
            params = [search_param] * 4  # Mismo término para todos los campos
        
        query += " ORDER BY name ASC"  # Orden alfabético por nombre
        
        with Database.get_cursor() as cursor:
            cursor.execute(query, params)
            return [Client(*row) for row in cursor.fetchall()]

    @staticmethod
    def create_client(client_data):
        query = """
            INSERT INTO clients (name, cedula, phone, email)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        with Database.get_cursor() as cursor:
            cursor.execute(query, (
                client_data['name'],
                client_data['cedula'],
                client_data['phone'],
                client_data['email']
            ))
            return cursor.fetchone()[0]