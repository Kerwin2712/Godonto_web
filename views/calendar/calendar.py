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
from utils.widgets import build_appointment_badge
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
        
        self.load_appointments()
        
        self.date_picker = ft.DatePicker(
            first_date=datetime.now().date() - timedelta(days=365),
            last_date=datetime.now().date() + timedelta(days=365),
            on_change=self.handle_date_picker_change
        )
        page.overlay.append(self.date_picker)

    def on_event(self, event_type, data):
        if event_type == 'APPOINTMENT_STATUS_CHANGED':
            self.appointments = {}
            self.load_appointments()
            self.update_calendar()
            self.update_appointments_list()
    
    def open_date_picker(self, e):
        self.page.open(self.date_picker)

    def handle_date_picker_change(self, e):
        if e.control.value:
            self.selected_date = e.control.value
            self.update_calendar()
            self.update_appointments_list()
    
    def build_view(self):
        nav_controls = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    on_click=lambda e: self.page.go("/dashboard"),
                    tooltip="Volver al Dashboard",
                    icon_color=ft.colors.BLUE_700
                ),
                ft.IconButton(
                    icon=ft.icons.CHEVRON_LEFT,
                    on_click=lambda e: self.change_month(-1),
                    tooltip="Mes anterior"
                ),
                ft.IconButton(
                    icon=ft.icons.CHEVRON_RIGHT,
                    on_click=lambda e: self.change_month(1),
                    tooltip="Mes siguiente"
                ),
                ft.ElevatedButton(
                    content=ft.Row([
                        ft.Icon(ft.icons.CALENDAR_MONTH),
                        ft.Text(self.month_year_header.value)
                    ]),
                    on_click=self.open_date_picker,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=5),
                        padding=ft.padding.symmetric(horizontal=10, vertical=5)
                    )
                ),
                ft.IconButton(
                    icon=ft.icons.TODAY,
                    on_click=lambda e: self.go_to_today(),
                    tooltip="Ir a hoy"
                ),
                ft.ElevatedButton(
                    "Nueva Cita",
                    icon=ft.icons.ADD,
                    on_click=lambda e: self.page.go("/appointment_form"),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=10, vertical=5),
                        shape=ft.RoundedRectangleBorder(radius=5)
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
                        text_align=ft.TextAlign.CENTER
                    ),
                    width=50,
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
            width=350
        )
        
        appointments_panel = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Citas del día", size=18, weight="bold"),
                    ft.Divider(),
                    self.appointments_list
                ],
                spacing=10,
                expand=True
            ),
            padding=10,
            expand=True
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
            controls=[main_content],
            padding=20,
            scroll=ft.ScrollMode.AUTO
        )

    def load_appointments(self):
        """Carga las citas desde la base de datos"""
        with get_db() as cursor:  # Cambia esto - get_db() ya devuelve un cursor
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
        self.month_year_header.value = f"{get_month_name(self.current_date.month)} {self.current_date.year}"
        
        cal = calendar.Calendar()
        month_days = cal.monthdatescalendar(self.current_date.year, self.current_date.month)
        
        self.calendar_grid.controls = []
        
        for week in month_days:
            for day in week:
                day_btn = self.build_day_button(day)
                self.calendar_grid.controls.append(day_btn)
        
        self.page.update()

    def build_day_button(self, day):
        is_current = is_current_month(day, self.current_date)
        is_selected = day == self.selected_date
        has_appointments = day.strftime("%Y-%m-%d") in self.appointments
        is_today_flag = is_today(day)
        
        text_color = (
            ft.colors.BLUE_900 if is_selected else
            ft.colors.GREY if not is_current else
            ft.colors.BLACK
        )
        
        bgcolor = (
            ft.colors.BLUE_100 if is_selected else
            ft.colors.GREY_200 if not is_current else
            ft.colors.TRANSPARENT
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
                        weight="bold" if is_selected else None,
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
        if is_current_month(day, self.current_date):
            self.selected_date = day
            self.update_calendar()
            self.update_appointments_list()

    def update_appointments_list(self):
        date_key = self.selected_date.strftime("%Y-%m-%d")
        daily_appointments = self.appointments.get(date_key, [])
        
        self.appointments_list.controls = []
        
        if not daily_appointments:
            self.appointments_list.controls.append(
                ft.Text("No hay citas programadas", italic=True)
            )
        else:
            for appt in daily_appointments:
                self.appointments_list.controls.append(
                    self.build_appointment_card(appt)
                )
        
        self.page.update()

    def build_appointment_card(self, appointment):
        status_color = {
            'pending': ft.colors.ORANGE,
            'completed': ft.colors.GREEN,
            'cancelled': ft.colors.RED
        }.get(appointment[4], ft.colors.BLUE)
        
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Icon(ft.icons.ACCESS_TIME, color=status_color),
                title=ft.Text(appointment[1]),
                subtitle=ft.Text(f"{appointment[3]} - {appointment[4]}"),
                trailing=ft.PopupMenuButton(
                    icon=ft.icons.MORE_VERT,
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
                            on_click=lambda e, a=appointment: self.page.go(f"/appointment_form?id={a[0]}")
                        )
                    ]
                )
            ),
            elevation=1
        )

    def change_month(self, delta):
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

    def go_to_today(self):
        self.current_date = datetime.now().date()
        self.selected_date = self.current_date
        self.appointments = {}
        self.load_appointments()
        self.update_calendar()
        self.update_appointments_list()

    def change_appointment_status(self, appointment_id, new_status):
        with get_db() as cursor:
            try:
                cursor.execute(
                    "UPDATE appointments SET status = %s WHERE id = %s",
                    (new_status, appointment_id)
                )
                # Mostrar notificación
                show_snackbar(self.page, f"Estado actualizado a {new_status}", "success")
                
                # Recargar datos y actualizar vistas
                self.appointments = {}
                self.load_appointments()
                self.update_calendar()
                self.update_appointments_list()
                
            except Exception as e:
                show_snackbar(self.page, f"Error al actualizar: {str(e)}", "error")

def calendar_view(page: ft.Page):
    """Función de fábrica para crear la vista del calendario"""
    return CalendarView(page).build_view()