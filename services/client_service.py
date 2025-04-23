from core.database import get_db, Database
from models.client import Client  # Asegúrate de tener este modelo
from typing import List
import logging

logger = logging.getLogger(__name__)

class ClientService:
    
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
    def delete_client_with_dependencies(client_id: int) -> bool:
        """Elimina un cliente y todos sus registros asociados (pagos, deudas, citas)"""
        with Database.get_cursor() as cursor:
            try:
                # 1. Eliminar registros en debt_payments (si existe esta tabla)
                cursor.execute(
                    "DELETE FROM debt_payments WHERE payment_id IN "
                    "(SELECT id FROM payments WHERE client_id = %s)",
                    (client_id,)
                )
                
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
        query = "SELECT id, name, cedula, phone, email, created_at, updated_at FROM clients"
        params = ()
        
        if search_term:
            query += " WHERE name ILIKE %s OR cedula ILIKE %s"
            params = (f"%{search_term}%", f"%{search_term}%")
            
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