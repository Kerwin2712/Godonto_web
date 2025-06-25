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
from utils.widgets import build_appointment_badge # Asumimos que build_appointment_badge maneja sus colores internamente
from services.appointment_service import AppointmentService

class CalendarView:
    def __init__(self, page: ft.Page):
        self.page = page
        # Suscribirse a eventos
        AppointmentService().subscribe(self)
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.appointments = {}
        
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
        self.month_year_header = ft.Text()
        # Nuevo control para el texto del botón del DatePicker
        self.selected_date_button_text = ft.Text(self.selected_date.strftime("%d/%m/%Y")) 
        
        self.load_appointments()
        
        self.date_picker = ft.DatePicker(
            first_date=datetime.now().date() - timedelta(days=365),
            last_date=datetime.now().date() + timedelta(days=365),
            on_change=self.handle_date_picker_change
        )
        page.overlay.append(self.date_picker)

    def on_event(self, event_type, data):
        """Maneja eventos de actualización de citas, recargando el calendario y la lista."""
        if event_type == 'APPOINTMENT_STATUS_CHANGED':
            self.appointments = {}
            self.load_appointments()
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

    def load_appointments(self):
        """Carga las citas desde la base de datos para el mes actual."""
        with get_db() as cursor:
            first_day = date(self.current_date.year, self.current_date.month, 1)
            last_day = date(
                self.current_date.year, 
                self.current_date.month, 
                calendar.monthrange(self.current_date.year, self.current_date.month)[1]
            )
            
            cursor.execute("""
                SELECT a.id, c.name, a.date, a.time, a.status 
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                WHERE a.date BETWEEN %s AND %s
                ORDER BY a.date, a.time
            """, (first_day, last_day))
            
            self.appointments = {}
            for appt in cursor.fetchall():
                appt_date = appt[2] if isinstance(appt[2], date) else datetime.strptime(appt[2], "%Y-%m-%d").date()
                appt_date_str = appt_date.strftime("%Y-%m-%d")
                
                if appt_date_str not in self.appointments:
                    self.appointments[appt_date_str] = []
                self.appointments[appt_date_str].append(appt)

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
        has_appointments = day.strftime("%Y-%m-%d") in self.appointments
        is_today_flag = is_today(day)
        
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
                    build_appointment_badge(has_appointments) if is_current else ft.Container()
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
        # Se asegura de que solo los días del mes actual sean seleccionables.
        # Ya no hay un if is_current_month(day, self.current_date) aquí, ya que el build_day_button
        # oculta los badges para días de otros meses y el tooltip.
        self.selected_date = day
        self.update_calendar()
        self.update_appointments_list()

    def update_appointments_list(self):
        """Actualiza la lista de citas mostradas para la fecha seleccionada."""
        date_key = self.selected_date.strftime("%Y-%m-%d")
        daily_appointments = self.appointments.get(date_key, [])
        
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.appointments_list.controls = []
        
        if not daily_appointments:
            self.appointments_list.controls.append(
                ft.Text("No hay citas programadas", italic=True, color=text_color)
            )
        else:
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
        }.get(appointment[4], ft.colors.BLUE)
        
        card_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        return ft.Card(
            content=ft.Container( # Envuelve el ListTile en un Container para el color de fondo
                content=ft.ListTile(
                    leading=ft.Icon(ft.icons.ACCESS_TIME, color=status_color),
                    title=ft.Text(appointment[1], color=text_color),
                    subtitle=ft.Text(f"{appointment[3]} - {appointment[4].capitalize()}", color=subtitle_color),
                    trailing=ft.PopupMenuButton(
                        icon=ft.icons.MORE_VERT,
                        icon_color=text_color, # Color del icono del menú
                        items=[
                            ft.PopupMenuItem(
                                text="Completar",
                                on_click=lambda e, a=appointment: self.change_appointment_status(a[0], "completed")
                            ),
                            ft.PopupMenuItem(
                                text="Cancelar",
                                on_click=lambda e, a=appointment: self.change_appointment_status(a[0], "cancelled")
                            ),
                            ft.PopupMenuItem(
                                text="Editar",
                                on_click=lambda e, a=appointment: self.page.go(f"/appointment_form/{a[0]}")
                                #on_click=lambda e: self.page.go(f"/appointment_form/{appointment.id}")
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
        self.appointments = {}
        self.load_appointments()
        self.update_calendar()
        self.update_appointments_list() # Asegura que la lista de citas se actualice al cambiar de mes

    def go_to_today(self):
        """Navega el calendario a la fecha actual (hoy)."""
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.appointments = {}
        self.load_appointments()
        self.update_calendar()
        self.update_appointments_list()

    def change_appointment_status(self, appointment_id, new_status):
        """Cambia el estado de una cita en la base de datos y actualiza la UI."""
        with get_db() as cursor:
            try:
                cursor.execute(
                    "UPDATE appointments SET status = %s WHERE id = %s",
                    (new_status, appointment_id)
                )
                show_snackbar(self.page, f"Estado actualizado a {new_status.capitalize()}", "success")
                
                self.appointments = {}
                self.load_appointments()
                self.update_calendar()
                self.update_appointments_list()
                
            except Exception as e:
                show_snackbar(self.page, f"Error al actualizar: {str(e)}", "error")

def calendar_view(page: ft.Page):
    """Función de fábrica para crear la vista del calendario."""
    return CalendarView(page).build_view()
