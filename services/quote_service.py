# quote_service.py
from datetime import date, datetime
from core.database import get_db, Database
from typing import List, Dict, Optional
from services.treatment_service import TreatmentService
import logging

logger = logging.getLogger(__name__)

class QuoteService:
    @staticmethod
    def create_quote(
        client_id: int,
        treatments: List[Dict],
        user_id: Optional[int] = None,
        expiration_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> Optional[int]:
        """Crea un nuevo presupuesto con tratamientos"""
        try:
            total_amount = sum(t['price'] * t['quantity'] for t in treatments)
            
            with Database.get_cursor() as cursor:
                # Crear presupuesto
                cursor.execute(
                    """
                    INSERT INTO quotes 
                    (client_id, user_id, quote_date, expiration_date, total_amount, status, notes, created_at, updated_at)
                    VALUES (%s, %s, CURRENT_DATE, %s, %s, 'pending', %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, user_id, expiration_date, total_amount, notes)
                )
                quote_id = cursor.fetchone()[0]
                
                # Agregar tratamientos
                for treatment in treatments:
                    treatment_id = TreatmentService.create_treatment_if_not_exists(
                        name=treatment['name'],
                        price=treatment['price']
                    )
                    cursor.execute(
                        """
                        INSERT INTO quote_treatments 
                        (quote_id, treatment_id, quantity, price_at_quote)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (quote_id, treatment_id, treatment['quantity'], treatment['price'])
                    )
                
                return quote_id
        except Exception as e:
            logger.error(f"Error al crear presupuesto: {str(e)}")
            return None

    @staticmethod
    def get_quote(quote_id: int) -> Optional[dict]:
        """Obtiene un presupuesto por ID con sus tratamientos"""
        with get_db() as cursor:
            # Obtener datos del presupuesto
            cursor.execute(
                """
                SELECT q.id, q.client_id, c.name, c.cedula, q.quote_date, 
                       q.expiration_date, q.total_amount, q.status, q.notes
                FROM quotes q
                JOIN clients c ON q.client_id = c.id
                WHERE q.id = %s
                """,
                (quote_id,)
            )
            quote_data = cursor.fetchone()
            if not quote_data:
                return None
            
            # Obtener tratamientos asociados
            cursor.execute(
                """
                SELECT t.id, t.name, qt.quantity, qt.price_at_quote
                FROM quote_treatments qt
                JOIN treatments t ON qt.treatment_id = t.id
                WHERE qt.quote_id = %s
                """,
                (quote_id,)
            )
            treatments = [
                {
                    'id': row[0],
                    'name': row[1],
                    'quantity': row[2],
                    'price': float(row[3])
                } for row in cursor.fetchall()
            ]
            
            return {
                'id': quote_data[0],
                'client_id': quote_data[1],
                'client_name': quote_data[2],
                'client_cedula': quote_data[3],
                'quote_date': quote_data[4],
                'expiration_date': quote_data[5],
                'total_amount': float(quote_data[6]),
                'status': quote_data[7],
                'notes': quote_data[8],
                'treatments': treatments
            }