import flet as ft
import calendar
from datetime import datetime, timedelta, date
from core.database import get_db
from utils.date_utils import (
    get_month_name,
    get_weekday_name,
    is_current_month,
    is_today
)
from utils.alerts import show_snackbar
from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.payment_service import PaymentService
from utils.alerts import show_snackbar, show_error, show_success

class CalendarView:
    def __init__(self, page: ft.Page):
        self.page = page
        # Suscribirse a eventos
        AppointmentService().subscribe(self)
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.appointments = {} # Ahora almacenará más información: {'fecha_str': {'appointments': [...], 'has_cancelled_appointments': bool}}
        
        self.calendar_grid = ft.GridView(
            expand=False,
            runs_count=7,
            max_extent=50,
            child_aspect_ratio=1,
            spacing=0,
            run_spacing=0
        )
        
        self.appointments_list = ft.ListView(
            expand=True,
            auto_scroll=False,
            on_scroll=ft.ScrollMode.AUTO
        )
        self.month_year_header = ft.Text(
            value=f"{get_month_name(self.current_date.month)} {self.current_date.year}",
            size=16,
            weight="bold"
        )
        # Nuevo control para el texto del botón del DatePicker
        self.selected_date_button_text = ft.Text(self.selected_date.strftime("%d/%m/%Y")) 
        
        self.load_data()
        
        self.date_picker = ft.DatePicker(
            first_date=datetime.now().date() - timedelta(days=365),
            last_date=datetime.now().date() + timedelta(days=365),
            on_change=self.handle_date_picker_change
        )
        page.overlay.append(self.date_picker)

    def on_event(self, event_type, data):
        """Maneja eventos de actualización de citas, recargando el calendario y la lista."""
        if event_type == 'APPOINTMENT_STATUS_CHANGED':
            # Recargar solo las citas del mes actual para eficiencia
            self.appointments = {} # Reiniciar para asegurar la recarga completa de estados
            self.load_data()
            self.update_calendar()
            self.update_appointments_list()
    
    def open_date_picker(self, e):
        """Abre el selector de fechas del calendario."""
        self.date_picker.value = self.selected_date # Establecer el valor inicial del DatePicker
        self.page.open(self.date_picker)

    def handle_date_picker_change(self, e):
        """Maneja el cambio de fecha seleccionado en el DatePicker."""
        if e.control.value:
            self.selected_date = e.control.value.date() # Asegúrate de obtener solo la fecha
            self.selected_date_button_text.value = self.selected_date.strftime("%d/%m/%Y") # Actualizar el texto del botón
            self.update_calendar()
            self.update_appointments_list()
            self.page.update() # Asegura que la UI se actualice

    def build_view(self):
        """Construye la vista principal del calendario, incluyendo la barra de navegación y los paneles."""
        # Colores para el modo oscuro/claro
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        header_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        section_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        section_border_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        appbar_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900

        app_bar = ft.AppBar(
            title=ft.Text("Calendario de Citas", color=ft.colors.WHITE),
            bgcolor=appbar_bgcolor,
            leading=ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                on_click=lambda e: self.page.go("/dashboard"),
                tooltip="Volver al Dashboard",
                icon_color=ft.colors.WHITE
            )
        )

        nav_controls = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.icons.CHEVRON_LEFT,
                    on_click=lambda e: self.change_month(-1),
                    tooltip="Mes anterior",
                    icon_color=text_color
                ),
                self.month_year_header, # Añadido para mostrar el mes y año
                ft.IconButton(
                    icon=ft.icons.CHEVRON_RIGHT,
                    on_click=lambda e: self.change_month(1),
                    tooltip="Mes siguiente",
                    icon_color=text_color
                ),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.icons.CALENDAR_MONTH, color=ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.DARK else None),
                        self.selected_date_button_text,
                    ]),
                    on_click=self.open_date_picker,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        bgcolor=ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800,
                        color=ft.colors.WHITE
                    )
                ),
                ft.IconButton(
                    icon=ft.icons.TODAY,
                    on_click=lambda e: self.go_to_today(),
                    tooltip="Ir a hoy",
                    icon_color=text_color
                ),
                ft.ElevatedButton(
                    "Nueva Cita",
                    icon=ft.icons.ADD,
                    on_click=lambda e: self.page.go("/appointment_form"),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        shape=ft.RoundedRectangleBorder(radius=5),
                        bgcolor=ft.colors.GREEN_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREEN_800,
                        color=ft.colors.WHITE
                    )
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10,
            wrap=True
        )
        
        weekdays_header = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Text(
                        get_weekday_name(day),
                        weight="bold",
                        size=12,
                        text_align=ft.TextAlign.CENTER,
                        color=header_text_color
                    ),
                    width=47,
                    height=30,
                    alignment=ft.alignment.center,
                    padding=0,
                    margin=0
                ) for day in range(7)
            ],
            spacing=0,
            tight=True
        )
        
        calendar_panel = ft.Container(
            content=ft.Column(
                controls=[
                    nav_controls,
                    weekdays_header,
                    self.calendar_grid
                ],
                spacing=10,
                tight=True,
                alignment=ft.MainAxisAlignment.START
            ),
            alignment=ft.alignment.top_left,
            padding=10,
            width=350, 
            bgcolor=section_bg_color,
            border=ft.border.all(1, section_border_color),
            border_radius=10
        )
        
        appointments_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Citas del día", size=18, weight="bold", color=header_text_color),
                    ft.Divider(color=section_border_color),
                    self.appointments_list
                ],
                spacing=10,
                expand=True
            ),
            padding=10,
            expand=True,
            bgcolor=section_bg_color,
            border=ft.border.all(1, section_border_color),
            border_radius=10
        )
        
        main_content = ft.ResponsiveRow(
            controls=[
                ft.Column(
                    col={"sm": 12, "md": 5},
                    controls=[calendar_panel],
                    alignment=ft.MainAxisAlignment.START,
                    scroll=ft.ScrollMode.AUTO
                ),
                ft.Column(
                    col={"sm": 12, "md": 7},
                    controls=[appointments_panel],
                    expand=True,
                    scroll=ft.ScrollMode.AUTO
                )
            ],
            spacing=20,
            expand=True
        )
        
        self.update_calendar()
        self.update_appointments_list()
        
        return ft.View(
            "/calendar",
            controls=[
                app_bar,
                main_content
            ],
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            scroll=ft.ScrollMode.AUTO
        )

    def load_data(self):
        """Carga las citas y cumpleaños desde la base de datos para el mes actual."""
        # 1. Cargar Citas
        with get_db() as cursor:
            first_day = date(self.current_date.year, self.current_date.month, 1)
            last_day = date(
                self.current_date.year,
                self.current_date.month,
                calendar.monthrange(self.current_date.year, self.current_date.month)[1]
            )

            cursor.execute("""
                SELECT
                    a.id,
                    c.name AS client_name,
                    c.id AS client_id,
                    a.date,
                    a.time,
                    a.status,
                    a.notes,
                    d.name AS dentist_name,
                    STRING_AGG(t.name, ', ') AS treatments,
                    SUM(t.price) AS total_amount
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                LEFT JOIN dentists d ON a.dentist_id = d.id
                LEFT JOIN appointment_treatments at ON a.id = at.appointment_id
                LEFT JOIN treatments t ON at.treatment_id = t.id
                WHERE a.date BETWEEN %s AND %s
                GROUP BY a.id, c.name, c.id, a.date, a.time, a.status, d.name
                ORDER BY a.date, a.time
            """, (first_day, last_day))

            self.appointments = {}  # Reiniciar el diccionario
            for appt in cursor.fetchall():
                appt_date = appt[3] if isinstance(appt[3], date) else datetime.strptime(appt[3], "%Y-%m-%d").date()
                appt_date_str = appt_date.strftime("%Y-%m-%d")

                if appt_date_str not in self.appointments:
                    self.appointments[appt_date_str] = {
                        'appointments': [],
                        'birthdays': [],
                        'has_cancelled_appointments': False
                    }

                self.appointments[appt_date_str]['appointments'].append(appt)
                if appt[5] == 'cancelled':  # Si el estado es 'cancelled'
                    self.appointments[appt_date_str]['has_cancelled_appointments'] = True

        # 2. Cargar Cumpleaños
        birthday_clients = ClientService.get_clients_with_birthdays_in_month(self.current_date.month)
        for client in birthday_clients:
            if client.birth_date:
                # Calcular la fecha del cumpleaños en el año actual (y mes actual)
                try:
                    bday_this_year = client.birth_date.replace(year=self.current_date.year)
                except ValueError:
                    # Manejar 29 de febrero en años no bisiestos
                    if client.birth_date.month == 2 and client.birth_date.day == 29:
                        bday_this_year = date(self.current_date.year, 3, 1) # O 28 de feb
                    else:
                        continue
                
                bday_str = bday_this_year.strftime("%Y-%m-%d")
                
                if bday_str not in self.appointments:
                    self.appointments[bday_str] = {
                        'appointments': [],
                        'birthdays': [],
                        'has_cancelled_appointments': False
                    }
                
                self.appointments[bday_str]['birthdays'].append(client)


    def update_calendar(self):
        """Actualiza la cuadrícula del calendario con los días y citas del mes."""
        self.month_year_header.value = f"{get_month_name(self.current_date.month)} {self.current_date.year}"
        self.selected_date_button_text.value = self.selected_date.strftime("%d/%m/%Y") # Actualizar el texto del botón del DatePicker
        
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(self.current_date.year, self.current_date.month)
        
        self.calendar_grid.controls = []
        
        for week in month_days:
            for day in week:
                day_btn = self.build_day_button(day)
                self.calendar_grid.controls.append(day_btn)
        
        self.page.update()

    def build_day_button(self, day):
        """Construye un botón individual para un día en el calendario."""
        is_current = is_current_month(day, self.current_date)
        is_selected = day == self.selected_date
        is_today_flag = is_today(day)
        
        day_info = self.appointments.get(day.strftime("%Y-%m-%d"), {'appointments': [], 'birthdays': [], 'has_cancelled_appointments': False})
        has_appointments = bool(day_info['appointments'])
        has_birthdays = bool(day_info['birthdays'])
        has_cancelled_appointments = day_info['has_cancelled_appointments']

        # Colores para el día del calendario
        day_text_color_current_month = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        day_text_color_other_month = ft.colors.GREY_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_300 # Más suave para oscuro
        
        day_bg_color_selected = ft.colors.BLUE_200 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800 # Más oscuro para oscuro
        day_bg_color_other_month = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        day_bg_color_current_month = ft.colors.TRANSPARENT if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900 # Fondo para días del mes actual

        text_color = (
            ft.colors.BLUE_900 if is_selected and self.page.theme_mode == ft.ThemeMode.LIGHT else
            ft.colors.BLUE_100 if is_selected and self.page.theme_mode == ft.ThemeMode.DARK else
            day_text_color_other_month if not is_current else
            day_text_color_current_month
        )
        
        bgcolor = (
            day_bg_color_selected if is_selected else
            day_bg_color_other_month if not is_current else
            day_bg_color_current_month
        )
            
        border = ft.border.all(
            2,
            ft.colors.GREEN_500 if is_today_flag else 
            ft.colors.BLUE_500 if is_selected else 
            ft.colors.TRANSPARENT
        )

        # Determinar indicadores
        indicators = []
        
        # Badge de citas
        badge_color = ft.colors.TRANSPARENT # Por defecto sin color
        if has_appointments and is_current: # Solo mostrar badge si hay citas y es el mes actual
            if has_cancelled_appointments:
                badge_color = ft.colors.RED_400 # Rojo si hay citas canceladas
            else:
                badge_color = ft.colors.BLUE_400 # Azul si hay citas y ninguna está cancelada
            
            indicators.append(ft.Container(
                content=ft.CircleAvatar(radius=3, bgcolor=badge_color),
                width=6, height=6
            ))
        
        # Icono de cumpleaños
        if has_birthdays and is_current:
            indicators.append(ft.Icon(ft.icons.CAKE, size=12, color=ft.colors.PINK_400))


        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        str(day.day),
                        size=12,
                        weight="bold" if is_selected or is_today_flag else None,
                        color=text_color,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Row(
                        controls=indicators,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=2
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                tight=True
            ),
            width=50,
            height=50,
            alignment=ft.alignment.center,
            bgcolor=bgcolor,
            border=border,
            border_radius=4,
            padding=0,
            on_click=lambda e, d=day: self.select_date(d),
            tooltip=f"{day.strftime('%d/%m/%Y')}" if is_current else None
        )

    def select_date(self, day):
        """Selecciona un día en el calendario y actualiza la lista de citas."""
        self.selected_date = day
        self.selected_date_button_text.value = self.selected_date.strftime("%d/%m/%Y") # Actualizar el texto del botón
        self.update_calendar()
        self.update_appointments_list()

    def update_appointments_list(self):
        """Actualiza la lista de citas mostradas para la fecha seleccionada."""
        date_key = self.selected_date.strftime("%Y-%m-%d")
        # Acceder a la lista de citas dentro del diccionario de día
        daily_info = self.appointments.get(date_key, {'appointments': [], 'birthdays': [], 'has_cancelled_appointments': False})
        daily_appointments = daily_info['appointments']
        daily_birthdays = daily_info['birthdays']
        
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.appointments_list.controls = []
        
        # Mostrar Cumpleaños primero
        if daily_birthdays:
            self.appointments_list.controls.append(ft.Text("Cumpleaños", weight="bold", color=ft.colors.PINK_400))
            for client in daily_birthdays:
                self.appointments_list.controls.append(
                    self.build_birthday_card(client)
                )
            self.appointments_list.controls.append(ft.Divider())

        # Mostrar Citas
        if not daily_appointments:
            if not daily_birthdays:
                self.appointments_list.controls.append(
                    ft.Text("No hay citas programadas ni cumpleaños", italic=True, color=text_color)
                )
        else:
            self.appointments_list.controls.append(ft.Text("Citas", weight="bold", color=text_color))
            for appt in daily_appointments:
                self.appointments_list.controls.append(
                    self.build_appointment_card(appt)
                )
        
        self.page.update()

    def build_appointment_card(self, appointment):
        """Construye una tarjeta para mostrar los detalles de una cita."""
        status_color = {
            'pending': ft.colors.ORANGE,
            'completed': ft.colors.GREEN,
            'cancelled': ft.colors.RED
        }.get(appointment[5], ft.colors.BLUE)

        card_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        notes = appointment[6] if appointment[6] else "No especificado"
        dentist_name = appointment[7] if appointment[7] else "No asignado"
        treatments = appointment[8] if appointment[8] else "No especificado"
        total_amount = appointment[9] if appointment[9] else 0

        details = ft.Column([
            ft.Text(f"Hora: {appointment[4]} - Estado: {appointment[5].capitalize()}", color=subtitle_color),
            ft.Text(f"Odontólogo: {dentist_name}", color=subtitle_color),
            ft.Text(f"Tratamientos: {treatments}", color=subtitle_color),
            ft.Text(f"Notas: {notes}", color=subtitle_color),
            ft.Text(f"Monto a pagar: ${total_amount:,.2f}", color=subtitle_color, weight="bold"),
        ])

        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    leading=ft.Icon(ft.icons.ACCESS_TIME, color=status_color),
                    title=ft.Text(appointment[1], color=text_color),
                    subtitle=details,
                    trailing=ft.PopupMenuButton(
                        icon=ft.icons.MORE_VERT,
                        icon_color=text_color,
                        items=[
                            ft.PopupMenuItem(
                                text="Registrar Pago",
                                icon=ft.icons.PAYMENT,
                                on_click=lambda e, a=appointment: self._show_payment_dialog(a[2], a[1])
                            ),
                            ft.PopupMenuItem(
                                text="Completar",
                                on_click=lambda e, a=appointment: self.change_appointment_status(a[0], "completed")
                            ),
                            ft.PopupMenuItem(
                                text="Cancelar",
                                on_click=lambda e, a=appointment: self.change_appointment_status(a[0], "cancelled")
                            ),
                            ft.PopupMenuItem(
                                text="Pendiente",
                                on_click=lambda e, a=appointment: self.change_appointment_status(a[0], "pending")
                            ),
                            ft.PopupMenuItem(
                                text="Editar",
                                on_click=lambda e, a=appointment: self.page.go(f"/appointment_form/{a[0]}")
                            )
                        ]
                    )
                ),
                bgcolor=card_bgcolor,
                padding=ft.padding.all(10),
                border_radius=10,
                border=ft.border.all(1, ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600)
            ),
            elevation=1
        )

    def _show_payment_dialog(self, client_id, client_name):
        amount_field = ft.TextField(label="Monto", keyboard_type=ft.KeyboardType.NUMBER)
        method_field = ft.Dropdown(
            label="Método de pago",
            options=[
                ft.dropdown.Option("Efectivo"),
                ft.dropdown.Option("Tarjeta"),
                ft.dropdown.Option("Transferencia"),
                ft.dropdown.Option("Otro")
            ]
        )
        notes_field = ft.TextField(label="Notas (opcional)", multiline=True)
        
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def handle_submit(e):
            try:
                amount = float(amount_field.value)
                method = method_field.value
                notes = notes_field.value
                
                payment_service = PaymentService()
                
                initial_summary = payment_service.get_payment_summary(client_id)
                initial_pending_debt = initial_summary.get('total_pending_debt', 0.0)
                
                success, message = payment_service.create_payment(
                    client_id=client_id,
                    amount=amount,
                    method=method,
                    notes=notes
                )
                
                if success:
                    new_summary = payment_service.get_payment_summary(client_id)
                    new_pending_debt = new_summary.get('total_pending_debt', 0.0)
                    
                    debt_applied_by_this_payment = initial_pending_debt - new_pending_debt
                    
                    if debt_applied_by_this_payment > 0.001:
                        msg = f"Pago de ${amount:,.2f} registrado. Se aplicó ${debt_applied_by_this_payment:,.2f} a deudas pendientes."
                        if new_pending_debt > 0:
                            msg += f" Saldo pendiente de deudas: ${new_pending_debt:,.2f}"
                        else:
                            msg += " Todas las deudas pendientes han sido cubiertas."
                    else:
                        msg = f"Pago de ${amount:,.2f} registrado para {client_name}."
                        if initial_pending_debt > 0:
                            msg += f" Aún quedan deudas pendientes: ${initial_pending_debt:,.2f}."
                        else:
                            msg += " No había deudas pendientes a las cuales aplicar el pago."

                    show_success(self.page, msg)
                    close_dialog(e)
                else:
                    show_error(self.page, message)
            except ValueError:
                show_error(self.page, "Ingrese un monto válido")
            except Exception as e:
                # logger.error(f"Error al registrar pago: {str(e)}") # Logger not imported in calendar.py view, verify imports
                show_error(self.page, f"Error al registrar pago: {str(e)}")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Registrar Pago para {client_name}"),
            content=ft.Column([
                amount_field,
                method_field,
                notes_field
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.TextButton("Registrar", on_click=handle_submit)
            ]
        )
        self.page.open(dialog)
        dialog.open = True
        self.page.update()

    def change_month(self, delta):
        """Cambia el mes actual del calendario."""
        new_month = self.current_date.month + delta
        new_year = self.current_date.year
        
        if new_month > 12:
            new_month = 1
            new_year += 1
        elif new_month < 1:
            new_month = 12
            new_year -= 1
            
        self.current_date = date(new_year, new_month, 1)
        self.appointments = {} # Resetear para forzar recarga
        self.load_data()
        self.update_calendar()
        self.update_appointments_list() # Asegura que la lista de citas se actualice al cambiar de mes

    def go_to_today(self):
        """Navega el calendario a la fecha actual (hoy)."""
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.appointments = {}
        self.load_data()
        self.update_calendar()
        self.update_appointments_list()

    def change_appointment_status(self, appointment_id, new_status):
        """Cambia el estado de una cita en la base de datos y actualiza la UI."""
        # Se asume que get_db() es un context manager o una función que obtiene un cursor
        with get_db() as cursor:
            try:
                # Actualizar el estado en la base de datos
                # Usa AppointmentService para actualizar el estado, ya que se encarga de las notificaciones
                # y lógica de negocio.
                success = AppointmentService.update_appointment_status(appointment_id, new_status)
                
                if success:
                    show_snackbar(self.page, f"Estado actualizado a {new_status.capitalize()}", "success")
                    # **CLAVE: Recargar las citas y actualizar la UI después del cambio**
                    self.appointments = {} # Limpiar para recargar los datos actualizados
                    self.load_data()
                    self.update_calendar()
                    self.update_appointments_list()
                else:
                    show_snackbar(self.page, f"Error al actualizar estado de la cita.", "error")
                    
            except Exception as e:
                show_snackbar(self.page, f"Error al actualizar: {str(e)}", "error")

    def build_birthday_card(self, client):
        """Construye una tarjeta para mostrar un cumpleaños."""
        card_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        
        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    leading=ft.Icon(ft.icons.CAKE, color=ft.colors.PINK_400),
                    title=ft.Row(
                        controls=[
                            ft.Text(client.name, color=text_color, weight="bold"),
                            ft.Icon(ft.icons.CAKE, size=16, color=ft.colors.PINK_400)
                        ],
                        spacing=5
                    ),
                    subtitle=ft.Text(f"¡Está de cumpleaños!", color=ft.colors.PINK_300),
                ),
                bgcolor=card_bgcolor,
                padding=ft.padding.all(5),
                border_radius=10,
                border=ft.border.all(1, ft.colors.PINK_200)
            ),
            elevation=1
        )

def calendar_view(page: ft.Page):
    """Función de fábrica para crear la vista del calendario."""
    return CalendarView(page).build_view()
