import flet as ft
from datetime import datetime, time
from typing import Optional, List
from services.appointment_service import (
    get_appointment_by_id,
    create_appointment,
    update_appointment,
    validate_appointment_time,
    search_clients,
    get_appointment_treatments # Importar para cargar tratamientos existentes
)
from services.treatment_service import (
    search_treatment
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
            'status': 'pending',
            'treatments': [] # Lista para almacenar tratamientos seleccionados
        }
        
        self.selected_treatments = [] # Lista para objetos de tratamiento completos (id, name, price)
        self.treatments_column = ft.Column() # Columna para mostrar los tratamientos seleccionados

        self.treatment_search = self._build_treatment_search()
        
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
        self.selected_treatments_text = ft.Text(
            "Ningún tratamiento seleccionado",
            italic=True,
            overflow=ft.TextOverflow.ELLIPSIS,
            color=ft.colors.BLACK,
        )
        
        # Añadir pickers al overlay de la página
        self.page.overlay.extend([self.date_picker, self.time_picker])
        
        # Cargar datos si es edición
        if self.appointment_id:
            self.load_appointment_data()

    """Metodos para la barra de busqueda de tratamientos"""
    
    def _build_treatment_search(self):
        """Componente para buscar tratamientos"""
        return ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.GREEN_400,
            bar_hint_text="Buscar tratamientos...",
            view_hint_text="Seleccione un tratamiento...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.treatment_search.open_view()
            ),
            controls=[],
            expand=True,
            on_change=self.handle_treatment_search_change,
            on_submit=lambda e: self.handle_treatment_search_submit(e)
        )
    
    
    def _build_search_treatment_row(self):
        """Fila de búsqueda responsive con botones de acción"""
        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        self.treatment_search,
                        ft.IconButton(
                            icon=ft.icons.CLEAR,
                            tooltip="Limpiar búsqueda",
                            on_click=lambda e: self._reset_treatment_search(),
                            icon_color=ft.colors.GREY_600
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 12}), # Ocupar todo el ancho para la búsqueda de tratamientos
                # ft.Column([ # Ya no necesitamos este contenedor de texto aquí
                #     ft.Container(
                #         content=self.selected_treatments_text,
                #         padding=10,
                #         bgcolor=ft.colors.GREY_100,
                #         border_radius=5,
                #         expand=True
                #     )
                # ], col={"sm": 12, "md": 4})
            ],
            spacing=10,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    def handle_treatment_search_change(self, e):
        """Maneja la búsqueda de tratamientos"""
        search_term = e.control.value.strip()
        
        if len(search_term) < 1:
            self.treatment_search.controls = []
            self.page.update()
            return

        try:
            treatments = search_treatment(search_term)
            self.treatment_search.controls = [
                ft.ListTile(
                    title=ft.Text(f"{name}"),
                    subtitle=ft.Text(f"Precio: {price}"),
                    on_click=lambda e, id=id, name=name, price=price: self.select_treatment(id, name, price),
                    data={'id': id, 'name': name, 'price': price} # Pasar como diccionario
                ) for (id, name, price) in treatments
            ]
            self.page.update()
        except Exception as e:
            show_error(self.page, f"Error en búsqueda de tratamientos: {str(e)}")
    
    def select_treatment(self, treatment_id: int, name: str, price: float):
        """Añade un tratamiento seleccionado a la lista"""
        # Verificar si el tratamiento ya está seleccionado
        if any(t['id'] == treatment_id for t in self.selected_treatments):
            show_error(self.page, "Este tratamiento ya ha sido añadido.")
            self.treatment_search.close_view()
            self.page.update()
            return

        selected_treatment_data = {'id': treatment_id, 'name': name, 'price': price}
        self.selected_treatments.append(selected_treatment_data)
        self.form_data['treatments'].append(selected_treatment_data) # Añadir a form_data

        self._update_treatments_display() # Actualizar la visualización de tratamientos
        self.treatment_search.value = "" # Limpiar el campo de búsqueda
        self.treatment_search.controls = [] # Limpiar los resultados de búsqueda
        self.treatment_search.close_view()
        self.page.update()

    def _remove_treatment(self, treatment_id: int):
        """Elimina un tratamiento de la lista de seleccionados"""
        self.selected_treatments = [t for t in self.selected_treatments if t['id'] != treatment_id]
        self.form_data['treatments'] = [t for t in self.form_data['treatments'] if t['id'] != treatment_id]
        self._update_treatments_display()
        self.page.update()

    def _update_treatments_display(self):
        """Actualiza la visualización de los tratamientos seleccionados"""
        if not self.selected_treatments:
            self.treatments_column.controls = [
                ft.Text(
                    "Ningún tratamiento seleccionado",
                    italic=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color=ft.colors.BLACK,
                )
            ]
        else:
            self.treatments_column.controls = [
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Text(f"{t['name']} - ${t['price']:.2f}", expand=True),
                            ft.IconButton(
                                icon=ft.icons.CLOSE,
                                icon_color=ft.colors.RED_500,
                                on_click=lambda e, tid=t['id']: self._remove_treatment(tid),
                                tooltip="Eliminar tratamiento"
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10
                    ),
                    margin=ft.margin.only(bottom=5)
                ) for t in self.selected_treatments
            ]
        self.page.update()
    
    def _reset_treatment_search(self):
        """Resetea la búsqueda de tratamientos y la lista de seleccionados"""
        self.treatment_search.value = ""
        self.treatment_search.controls = []
        self.selected_treatments = []
        self.form_data['treatments'] = [] # Limpiar también en form_data
        self._update_treatments_display() # Asegurarse de que la UI se actualice
        self.treatment_search.close_view()
        self.page.update()
    
    def handle_treatment_search_submit(self, e):
        """Maneja la selección directa con Enter"""
        if self.treatment_search.controls and len(self.treatment_search.controls) > 0:
            selected_data = self.treatment_search.controls[0].data
            self.select_treatment(selected_data['id'], selected_data['name'], selected_data['price'])
    
    """Metodos para la barra de busqueda de clientes"""
    
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
            show_error(self.page, f"Error en búsqueda de clientes: {str(e)}")

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
        
        # Cargar tratamientos asociados a la cita
        appointment_treatments = get_appointment_treatments(self.appointment_id)
        if appointment_treatments:
            self.selected_treatments = appointment_treatments
            self.form_data['treatments'] = appointment_treatments
            self._update_treatments_display() # Renderizar los tratamientos cargados

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
                    status=self.form_data['status'],
                    treatments=self.form_data['treatments'] # Pasar tratamientos al actualizar
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
                    self.form_data['treatments'], # Pasar tratamientos al crear
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
        # Asegurarse de que la visualización de tratamientos inicial se renderice
        self._update_treatments_display() 

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
                        ft.Divider(),
                        ft.Text("Tratamientos", weight="bold"),
                        self._build_search_treatment_row(),
                        self.treatments_column, # Aquí se mostrarán los tratamientos seleccionados
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
