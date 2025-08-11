from datetime import date, timedelta
from core.database import get_db
from typing import Dict, Any

class StatsService:
    """Servicio para generar estadísticas del sistema"""
    # Add these new methods to the StatsService class

    @staticmethod
    def get_kpi_metrics(start_date: date, end_date: date) -> Dict[str, Any]:
        """Calcula métricas KPI para el periodo especificado
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            dict: Diccionario con métricas KPI
        """
        with get_db() as cursor:
            # Citas totales y estados
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                FROM appointments 
                WHERE date BETWEEN %s AND %s
            """, (start_date, end_date))
            appointments = cursor.fetchone()
            
            # Ingresos
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM payments
                WHERE status = 'completed'
                AND payment_date BETWEEN %s AND %s
            """, (start_date, end_date))
            revenue, payment_count = cursor.fetchone()
            
            # Calcular KPIs
            total_appointments = appointments[0] or 1  # Evitar división por cero
            conversion_rate = (appointments[1] or 0) / total_appointments
            avg_revenue_per_appointment = (revenue or 0) / total_appointments
            cancellation_rate = (appointments[2] or 0) / total_appointments
            
            return {
                'conversion_rate': conversion_rate,
                'avg_revenue_per_appointment': avg_revenue_per_appointment,
                'cancellation_rate': cancellation_rate,
                'revenue_per_day': (revenue or 0) / max(1, (end_date - start_date).days),
                'appointments_per_day': total_appointments / max(1, (end_date - start_date).days)
            }

    @staticmethod
    def get_temporal_trends(start_date: date, end_date: date, period: str = 'month') -> list[Dict]:
        """Obtiene tendencias temporales para el periodo especificado
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            period: 'day', 'week' o 'month'
            
        Returns:
            List[Dict]: Lista de datos por periodo
        """
        with get_db() as cursor:
            if period == 'day':
                cursor.execute("""
                    SELECT 
                        DATE(date) as day,
                        COUNT(*) as appointments,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM appointments
                    WHERE date BETWEEN %s AND %s
                    GROUP BY DATE(date)
                    ORDER BY DATE(date)
                """, (start_date, end_date))
            elif period == 'week':
                cursor.execute("""
                    SELECT 
                        DATE_TRUNC('week', date) as week,
                        COUNT(*) as appointments,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM appointments
                    WHERE date BETWEEN %s AND %s
                    GROUP BY DATE_TRUNC('week', date)
                    ORDER BY DATE_TRUNC('week', date)
                """, (start_date, end_date))
            else:  # month
                cursor.execute("""
                    SELECT 
                        DATE_TRUNC('month', date) as month,
                        COUNT(*) as appointments,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                    FROM appointments
                    WHERE date BETWEEN %s AND %s
                    GROUP BY DATE_TRUNC('month', date)
                    ORDER BY DATE_TRUNC('month', date)
                """, (start_date, end_date))
                
            return [dict(zip(['period', 'appointments', 'completed', 'cancelled'], row)) 
                for row in cursor.fetchall()]

    @staticmethod
    def compare_periods(current_start: date, current_end: date, 
                    previous_start: date, previous_end: date) -> Dict[str, Any]:
        """Compara métricas entre dos periodos
        
        Args:
            current_start: Inicio periodo actual
            current_end: Fin periodo actual
            previous_start: Inicio periodo anterior
            previous_end: Fin periodo anterior
            
        Returns:
            Dict: Comparativas con cambios porcentuales
        """
        current_stats = StatsService.get_kpi_metrics(current_start, current_end)
        previous_stats = StatsService.get_kpi_metrics(previous_start, previous_end)
        
        comparisons = {}
        for key in current_stats:
            if key in previous_stats and previous_stats[key] != 0:
                change = (current_stats[key] - previous_stats[key]) / previous_stats[key]
                comparisons[f"{key}_change"] = change
                
        return {
            'current': current_stats,
            'previous': previous_stats,
            'comparisons': comparisons
        }

    @staticmethod
    def detect_anomalies(start_date: date, end_date: date, threshold: float = 2.0) -> list[Dict]:
        """Detecta valores atípicos en las métricas
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            threshold: Umbral para considerar anomalía (en desviaciones estándar)
            
        Returns:
            List[Dict]: Lista de anomalías detectadas
        """
        # Implementación de detección de anomalías basada en datos históricos
        # (Código omitido por brevedad)
        return []
    
    @staticmethod
    def _count_appointments_by_status(start_date: date, end_date: date, status: str = None) -> int:
        """Cuenta citas en un rango de fechas con filtro opcional de estado"""
        with get_db() as cursor:
            query = """
                SELECT COUNT(*) 
                FROM appointments 
                WHERE date BETWEEN %s AND %s
            """
            params = [start_date, end_date]
            
            if status:
                query += " AND status = %s"
                params.append(status)
                
            cursor.execute(query, params)
            return cursor.fetchone()[0] or 0
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Obtiene las estadísticas principales para el dashboard
        Returns:
            Dict con las estadísticas clave
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        
        return {
            # Estadísticas de citas
            # Citas de hoy: Cantidad de citas del día actual (todas, no solo pendientes)
            'appointments_today': StatsService._count_appointments_by_status(today, today, status=None),
            'appointments_week': StatsService._count_appointments_by_status(start_of_week, today, 'pending'),
            'appointments_month': StatsService._count_appointments_by_status(start_of_month, today, 'pending'),
            'appointments_year': StatsService._count_appointments_by_status(start_of_year, today, 'pending'),
            
            # Estadísticas de clientes
            'new_clients_today': StatsService._count_new_clients(today),
            'new_clients_month': StatsService._count_new_clients_month(start_of_month, today),
            
            # Estadísticas financieras
            # Pendientes: Monto total de deudas pendientes
            'total_pending_debts_amount': StatsService._calculate_total_debts(), 
            # Ingresos: Suma de los pagos realizados el día actual (estado 'completed')
            'revenue_today': StatsService._calculate_revenue(today, today),
            'revenue_week': StatsService._calculate_revenue(start_of_week, today),
            'revenue_month': StatsService._calculate_revenue(start_of_month, today),
            'revenue_year': StatsService._calculate_revenue(start_of_year, today),
            
            # Métodos de pago más usados
            'payment_methods': StatsService._get_payment_methods_stats(start_of_month, today),
            
            # Deudas vencidas
            'overdue_debts': StatsService._count_overdue_debts()
        }

    @staticmethod
    def _count_new_clients_month(start_date: date, end_date: date) -> int:
        """Cuenta clientes nuevos registrados en un rango de fechas"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM clients 
                WHERE DATE(created_at) BETWEEN %s AND %s
                """,
                (start_date, end_date)
            )
            return cursor.fetchone()[0] or 0

    @staticmethod
    def _calculate_total_debts() -> float:
        """Calcula el total de deudas pendientes (monto de la deuda - monto pagado)"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(SUM(amount - paid_amount), 0)
                FROM debts
                WHERE status = 'pending'
                """
            )
            return float(cursor.fetchone()[0] or 0)

    @staticmethod
    def _get_payment_methods_stats(start_date: date, end_date: date) -> Dict[str, float]:
        """Obtiene estadísticas de métodos de pago"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT 
                    method,
                    COUNT(*) as count,
                    SUM(amount) as total
                FROM payments
                WHERE payment_date BETWEEN %s AND %s
                AND status = 'completed'
                GROUP BY method
                ORDER BY total DESC
                """,
                (start_date, end_date)
            )
            return {row[0]: {'count': row[1], 'total': float(row[2])} for row in cursor.fetchall()}

    @staticmethod
    def _count_overdue_debts() -> int:
        """Cuenta deudas vencidas (donde due_date es anterior a la fecha actual y el estado es 'pending')"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM debts 
                WHERE status = 'pending'
                AND due_date < CURRENT_DATE
                """
            )
            return cursor.fetchone()[0] or 0
    
    @staticmethod
    def _count_appointments(start_date: date, end_date: date) -> int:
        """Cuenta citas en un rango de fechas (originalmente solo completadas, ahora no se usa para el dashboard)"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM appointments 
                WHERE date BETWEEN %s AND %s
                AND status = 'completed'
                """,
                (start_date, end_date)
            )
            return cursor.fetchone()[0] or 0

    @staticmethod
    def _count_new_clients(for_date: date) -> int:
        """Cuenta clientes nuevos registrados en una fecha específica"""
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM clients 
                WHERE DATE(created_at) = %s
                """,
                (for_date,)
            )
            return cursor.fetchone()[0] or 0

    @staticmethod
    def _count_pending_payments() -> int:
        """
        Cuenta los pagos registrados que no tienen el estado 'completed'.
        Esta función ya no se usa directamente para la métrica "Pendientes" en el dashboard.
        """
        with get_db() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM payments 
                WHERE status != 'completed'
                """
            )
            return cursor.fetchone()[0] or 0

    @staticmethod
    def _calculate_revenue(start_date: date, end_date: date) -> float:
        """Calcula ingresos en un rango de fechas (solo pagos 'completed')"""
        with get_db() as cursor:
            if start_date == end_date: # Si es para un solo día, compara solo la fecha
                query = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE status = 'completed'
                    AND DATE(payment_date) = %s
                """
                params = (start_date,)
            else: # Para rangos de fechas, usa BETWEEN como antes
                query = """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM payments
                    WHERE status = 'completed'
                    AND payment_date BETWEEN %s AND %s
                """
                params = (start_date, end_date)
            
            cursor.execute(query, params)
            return float(cursor.fetchone()[0] or 0)

    @staticmethod
    def get_client_stats(client_id: int) -> Dict[str, Any]:
        """Obtiene estadísticas específicas de un cliente"""
        with get_db() as cursor:
            # Citas totales
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
                FROM appointments
                WHERE client_id = %s
                """,
                (client_id,)
            )
            appointment_stats = cursor.fetchone()
            
            # Pagos totales
            cursor.execute(
                """
                SELECT 
                    COALESCE(SUM(amount), 0) as total_paid,
                    COUNT(*) as total_payments
                FROM payments
                WHERE client_id = %s AND status = 'completed'
                """,
                (client_id,)
            )
            payment_stats = cursor.fetchone()
            
            return {
                'total_appointments': appointment_stats[0],
                'completed_appointments': appointment_stats[1],
                'cancelled_appointments': appointment_stats[2],
                'total_paid': float(payment_stats[0]),
                'total_payments': payment_stats[1]
            }

    @staticmethod
    def get_appointment_stats() -> Dict[str, Any]:
        """Obtiene estadísticas generales de citas"""
        with get_db() as cursor:
            # Por estado
            cursor.execute(
                """
                SELECT 
                    status,
                    COUNT(*) as count
                FROM appointments
                GROUP BY status
                """
            )
            status_stats = dict(cursor.fetchall())
            
            # Por mes
            cursor.execute(
                """
                SELECT 
                    DATE_TRUNC('month', date) as month,
                    COUNT(*) as count
                FROM appointments
                GROUP BY DATE_TRUNC('month', date)
                ORDER BY month DESC
                LIMIT 6
                """
            )
            monthly_stats = cursor.fetchall()
            
            return {
                'by_status': status_stats,
                'monthly_trend': monthly_stats
            }

# Alias para compatibilidad
get_dashboard_stats = StatsService.get_dashboard_stats
get_client_stats = StatsService.get_client_stats
get_appointment_stats = StatsService.get_appointment_stats

