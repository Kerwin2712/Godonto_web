import flet as ft
from datetime import datetime, timedelta
from core.database import get_db, Database
from utils.date_utils import (
    format_date,
    get_month_name,
    get_week_range,
    get_last_day_of_month
)
from utils.widgets import (
    build_bar_chart,
    build_pie_chart,
    build_stat_card,
    build_data_table
)
from utils.alerts import show_snackbar
import logging
logger = logging.getLogger(__name__)
#documenta todo el codigo
class ReportsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.report_type = 'monthly'
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=30)
        
        # Componentes UI
        self.stats_row = ft.ResponsiveRow(spacing=20, run_spacing=20)
        self.charts_column = ft.Column(spacing=20)
        
        # Inicializar todas las tablas aquí
        self.appointments_table = self._create_appointments_table()
        self.payments_table = self._create_payments_table()
        self.debts_table = self._create_debts_table()
        
        # DatePickers
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
        
        self.page.overlay.extend([self.start_date_picker, self.end_date_picker])
        
        # Textos para fechas
        self.start_date_text = ft.Text(format_date(self.start_date))
        self.end_date_text = ft.Text(format_date(self.end_date))
        
        # Escuchar cambios de tamaño de pantalla
        self.page.on_resize = self.handle_resize

    def _create_appointments_table(self):
        """
        Crea un widget DataTable para mostrar información de citas.

        La tabla incluye las siguientes columnas:
        - Fecha: La fecha de la cita.
        - Cliente: El nombre del cliente.
        - Hora: La hora de la cita.
        - Estado: El estado de la cita.
        - Monto: El monto asociado con la cita (numérico).

        La tabla está estilizada con bordes, esquinas redondeadas y colores personalizados
        para la fila de encabezado y las líneas. También admite alturas ajustables para las
        filas y espaciado entre columnas.

        Retorna:
            ft.DataTable: Un widget DataTable configurado para mostrar citas.
        """
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Hora")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Monto"), numeric=True)
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )

    def _create_payments_table(self):
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Método")),
                ft.DataColumn(ft.Text("Monto"), numeric=True),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Factura"))
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )

    def _create_debts_table(self):
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Monto"), numeric=True),
                ft.DataColumn(ft.Text("Descripción")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Días Vencida"), numeric=True)
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )
    
    def cleanup(self):
        """Limpia recursos antes de salir de la vista"""
        try:
            if self.start_date_picker in self.page.overlay:
                self.page.overlay.remove(self.start_date_picker)
            if self.end_date_picker in self.page.overlay:
                self.page.overlay.remove(self.end_date_picker)
            self.page.update()
        except Exception as e:
            logger.error(f"Error en cleanup: {str(e)}")
    
    def build_view(self):
        """Construye y devuelve la vista completa de reportes"""
        # Limpiar overlays existentes para evitar duplicados
        if self.start_date_picker in self.page.overlay:
            self.page.overlay.remove(self.start_date_picker)
        if self.end_date_picker in self.page.overlay:
            self.page.overlay.remove(self.end_date_picker)
        
        # Volver a agregar los datepickers
        self.page.overlay.extend([self.start_date_picker, self.end_date_picker])
        
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Resumen General"),
                ft.Tab(text="Pagos"),
                ft.Tab(text="Deudas"),
            ],
            expand=1
        )
        
        content = ft.Column(
            controls=[
                ft.ResponsiveRow([
                    ft.Column([
                        ft.Text("Reportes Financieros", size=24, weight="bold"),
                    ], col={"sm": 12, "md": 6}),
                    ft.Column([
                        ft.ElevatedButton(
                            "Volver al Dashboard",
                            icon=ft.icons.ARROW_BACK,
                            on_click=lambda e: self.page.go("/dashboard"),
                            style=ft.ButtonStyle(
                                padding=20,
                                shape=ft.RoundedRectangleBorder(radius=10)
                            ),
                            expand=True
                        )
                    ], col={"sm": 12, "md": 6}, alignment=ft.MainAxisAlignment.END)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                self.build_report_selector(),
                tabs,
                # Contenedores modificados
                self._create_report_container(self.build_general_report(), True, "general_report"),
                self._create_report_container(self.build_payments_report(), False, "payments_report"),
                self._create_report_container(self.build_debts_report(), False, "debts_report")
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            expand=True
        )
        
        # Manejar cambio de pestañas
        def handle_tab_change(e):
            # Obtener todos los contenedores de reportes
            general_report = next(c for c in content.controls if hasattr(c, 'id') and c.id == "general_report")
            payments_report = next(c for c in content.controls if hasattr(c, 'id') and c.id == "payments_report")
            debts_report = next(c for c in content.controls if hasattr(c, 'id') and c.id == "debts_report")
            
            # Ocultar todos los reportes primero
            general_report.visible = False
            payments_report.visible = False
            debts_report.visible = False
            
            # Mostrar solo el reporte seleccionado
            if e.control.selected_index == 0:
                general_report.visible = True
            elif e.control.selected_index == 1:
                payments_report.visible = True
            elif e.control.selected_index == 2:
                debts_report.visible = True
                
            content.update()
        
        tabs.on_change = handle_tab_change
        
        # Cargar datos después de que la vista esté construida
        self.load_data()
        
        return ft.View(
            "/reports",
            controls=[content],
            padding=20
        )

    def _create_report_container(self, content, visible, id_name):
        """Helper para crear contenedores de reportes con id"""
        container = ft.Container(
            content=content,
            visible=visible
        )
        container.id = id_name
        return container
    
    def build_general_report(self):
        """Construye el reporte general"""
        return ft.Column([
            ft.Text("Resumen Estadístico", size=18, weight="bold"),
            self.stats_row,
            ft.Text("Visualización de Datos", size=18, weight="bold"),
            self.charts_column,
            ft.Text("Detalle de Citas", size=18, weight="bold"),
            ft.Container(
                content=self.appointments_table,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=5,
                height=300,
                expand=True
            )
        ], spacing=15)

    def build_payments_report(self):
        """Construye el reporte de pagos"""
        self.payments_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Método")),
                ft.DataColumn(ft.Text("Monto"), numeric=True),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Factura"))
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )
        
        return ft.Column([
            ft.Text("Reporte de Pagos", size=18, weight="bold"),
            ft.Container(
                content=self.payments_table,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=5,
                height=400,
                expand=True
            )
        ], spacing=15)

    def build_debts_report(self):
        """Construye el reporte de deudas"""
        self.debts_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Cliente")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Monto"), numeric=True),
                ft.DataColumn(ft.Text("Descripción")),
                ft.DataColumn(ft.Text("Estado")),
                ft.DataColumn(ft.Text("Días Vencida"), numeric=True)
            ],
            rows=[],
            border=ft.border.all(1, ft.colors.GREY_300),
            border_radius=5,
            heading_row_color=ft.colors.GREY_200,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=60,
            horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_200),
            column_spacing=20,
            divider_thickness=1,
            show_checkbox_column=False,
            expand=True
        )
        
        return ft.Column([
            ft.Text("Reporte de Deudas", size=18, weight="bold"),
            ft.Container(
                content=self.debts_table,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=5,
                height=400,
                expand=True
            )
        ], spacing=15)
    
    def build_report_selector(self):
        """Construye los controles para seleccionar el tipo de reporte"""
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
                                expand=True
                            )
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.Text("Desde:", size=12),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Seleccionar",
                                    icon=ft.icons.CALENDAR_TODAY,
                                    on_click=lambda e: self.page.open(self.start_date_picker),
                                    height=40,
                                    expand=True
                                ),
                                self.start_date_text
                            ])
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.Text("Hasta:", size=12),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Seleccionar",
                                    icon=ft.icons.CALENDAR_TODAY,
                                    on_click=lambda e: self.page.open(self.end_date_picker),
                                    height=40,
                                    expand=True
                                ),
                                self.end_date_text
                            ])
                        ], col={"sm": 12, "md": 6, "lg": 3}),
                        ft.Column([
                            ft.IconButton(
                                icon=ft.icons.REFRESH,
                                tooltip="Actualizar reporte",
                                on_click=lambda e: self.load_data(),
                                height=40,
                                width=40
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

    def handle_resize(self, e):
        """Maneja el cambio de tamaño de la pantalla"""
        self.page.update()

    def handle_date_change(self, e, is_start_date):
        """Maneja el cambio de fecha en los DatePickers"""
        try:
            if is_start_date:
                if self.start_date_picker.value:
                    self.start_date = self.start_date_picker.value
                    self.start_date_text.value = format_date(self.start_date)
            else:
                if self.end_date_picker.value:
                    self.end_date = self.end_date_picker.value
                    self.end_date_text.value = format_date(self.end_date)
            
            # Asegurarse de que end_date no sea menor que start_date
            if self.end_date < self.start_date:
                self.end_date = self.start_date
                self.end_date_picker.value = self.start_date
                self.end_date_text.value = format_date(self.start_date)
                show_snackbar(self.page, "La fecha final no puede ser anterior a la inicial", "warning")
            
            self.load_data()
        except Exception as ex:
            logger.error(f"Error al cambiar fecha: {str(ex)}")
            show_snackbar(self.page, f"Error al cambiar fecha: {str(ex)}", "error")

    def update_date_range(self):
        """Actualiza el rango de fechas según el tipo de reporte"""
        today = datetime.now().date()
        
        if self.report_type == 'daily':
            self.start_date = today
            self.end_date = today
        elif self.report_type == 'weekly':
            self.start_date, self.end_date = get_week_range(today)
        elif self.report_type == 'monthly':
            self.start_date = today.replace(day=1)
            self.end_date = get_last_day_of_month(today)
        
        self.start_date_picker.value = self.start_date
        self.end_date_picker.value = self.end_date
        self.start_date_text.value = format_date(self.start_date)
        self.end_date_text.value = format_date(self.end_date)
        self.page.update()

    def update_report_type(self, e):
        """Actualiza el tipo de reporte seleccionado"""
        self.report_type = e.control.value
        self.update_date_range()
        self.load_data()

    def load_data(self):
        """Carga todos los datos para los reportes"""
        try:
            stats = self.load_statistics()
            self.update_stats_row(stats)
            
            chart_data = self.load_chart_data()
            self.update_charts(chart_data)
            
            appointments = self.load_recent_appointments()
            self.update_appointments_table(appointments)
            
            # Forzar recarga de pagos
            payments = self.load_payments()
            self.payments_table = self._create_payments_table()  # Recrear la tabla
            self.update_payments_table(payments)
            
            debts = self.load_debts()
            self.update_debts_table(debts)
            
            self.page.update()
        except Exception as e:
            logger.error(f"Error al cargar datos: {str(e)}")
            show_snackbar(self.page, f"Error al cargar datos: {str(e)}", "error")

    def load_payments(self):
        """Carga los pagos para mostrar en la tabla"""
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
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
                        JOIN appointments a ON p.appointment_id = a.id
                        JOIN clients c ON a.client_id = c.id
                        WHERE p.payment_date BETWEEN %s AND %s
                        ORDER BY p.payment_date DESC
                        LIMIT 100
                    """, (self.start_date, self.end_date))
                    results = cursor.fetchall()
                    logger.info(f"Pagos cargados: {len(results)} registros")
                    return results
        except Exception as e:
            logger.error(f"Error al cargar pagos: {str(e)}")
            return []

    def update_payments_table(self, payments):
        """Actualiza la tabla de pagos con datos financieros"""
        try:
            if not hasattr(self, 'payments_table'):
                self.payments_table = self._create_payments_table()
                
            self.payments_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(payment[1].strftime("%d/%m/%Y") if payment[1] else "N/A")),
                        ft.DataCell(ft.Text(payment[2] if payment[2] else "N/A")),
                        ft.DataCell(ft.Text(payment[3] if payment[3] else "N/A")),
                        ft.DataCell(ft.Text(f"${float(payment[4]):,.2f}" if payment[4] else "$0.00")),
                        ft.DataCell(
                            ft.Container(
                                content=ft.Text(str(payment[5]).capitalize() if payment[5] else "N/A"),
                                padding=5,
                                bgcolor=ft.colors.GREEN_100 if str(payment[5]).lower() == 'completed' else ft.colors.ORANGE_100,
                                border_radius=5
                            )
                        ),
                        ft.DataCell(ft.Text(payment[6] if payment[6] else "N/A"))
                    ]
                ) for payment in payments
            ]
            
            if hasattr(self.payments_table, 'page') and self.payments_table.page:
                self.payments_table.update()
        except Exception as e:
            logger.error(f"Error al actualizar tabla de pagos: {str(e)}")
            show_snackbar(self.page, f"Error al mostrar pagos: {str(e)}", "error")

    def load_debts(self):
        """Carga las deudas para mostrar en la tabla"""
        with Database.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        d.id,
                        c.name,
                        d.created_at,
                        d.amount,
                        d.description,
                        d.status,
                        EXTRACT(DAY FROM (CURRENT_DATE - d.created_at))::int as days_overdue
                    FROM debts d
                    JOIN clients c ON d.client_id = c.id
                    WHERE d.created_at BETWEEN %s AND %s
                    ORDER BY days_overdue DESC
                    LIMIT 100
                """, (self.start_date, self.end_date))
                return cursor.fetchall()

    def update_debts_table(self, debts):
        """Actualiza la tabla de deudas"""
        self.debts_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(debt[1])),
                    ft.DataCell(ft.Text(debt[2].strftime("%d/%m/%Y"))),
                    ft.DataCell(ft.Text(f"${debt[3]:,.2f}")),
                    ft.DataCell(ft.Text(debt[4] or "N/A")),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text("Vencida" if debt[5] == 'pending' and debt[6] > 30 else "Pendiente"),
                            padding=5,
                            bgcolor=ft.colors.RED_100 if debt[5] == 'pending' and debt[6] > 30 else ft.colors.ORANGE_100,
                            border_radius=5
                        )
                    ),
                    ft.DataCell(ft.Text(str(debt[6]) if debt[5] == 'pending' else "-"))
                ]
            ) for debt in debts
        ]
    
    def load_statistics(self):
        """Carga estadísticas generales desde la base de datos"""
        stats = {}
        
        with Database.get_connection() as conn:
            with conn.cursor() as cursor:
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
                    'total_appointments': appointment_stats[0] or 0,
                    'completed_appointments': appointment_stats[1] or 0,
                    'cancelled_appointments': appointment_stats[2] or 0,
                    'pending_appointments': appointment_stats[3] or 0
                })
                
                # Estadísticas financieras
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(amount), 0) as total_revenue,
                        COUNT(*) as total_payments,
                        COALESCE(SUM(CASE WHEN status = 'pending' THEN amount ELSE 0 END), 0) as pending_payments
                    FROM payments
                    WHERE payment_date BETWEEN %s AND %s
                """, (self.start_date, self.end_date))
                payment_stats = cursor.fetchone()
                stats.update({
                    'total_revenue': payment_stats[0],
                    'total_payments': payment_stats[1],
                    'pending_payments': payment_stats[2]
                })
                
                # Métodos de pago más usados
                cursor.execute("""
                    SELECT method, COUNT(*) as count
                    FROM payments
                    WHERE status = 'completed'
                    AND payment_date BETWEEN %s AND %s
                    GROUP BY method
                    ORDER BY count DESC
                    LIMIT 1
                """, (self.start_date, self.end_date))
                popular_method = cursor.fetchone()
                stats['popular_payment_method'] = popular_method[0] if popular_method else "N/A"
                
                # Deudas pendientes
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(amount), 0) as total_debts,
                        COUNT(*) as count_debts
                    FROM debts
                    WHERE status = 'pending'
                    AND created_at BETWEEN %s AND %s
                """, (self.start_date, self.end_date))
                debt_stats = cursor.fetchone()
                stats.update({
                    'total_debts': debt_stats[0],
                    'count_debts': debt_stats[1]
                })
                
                # Deudas vencidas
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(amount), 0) as overdue_amount,
                        COUNT(*) as overdue_count
                    FROM debts
                    WHERE status = 'pending'
                    AND created_at < CURRENT_DATE - INTERVAL '30 days'
                    AND created_at BETWEEN %s AND %s
                """, (self.start_date, self.end_date))
                overdue_stats = cursor.fetchone()
                stats.update({
                    'overdue_amount': overdue_stats[0],
                    'overdue_count': overdue_stats[1]
                })
                
                # Clientes nuevos
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM clients 
                    WHERE created_at BETWEEN %s AND %s
                """, (self.start_date, self.end_date))
                stats['new_clients'] = cursor.fetchone()[0]
        
        return stats

    def update_stats_row(self, stats):
        """Actualiza la fila de estadísticas con datos financieros"""
        # Asegurarse de que los valores no sean None
        stats['completed_appointments'] = stats.get('completed_appointments', 0) or 0
        
        self.stats_row.controls = [
            # Primera fila de estadísticas
            ft.ResponsiveRow([
                ft.Column([
                    build_stat_card("Citas Totales", stats['total_appointments'], 
                                ft.icons.CALENDAR_TODAY, ft.colors.BLUE_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Completadas", stats['completed_appointments'], 
                                ft.icons.CHECK_CIRCLE, ft.colors.GREEN_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Ingresos", f"${stats['total_revenue']:,.2f}", 
                                ft.icons.ATTACH_MONEY, ft.colors.PURPLE_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Clientes Nuevos", stats['new_clients'], 
                                ft.icons.PERSON_ADD, ft.colors.ORANGE_400)
                ], col={"xs": 12, "sm": 6, "md": 3})
            ]),
            
            # Segunda fila de estadísticas financieras
            ft.ResponsiveRow([
                ft.Column([
                    build_stat_card("Pagos Registrados", stats['total_payments'], 
                                ft.icons.PAYMENT, ft.colors.TEAL_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Pagos Pendientes", f"${stats['pending_payments']:,.2f}", 
                                ft.icons.PENDING, ft.colors.AMBER_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Deudas Totales", f"${stats['total_debts']:,.2f}", 
                                ft.icons.MONEY_OFF, ft.colors.RED_400)
                ], col={"xs": 12, "sm": 6, "md": 3}),
                ft.Column([
                    build_stat_card("Deudas Vencidas", stats['overdue_count'], 
                                ft.icons.WARNING, ft.colors.DEEP_ORANGE_400)
                ], col={"xs": 12, "sm": 6, "md": 3})
            ])
        ]

    def load_chart_data(self):
        """Carga datos para gráficos incluyendo información financiera"""
        chart_data = {}
        
        with Database.get_connection() as conn:
            with conn.cursor() as cursor:
                # Datos de citas por estado
                cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM appointments 
                    WHERE date BETWEEN %s AND %s
                    GROUP BY status
                """, (self.start_date, self.end_date))
                chart_data['appointments_by_status'] = dict(cursor.fetchall())
                
                # Datos de ingresos por método de pago
                cursor.execute("""
                    SELECT method, SUM(amount)
                    FROM payments
                    WHERE status = 'completed'
                    AND payment_date BETWEEN %s AND %s
                    GROUP BY method
                """, (self.start_date, self.end_date))
                chart_data['revenue_by_method'] = dict(cursor.fetchall())
                
                # Datos de deudas por estado
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN d.created_at < CURRENT_DATE - INTERVAL '30 days' THEN 'Vencidas'
                            ELSE 'Pendientes'
                        END as status,
                        SUM(d.amount) as total_amount
                    FROM debts d
                    WHERE d.status = 'pending'
                    AND d.created_at BETWEEN %s AND %s
                    GROUP BY 
                        CASE 
                            WHEN d.created_at < CURRENT_DATE - INTERVAL '30 days' THEN 'Vencidas'
                            ELSE 'Pendientes'
                        END
                """, (self.start_date, self.end_date))
                chart_data['debts_by_status'] = dict(cursor.fetchall())
                
                # Datos temporales según el tipo de reporte
                if self.report_type == 'daily':
                    cursor.execute("""
                        SELECT DATE(payment_date), SUM(amount)
                        FROM payments
                        WHERE status = 'completed'
                        AND payment_date BETWEEN %s AND %s
                        GROUP BY DATE(payment_date)
                        ORDER BY DATE(payment_date)
                    """, (self.start_date, self.end_date))
                    chart_data['revenue_over_time'] = cursor.fetchall()
                elif self.report_type == 'weekly':
                    cursor.execute("""
                        SELECT EXTRACT(YEAR FROM payment_date)::int, 
                            EXTRACT(WEEK FROM payment_date)::int, 
                            SUM(amount)
                        FROM payments
                        WHERE status = 'completed'
                        AND payment_date BETWEEN %s AND %s
                        GROUP BY EXTRACT(YEAR FROM payment_date), EXTRACT(WEEK FROM payment_date)
                        ORDER BY EXTRACT(YEAR FROM payment_date), EXTRACT(WEEK FROM payment_date)
                    """, (self.start_date, self.end_date))
                    chart_data['revenue_over_time'] = [
                        (f"Semana {int(week)}", float(amount)) for year, week, amount in cursor.fetchall()
                    ]
                else:  # monthly
                    cursor.execute("""
                        SELECT EXTRACT(YEAR FROM payment_date)::int, 
                            EXTRACT(MONTH FROM payment_date)::int, 
                            SUM(amount)
                        FROM payments
                        WHERE status = 'completed'
                        AND payment_date BETWEEN %s AND %s
                        GROUP BY EXTRACT(YEAR FROM payment_date), EXTRACT(MONTH FROM payment_date)
                        ORDER BY EXTRACT(YEAR FROM payment_date), EXTRACT(MONTH FROM payment_date)
                    """, (self.start_date, self.end_date))
                    chart_data['revenue_over_time'] = [
                        (get_month_name(int(month)), float(amount)) for year, month, amount in cursor.fetchall()
                    ]
        
        return chart_data

    def build_bar_chart(title: str, data: list, x_label: str, y_label: str, color: str = None):
        """Construye un gráfico de barras mejorado"""
        bars = [
            ft.BarChartGroup(
                x=i,
                bar_rods=[
                    ft.BarChartRod(
                        from_y=0,
                        to_y=value[1] if isinstance(value, tuple) else value,
                        width=20,
                        color=color or ft.colors.BLUE_400,
                        tooltip=f"${value[1]:,.2f}" if "Ingresos" in title and isinstance(value, tuple) else str(value[1] if isinstance(value, tuple) else value),
                        border_radius=0,
                    )
                ],
                tooltip=value[0] if isinstance(value, tuple) else str(value),
            )
            for i, value in enumerate(data)
        ]
        
        return ft.Column([
            ft.Text(title, size=16, weight="bold"),
            ft.BarChart(
                bar_groups=bars,
                border=ft.border.all(1, ft.colors.GREY_300),
                left_axis=ft.ChartAxis(
                    labels=[
                        ft.ChartAxisLabel(
                            value=0,
                            label=ft.Text("0")
                        ),
                        ft.ChartAxisLabel(
                            value=max(value[1] if isinstance(value, tuple) else value for value in data) * 0.5,
                            label=ft.Text(f"{max(value[1] if isinstance(value, tuple) else value for value in data) * 0.5:,.2f}" if "Ingresos" in title else f"{max(value[1] if isinstance(value, tuple) else value for value in data) * 0.5:,.0f}")
                        ),
                        ft.ChartAxisLabel(
                            value=max(value[1] if isinstance(value, tuple) else value for value in data),
                            label=ft.Text(f"{max(value[1] if isinstance(value, tuple) else value for value in data):,.2f}" if "Ingresos" in title else f"{max(value[1] if isinstance(value, tuple) else value for value in data):,.0f}")
                        )
                    ],
                    labels_size=40
                ),
                bottom_axis=ft.ChartAxis(
                    labels=[
                        ft.ChartAxisLabel(
                            value=i,
                            label=ft.Text(value[0] if isinstance(value, tuple) else str(value), size=12)
                        )
                        for i, value in enumerate(data)
                    ],
                    labels_size=40
                ),
                horizontal_grid_lines=ft.ChartGridLines(
                    color=ft.colors.GREY_300, width=1, dash_pattern=[3, 3]
                ),
                tooltip_bgcolor=ft.colors.with_opacity(0.8, ft.colors.GREY_800),
                interactive=True,
                expand=True
            ),
            ft.Row([
                ft.Text(x_label, size=12, color=ft.colors.GREY),
                ft.Text(y_label, size=12, color=ft.colors.GREY)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ], spacing=10)

    def build_pie_chart(title: str, data: dict, colors: dict = None):
        """Construye un gráfico de pastel mejorado"""
        if not data:
            return ft.Text("No hay datos disponibles", size=14, color=ft.colors.GREY)
        
        total = sum(data.values())
        color_fn = lambda k: colors.get(k, ft.colors.GREY) if colors else ft.colors.BLUE
        is_money = "Ingresos" in title or "Deudas" in title
        
        return ft.Column([
            ft.Text(title, size=16, weight="bold"),
            ft.PieChart(
                sections=[
                    ft.PieChartSection(
                        value=value,
                        title=f"{value/total*100:.1f}%",
                        color=color_fn(key),
                        radius=20,
                        title_style=ft.TextStyle(
                            size=12,
                            color=ft.colors.WHITE,
                            weight="bold"
                        )
                    )
                    for key, value in data.items()
                ],
                sections_space=1,
                center_space_radius=40,
                expand=True
            ),
            ft.Column(
                controls=[
                    ft.Row([
                        ft.Container(
                            width=12,
                            height=12,
                            bgcolor=color_fn(key),
                            border_radius=6,
                            margin=ft.margin.only(right=5)
                        ),
                        ft.Text(f"{key} (${value:,.2f})" if is_money else f"{key} ({value})")
                    ])
                    for key, value in data.items()
                ],
                wrap=True
            )
        ], spacing=10)
    '''
    def build_payments_report(self):
        """Construye el reporte de pagos"""
        return ft.Column([
            ft.Text("Reporte de Pagos", size=18, weight="bold"),
            ft.Container(
                content=self.payments_table,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=5,
                height=400,
                expand=True
            )
        ], spacing=15)

    def build_debts_report(self):
        """Construye el reporte de deudas"""
        return ft.Column([
            ft.Text("Reporte de Deudas", size=18, weight="bold"),
            ft.Container(
                content=self.debts_table,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=5,
                height=400,
                expand=True
            )
        ], spacing=15)'''
    
    def update_charts(self, chart_data):
        """Actualiza los gráficos con datos financieros"""
        # Gráfico de ingresos por período
        revenue_chart = build_bar_chart(
            title="Ingresos por Período",
            data=chart_data.get('revenue_over_time', []),
            x_label="Período",
            y_label="Monto ($)",
            bar_color=ft.colors.GREEN_400
        )
        
        # Gráfico de distribución de métodos de pago
        payment_methods_chart = build_pie_chart(
            title="Ingresos por Método",
            data=chart_data.get('revenue_by_method', {}),
            colors={
                'Efectivo': ft.colors.GREEN,
                'Tarjeta de Crédito': ft.colors.BLUE,
                'Transferencia': ft.colors.PURPLE,
                'Cheque': ft.colors.ORANGE
            }
        )
        
        # Gráfico de estado de deudas
        debts_chart = build_pie_chart(
            title="Distribución de Deudas",
            data=chart_data.get('debts_by_status', {}),
            colors={
                'Vencidas': ft.colors.RED,
                'Pendientes': ft.colors.ORANGE
            }
        )
        
        self.charts_column.controls = [
            ft.ResponsiveRow([
                ft.Column([
                    ft.Container(
                        content=revenue_chart,
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=5
                    )
                ], col={"sm": 12, "lg": 6}),
                ft.Column([
                    ft.Container(
                        content=payment_methods_chart,
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=5
                    )
                ], col={"sm": 12, "lg": 6})
            ]),
            ft.ResponsiveRow([
                ft.Column([
                    ft.Container(
                        content=debts_chart,
                        padding=10,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=5
                    )
                ], col={"sm": 12})
            ])
        ]

    def load_recent_appointments(self):
        """Carga las citas para mostrar en la tabla"""
        with Database.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT a.id, c.name, c.cedula, a.date, a.hour, a.status, 
                        COALESCE(SUM(p.amount), 0) as amount
                    FROM appointments a
                    JOIN clients c ON a.client_id = c.id
                    LEFT JOIN payments p ON a.id = p.appointment_id
                    WHERE a.date BETWEEN %s AND %s
                    GROUP BY a.id, c.name, c.cedula, a.date, a.hour, a.status
                    ORDER BY a.date DESC, a.hour DESC
                    LIMIT 50
                """, (self.start_date, self.end_date))
                return cursor.fetchall()

    def update_appointments_table(self, appointments):
        """Actualiza la tabla de citas"""
        self.appointments_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(appt[3].strftime("%d/%m/%Y"))),
                    ft.DataCell(ft.Text(appt[1])),
                    ft.DataCell(ft.Text(appt[4])),
                    ft.DataCell(
                        ft.Text(appt[5].capitalize()),
                        on_tap=lambda e, a=appt: self.show_appointment_detail(a[0])
                    ),
                    ft.DataCell(ft.Text(f"${appt[6]:,.2f}"))
                ]
            ) for appt in appointments
        ]
        if hasattr(self.appointments_table, 'page') and self.appointments_table.page:
            self.appointments_table.update()

    def show_appointment_detail(self, appointment_id):
        """Muestra el detalle de una cita específica"""
        pass

    def export_to_pdf(self):
        """Exporta el reporte actual a PDF"""
        pass

def reports_view(page: ft.Page):
    """Función de fábrica para crear la vista de reportes"""
    view = ReportsView(page)
    
    def on_close(e):
        view.cleanup()
        page.go(e.route)
    
    # Reemplazar el manejador de ruta temporalmente
    original_on_route_change = page.on_route_change
    page.on_route_change = on_close
    
    built_view = view.build_view()
    
    # Restaurar el manejador original después de construir la vista
    page.on_route_change = original_on_route_change
    
    return built_view