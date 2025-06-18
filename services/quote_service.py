from datetime import date, datetime
from core.database import get_db, Database # Asegúrate de que get_db y Database estén correctamente importados
from typing import List, Dict, Optional
from services.treatment_service import TreatmentService
from services.payment_service import PaymentService # Importar PaymentService
from services.history_service import HistoryService # Importar HistoryService
import logging
import json
# Para usar RealDictCursor si estás con psycopg2 para obtener diccionarios
try:
    from psycopg2.extras import RealDictCursor
except ImportError:
    RealDictCursor = None


logger = logging.getLogger(__name__)

class QuoteService:
    @staticmethod
    def create_quote(
        client_id: int,
        treatments: List[Dict],
        user_id: Optional[int] = None,
        expiration_date: Optional[date] = None,
        notes: Optional[str] = None,
        discount: Optional[float] = 0.0 # Nuevo parámetro para el descuento
    ) -> Optional[int]:
        """Crea un nuevo presupuesto con tratamientos, aplica un descuento y genera una deuda para el cliente."""
        try:
            # Calcular el total_amount antes del descuento
            total_amount_before_discount = sum(t['price'] * t['quantity'] for t in treatments)
            
            # Aplicar el descuento
            final_total_amount = total_amount_before_discount - discount
            if final_total_amount < 0:
                final_total_amount = 0 # Evitar totales negativos

            with Database.get_cursor() as cursor: # Usar Database.get_cursor() directamente
                # Crear presupuesto
                cursor.execute(
                    """
                    INSERT INTO quotes 
                    (client_id, user_id, quote_date, expiration_date, total_amount, status, notes, discount, created_at, updated_at)
                    VALUES (%s, %s, CURRENT_DATE, %s, %s, 'pending', %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (client_id, user_id, expiration_date, final_total_amount, notes, discount) # Se añade discount aquí
                )
                quote_id = cursor.fetchone()[0]
                
                # Crear una descripción de deuda combinada para todos los tratamientos del presupuesto
                debt_description_parts = []

                # Agregar tratamientos asociados al presupuesto
                for treatment in treatments:
                    # Crear tratamiento si no existe y obtener su ID
                    treatment_id = TreatmentService.create_treatment_if_not_exists(
                        name=treatment['name'],
                        price=treatment['price']
                    )
                    
                    debt_description_parts.append(f"{treatment.get('name', 'Desconocido')} ({treatment.get('quantity', 1)}x)")

                    cursor.execute(
                        """
                        INSERT INTO quote_treatments 
                        (quote_id, treatment_id, quantity, price_at_quote)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (quote_id, treatment_id, treatment['quantity'], treatment['price'])
                    )

                    # Añadir el tratamiento al historial del cliente como "pendiente" del presupuesto
                    HistoryService.add_client_treatment(
                        client_id=client_id,
                        treatment_id=treatment_id,
                        notes=f"Asociado a presupuesto ID: {quote_id}",
                        treatment_date=date.today(), # Fecha actual como fecha de registro en historial
                        quote_id=quote_id,
                        quantity_to_mark_completed=0, # Inicialmente, no hay cantidad completada de este presupuesto
                        cursor=cursor # Pasa el cursor para que sea parte de la misma transacción
                    )
                
                final_debt_description = f"Presupuesto #{quote_id}: " + ", ".join(debt_description_parts)

                # Crear deuda asociada al presupuesto con el monto final (descontado)
                PaymentService.create_debt(
                    client_id=client_id,
                    amount=final_total_amount, # Se usa el monto final después del descuento
                    description=final_debt_description,
                    quote_id=quote_id, # Asociar la deuda con el ID del presupuesto
                    cursor=cursor # Pasar el cursor para que sea parte de la misma transacción
                )

                return quote_id
        except Exception as e:
            logger.error(f"Error al crear presupuesto: {str(e)}")
            return None

    @staticmethod
    def get_quote(quote_id: int) -> Optional[Dict]:
        """Obtiene un presupuesto por ID con sus tratamientos, descuento y nombre de cliente."""
        with get_db() as cursor:
            # Obtener datos del presupuesto y nombre/cédula del cliente
            cursor.execute(
                """
                SELECT q.id, q.client_id, c.name, c.cedula, q.quote_date, 
                       q.expiration_date, q.total_amount, q.status, q.notes,
                       q.created_at, q.updated_at, q.discount,
                       c.phone, c.email, c.address
                FROM quotes q
                JOIN clients c ON q.client_id = c.id
                WHERE q.id = %s
                """,
                (quote_id,)
            )
            quote_data_tuple = cursor.fetchone()
            if not quote_data_tuple:
                return None
            
            # Mapear la tupla a un diccionario manualmente
            quote_data = {
                'id': quote_data_tuple[0],
                'client_id': quote_data_tuple[1],
                'name': quote_data_tuple[2],
                'cedula': quote_data_tuple[3],
                'quote_date': quote_data_tuple[4],
                'expiration_date': quote_data_tuple[5],
                'total_amount': float(quote_data_tuple[6]),
                'status': quote_data_tuple[7],
                'notes': quote_data_tuple[8],
                'created_at': quote_data_tuple[9],
                'updated_at': quote_data_tuple[10],
                'discount': float(quote_data_tuple[11]),
                'phone': quote_data_tuple[12],
                'email': quote_data_tuple[13],
                'address': quote_data_tuple[14],
            }


            # Obtener tratamientos asociados
            cursor.execute(
                """
                SELECT t.id, t.name, qt.quantity, qt.price_at_quote, qt.subtotal
                FROM quote_treatments qt
                JOIN treatments t ON qt.treatment_id = t.id
                WHERE qt.quote_id = %s
                ORDER BY t.name
                """,
                (quote_id,)
            )
            treatments = [
                {
                    'id': row[0],
                    'name': row[1],
                    'quantity': row[2],
                    'price': float(row[3]), 
                    'subtotal': float(row[4])
                } for row in cursor.fetchall()
            ]
            
            return {
                'id': quote_data['id'],
                'client_id': quote_data['client_id'],
                'client_name': quote_data['name'],
                'client_cedula': quote_data['cedula'],
                'quote_date': quote_data['quote_date'],
                'expiration_date': quote_data['expiration_date'],
                'total_amount': float(quote_data['total_amount']),
                'status': quote_data['status'],
                'notes': quote_data['notes'],
                'created_at': quote_data['created_at'],
                'updated_at': quote_data['updated_at'],
                'discount': float(quote_data['discount']),
                'client_phone': quote_data['phone'],
                'client_email': quote_data['email'],
                'client_address': quote_data['address'],
                'treatments': treatments
            }

    @staticmethod
    def get_all_quotes(
        search_term: Optional[str] = None, 
        status_filter: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: Optional[int] = None, # Añadido para paginación
        offset: int = 0             # Añadido para paginación
    ) -> List[Dict]:
        """Obtiene todos los presupuestos con filtros opcionales, paginación y detalles extendidos."""
        query = """
            SELECT 
                q.id, q.client_id, q.quote_date, q.expiration_date, q.total_amount, q.status, q.notes, q.discount,
                c.name AS client_name, c.cedula AS client_cedula, c.phone AS client_phone, c.email AS client_email, c.address AS client_address,
                COALESCE(
                    JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'id', t.id,
                            'name', t.name,
                            'quantity', qt.quantity,
                            'price_at_quote', qt.price_at_quote,
                            'subtotal', qt.subtotal
                        )
                        ORDER BY t.name
                    ) FILTER (WHERE qt.quote_id IS NOT NULL),
                    '[]'::json
                ) AS treatments_summary
            FROM quotes q
            JOIN clients c ON q.client_id = c.id
            LEFT JOIN quote_treatments qt ON q.id = qt.quote_id
            LEFT JOIN treatments t ON qt.treatment_id = t.id
            WHERE 1=1
        """
        params = []

        if search_term:
            query += " AND (c.name ILIKE %s OR c.cedula ILIKE %s OR c.phone ILIKE %s OR c.email ILIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if status_filter and status_filter != "all":
            query += " AND q.status = %s"
            params.append(status_filter)
        
        if start_date:
            query += " AND q.quote_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND q.quote_date <= %s"
            params.append(end_date)
            
        query += """
            GROUP BY q.id, q.client_id, q.quote_date, q.expiration_date, q.total_amount, q.status, q.notes, q.discount,
                     c.name, c.cedula, c.phone, c.email, c.address
            ORDER BY q.quote_date DESC
        """

        if limit is not None:
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

        with get_db() as cursor:
            cursor.execute(query, params)
            
            col_names = [desc[0] for desc in cursor.description]
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(col_names, row))
                
                # Convertir a float los campos numéricos que lo requieran
                if 'total_amount' in row_dict:
                    row_dict['total_amount'] = float(row_dict['total_amount'])
                if 'discount' in row_dict: # Asegura que el descuento sea un float
                    row_dict['discount'] = float(row_dict['discount'])

                # Cargar treatments_summary si es una cadena JSON
                if isinstance(row_dict.get('treatments_summary'), str):
                    try:
                        row_dict['treatments_summary'] = json.loads(row_dict['treatments_summary'])
                    except json.JSONDecodeError:
                        logger.error(f"Error al decodificar JSON para treatments_summary en quote ID {row_dict.get('id')}")
                        row_dict['treatments_summary'] = [] # Vacío si falla
                results.append(row_dict)
            return results

    @staticmethod
    def count_quotes(
        search_term: Optional[str] = None, 
        status_filter: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """Cuenta el número total de presupuestos con filtros opcionales."""
        query = """
            SELECT COUNT(q.id)
            FROM quotes q
            JOIN clients c ON q.client_id = c.id
            WHERE 1=1
        """
        params = []

        if search_term:
            query += " AND (c.name ILIKE %s OR c.cedula ILIKE %s OR c.phone ILIKE %s OR c.email ILIKE %s)"
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if status_filter and status_filter != "all":
            query += " AND q.status = %s"
            params.append(status_filter)
        
        if start_date:
            query += " AND q.quote_date >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND q.quote_date <= %s"
            params.append(end_date)
            
        with get_db() as cursor:
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            return count

    @staticmethod
    def update_quote(
        quote_id: int,
        client_id: int,
        treatments: List[Dict],
        expiration_date: Optional[date] = None,
        notes: Optional[str] = None,
        status: str = 'pending', # Permite actualizar el estado
        discount: Optional[float] = 0.0 # Nuevo parámetro para el descuento
    ) -> bool:
        """Actualiza un presupuesto existente y su deuda asociada, incluyendo el descuento."""
        try:
            # Calcular el total_amount antes del descuento
            total_amount_before_discount = sum(t['price'] * t['quantity'] for t in treatments)
            
            # Aplicar el descuento
            new_final_total_amount = total_amount_before_discount - discount
            if new_final_total_amount < 0:
                new_final_total_amount = 0 # Evitar totales negativos
            
            with Database.get_cursor() as cursor:
                # Actualizar presupuesto
                cursor.execute(
                    """
                    UPDATE quotes
                    SET client_id = %s,
                        expiration_date = %s,
                        total_amount = %s,
                        status = %s,
                        notes = %s,
                        discount = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (client_id, expiration_date, new_final_total_amount, status, notes, discount, quote_id)
                )
                
                # Eliminar tratamientos existentes del presupuesto
                cursor.execute(
                    "DELETE FROM quote_treatments WHERE quote_id = %s",
                    (quote_id,)
                )
                
                # Eliminar tratamientos de historial asociados a este presupuesto
                cursor.execute(
                    """
                    DELETE FROM client_treatments
                    WHERE quote_id = %s;
                    """,
                    (quote_id,)
                )

                # Crear una descripción de deuda combinada para todos los tratamientos del presupuesto
                debt_description_parts = []

                # Insertar tratamientos actualizados
                for treatment in treatments:
                    # Crear tratamiento si no existe y obtener su ID
                    treatment_id = TreatmentService.create_treatment_if_not_exists(
                        name=treatment['name'],
                        price=treatment['price']
                    )
                    
                    debt_description_parts.append(f"{treatment.get('name', 'Desconocido')} ({treatment.get('quantity', 1)}x)")

                    cursor.execute(
                        """
                        INSERT INTO quote_treatments 
                        (quote_id, treatment_id, quantity, price_at_quote)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (quote_id, treatment_id, treatment['quantity'], treatment['price'])
                    )
                    # Añadir el tratamiento al historial del cliente como "pendiente" del presupuesto
                    HistoryService.add_client_treatment(
                        client_id=client_id,
                        treatment_id=treatment_id,
                        notes=f"Asociado a presupuesto ID: {quote_id}",
                        treatment_date=date.today(), # Fecha actual como fecha de registro en historial
                        quote_id=quote_id,
                        quantity_to_mark_completed=0, # Inicialmente, no hay cantidad completada de este presupuesto
                        cursor=cursor # Pasa el cursor
                    )

                final_debt_description = f"Presupuesto #{quote_id}: " + ", ".join(debt_description_parts)

                # Actualizar la deuda asociada al presupuesto
                # Primero, elimina cualquier deuda anterior asociada a este presupuesto
                cursor.execute(
                    "DELETE FROM debts WHERE quote_id = %s",
                    (quote_id,)
                )
                
                # Luego, crea una nueva deuda con el nuevo total_amount (descontado)
                PaymentService.create_debt(
                    client_id=client_id,
                    amount=new_final_total_amount, # Se usa el monto final después del descuento
                    description=final_debt_description,
                    quote_id=quote_id,
                    cursor=cursor
                )

                return True
        except Exception as e:
            logger.error(f"Error al actualizar presupuesto {quote_id}: {str(e)}")
            return False

    @staticmethod
    def delete_quote(quote_id: int) -> bool:
        """Elimina un presupuesto y sus tratamientos asociados, y la deuda asociada."""
        try:
            with Database.get_cursor() as cursor:
                # Eliminar las deudas asociadas al presupuesto primero
                cursor.execute("DELETE FROM debts WHERE quote_id = %s", (quote_id,))
                logger.info(f"Eliminadas {cursor.rowcount} deudas asociadas al presupuesto {quote_id}.")

                # Eliminar tratamientos de historial asociados a este presupuesto
                cursor.execute(
                    """
                    DELETE FROM client_treatments
                    WHERE quote_id = %s;
                    """,
                    (quote_id,)
                )
                logger.info(f"Eliminados {cursor.rowcount} registros de historial para presupuesto {quote_id}.")


                # Eliminar tratamientos del presupuesto (ON DELETE CASCADE se encargará de esto)
                cursor.execute("DELETE FROM quote_treatments WHERE quote_id = %s", (quote_id,))
                
                # Eliminar el presupuesto
                cursor.execute("DELETE FROM quotes WHERE id = %s RETURNING id", (quote_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error al eliminar presupuesto {quote_id}: {str(e)}")
            return False

    @staticmethod
    def update_quote_status(quote_id: int, new_status: str) -> bool:
        """Actualiza el estado de un presupuesto."""
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE quotes SET status = %s, updated_at = NOW() WHERE id = %s",
                    (new_status, quote_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error al actualizar estado de presupuesto {quote_id}: {str(e)}")
            return False

    @staticmethod
    def get_quote_treatments(quote_id: int) -> List[Dict]:
        """Obtiene los tratamientos asociados a un presupuesto."""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT t.id, t.name, qt.quantity, qt.price_at_quote, qt.subtotal
                FROM quote_treatments qt
                JOIN treatments t ON qt.treatment_id = t.id
                WHERE qt.quote_id = %s
                ORDER BY t.name
                """,
                (quote_id,)
            )
            # Mapear las tuplas a diccionarios
            return [
                {
                    'id': row[0],
                    'name': row[1],
                    'quantity': row[2],
                    'price': float(row[3]),
                    'subtotal': float(row[4])
                } for row in cursor.fetchall()
            ]

    @staticmethod
    def get_client_info_for_quote_pdf(client_id: int) -> Optional[Dict]:
        """
        Obtiene la información del cliente necesaria para el PDF del presupuesto.
        """
        try:
            with Database.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT name, cedula, phone, email, address
                    FROM clients
                    WHERE id = %s
                    """,
                    (client_id,)
                )
                client_data = cursor.fetchone()
                if client_data:
                    # Mapear la tupla a un diccionario manualmente
                    return {
                        'name': client_data[0],
                        'cedula': client_data[1],
                        'phone': client_data[2],
                        'email': client_data[3],
                        'address': client_data[4]
                    }
                return None
        except Exception as e:
            logger.error(f"Error al obtener información del cliente {client_id} para PDF: {str(e)}")
            return None
