import flet as ft
from datetime import datetime, time
from typing import Optional
from services.appointment_service import (
    get_appointment_by_id,
    create_appointment,
    update_appointment,
    validate_appointment_time,
    search_clients  
)
from utils.alerts import show_error, show_success
from utils.date_utils import to_local_time


class AppointmentFormView:
    def __init__(self, page: ft.Page, appointment_id: Optional[int] = None):
        self.page = page
        self.appointment_id = appointment_id
        self.form_data = {
            'client_id': None,
            'date': None,
            'hour': None,
            'notes': None,
            'status': 'pending'
        }
        
        # Componentes UI mejorados para búsqueda de clientes
        self.client_search = self._build_client_search()
        
        self.date_picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=self.handle_date_change
        )
        
        self.time_picker = ft.TimePicker(
            on_change=self.handle_time_change
        )
        
        self.notes_field = ft.TextField(
            label="Notas", 
            multiline=True,
            min_lines=3,
            max_lines=5,
            expand=True
        )
        
        self.date_text = ft.Text("No seleccionada", color=ft.colors.BLACK)
        self.time_text = ft.Text("No seleccionada", color=ft.colors.BLACK)
        self.selected_client_text = ft.Text(
            "Ningún cliente seleccionado", 
            italic=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            color = ft.colors.BLACK,
        )
        
        # Añadir pickers al overlay de la página
        self.page.overlay.extend([self.date_picker, self.time_picker])
        
        # Cargar datos si es edición
        if self.appointment_id:
            self.load_appointment_data()

    def _build_client_search(self):
        """Construye el componente de búsqueda de clientes responsive"""
        return ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.BLUE_400,
            bar_hint_text="Buscar cliente...",
            view_hint_text="Seleccione un cliente...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.client_search.open_view()
            ),
            controls=[],
            expand=True,
            on_change=self.handle_search_change,
            on_submit=lambda e: self.handle_search_submit(e)
        )

    def _build_search_row(self):
        """Fila de búsqueda responsive con botones de acción"""
        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        self.client_search,
                        ft.IconButton(
                            icon=ft.icons.CLEAR,
                            tooltip="Limpiar búsqueda",
                            on_click=lambda e: self._reset_client_search(),
                            icon_color=ft.colors.GREY_600
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 8}),
                ft.Column([
                    ft.Container(
                        content=self.selected_client_text,
                        padding=10,
                        bgcolor=ft.colors.GREY_100,
                        border_radius=5,
                        expand=True
                    )
                ], col={"sm": 12, "md": 4})
            ],
            spacing=10,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

    def handle_search_change(self, e):
        """Maneja el cambio en la búsqueda de clientes"""
        search_term = e.control.value.strip()
        
        if len(search_term) < 1:
            self.client_search.controls = []
            self.page.update()
            return

        try:
            clients = search_clients(search_term)
            self.client_search.controls = [
                ft.ListTile(
                    title=ft.Text(f"{name}"),
                    subtitle=ft.Text(f"Cédula: {cedula}"),
                    on_click=lambda e, id=id, name=name, cedula=cedula: self.select_client(id, name, cedula),
                    data=(id, name, cedula)
                ) for (id, name, cedula) in clients
            ]
            self.page.update()
        except Exception as e:
            show_error(self.page, f"Error en búsqueda: {str(e)}")

    def handle_search_submit(self, e):
        """Maneja la selección directa con Enter"""
        if self.client_search.controls and len(self.client_search.controls) > 0:
            client_id, name, cedula = self.client_search.controls[0].data
            self.select_client(client_id, name, cedula)

    def select_client(self, client_id, name, cedula):
        """Selecciona un cliente de los resultados"""
        self.form_data['client_id'] = client_id
        self.client_search.value = f"{name} - {cedula}"
        self.selected_client_text.value = f"{name} (Cédula: {cedula})"
        self.selected_client_text.style = None
        self.client_search.close_view()
        self.page.update()

    def _reset_client_search(self):
        """Resetea la búsqueda de clientes"""
        self.client_search.value = ""
        self.client_search.controls = []
        self.form_data['client_id'] = None
        self.selected_client_text.value = "Ningún cliente seleccionado"
        self.selected_client_text.style = ft.TextStyle(italic=True)
        self.client_search.close_view()
        self.page.update()

    def handle_date_change(self, e):
        """Maneja el cambio de fecha"""
        self.form_data['date'] = self.date_picker.value
        self.date_text.value = self.date_picker.value.strftime("%d/%m/%Y") if self.date_picker.value else "No seleccionada"
        self.page.update()
    
    def handle_time_change(self, e):
        """Maneja el cambio de hora"""
        self.form_data['hour'] = self.time_picker.value
        self.time_text.value = self.time_picker.value.strftime("%H:%M") if self.time_picker.value else "No seleccionada"
        self.page.update()
    
    def load_appointment_data(self):
        """Carga los datos de una cita existente"""
        appointment = get_appointment_by_id(self.appointment_id)
        if not appointment:
            return

        date_value = appointment.date
        hour_value = appointment.time
        
        if isinstance(date_value, str):
            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
        if isinstance(hour_value, str):
            try:
                hour_value = datetime.strptime(hour_value, "%H:%M:%S").time()
            except ValueError:
                hour_value = datetime.strptime(hour_value, "%H:%M").time()
        
        self.form_data.update({
            'client_id': appointment.client_id,
            'date': date_value,
            'hour': hour_value,
            'notes': appointment.notes,
            'status': appointment.status
        })
        
        self.notes_field.value = self.form_data['notes']
        
        if self.form_data['date']:
            self.date_picker.value = self.form_data['date']
            self.date_text.value = self.form_data['date'].strftime("%d/%m/%Y")
        
        if self.form_data['hour']:
            self.time_picker.value = self.form_data['hour']
            self.time_text.value = self.form_data['hour'].strftime("%H:%M")
        
        if self.form_data['client_id']:
            self.client_search.value = f"{appointment.client_name} - {appointment.client_cedula}"
            self.selected_client_text.value = f"{appointment.client_name} (Cédula: {appointment.client_cedula})"
            self.selected_client_text.style = None
        
        self.page.update()
    
    def handle_save(self, e):
        """Maneja el guardado de la cita"""
        try:
            # Validar campos requeridos
            if not all([self.form_data['client_id'], self.form_data['date'], self.form_data['hour']]):
                show_error(self.page, "Cliente, fecha y hora son requeridos")
                return
            
            # Validar disponibilidad de horario
            is_valid, error_msg = validate_appointment_time(
                self.form_data['date'],
                self.form_data['hour'],
                self.appointment_id
            )
            if not is_valid:
                show_error(self.page, error_msg)
                return
            
            # Actualizar notas
            self.form_data['notes'] = self.notes_field.value
            
            # Guardar o actualizar
            if self.appointment_id:
                success, message = update_appointment(
                    appointment_id=self.appointment_id,
                    client_id=self.form_data['client_id'],
                    date=self.form_data['date'],
                    time=self.form_data['hour'],
                    notes=self.form_data['notes'],
                    status=self.form_data['status']
                )
                if success:
                    show_success(self.page, "Cita actualizada exitosamente")
                    self.page.go("/appointments")
                else:
                    show_error(self.page, message)
            else:
                success, message = create_appointment(
                    self.form_data['client_id'],
                    self.form_data['date'],
                    self.form_data['hour'],
                    self.form_data['notes']
                )
                if success:
                    show_success(self.page, "Cita creada exitosamente")
                    self.page.go("/appointments")
                else:
                    show_error(self.page, message)
        
        except Exception as e:
            show_error(self.page, f"Error al guardar: {str(e)}")
    
    def _build_date_time_controls(self):
        """Construye controles de fecha y hora responsive"""
        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Text("Fecha:", weight="bold"),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.CALENDAR_TODAY,
                            on_click=lambda e: self.page.open(self.date_picker),
                            expand=True
                        ),
                        ft.Container(
                            content=self.date_text,
                            padding=10,
                            bgcolor=ft.colors.GREY_100,
                            border_radius=5,
                            expand=True
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 6}),
                ft.Column([
                    ft.Text("Hora:", weight="bold"),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.ACCESS_TIME,
                            on_click=lambda e: self.page.open(self.time_picker),
                            expand=True
                        ),
                        ft.Container(
                            content=self.time_text,
                            padding=10,
                            bgcolor=ft.colors.GREY_100,
                            border_radius=5,
                            expand=True
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 6})
            ],
            spacing=10,
            run_spacing=10
        )
    
    def _build_action_buttons(self):
        """Construye botones de acción responsive"""
        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        ft.ElevatedButton(
                            "Guardar",
                            icon=ft.icons.SAVE,
                            on_click=self.handle_save,
                            style=ft.ButtonStyle(
                                bgcolor=ft.colors.BLUE_700,
                                color=ft.colors.WHITE
                            ),
                            expand=True
                        ),
                        ft.OutlinedButton(
                            "Cancelar",
                            icon=ft.icons.CANCEL,
                            on_click=lambda e: self.page.go("/appointments"),
                            expand=True
                        )
                    ], spacing=10)
                ], col={"sm": 12, "md": 6, "lg": 4}, 
                alignment=ft.MainAxisAlignment.END)
            ],
            alignment=ft.MainAxisAlignment.END
        )
    
    def build_view(self):
        """Construye y devuelve la vista del formulario responsive"""
        return ft.View(
            "/appointment_form" if not self.appointment_id else f"/appointment_form/{self.appointment_id}",
            controls=[
                ft.AppBar(
                    title=ft.Text("Editar Cita" if self.appointment_id else "Nueva Cita"),
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: self.page.go("/dashboard"),
                        tooltip="Volver al Dashboard"
                    )
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Seleccionar Cliente", weight="bold"),
                        self._build_search_row(),
                        ft.Divider(),
                        ft.Text("Información de la Cita", weight="bold"),
                        self._build_date_time_controls(),
                        ft.Text("Notas:", weight="bold"),
                        self.notes_field,
                        self._build_action_buttons()
                    ], 
                    spacing=20,
                    expand=True),
                    padding=20,
                    expand=True
                )
            ],
            scroll=ft.ScrollMode.AUTO
        )

def appointment_form_view(page: ft.Page, appointment_id: Optional[int] = None):
    """Función de fábrica para crear la vista del formulario de citas"""
    return AppointmentFormView(page, appointment_id).build_view()