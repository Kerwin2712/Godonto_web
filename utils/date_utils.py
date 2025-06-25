from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple
import calendar
import pytz  # Usamos pytz como alternativa compatible
#
# Configuración de zona horaria para Venezuela
ZONA_HORARIA = pytz.timezone('America/Caracas')

class DateUtils:
    """Clase utilitaria para operaciones con fechas y horas con soporte para Venezuela"""
    
    @staticmethod
    def is_working_hours(check_time: time) -> bool:
        """
        Verifica si una hora está dentro del horario laboral (07:30 - 19:30)
        Args:
            check_time: Hora a verificar
        Returns:
            bool: True si está en horario laboral
        """
        return time(7, 30) <= check_time <= time(19, 30)

    @staticmethod
    def is_future_datetime(dt: datetime) -> bool:
        """
        Verifica si una fecha/hora está en el futuro (según hora de Venezuela)
        Args:
            dt: DateTime a verificar (se asume en UTC o naive)
        Returns:
            bool: True si es en el futuro
        """
        now = datetime.now(ZONA_HORARIA)
        if dt.tzinfo is None:
            dt = ZONA_HORARIA.localize(dt)
        return dt > now

    @staticmethod
    def to_local_time(utc_dt: datetime) -> datetime:
        """
        Convierte un datetime UTC a la zona horaria de Venezuela
        Args:
            utc_dt: DateTime en UTC
        Returns:
            DateTime en zona horaria de Venezuela
        """
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(ZONA_HORARIA)

    @staticmethod
    def format_date(dt: date, fmt: str = "%d/%m/%Y") -> str:
        """Formatea una fecha según formato especificado (default: dd/mm/yyyy)"""
        return dt.strftime(fmt)

    @staticmethod
    def format_datetime(dt: datetime, fmt: str = "%d/%m/%Y %H:%M") -> str:
        """Formatea un datetime según formato especificado"""
        return dt.strftime(fmt)

    @staticmethod
    def get_month_name(month: int) -> str:
        """Obtiene el nombre del mes en español"""
        months = [
            "Enero", "Febrero", "Marzo", "Abril", 
            "Mayo", "Junio", "Julio", "Agosto",
            "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        return months[month - 1]

    @staticmethod
    def get_weekday_name(day: int) -> str:
        """Obtiene el nombre del día de la semana en español"""
        days = [
            "Lun", "Mar", "Mié", 
            "Jue", "Vie", "Sáb", "Dom"
        ]
        return days[day]

    @staticmethod
    def get_week_range(for_date: date) -> Tuple[date, date]:
        """
        Obtiene el rango de fechas (lunes a domingo) para una fecha dada
        Returns:
            Tuple (fecha_inicio, fecha_fin)
        """
        start = for_date - timedelta(days=for_date.weekday())
        end = start + timedelta(days=6)
        return start, end

    @staticmethod
    def get_last_day_of_month(for_date: date) -> date:
        """Obtiene el último día del mes para una fecha dada"""
        _, last_day = calendar.monthrange(for_date.year, for_date.month)
        return for_date.replace(day=last_day)

    @staticmethod
    def is_today(check_date: date) -> bool:
        """Verifica si una fecha es hoy (según hora de Venezuela)"""
        return check_date == datetime.now(ZONA_HORARIA).date()

    @staticmethod
    def is_current_month(check_date: date, reference_date: date) -> bool:
        """Verifica si una fecha está en el mismo mes que la fecha de referencia"""
        return (check_date.year == reference_date.year and 
                check_date.month == reference_date.month)

# Funciones de conveniencia para mantener compatibilidad
is_working_hours = DateUtils.is_working_hours
is_future_datetime = DateUtils.is_future_datetime
to_local_time = DateUtils.to_local_time
format_date = DateUtils.format_date
get_month_name = DateUtils.get_month_name
get_weekday_name = DateUtils.get_weekday_name
get_week_range = DateUtils.get_week_range
get_last_day_of_month = DateUtils.get_last_day_of_month 
is_today = DateUtils.is_today
is_current_month = DateUtils.is_current_month