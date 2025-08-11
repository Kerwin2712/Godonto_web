import flet as ft
from datetime import datetime, timedelta
from core.database import get_db
from utils.date_utils import (
    format_date,
    get_month_name,
    get_week_range,
    get_last_day_of_month
)
from utils.alerts import show_snackbar
import logging
from fpdf import FPDF
import os
import asyncio

logger = logging.getLogger(__name__)

# Clase para generar el PDF del reporte
class ReportGenerator:
    def __init__(self):
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=15)
        self.pdf.add_page()
        self.pdf.set_font("Arial", size=10) 

    def _add_header(self, title, start_date, end_date):
        self.pdf.set_font("Arial", "B", 16)
        self.pdf.cell(0, 10, title, 0, 1, "C")
        self.pdf.set_font("Arial", "", 10)
        self.pdf.cell(0, 7, f"Período: {format_date(start_date)} - {format_date(end_date)}\\n", 0, 1, "C")
        self.pdf.ln(5)

    def _add_section_title(self, title):
        self.pdf.set_font("Arial", "B", 12)
        self.pdf.cell(0, 8, title, 0, 1, "L")
        self.pdf.ln(2)

    def _add_stat_card_to_pdf(self, title, value):
        self.pdf.set_font("Arial", "B", 10)
        self.pdf.cell(0, 6, f"{title}:", 0, 0, "L")
        self.pdf.set_font("Arial", "", 10)
        self.pdf.cell(0, 6, str(value), 0, 1, "R")
        self.pdf.ln(1)

    def _add_table_header(self, headers, col_widths):
        self.pdf.set_fill_color(200, 220, 255) # Light blue background for headers
        self.pdf.set_font("Arial", "B", 8)
        for header, width in zip(headers, col_widths):
            self.pdf.cell(width, 7, header, 1, 0, "C", True)
        self.pdf.ln()

    def _add_table_row(self, row_data, col_widths):
        self.pdf.set_font("Arial", "", 8)
        # Calculate max height needed for multi-line cells
        max_cell_height = 7
        for data, width in zip(row_data, col_widths):
            # Estimate number of lines for description
            if width > 0: # Avoid division by zero
                num_lines = self.pdf.get_string_width(str(data)) / width
                if num_lines > 1:
                    max_cell_height = max(max_cell_height, self.pdf.font_size * 1.2 * (int(num_lines) + 1)) # Add some padding

        for data, width in zip(row_data, col_widths):
            # Use multi_cell for description to allow wrapping
            if data == row_data[5]: # Assuming description is the 6th column (index 5)
                self.pdf.multi_cell(width, max_cell_height / (str(data).count('\n') + 1) if str(data).count('\n') > 0 else 7, str(data), 1, "L", False)
            else:
                self.pdf.cell(width, max_cell_height, str(data), 1, 0, "L")
        self.pdf.ln()

    def generate_report_pdf(self, file_path: str, report_data: dict, start_date: datetime.date, end_date: datetime.date):
        self._add_header("Reporte General de Clínica Odontológica", start_date, end_date)

        # Sección de Estadísticas
        self._add_section_title("Resumen Estadístico")
        stats = report_data.get('stats', {})
        self.pdf.set_left_margin(20) # Indent for stats
        self.pdf.set_right_margin(20)

        stats_display_order = [
            ("Citas Totales", stats.get('total_appointments', 0)),
            ("Citas Completadas", stats.get('completed_appointments', 0)),
            ("Ingresos Total", f"${stats.get('total_revenue', 0.0):,.2f}"),
            ("Cantidad de Clientes", stats.get('total_clients', 0)), # Actualizado
            ("Pagos Registrados", stats.get('total_payments', 0)),
            ("Monto Deudas Pendientes", f"${stats.get('total_pending_debts_amount', 0.0):,.2f}"),
            ("Monto Deudas Vencidas", f"${stats.get('overdue_debts_amount', 0.0):,.2f}"),
            ("Deudas Vencidas (Conteo)", stats.get('overdue_count', 0)),
            ("Método de Pago Popular", stats.get('popular_payment_method', 'N/A'))
        ]

        for title, value in stats_display_order:
            self._add_stat_card_to_pdf(title, value)
        self.pdf.ln(5)
        self.pdf.set_left_margin(10) # Reset margin
        self.pdf.set_right_margin(10)

        # Sección de Citas Recientes
        self._add_section_title("Citas Recientes")
        appointments = report_data.get('appointments', [])
        if appointments:
            headers = ["Fecha", "Cliente", "Hora", "Estado", "Monto Tratamientos"]
            col_widths = [30, 60, 20, 25, 45] # Ajustar según el contenido
            self._add_table_header(headers, col_widths)
            for appt in appointments:
                row_data = [
                    appt[2].strftime("%d/%m/%Y"),
                    appt[1],
                    appt[3].strftime("%H:%M"),
                    appt[4].capitalize(),
                    f"${appt[5]:,.2f}"
                ]
                self._add_table_row(row_data, col_widths)
        else:
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(0, 10, "No hay citas recientes en este período.", 0, 1)
        self.pdf.ln(5)

        # Sección de Pagos
        self._add_section_title("Detalle de Pagos")
        payments = report_data.get('payments', [])
        if payments:
            headers = ["Fecha Pago", "Cliente", "Monto", "Método", "Estado", "Factura"]
            col_widths = [25, 50, 25, 25, 25, 30]
            self._add_table_header(headers, col_widths)
            for payment in payments:
                row_data = [
                    payment[1].strftime("%d/%m/%Y"),
                    payment[2],
                    f"${payment[4]:,.2f}",
                    payment[3],
                    str(payment[5]).capitalize(),
                    payment[6] or "N/A"
                ]
                self.pdf.ln(0.5) # Small padding
                self._add_table_row(row_data, col_widths)
        else:
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(0, 10, "No hay pagos en este período.", 0, 1)
        self.pdf.ln(5)

        # Sección de Deudas
        self._add_section_title("Detalle de Deudas")
        debts = report_data.get('debts', [])
        if debts:
            # Columnas actualizadas: eliminar "Fecha Vencimiento" y "Días Vencida"
            headers = ["Cliente", "Fecha Creación", "Monto Total", "Monto Pagado", "Monto Restante", "Descripción", "Estado"]
            col_widths = [35, 25, 25, 25, 25, 55, 20] # Ajustar anchos, aumentar descripción
            self._add_table_header(headers, col_widths)
            for debt in debts:
                remaining_amount = debt[3] - debt[7] # total - paid

                row_data = [
                    debt[1],
                    debt[2].strftime("%d/%m/%Y"),
                    f"${debt[3]:,.2f}",
                    f"${debt[7]:,.2f}",
                    f"${remaining_amount:,.2f}",
                    debt[4] or "N/A", # Descripción
                    str(debt[5]).capitalize()
                ]
                self._add_table_row(row_data, col_widths)
        else:
            self.pdf.set_font("Arial", "", 10)
            self.pdf.cell(0, 10, "No hay deudas en este período.", 0, 1)
        self.pdf.ln(5)

        try:
            self.pdf.output(file_path)
            logger.info(f"PDF del reporte generado exitosamente en: {file_path}")
            return True, f"PDF del reporte generado exitosamente en: {file_path}"
        except Exception as e:
            logger.error(f"Error al generar el PDF del reporte en '{file_path}': {e}")
            return False, f"Error al generar el PDF del reporte: {str(e)}"

class ReportsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.report_type = 'monthly' # Tipo de reporte inicial
        self.end_date = datetime.now().date() + timedelta(days=60) # Inicializa end_date 60 dias despues de hoy
        self.start_date = self.end_date - timedelta(days=120) # Inicializa start_date a 120 días antes de end_date
        
        # Almacenar datos cargados para el PDF
        self.current_stats = {}
        self.current_appointments = []
        self.current_payments = []
        self.current_debts = []
        self._temp_report_data = None # Para almacenar datos temporales para el PDF

        # Configurar el FilePicker para la descarga con un handler de resultado
        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self.page.overlay.append(self.file_picker) # Añadir el FilePicker al overlay de la página
        self.page.update()

        # Componentes UI principales para el diseño
        self.stats_row = ft.ResponsiveRow(spacing=20, run_spacing=20)
        self.charts_column = ft.Column(spacing=20)
        
        # DatePickers para rango de fechas personalizado
        self.start_date_picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=lambda e: self.handle_date_change(e, is_start_date=True)
        )
        
        self.end_date_picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=lambda e: self.handle_date_change(e, is_start_date=False)
        )
        
        # Añadir DatePickers al overlay de la página (se limpian en cleanup)
        self.page.overlay.extend([self.start_date_picker, self.end_date_picker])
        
        # Textos para mostrar las fechas seleccionadas
        self.start_date_text = ft.Text(format_date(self.start_date))
        self.end_date_text = ft.Text(format_date(self.end_date))
        
        # Escuchar cambios de tamaño de pantalla para la responsividad
        self.page.on_resize = self.handle_resize

        # Inicializar el selector de fechas y tipo de reporte
        self.report_selector = self._build_report_selector()

        # Inicializar tablas (ahora como métodos de instancia)
        # Se crean aquí para que sus referencias existan cuando se construya la vista
        self.appointments_table = self._create_appointments_table()
        self.payments_table = self._create_payments_table()
        self.debts_table = self._create_debts_table()

        # Contenedores para las diferentes pestañas
        self.general_report_container = ft.Container(content=ft.Column(), visible=True, expand=True)
        self.payments_report_container = ft.Container(content=ft.Column(), visible=False, expand=True)
        self.debts_report_container = ft.Container(content=ft.Column(), visible=False, expand=True)


    def handle_resize(self, e):
        """Maneja el cambio de tamaño de la pantalla."""
        # Al redimensionar, la vista se actualizará automáticamente si los controles son responsive
        self.page.update()

    def handle_date_change(self, e, is_start_date):
        """Maneja el cambio de fecha en los DatePickers."""
        try:
            if is_start_date:
                if self.start_date_picker.value:
                    self.start_date = self.start_date_picker.value.date()
                    self.start_date_text.value = format_date(self.start_date)
            else:
                if self.end_date_picker.value:
                    self.end_date = self.end_date_picker.value.date()
                    self.end_date_text.value = format_date(self.end_date)
            
            # Asegurarse de que end_date no sea menor que start_date
            if self.end_date < self.start_date:
                self.end_date = self.start_date
                # Sincroniza el DatePicker y el texto para reflejar la corrección
                self.end_date_picker.value = datetime(self.start_date.year, self.start_date.month, self.start_date.day) 
                self.end_date_text.value = format_date(self.start_date)
                show_snackbar(self.page, "La fecha final no puede ser anterior a la inicial.", "warning")
            
            # Al cambiar manualmente las fechas, el tipo de reporte se considera 'custom'
            self.report_type = 'custom' 
            # Actualizar el Dropdown del selector de reportes para reflejar 'Personalizado'
            for control in self.report_selector.controls[0].controls: # Acceder al Dropdown
                if isinstance(control, ft.Dropdown) and control.label == "Tipo de Reporte":
                    control.value = 'custom'
                    control.update()
                    break

            self.load_data() # Recargar datos con el nuevo rango
        except Exception as ex:
            logger.error(f"Error al cambiar fecha: {str(ex)}")
            show_snackbar(self.page, f"Error al cambiar fecha: {str(ex)}", "error")

    def update_date_range(self, init_load=False):
        """
        Actualiza el rango de fechas según el tipo de reporte.
        Agregado 'init_load' para evitar sobreescritura si las fechas vienen de un estado inicial.
        """
        # Solo actualiza si no es la carga inicial o si el tipo de reporte no es 'custom'
        if not init_load and self.report_type != 'custom': 
            today = datetime.now().date()
            
            if self.report_type == 'daily':
                self.start_date = today
                self.end_date = today
            elif self.report_type == 'weekly':
                self.start_date, self.end_date = get_week_range(today)
            elif self.report_type == 'monthly':
                self.start_date = today.replace(day=1)
                self.end_date = get_last_day_of_month(today)
            
            # Sincronizar los DatePickers y Textos
            self.start_date_picker.value = datetime(self.start_date.year, self.start_date.month, self.start_date.day)
            self.end_date_picker.value = datetime(self.end_date.year, self.end_date.month, self.end_date.day)
            self.start_date_text.value = format_date(self.start_date)
            self.end_date_text.value = format_date(self.end_date)
            self.page.update()

    def update_report_type(self, e):
        """Actualiza el tipo de reporte seleccionado y el rango de fechas."""
        self.report_type = e.control.value
        self.update_date_range() # Actualiza el rango de fechas según el tipo
        self.load_data() # Recarga los datos con el nuevo rango

    def load_data(self):
        """Carga todos los datos para los reportes."""
        try:
            self.current_stats = self.load_statistics()
            self.update_stats_row(self.current_stats)
            
            chart_data = self.load_chart_data()
            self.update_charts(chart_data)
            
            self.current_appointments = self.load_recent_appointments()
            self.update_appointments_table(self.current_appointments)
            
            self.current_payments = self.load_payments()
            self.update_payments_table(self.current_payments)
            
            self.current_debts = self.load_debts()
            self.update_debts_table(self.current_debts)
            
            self.page.update()
        except Exception as e:
            logger.error(f"Error al cargar datos: {str(e)}")
            show_snackbar(self.page, f"Error al cargar datos: {str(e)}", "error")

    def load_payments(self):
        """Carga los pagos para mostrar en la tabla."""
        try:
            with get_db() as cursor: # Usar get_db directamente si es un contexto manager
                cursor.execute("""
                    SELECT 
                        p.id,
                        p.payment_date,
                        c.name,
                        p.method,
                        p.amount,
                        p.status,
                        p.invoice_number
                    FROM payments p
                    JOIN clients c ON p.client_id = c.id
                    WHERE p.payment_date BETWEEN %s AND %s
                    ORDER BY p.payment_date DESC
                    LIMIT 100
                """, (self.start_date, self.end_date))
                results = cursor.fetchall()
                logger.info(f"Pagos cargados: {len(results)} registros")
                
                # Convertir Decimal a float al cargar
                return [
                    (
                        row[0], row[1], row[2], row[3], 
                        float(row[4]) if row[4] is not None else 0.0, # Convertir amount a float
                        row[5], row[6]
                    ) for row in results
                ]
        except Exception as e:
            logger.error(f"Error al cargar pagos: {str(e)}")
            return []

    def update_payments_table(self, payments):
        """Actualiza la tabla de pagos con datos financieros."""
        # Colores para el texto de la tabla
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        try:
            self.payments_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(payment[1].strftime("%d/%m/%Y") if payment[1] else "N/A", color=text_color)),
                        ft.DataCell(ft.Text(payment[2] if payment[2] else "N/A", color=text_color)), # client_name
                        ft.DataCell(ft.Text(f"${payment[4]:,.2f}" if payment[4] is not None else "$0.00", color=text_color)), # amount (ya es float)
                        ft.DataCell(ft.Text(payment[3] if payment[3] else "N/A", color=text_color)), # method (index changed from 3 to 2)
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(str(payment[5]).capitalize() if payment[5] else "N/A", color=ft.colors.WHITE), # status
                                padding=5,
                                # Ajustar colores de estado para modo oscuro
                                bgcolor=ft.colors.GREEN_700 if str(payment[5]).lower() == 'completed' else ft.colors.ORANGE_700,
                                border_radius=5
                            )
                        ),
                        ft.DataCell(ft.Text(payment[6] if payment[6] else "N/A", color=text_color)) # invoice_number
                    ]
                ) for payment in payments
            ]
            
            # Solo actualizar si la tabla ya está en el árbol de controles
            if hasattr(self.payments_table, 'page') and self.payments_table.page:
                self.payments_table.update()
        except Exception as e:
            logger.error(f"Error al actualizar tabla de pagos: {str(e)}")
            show_snackbar(self.page, f"Error al mostrar pagos: {str(e)}", "error")

    def load_debts(self):
        """Carga las deudas para mostrar en la tabla."""
        try:
            with get_db() as cursor:
                cursor.execute("""
                    SELECT 
                        d.id,
                        c.name,
                        d.created_at,
                        d.amount,
                        d.description,
                        d.status,
                        d.due_date,
                        d.paid_amount,
                        d.quote_id -- Ahora cargamos el quote_id
                    FROM debts d
                    JOIN clients c ON d.client_id = c.id
                    WHERE d.created_at BETWEEN %s AND %s
                    ORDER BY d.created_at DESC
                    LIMIT 100
                """, (self.start_date, self.end_date))
                results = cursor.fetchall()
                logger.info(f"Deudas cargadas: {len(results)} registros")

                # Convertir Decimal a float al cargar
                return [
                    (
                        row[0], row[1], row[2], 
                        float(row[3]) if row[3] is not None else 0.0, # amount a float
                        row[4], row[5], row[6], 
                        float(row[7]) if row[7] is not None else 0.0, # paid_amount a float
                        row[8] # quote_id
                    ) for row in results
                ]
        except Exception as e:
            logger.error(f"Error al cargar deudas: {str(e)}")
            return []

    def update_debts_table(self, debts):
        """Actualiza la tabla de deudas."""
        # Colores para el texto de la tabla
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.debts_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(debt[1], color=text_color)), # client_name
                    ft.DataCell(ft.Text(debt[2].strftime("%d/%m/%Y"), color=text_color)), # created_at
                    ft.DataCell(ft.Text(f"${debt[3]:,.2f}", color=text_color)), # amount (ya es float)
                    ft.DataCell(ft.Text(f"${debt[7]:,.2f}", color=text_color)), # paid_amount (ya es float)
                    ft.DataCell(ft.Text(f"${debt[3] - debt[7]:,.2f}", color=text_color)), # remaining amount (ambos ya son float)
                    ft.DataCell(
                        ft.Text(debt[4] or "N/A", color=text_color, selectable=True), # description, make selectable
                        on_tap=lambda e, debt_id=debt[0], quote_id=debt[8]: self._show_debt_treatments_dialog(debt_id, quote_id)
                    ),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(str(debt[5]).capitalize() if debt[5] else "N/A", color=ft.colors.WHITE), # status
                            padding=5,
                            bgcolor=ft.colors.GREEN_700 if str(debt[5]).lower() == 'paid' else ft.colors.ORANGE_700, # Verde si pagada, Naranja si pendiente
                            border_radius=5
                        )
                    ),
                ]
            ) for debt in debts
        ]
        if hasattr(self.debts_table, 'page') and self.debts_table.page:
            self.debts_table.update()
    
    def _show_debt_treatments_dialog(self, debt_id: int, quote_id: int):
        """
        Muestra un diálogo con los tratamientos asociados a una deuda a través de su quote_id.
        """
        dialog_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dialog_content_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        dialog_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800

        treatments_content = []
        if quote_id:
            try:
                with get_db() as cursor:
                    cursor.execute("""
                        SELECT t.name, qt.price_at_quote, t.description, qt.quantity
                        FROM treatments t
                        JOIN quote_treatments qt ON t.id = qt.treatment_id
                        WHERE qt.quote_id = %s
                        ORDER BY t.name
                    """, (quote_id,))
                    treatments = cursor.fetchall()

                if treatments:
                    for name, price_at_quote, description, quantity in treatments:
                        treatments_content.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"• {name} (x{quantity})", weight="bold", color=dialog_content_color),
                                    ft.Text(f"  Precio en presupuesto: ${float(price_at_quote):,.2f}", color=dialog_content_color),
                                    ft.Text(f"  Descripción: {description or 'N/A'}", color=dialog_content_color, size=12),
                                ], spacing=2),
                                padding=ft.padding.symmetric(vertical=5),
                                border_radius=5,
                                border=ft.border.only(bottom=ft.border.BorderSide(0.5, ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600))
                            )
                        )
                else:
                    treatments_content.append(ft.Text("No hay tratamientos asociados a este presupuesto.", color=dialog_content_color))

            except Exception as e:
                logger.error(f"Error al cargar tratamientos para la deuda {debt_id} (presupuesto {quote_id}): {e}")
                treatments_content.append(ft.Text(f"Error al cargar tratamientos: {str(e)}", color=ft.colors.RED_500))
        else:
            treatments_content.append(ft.Text("Esta deuda no está directamente asociada a un presupuesto con tratamientos.", color=dialog_content_color))

        self.page.dialog = ft.AlertDialog(
            modal=True,
            bgcolor=dialog_bgcolor,
            title=ft.Text(f"Tratamientos de la Deuda #{debt_id}", color=dialog_title_color),
            content=ft.Column(treatments_content, scroll=ft.ScrollMode.AUTO, height=300),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._close_dialog(e)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog)
        self.page.update()

    def _close_dialog(self, e):
        """Cierra el diálogo actual."""
        self.page.dialog.open = False
        self.page.update()
    
    def load_statistics(self):
        """Carga estadísticas generales desde la base de datos."""
        stats = {}
        
        with get_db() as cursor:
            # Estadísticas de citas
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                FROM appointments 
                WHERE date BETWEEN %s AND %s
            """, (self.start_date, self.end_date))
            appointment_stats = cursor.fetchone()
            stats.update({
                'total_appointments': int(appointment_stats[0]) if appointment_stats and appointment_stats[0] is not None else 0,
                'completed_appointments': int(appointment_stats[1]) if appointment_stats and appointment_stats[1] is not None else 0,
                'cancelled_appointments': int(appointment_stats[2]) if appointment_stats and appointment_stats[2] is not None else 0,
                'pending_appointments': int(appointment_stats[3]) if appointment_stats and appointment_stats[3] is not None else 0
            })
            
            # Estadísticas financieras (pagos completados)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount), 0) as total_revenue,
                    COUNT(*) as total_payments
                FROM payments
                WHERE payment_date BETWEEN %s AND %s
            """, (self.start_date, self.end_date))
            payment_stats = cursor.fetchone()
            stats.update({
                'total_revenue': float(payment_stats[0]) if payment_stats and payment_stats[0] is not None else 0.0,
                'total_payments': int(payment_stats[1]) if payment_stats and payment_stats[1] is not None else 0
            })

            # Monto total de deudas pendientes (todas, no solo vencidas)
            cursor.execute("""
                SELECT COALESCE(SUM(amount - paid_amount), 0) as total_pending_debts_amount
                FROM debts
                WHERE status = 'pending'
                AND created_at BETWEEN %s AND %s
            """, (self.start_date, self.end_date))
            total_pending_debts_stats = cursor.fetchone()
            stats.update({
                'total_pending_debts_amount': float(total_pending_debts_stats[0]) if total_pending_debts_stats and total_pending_debts_stats[0] is not None else 0.0
            })

            # Monto total de deudas vencidas (solo las que están pending Y due_date < CURRENT_DATE)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(amount - paid_amount), 0) as overdue_debts_amount,
                    COUNT(*) as overdue_count
                FROM debts
                WHERE status = 'pending'
                AND due_date < CURRENT_DATE
                AND created_at BETWEEN %s AND %s
            """, (self.start_date, self.end_date))
            overdue_stats = cursor.fetchone()
            stats.update({
                'overdue_debts_amount': float(overdue_stats[0]) if overdue_stats and overdue_stats[0] is not None else 0.0,
                'overdue_count': int(overdue_stats[1]) if overdue_stats and overdue_stats[1] is not None else 0
            })
            
            # Métodos de pago más usados
            cursor.execute("""
                SELECT method, COUNT(*) as count
                FROM payments
                WHERE payment_date BETWEEN %s AND %s
                GROUP BY method
                ORDER BY count DESC
                LIMIT 1
            """, (self.start_date, self.end_date))
            popular_method = cursor.fetchone()
            stats['popular_payment_method'] = popular_method[0] if popular_method else "N/A"
            
            # Cantidad total de clientes (todos, no solo nuevos)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM clients 
            """) # No se filtra por fecha para obtener el total general
            total_clients_result = cursor.fetchone() 
            stats['total_clients'] = int(total_clients_result[0]) if total_clients_result and total_clients_result[0] is not None else 0
        
        return stats

    def update_stats_row(self, stats):
        """Actualiza la fila de estadísticas con datos financieros."""
        self.stats_row.controls.clear() # Limpiar antes de añadir nuevos controles
        self.stats_row.controls.extend([
            ft.ResponsiveRow([
                # Ajustar colores de las tarjetas de estadísticas para modo oscuro
                self._build_stat_card("Citas Totales", stats['total_appointments'], 
                                ft.icons.CALENDAR_TODAY, ft.colors.BLUE_400),
                self._build_stat_card("Citas Completadas", stats['completed_appointments'], 
                                ft.icons.CHECK_CIRCLE, ft.colors.GREEN_400),
                self._build_stat_card("Ingresos Total", f"${stats['total_revenue']:,.2f}", 
                                ft.icons.ATTACH_MONEY, ft.colors.PURPLE_400),
                self._build_stat_card("Cantidad de Clientes", stats['total_clients'], # Actualizado aquí
                                ft.icons.PERSON_ADD, ft.colors.ORANGE_400)
            ]),
            
            ft.ResponsiveRow([
                self._build_stat_card("Pagos Registrados", stats['total_payments'], 
                                ft.icons.PAYMENT, ft.colors.TEAL_400),
                self._build_stat_card("Total Deudas Pendientes", f"${stats['total_pending_debts_amount']:,.2f}",
                                ft.icons.RECEIPT_LONG, ft.colors.AMBER_400),
                self._build_stat_card("Monto Deudas Vencidas", f"${stats['overdue_debts_amount']:,.2f}",
                                ft.icons.WARNING, ft.colors.RED_400),
                self._build_stat_card("Deudas Vencidas (Conteo)", stats['overdue_count'],
                                ft.icons.WARNING, ft.colors.DEEP_ORANGE_400)
            ])
        ])
        self.page.update() # Asegurar que la fila de estadísticas se actualice

    def _build_stat_card(self, title: str, value: any, icon: ft.icons, color: str):
        """
        Helper para construir una tarjeta de estadística consistente.
        Los colores de fondo y texto se ajustan según el theme_mode.
        """
        card_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        title_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200
        value_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        return ft.Column([
            ft.Card(
                content=ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(icon, color=color, size=30),
                            ft.Column(
                                [
                                    ft.Text(title, size=14, weight="bold", color=title_color),
                                    ft.Text(str(value), size=24, weight="bold", color=value_color)
                                ],
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                expand=True
                            )
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=15
                    ),
                    padding=15,
                    # Para asegurar que las tarjetas se adapten en pantallas pequeñas,
                    # se elimina el ancho fijo y se confía en el ResponsiveRow
                    # width=250, 
                    height=100,
                    bgcolor=card_bg_color, # Color de fondo del container dentro de la tarjeta
                    border_radius=10 # Bordes más redondeados
                ),
                elevation=2,
                margin=ft.margin.symmetric(vertical=5)
            )
        ], col={"xs": 12, "sm": 6, "md": 3}) # Column para ResponsiveRow

    def load_chart_data(self):
        """Carga datos para gráficos incluyendo información financiera."""
        chart_data = {}
        
        with get_db() as cursor:
            # Datos de citas por estado (Pie Chart)
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM appointments 
                WHERE date BETWEEN %s AND %s
                GROUP BY status
            """, (self.start_date, self.end_date))
            chart_data['appointments_by_status'] = {
                status: int(count) if count is not None else 0 
                for status, count in cursor.fetchall()
            }
            
            # Datos de ingresos por método de pago (Pie Chart)
            cursor.execute("""
                SELECT method, SUM(amount)
                FROM payments
                WHERE payment_date BETWEEN %s AND %s
                GROUP BY method
            """, (self.start_date, self.end_date))
            chart_data['revenue_by_method'] = {
                method: float(amount) if amount is not None else 0.0
                for method, amount in cursor.fetchall()
            }
            
            # Datos de deudas por estado (Pie Chart - Distinción entre pendientes y vencidas)
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN status = 'pending' AND due_date < CURRENT_DATE THEN 'Vencidas'
                        WHEN status = 'pending' THEN 'Pendientes'
                        ELSE 'Pagadas'
                    END as status_category,
                    COALESCE(
                        CASE
                            WHEN status = 'pending' THEN SUM(amount - paid_amount)
                            WHEN status = 'paid' THEN SUM(amount)
                            ELSE 0
                        END, 0
                    ) as total_amount
                FROM debts
                WHERE created_at BETWEEN %s AND %s
                GROUP BY status_category, status
            """, (self.start_date, self.end_date))
            chart_data['debts_by_status'] = {
                category: float(amount) if amount is not None else 0.0
                for category, amount in cursor.fetchall()
            }
            
            # Datos temporales de ingresos (Bar Chart)
            if self.report_type == 'daily':
                cursor.execute("""
                    SELECT DATE(payment_date), SUM(amount)
                    FROM payments
                    WHERE payment_date BETWEEN %s AND %s
                    GROUP BY DATE(payment_date)
                    ORDER BY DATE(payment_date)
                """, (self.start_date, self.end_date))
                chart_data['revenue_over_time'] = [(date, float(amount) if amount is not None else 0.0) for date, amount in cursor.fetchall()]
            elif self.report_type == 'weekly':
                cursor.execute("""
                    SELECT EXTRACT(YEAR FROM payment_date)::int, 
                        EXTRACT(WEEK FROM payment_date)::int, 
                        SUM(amount)
                    FROM payments
                    WHERE payment_date BETWEEN %s AND %s
                    GROUP BY EXTRACT(YEAR FROM payment_date), EXTRACT(WEEK FROM payment_date)
                    ORDER BY EXTRACT(YEAR FROM payment_date), EXTRACT(WEEK FROM payment_date)
                """, (self.start_date, self.end_date))
                chart_data['revenue_over_time'] = [
                    (f"Semana {int(week)}", float(amount) if amount is not None else 0.0) for year, week, amount in cursor.fetchall()
                ]
            else:  # monthly (o cualquier otro por defecto a mensual)
                cursor.execute("""
                    SELECT EXTRACT(YEAR FROM payment_date)::int, 
                        EXTRACT(MONTH FROM payment_date)::int, 
                        SUM(amount)
                    FROM payments
                    WHERE payment_date BETWEEN %s AND %s
                    GROUP BY EXTRACT(YEAR FROM payment_date), EXTRACT(MONTH FROM payment_date)
                    ORDER BY EXTRACT(YEAR FROM payment_date), EXTRACT(MONTH FROM payment_date)
                """, (self.start_date, self.end_date))
                chart_data['revenue_over_time'] = [
                    (get_month_name(int(month)), float(amount) if amount is not None else 0.0) for year, month, amount in cursor.fetchall()
                ]
        
        return chart_data

    def update_charts(self, chart_data):
        """Actualiza los gráficos con datos financieros."""
        self.charts_column.controls.clear()

        # Gráfico de ingresos por período (Bar Chart)
        revenue_over_time_chart = self._build_bar_chart(
            title="Ingresos por Período",
            data=chart_data.get('revenue_over_time', []),
            x_label="Período",
            y_label="Monto ($)",
            color=ft.colors.GREEN_400
        )
        
        # Gráfico de distribución de métodos de pago (Pie Chart)
        payment_methods_chart = self._build_pie_chart(
            title="Ingresos por Método de Pago",
            data=chart_data.get('revenue_by_method', {}),
            colors={
                'Efectivo': ft.colors.GREEN_500,
                'Tarjeta': ft.colors.BLUE_500,
                'Transferencia': ft.colors.PURPLE_500,
                'Otro': ft.colors.ORANGE_500
            }
        )
        
        # Gráfico de estado de deudas (Pie Chart)
        debts_status_chart = self._build_pie_chart(
            title="Distribución de Deudas",
            data=chart_data.get('debts_by_status', {}),
            colors={
                'Vencidas': ft.colors.RED_500,
                'Pendientes': ft.colors.AMBER_500,
                'Pagadas': ft.colors.GREEN_500
            }
        )
        
        # Gráfico de citas por estado (Pie Chart)
        appointments_status_chart = self._build_pie_chart(
            title="Citas por Estado",
            data=chart_data.get('appointments_by_status', {}),
            colors={
                'completed': ft.colors.GREEN_500,
                'pending': ft.colors.ORANGE_500,
                'cancelled': ft.colors.RED_500
            }
        )

        # Colores para el contenedor de los gráficos
        chart_container_border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        chart_container_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        self.charts_column.controls.extend([
            ft.ResponsiveRow([
                ft.Column([
                    ft.Container(
                        content=revenue_over_time_chart,
                        padding=10,
                        border=ft.border.all(1, chart_container_border_color),
                        border_radius=5,
                        expand=True,
                        height=300,
                        bgcolor=chart_container_bgcolor
                    )
                ], col={"sm": 12, "lg": 6}),
                ft.Column([
                    ft.Container(
                        content=appointments_status_chart,
                        padding=10,
                        border=ft.border.all(1, chart_container_border_color),
                        border_radius=5,
                        expand=True,
                        height=300,
                        bgcolor=chart_container_bgcolor
                    )
                ], col={"sm": 12, "lg": 6})
            ]),
            ft.ResponsiveRow([
                ft.Column([
                    ft.Container(
                        content=payment_methods_chart,
                        padding=10,
                        border=ft.border.all(1, chart_container_border_color),
                        border_radius=5,
                        expand=True,
                        height=300,
                        bgcolor=chart_container_bgcolor
                    )
                ], col={"sm": 12, "lg": 6}),
                 ft.Column([
                    ft.Container(
                        content=debts_status_chart,
                        padding=10,
                        border=ft.border.all(1, chart_container_border_color),
                        border_radius=5,
                        expand=True,
                        height=300,
                        bgcolor=chart_container_bgcolor
                    )
                ], col={"sm": 12, "lg": 6})
            ])
        ])
        self.page.update()

    def _build_bar_chart(self, title: str, data: list, x_label: str, y_label: str, color: str = None):
        """Construye un gráfico de barras mejorado."""
        chart_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        axis_label_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        grid_line_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_500
        tooltip_bgcolor = ft.colors.with_opacity(0.8, ft.colors.GREY_800) if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.with_opacity(0.9, ft.colors.BLUE_GREY_900)
        border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600

        if not data:
            return ft.Column([
                ft.Text(title, size=16, weight="bold", color=chart_title_color), 
                ft.Text("No hay datos disponibles para este período.", italic=True, color=chart_title_color)
            ], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        processed_data = []
        for item in data:
            if isinstance(item, tuple) and len(item) == 2:
                processed_data.append((str(item[0]), float(item[1])))
            else:
                processed_data.append((str(item), float(item))) 

        bars = [
            ft.BarChartGroup(
                x=i,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=value,
                        width=20,
                        color=color or (ft.colors.BLUE_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_600),
                        tooltip=f"{label}: ${value:,.2f}" if "Monto" in y_label else f"{label}: {value}",
                        border_radius=4,
                    )
                ],
            )
            for i, (label, value) in enumerate(processed_data)
        ]
        
        max_y_val = max(value for _, value in processed_data) if processed_data else 100
        
        return ft.Column([
            ft.Text(title, size=16, weight="bold", color=chart_title_color),
            ft.BarChart(
                bar_groups=bars,
                border=ft.border.all(1, border_color),
                left_axis=ft.ChartAxis(
                    labels_size=40,
                    title=ft.Text(y_label, size=12, color=axis_label_color),
                    labels=[
                        ft.ChartAxisLabel(
                            value=i, 
                            label=ft.Text(f"${val:,.0f}", color=axis_label_color)
                        ) for i, val in enumerate(range(0, int(max_y_val * 1.2) + 1, max(1, int(max_y_val * 0.2 // 100) * 100)))
                    ]
                ),
                bottom_axis=ft.ChartAxis(
                    labels=[
                        ft.ChartAxisLabel(
                            value=i,
                            label=ft.Text(label, size=10, color=axis_label_color)
                        )
                        for i, (label, _) in enumerate(processed_data)
                    ],
                    labels_size=40,
                    title=ft.Text(x_label, size=12, color=axis_label_color)
                ),
                horizontal_grid_lines=ft.ChartGridLines(
                    color=grid_line_color, width=1, dash_pattern=[3, 3]
                ),
                tooltip_bgcolor=tooltip_bgcolor,
                interactive=True,
                expand=True,
                max_y=max_y_val * 1.2
            ),
        ], spacing=10, expand=True)

    def _build_pie_chart(self, title: str, data: dict, colors: dict = None):
        """Construye un gráfico de pastel mejorado."""
        chart_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        legend_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        if not data or sum(data.values()) == 0:
            return ft.Column([
                ft.Text(title, size=16, weight="bold", color=chart_title_color), 
                ft.Text("No hay datos disponibles para este período.", italic=True, color=chart_title_color)
            ], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        total = sum(data.values())
        
        sections = []
        default_light_colors = [
            ft.colors.BLUE_500, ft.colors.GREEN_500, ft.colors.ORANGE_500,
            ft.colors.PURPLE_500, ft.colors.TEAL_500, ft.colors.RED_500
        ]
        default_dark_colors = [
            ft.colors.BLUE_300, ft.colors.GREEN_300, ft.colors.ORANGE_300,
            ft.colors.PURPLE_300, ft.colors.TEAL_300, ft.colors.RED_300
        ]
        
        current_default_colors = default_dark_colors if self.page.theme_mode == ft.ThemeMode.DARK else default_light_colors
        color_index = 0
        
        for key, value in data.items():
            percentage = value / total * 100
            
            section_color = colors.get(key, current_default_colors[color_index % len(current_default_colors)])
            color_index += 1

            sections.append(
                ft.PieChartSection(
                    value=value,
                    title=f"{percentage:.1f}%",
                    color=section_color,
                    radius=80,
                    title_style=ft.TextStyle(
                        size=14,
                        color=ft.colors.WHITE, 
                        weight="bold"
                    ),
                )
            )
        
        return ft.Column([
            ft.Text(title, size=16, weight="bold", color=chart_title_color),
            ft.PieChart(
                sections=sections,
                sections_space=1,
                center_space_radius=0, 
                expand=True,
            ),
            ft.Column( 
                controls=[
                    ft.Row([
                        ft.Container(
                            width=16,
                            height=16,
                            bgcolor=colors.get(key, current_default_colors[i % len(current_default_colors)]), 
                            border_radius=8,
                            margin=ft.margin.only(right=5)
                        ),
                        ft.Text(f"{key}: {value} (${value:,.2f})" if "Ingresos" in title or "Deudas" in title else f"{key}: {value}",
                                color=legend_text_color),
                    ])
                    for i, (key, value) in enumerate(data.items())
                ],
                wrap=True,
                spacing=5
            )
        ], spacing=10, expand=True)

    def load_recent_appointments(self):
        """Carga las citas para mostrar en la tabla."""
        try:
            with get_db() as cursor:
                cursor.execute("""
                    SELECT a.id, c.name, a.date, a.time, a.status, 
                        COALESCE(SUM(t.price), 0) as total_treatments_amount
                    FROM appointments a
                    JOIN clients c ON a.client_id = c.id
                    LEFT JOIN appointment_treatments at ON a.id = at.appointment_id
                    LEFT JOIN treatments t ON at.treatment_id = t.id
                    WHERE a.date BETWEEN %s AND %s
                    GROUP BY a.id, c.name, a.date, a.time, a.status
                    ORDER BY a.date DESC, a.time DESC
                    LIMIT 50
                """, (self.start_date, self.end_date))
                results = cursor.fetchall()
                logger.info(f"Citas cargadas para tabla: {len(results)} registros")
                
                # Convertir Decimal a float al cargar
                return [
                    (
                        row[0], row[1], row[2], row[3], row[4], 
                        float(row[5]) if row[5] is not None else 0.0
                    ) for row in results
                ]
        except Exception as e:
            logger.error(f"Error al cargar citas recientes para tabla: {str(e)}")
            return []

    def update_appointments_table(self, appointments):
        """Actualiza la tabla de citas."""
        # Colores para el texto de la tabla
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.appointments_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(appt[2].strftime("%d/%m/%Y"), color=text_color)), # date
                    ft.DataCell(ft.Text(appt[1], color=text_color)), # client_name
                    ft.DataCell(ft.Text(appt[3].strftime("%H:%M"), color=text_color)), # time
                    ft.DataCell(
                        ft.Text(appt[4].capitalize(), color=text_color), # status
                        on_tap=lambda e, a_id=appt[0]: self.show_appointment_detail(a_id)
                    ),
                    ft.DataCell(ft.Text(f"${appt[5]:,.2f}", color=text_color)) # total_treatments_amount (ya es float)
                ]
            ) for appt in appointments
        ]
        if hasattr(self.appointments_table, 'page') and self.appointments_table.page:
            self.appointments_table.update()

    def show_appointment_detail(self, appointment_id):
        """Muestra el detalle de una cita específica."""
        show_snackbar(self.page, f"Ver detalle de cita ID: {appointment_id}", "info")

    async def export_to_pdf(self):
        """Exporta el reporte actual a PDF."""
        # Recopilar todos los datos necesarios para el PDF
        self._temp_report_data = {
            'stats': self.current_stats,
            'appointments': self.current_appointments,
            'payments': self.current_payments,
            'debts': self.current_debts
        }
        
        # Abrir el diálogo para guardar el archivo
        # Añadir un pequeño retraso para permitir que Flet's internal mechanisms se sincronicen
        await asyncio.sleep(0.1) 
        if self.file_picker and hasattr(self.file_picker, 'save_file') and callable(self.file_picker.save_file):
            self.file_picker.save_file(
                file_name=f"reporte_odontologico_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
                allowed_extensions=["pdf"]
            )
            self.page.update() # Asegurarse de que la UI se actualice después de abrir el diálogo
        else:
            logger.error(f"Error: self.file_picker o su método save_file no está disponible. self.file_picker: {self.file_picker}")
            show_snackbar(self.page, "Error interno: El sistema de guardado de archivos no está listo.", "error")

    async def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Maneja el resultado del diálogo de FilePicker (la ruta seleccionada)."""
        logger.info(f"Resultado del FilePicker: {e.path}")
        if e.path:
            if self._temp_report_data:
                try:
                    generator = ReportGenerator()
                    success, message = generator.generate_report_pdf(e.path, self._temp_report_data, self.start_date, self.end_date)
                    show_snackbar(self.page, message, "success" if success else "error")
                    self._temp_report_data = None # Limpiar datos temporales
                except Exception as ex:
                    logger.error(f"Error al generar PDF en _on_file_picker_result: {ex}")
                    show_snackbar(self.page, f"Error al generar PDF: {ex}", "error")
            else:
                show_snackbar(self.page, "Error: Datos del reporte no disponibles para generar el PDF.", "error")
        else:
            show_snackbar(self.page, "Operación de guardado de PDF cancelada.", "info")


    def _create_appointments_table(self):
        """
        Crea un widget DataTable para mostrar información de citas.
        Los colores se ajustan según el theme_mode.
        """
        header_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        heading_row_bgcolor = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        line_color = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha", color=header_text_color)),
                ft.DataColumn(ft.Text("Cliente", color=header_text_color)),
                ft.DataColumn(ft.Text("Hora", color=header_text_color)),
                ft.DataColumn(ft.Text("Estado", color=header_text_color)),
                ft.DataColumn(ft.Text("Monto Tratamientos", color=header_text_color), numeric=True)
            ],
            rows=[],
            border=ft.border.all(1, border_color),
            border_radius=5,
            heading_row_color=heading_row_bgcolor,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, line_color),
            vertical_lines=ft.border.BorderSide(1, line_color),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )

    def _create_payments_table(self):
        """
        Crea un widget DataTable para mostrar información de pagos.
        Los colores se ajustan según el theme_mode.
        """
        header_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        heading_row_bgcolor = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        line_color = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha Pago", color=header_text_color)),
                ft.DataColumn(ft.Text("Cliente", color=header_text_color)),
                ft.DataColumn(ft.Text("Método", color=header_text_color)),
                ft.DataColumn(ft.Text("Monto", color=header_text_color), numeric=True),
                ft.DataColumn(ft.Text("Estado", color=header_text_color)),
                ft.DataColumn(ft.Text("Factura", color=header_text_color))
            ],
            rows=[],
            border=ft.border.all(1, border_color),
            border_radius=5,
            heading_row_color=heading_row_bgcolor,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, line_color),
            vertical_lines=ft.border.BorderSide(1, line_color),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )

    def _create_debts_table(self):
        """
        Crea un widget DataTable para mostrar información de deudas.
        Los colores se ajustan según el theme_mode.
        Se han eliminado las columnas "Fecha Vencimiento" y "Días Vencida".
        La columna "Descripción" ahora tiene más espacio y el texto es seleccionable
        para mejorar la visualización de datos largos.
        """
        header_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        heading_row_bgcolor = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        line_color = ft.colors.GREY_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700


        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cliente", color=header_text_color)),
                ft.DataColumn(ft.Text("Fecha Creación", color=header_text_color)),
                ft.DataColumn(ft.Text("Monto Total", color=header_text_color), numeric=True),
                ft.DataColumn(ft.Text("Monto Pagado", color=header_text_color), numeric=True),
                ft.DataColumn(ft.Text("Monto Restante", color=header_text_color), numeric=True),
                ft.DataColumn(
                    ft.Text("Descripción", color=header_text_color)
                ),
                ft.DataColumn(ft.Text("Estado", color=header_text_color)),
            ],
            rows=[],
            border=ft.border.all(1, border_color),
            border_radius=5,
            heading_row_color=heading_row_bgcolor,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=100,
            horizontal_lines=ft.border.BorderSide(1, line_color),
            vertical_lines=ft.border.BorderSide(1, line_color),
            column_spacing=10,
            divider_thickness=1,
            show_checkbox_column=True,
            expand=True
        )
    
    def cleanup(self):
        """Limpia recursos antes de salir de la vista."""
        try:
            if self.start_date_picker in self.page.overlay:
                self.page.overlay.remove(self.start_date_picker)
            if self.end_date_picker in self.page.overlay:
                self.page.overlay.remove(self.end_date_picker)
            # Asegurarse de remover el FilePicker también
            if self.file_picker in self.page.overlay:
                self.page.overlay.remove(self.file_picker)
            self.page.update()
        except Exception as e:
            logger.error(f"Error en cleanup: {str(e)}")
    
    def _build_appbar(self):
        """Construye la barra de aplicación responsive para la vista de reportes."""
        appbar_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        appbar_text_color = ft.colors.WHITE

        return ft.AppBar(
            title=ft.Text("Reportes Financieros", weight=ft.FontWeight.BOLD, color=appbar_text_color),
            center_title=False,
            bgcolor=appbar_bgcolor,
            automatically_imply_leading=False, 
            leading=ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                tooltip="Volver al Dashboard",
                on_click=lambda _: self.page.go("/dashboard"),
                icon_color=appbar_text_color
            )
        )

    def build_view(self):
        """Construye y devuelve la vista completa de reportes."""
        # Limpiar overlays existentes para evitar duplicados al reconstruir la vista
        if self.start_date_picker in self.page.overlay:
            self.page.overlay.remove(self.start_date_picker)
        if self.end_date_picker in self.page.overlay:
            self.page.overlay.remove(self.end_date_picker)
        if self.file_picker in self.page.overlay:
            self.page.overlay.remove(self.file_picker)
        
        # Volver a agregar los datepickers y el filepicker
        self.page.overlay.extend([self.start_date_picker, self.end_date_picker, self.file_picker])

        # Colores para el contenido principal
        main_content_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Resumen General", icon=ft.icons.DASHBOARD),
                ft.Tab(text="Pagos", icon=ft.icons.PAYMENT),
                ft.Tab(text="Deudas", icon=ft.icons.MONEY_OFF),
            ],
            expand=1,
            on_change=self._handle_tab_change,
        )
        
        # Asignar contenido a los contenedores de las pestañas
        self.general_report_container.content = self._build_general_report_content()
        self.payments_report_container.content = self._build_payments_report_content()
        self.debts_report_container.content = self._build_debts_report_content()


        content_with_padding = ft.Container(
            content=ft.Column(
                controls=[
                    self.report_selector,
                    tabs,
                    self.general_report_container,
                    self.payments_report_container,
                    self.debts_report_container,
                    # Nuevo contenedor para el botón Generar PDF al final de la página
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.ElevatedButton(
                                    text="Generar PDF del Reporte",
                                    icon=ft.icons.PICTURE_AS_PDF,
                                    on_click=lambda e: self.page.run_task(self.export_to_pdf),
                                    height=50,
                                    width=250,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.colors.BLUE_700,
                                        color=ft.colors.WHITE,
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                                        elevation=5,
                                        animation_duration=300
                                    )
                                )
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        padding=ft.padding.symmetric(vertical=20),
                        alignment=ft.alignment.center
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=20,
                expand=True,
            ),
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            expand=True,
            bgcolor=main_content_bgcolor
        )
        
        self.load_data() # Cargar datos después de que la vista esté construida y los controles estén inicializados
        
        return ft.View(
            "/reports",
            controls=[
                self._build_appbar(),
                content_with_padding
            ],
            padding=0
        )

    def _handle_tab_change(self, e):
        """Maneja el cambio de pestañas para mostrar el reporte correcto."""
        self.general_report_container.visible = False
        self.payments_report_container.visible = False
        self.debts_report_container.visible = False

        if e.control.selected_index == 0:
            self.general_report_container.visible = True
        elif e.control.selected_index == 1:
            self.payments_report_container.visible = True
        elif e.control.selected_index == 2:
            self.debts_report_container.visible = True
            
        self.page.update()

    def _build_general_report_content(self):
        """Construye el contenido del reporte general."""
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        divider_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        table_border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        table_container_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        # Al construir las tablas aquí, se re-crean y se asegura que tomen el tema actual
        self.appointments_table = self._create_appointments_table()
        # Las tablas se actualizarán con datos al llamar a load_data() en build_view
        
        return ft.Column([
            ft.Text("Resumen Estadístico", size=20, weight="bold", color=section_title_color),
            self.stats_row, 
            ft.Divider(color=divider_color),
            ft.Text("Visualización de Datos", size=20, weight="bold", color=section_title_color),
            self.charts_column,
            ft.Divider(color=divider_color),
            ft.Text("Detalle de Citas Recientes", size=20, weight="bold", color=section_title_color),
            ft.Container(
                content=self.appointments_table,
                border=ft.border.all(1, table_border_color),
                border_radius=5,
                height=300,
                expand=True,
                bgcolor=table_container_bgcolor
            )
        ], spacing=15, expand=True)

    def _build_payments_report_content(self):
        """Construye el contenido del reporte de pagos."""
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        table_border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        table_container_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        # Al construir las tablas aquí, se re-crean y se asegura que tomen el tema actual
        self.payments_table = self._create_payments_table()

        return ft.Column([
            ft.Text("Reporte de Pagos", size=20, weight="bold", color=section_title_color),
            ft.Container(
                content=ft.Column([  # Envuelve DataTable en un Column para manejar el scroll
                    self.payments_table,
                ], scroll=ft.ScrollMode.AUTO, expand=True), # El scroll va en Column
                border=ft.border.all(1, table_border_color),
                border_radius=5,
                height=500,
                expand=True,
                bgcolor=table_container_bgcolor
            )
        ], spacing=15, expand=True)

    def _build_debts_report_content(self):
        """Construye el contenido del reporte de deudas."""
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        table_border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        table_container_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700

        # Al construir las tablas aquí, se re-crean y se asegura que tomen el tema actual
        self.debts_table = self._create_debts_table()

        return ft.Column([
            ft.Text("Reporte de Deudas", size=20, weight="bold", color=section_title_color),
            ft.Container(
                content=ft.Column([ # Envuelve DataTable en un Column para manejar el scroll
                    self.debts_table,
                ], scroll=ft.ScrollMode.AUTO, expand=True), # El scroll va en Column
                border=ft.border.all(1, table_border_color),
                border_radius=5,
                height=500,
                expand=True,
                bgcolor=table_container_bgcolor
            )
        ], spacing=15, expand=True)

    def _build_report_selector(self):
        """Construye los controles para seleccionar el tipo de reporte y rango de fechas."""
        # Colores para los elementos del selector de reportes
        dropdown_label_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        text_color_date_label = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        date_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        date_container_bg = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        button_bgcolor = ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800
        button_color = ft.colors.WHITE
        icon_button_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        # Actualiza el color del texto de las fechas al construir los controles
        self.start_date_text.color = date_text_color
        self.end_date_text.color = date_text_color

        return ft.Column(
            controls=[
                ft.ResponsiveRow(
                    controls=[
                        ft.Column([
                            ft.Dropdown(
                                label="Tipo de Reporte",
                                options=[
                                    ft.dropdown.Option("daily", "Diario"),
                                    ft.dropdown.Option("weekly", "Semanal"),
                                    ft.dropdown.Option("monthly", "Mensual"),
                                    ft.dropdown.Option("custom", "Personalizado")
                                ],
                                value=self.report_type,
                                on_change=self.update_report_type,
                                expand=True,
                                label_style=ft.TextStyle(color=dropdown_label_color)
                            )
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.Text("Desde:", size=12, color=text_color_date_label),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Seleccionar",
                                    icon=ft.icons.CALENDAR_TODAY,
                                    on_click=lambda e: self.page.open(self.start_date_picker),
                                    height=40,
                                    expand=True,
                                    style=ft.ButtonStyle(bgcolor=button_bgcolor, color=button_color)
                                ),
                                ft.Container(
                                    content=self.start_date_text,
                                    padding=10,
                                    bgcolor=date_container_bg,
                                    border_radius=5,
                                    expand=True
                                )
                            ])
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.Text("Hasta:", size=12, color=text_color_date_label),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Seleccionar",
                                    icon=ft.icons.CALENDAR_TODAY,
                                    on_click=lambda e: self.page.open(self.end_date_picker),
                                    height=40,
                                    expand=True,
                                    style=ft.ButtonStyle(bgcolor=button_bgcolor, color=button_color)
                                ),
                                ft.Container(
                                    content=self.end_date_text,
                                    padding=10,
                                    bgcolor=date_container_bg,
                                    border_radius=5,
                                    expand=True
                                )
                            ])
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.IconButton(
                                icon=ft.icons.REFRESH,
                                tooltip="Actualizar reporte",
                                on_click=lambda e: self.load_data(),
                                height=40,
                                width=40,
                                icon_color=icon_button_color
                            )
                        ], col={"sm": 12, "md": 6, "lg": 3}, 
                          alignment=ft.MainAxisAlignment.CENTER)
                    ],
                    spacing=10,
                    run_spacing=10
                )
            ],
            spacing=10
        )


def reports_view(page: ft.Page):
    """Función de fábrica para crear la vista de reportes."""
    view = ReportsView(page)
    
    def on_close(e):
        view.cleanup()
        page.go(e.route)
    
    return view.build_view()

