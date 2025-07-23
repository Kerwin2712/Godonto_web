import flet as ft
from datetime import datetime, time
from typing import Optional, List
from services.appointment_service import (
    get_appointment_by_id,
    create_appointment,
    update_appointment,
    validate_appointment_time,
    search_clients,
    get_appointment_treatments
)
from services.treatment_service import search_treatment
from services.dentist_service import DentistService # Importar el servicio de dentistas
import logging
from utils.alerts import show_error, show_success
from utils.date_utils import to_local_time

logger = logging.getLogger(__name__)

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
            'treatments': [],
            'dentist_id': None # Nuevo: para almacenar el ID del dentista seleccionado
        }
        
        self.selected_treatments = []
        self.treatments_column = ft.Column()

        # Se eliminan las columnas separadas para resultados de búsqueda
        # self.treatment_search_results_column = ft.Column()
        # self.client_search_results_column = ft.Column()

        self.treatment_search = self._build_treatment_search()
        self.client_search = self._build_client_search()
        
        # Nuevo: Dropdown para seleccionar dentista
        self.dentist_dropdown = ft.Dropdown(
            label="Dentista",
            options=[], # Se llenará dinámicamente
            expand=True,
            on_change=self._handle_dentist_change
        )
        self._load_dentists_for_dropdown() # Cargar dentistas al inicializar

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
        
        self.date_text = ft.Text("No seleccionada")
        self.time_text = ft.Text("No seleccionada")
        self.selected_client_text = ft.Text(
            "Ningún cliente seleccionado", 
            italic=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        
        self.page.overlay.extend([self.date_picker, self.time_picker])
        
        if self.appointment_id:
            self.load_appointment_data()
        
        self._update_treatments_display()

    def _load_dentists_for_dropdown(self):
        """Carga los dentistas activos para el Dropdown."""
        try:
            dentists = DentistService.get_all_dentists()
            self.dentist_dropdown.options = [
                ft.dropdown.Option(str(d.id), d.name) for d in dentists if d.is_active
            ]
            self.page.update()
        except Exception as e:
            logger.error(f"Error al cargar dentistas para el dropdown: {e}")
            show_error(self.page, "Error al cargar la lista de dentistas.")

    def _handle_dentist_change(self, e):
        """Maneja la selección de un dentista en el Dropdown."""
        self.form_data['dentist_id'] = int(e.control.value) if e.control.value else None
        self.page.update()

    """Metodos para la barra de busqueda de tratamientos"""
    
    def _build_treatment_search(self):
        """Componente para buscar tratamientos"""
        # Colores para SearchBar de tratamientos
        divider_color = ft.colors.GREEN_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREEN_700
        bar_leading_icon_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        view_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        
        return ft.SearchBar(
            view_elevation=4,
            divider_color=divider_color,
            bar_hint_text="Buscar tratamientos...",
            view_hint_text="Seleccione un tratamiento...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.treatment_search.open_view(),
                icon_color=bar_leading_icon_color
            ),
            on_tap=lambda e: self.treatment_search.open_view(),
            # Revertido a 'controls'
            controls=[], 
            expand=True,
            on_change=self.handle_treatment_search_change,
            on_submit=lambda e: self.handle_treatment_search_submit(e),
            bar_text_style=ft.TextStyle(color=view_text_color) # Color del texto en el SearchBar
        )
    
    
    def _build_search_treatment_row(self):
        """Fila de búsqueda responsive con botones de acción"""
        # Colores para los íconos de acción
        icon_color_clear = ft.colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_300

        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        self.treatment_search,
                        ft.IconButton(
                            icon=ft.icons.CLEAR,
                            tooltip="Limpiar búsqueda",
                            on_click=lambda e: self._reset_treatment_search(),
                            icon_color=icon_color_clear
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 12}), # Ocupar todo el ancho para la búsqueda de tratamientos
            ],
            spacing=10,
            run_spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    def handle_treatment_search_change(self, e):
        """Maneja la búsqueda de tratamientos, actualizando los resultados en el SearchBar."""
        search_term = e.control.value.strip()
        
        # Colores para los resultados de búsqueda
        list_tile_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        list_tile_subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        # Limpiar los controles del SearchBar
        self.treatment_search.controls.clear()

        if len(search_term) < 1:
            self.treatment_search.close_view() # Cerrar la vista si no hay texto
            self.treatment_search.update() # Actualizar el SearchBar
            self.page.update()
            return

        try:
            treatments = search_treatment(search_term)
            
            # Añadir los nuevos resultados directamente a los controls del SearchBar
            self.treatment_search.controls.extend([
                ft.ListTile(
                    title=ft.Text(f"{name}", color=list_tile_title_color),
                    subtitle=ft.Text(f"Precio: ${price:.2f}", color=list_tile_subtitle_color), # Formatear precio
                    on_click=lambda e, id=id, name=name, price=price: self.select_treatment(id, name, price),
                    data={'id': id, 'name': name, 'price': price} # Pasar como diccionario
                ) for (id, name, price) in treatments
            ])
            
            # Si hay resultados, asegurar que la vista esté abierta
            if treatments:
                self.treatment_search.open_view()
            else:
                self.treatment_search.close_view() # Cerrar si no hay resultados
            
            self.treatment_search.update() # Actualizar el SearchBar para reflejar los nuevos controls
            self.page.update() # Actualizar la página
        except Exception as e:
            show_error(self.page, f"Error en búsqueda de tratamientos: {str(e)}")
    
    def select_treatment(self, treatment_id: int, name: str, price: float):
        """Añade un tratamiento seleccionado a la lista con una cantidad inicial de 1."""
        # Verificar si el tratamiento ya está seleccionado
        existing_treatment = next((t for t in self.selected_treatments if t['id'] == treatment_id), None)
        if existing_treatment:
            show_error(self.page, "Este tratamiento ya ha sido añadido. Puedes ajustar su cantidad.")
            self.treatment_search.close_view()
            self.page.update()
            return

        selected_treatment_data = {'id': treatment_id, 'name': name, 'price': price, 'quantity': 1} # Cantidad inicial 1
        self.selected_treatments.append(selected_treatment_data)
        self.form_data['treatments'].append(selected_treatment_data)

        self._update_treatments_display()
        self.treatment_search.value = ""
        self.treatment_search.controls.clear() # Limpiar resultados directamente del SearchBar
        self.treatment_search.close_view()
        self.page.update()

    def _remove_treatment(self, treatment_id: int):
        """Elimina un tratamiento de la lista de seleccionados."""
        self.selected_treatments = [t for t in self.selected_treatments if t['id'] != treatment_id]
        self.form_data['treatments'] = [t for t in self.form_data['treatments'] if t['id'] != treatment_id]
        self._update_treatments_display()
        self.page.update()

    def _update_treatment_quantity(self, treatment_id: int, new_quantity: str):
        """Actualiza la cantidad de un tratamiento seleccionado."""
        try:
            quantity = int(new_quantity)
            if quantity < 1:
                show_error(self.page, "La cantidad debe ser al menos 1.")
                return

            for t in self.selected_treatments:
                if t['id'] == treatment_id:
                    t['quantity'] = quantity
                    break
            
            for t_fd in self.form_data['treatments']:
                if t_fd['id'] == treatment_id:
                    t_fd['quantity'] = quantity
                    break
            self.page.update()
        except ValueError:
            show_error(self.page, "La cantidad debe ser un número entero válido.")

    def _increment_treatment_quantity(self, treatment_id: int):
        """Incrementa la cantidad de un tratamiento seleccionado."""
        for t in self.selected_treatments:
            if t['id'] == treatment_id:
                t['quantity'] += 1
                break
        self._update_treatments_display()
        self.page.update()

    def _decrement_treatment_quantity(self, treatment_id: int):
        """Decrementa la cantidad de un tratamiento seleccionado, mínimo 1."""
        for t in self.selected_treatments:
            if t['id'] == treatment_id:
                if t['quantity'] > 1:
                    t['quantity'] -= 1
                else:
                    show_error(self.page, "La cantidad no puede ser menor a 1.")
                break
        self._update_treatments_display()
        self.page.update()
        
    def _update_treatments_display(self):
        """Actualiza la visualización de los tratamientos seleccionados."""
        # Colores para los tratamientos seleccionados
        treatment_card_bgcolor = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        treatment_card_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        icon_color_close = ft.colors.RED_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.RED_300

        if not self.selected_treatments:
            self.treatments_column.controls = [
                ft.Text(
                    "Ningún tratamiento seleccionado",
                    italic=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    color=treatment_card_text_color,
                )
            ]
        else:
            self.treatments_column.controls = [
                ft.Card(
                    content=ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"{t['name']} - ${t['price']:.2f}", color=treatment_card_text_color),
                                ft.Row([
                                    ft.IconButton(
                                        icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
                                        icon_color=ft.colors.RED_500,
                                        on_click=lambda e, tid=t['id']: self._decrement_treatment_quantity(tid),
                                        tooltip="Disminuir cantidad"
                                    ),
                                    ft.TextField(
                                        value=str(t.get('quantity', 1)),
                                        width=60,
                                        height=40,
                                        text_align=ft.TextAlign.CENTER,
                                        keyboard_type=ft.KeyboardType.NUMBER,
                                        on_change=lambda e, tid=t['id']: self._update_treatment_quantity(tid, e.control.value),
                                        dense=True
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.ADD_CIRCLE_OUTLINE,
                                        icon_color=ft.colors.GREEN_500,
                                        on_click=lambda e, tid=t['id']: self._increment_treatment_quantity(tid),
                                        tooltip="Aumentar cantidad"
                                    )
                                ])
                            ], expand=True),
                            ft.IconButton(
                                icon=ft.icons.CLOSE,
                                icon_color=icon_color_close,
                                on_click=lambda e, tid=t['id']: self._remove_treatment(tid),
                                tooltip="Eliminar tratamiento"
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=10,
                        bgcolor=treatment_card_bgcolor,
                        border_radius=5
                    ),
                    margin=ft.margin.only(bottom=5),
                    elevation=1
                ) for t in self.selected_treatments
            ]
    
    def _reset_treatment_search(self):
        """Resetea la búsqueda de tratamientos y la lista de seleccionados."""
        self.treatment_search.value = ""
        self.treatment_search.controls.clear() # Limpiar resultados directamente del SearchBar
        self.selected_treatments = []
        self.form_data['treatments'] = []
        self._update_treatments_display()
        self.treatment_search.close_view()
        self.page.update()
    
    def handle_treatment_search_submit(self, e):
        """Maneja la selección directa con Enter en la búsqueda de tratamientos."""
        if self.treatment_search.controls and len(self.treatment_search.controls) > 0:
            selected_data = self.treatment_search.controls[0].data
            self.select_treatment(selected_data['id'], selected_data['name'], selected_data['price'])
    
    """Metodos para la barra de busqueda de clientes"""
    
    def _build_client_search(self):
        """Construye el componente de búsqueda de clientes responsive."""
        # Colores para SearchBar de clientes
        divider_color = ft.colors.BLUE_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_700
        bar_leading_icon_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        view_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        
        return ft.SearchBar(
            view_elevation=4,
            divider_color=divider_color,
            bar_hint_text="Buscar cliente...",
            view_hint_text="Seleccione un cliente...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.client_search.open_view(),
                icon_color=bar_leading_icon_color
            ),
            on_tap=lambda e: self.client_search.open_view(),
            # Revertido a 'controls'
            controls=[],
            expand=True,
            on_change=self.handle_search_change,
            on_submit=lambda e: self.handle_search_submit(e),
            bar_text_style=ft.TextStyle(color=view_text_color)
        )

    def _build_search_row(self):
        """Fila de búsqueda responsive con botones de acción."""
        # Colores para los íconos de acción y el contenedor de texto del cliente
        icon_color_clear = ft.colors.GREY_600 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_300
        selected_client_bg = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        selected_client_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.selected_client_text.color = selected_client_text_color
        
        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        self.client_search,
                        ft.IconButton(
                            icon=ft.icons.CLEAR,
                            tooltip="Limpiar búsqueda",
                            on_click=lambda e: self._reset_client_search(),
                            icon_color=icon_color_clear
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 8}),
                ft.Column([
                    ft.Container(
                        content=self.selected_client_text,
                        padding=10,
                        bgcolor=selected_client_bg,
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
        """Maneja el cambio en la búsqueda de clientes, actualizando los resultados en el SearchBar."""
        search_term = e.control.value.strip()
        
        # Colores para los resultados de búsqueda
        list_tile_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        list_tile_subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        # Limpiar los controles del SearchBar
        self.client_search.controls.clear()

        if len(search_term) < 1:
            self.client_search.close_view() # Cerrar la vista si no hay texto
            self.client_search.update() # Actualizar el SearchBar
            self.page.update()
            return

        try:
            clients = search_clients(search_term)
            
            # Añadir los nuevos resultados directamente a los controls del SearchBar
            self.client_search.controls.extend([
                ft.ListTile(
                    title=ft.Text(f"{name}", color=list_tile_title_color),
                    subtitle=ft.Text(f"Cédula: {cedula}", color=list_tile_subtitle_color),
                    on_click=lambda e, id=id, name=name, cedula=cedula: self.select_client(id, name, cedula),
                    data=(id, name, cedula)
                ) for (id, name, cedula) in clients
            ])

            
            # Si hay resultados, asegurar que la vista esté abierta
            if clients:
                self.client_search.open_view()
            else:
                self.client_search.close_view() # Cerrar si no hay resultados

            self.client_search.update() # Actualizar el SearchBar para reflejar los nuevos controls
            self.page.update() # Actualizar la página
        except Exception as e:
            show_error(self.page, f"Error en búsqueda de clientes: {str(e)}")

    def handle_search_submit(self, e):
        """Maneja la selección directa con Enter en la búsqueda de clientes."""
        if self.client_search.controls and len(self.client_search.controls) > 0:
            client_id, name, cedula = self.client_search.controls[0].data
            self.select_client(client_id, name, cedula)

    def select_client(self, client_id, name, cedula):
        """Selecciona un cliente de los resultados y actualiza la UI."""
        self.form_data['client_id'] = client_id
        self.client_search.value = f"{name} - {cedula}"
        self.selected_client_text.value = f"{name} (Cédula: {cedula})"
        self.selected_client_text.style = None 
        self.selected_client_text.color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.client_search.close_view()
        self.page.update()

    def _reset_client_search(self):
        """Resetea la búsqueda de clientes y la selección."""
        self.client_search.value = ""
        self.client_search.controls.clear() # Limpiar resultados directamente del SearchBar
        self.form_data['client_id'] = None
        self.selected_client_text.value = "Ningún cliente seleccionado"
        self.selected_client_text.style = ft.TextStyle(italic=True)
        self.selected_client_text.color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        self.client_search.close_view()
        self.page.update()

    def handle_date_change(self, e):
        """Maneja el cambio de fecha seleccionado en el DatePicker."""
        self.form_data['date'] = self.date_picker.value.date()
        self.date_text.value = self.form_data['date'].strftime("%d/%m/%Y") if self.form_data['date'] else "No seleccionada"
        self.page.update()
    
    def handle_time_change(self, e):
        """Maneja el cambio de hora seleccionado en el TimePicker."""
        self.form_data['hour'] = self.time_picker.value
        self.time_text.value = self.form_data['hour'].strftime("%H:%M") if self.form_data['hour'] else "No seleccionada"
        self.page.update()
    
    def load_appointment_data(self):
        """Carga los datos de una cita existente para edición."""
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
            'status': appointment.status.name.lower(), # Asegurarse de guardar como string
            'dentist_id': appointment.dentist_id # Cargar el ID del dentista
        })
        
        self.notes_field.value = self.form_data['notes']
        
        if self.form_data['date']:
            self.date_picker.value = datetime(self.form_data['date'].year, self.form_data['date'].month, self.form_data['date'].day)
            self.date_text.value = self.form_data['date'].strftime("%d/%m/%Y")
        
        if self.form_data['hour']:
            self.time_picker.value = self.form_data['hour']
            self.time_text.value = self.form_data['hour'].strftime("%H:%M")
        
        if self.form_data['client_id']:
            self.client_search.value = f"{appointment.client_name} - {appointment.client_cedula}"
            self.selected_client_text.value = f"{appointment.client_name} (Cédula: {appointment.client_cedula})"
            self.selected_client_text.style = None
        
        # Seleccionar el dentista en el dropdown
        if self.form_data['dentist_id']:
            self.dentist_dropdown.value = str(self.form_data['dentist_id'])
        
        # Cargar tratamientos asociados a la cita
        appointment_treatments = get_appointment_treatments(self.appointment_id)
        if appointment_treatments:
            self.selected_treatments = [{**t, 'quantity': t.get('quantity', 1)} for t in appointment_treatments]
            self.form_data['treatments'] = self.selected_treatments
            self._update_treatments_display()

        self.page.update()
    
    def handle_save(self, e):
        """Maneja el guardado de la cita, validando datos y llamando al servicio."""
        try:
            # Validar campos requeridos
            if not all([self.form_data['client_id'], self.form_data['date'], self.form_data['hour'], self.form_data['dentist_id']]):
                show_error(self.page, "Cliente, dentista, fecha y hora son requeridos")
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
                    treatments=self.form_data['treatments'],
                    dentist_id=self.form_data['dentist_id'] # Pasar dentist_id
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
                    self.form_data['treatments'],
                    self.form_data['notes'],
                    self.form_data['dentist_id'] # Pasar dentist_id
                )
                if success:
                    show_success(self.page, "Cita creada exitosamente")
                    self.page.go("/appointments")
                else:
                    show_error(self.page, message)
        
        except Exception as e:
            logger.error(f"Error al guardar cita: {str(e)}")
            show_error(self.page, f"Error al guardar: {str(e)}")
    
    def _build_date_time_controls(self):
        """Construye controles de fecha y hora responsive."""
        # Colores para el texto de fecha/hora y los botones
        text_label_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        date_time_container_bg = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        date_time_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        
        self.date_text.color = date_time_text_color
        self.time_text.color = date_time_text_color

        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Text("Fecha:", weight="bold", color=text_label_color),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.CALENDAR_TODAY,
                            on_click=lambda e: self.page.open(self.date_picker),
                            expand=True,
                            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800,
                                                 color=ft.colors.WHITE)
                        ),
                        ft.Container(
                            content=self.date_text,
                            padding=10,
                            bgcolor=date_time_container_bg,
                            border_radius=5,
                            expand=True
                        )
                    ], spacing=5)
                ], col={"sm": 12, "md": 6}),
                ft.Column([
                    ft.Text("Hora:", weight="bold", color=text_label_color),
                    ft.Row([
                        ft.ElevatedButton(
                            "Seleccionar",
                            icon=ft.icons.ACCESS_TIME,
                            on_click=lambda e: self.page.open(self.time_picker),
                            expand=True,
                            style=ft.ButtonStyle(bgcolor=ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_800,
                                                 color=ft.colors.WHITE)
                        ),
                        ft.Container(
                            content=self.time_text,
                            padding=10,
                            bgcolor=date_time_container_bg,
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
        """Construye botones de acción responsive."""
        # Colores para los botones de acción
        save_button_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_900
        save_button_color = ft.colors.WHITE
        cancel_button_border_color = ft.colors.GREY_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_300
        cancel_button_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE


        return ft.ResponsiveRow(
            controls=[
                ft.Column([
                    ft.Row([
                        ft.ElevatedButton(
                            "Guardar",
                            icon=ft.icons.SAVE,
                            on_click=self.handle_save,
                            style=ft.ButtonStyle(
                                bgcolor=save_button_bgcolor,
                                color=save_button_color
                            ),
                            expand=True
                        ),
                        ft.OutlinedButton(
                            "Cancelar",
                            icon=ft.icons.CANCEL,
                            on_click=lambda e: self.page.go("/appointments"),
                            expand=True,
                            style=ft.ButtonStyle(
                                side=ft.border.BorderSide(1, cancel_button_border_color),
                                color=cancel_button_color
                            )
                        )
                    ], spacing=10)
                ], col={"sm": 12, "md": 6, "lg": 4}, 
                alignment=ft.MainAxisAlignment.END)
            ],
            alignment=ft.MainAxisAlignment.END
        )
    
    def build_view(self):
        """Construye y devuelve la vista del formulario responsive."""
        # Colores para el AppBar y el fondo general del formulario
        appbar_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        appbar_text_color = ft.colors.WHITE
        main_content_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        divider_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        
        self._update_treatments_display() 

        return ft.View(
            "/appointment_form" if not self.appointment_id else f"/appointment_form/{self.appointment_id}",
            controls=[
                ft.AppBar(
                    title=ft.Text("Editar Cita" if self.appointment_id else "Nueva Cita", color=appbar_text_color),
                    bgcolor=appbar_bgcolor,
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: self.page.go("/appointments"),
                        tooltip="Volver al Dashboard",
                        icon_color=appbar_text_color
                    )
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Seleccionar Cliente", weight="bold", color=section_title_color),
                        self._build_search_row(),
                        ft.Divider(color=divider_color),
                        ft.Text("Seleccionar Dentista", weight="bold", color=section_title_color), # Nuevo título
                        self.dentist_dropdown, # Nuevo: Dropdown para dentistas
                        ft.Divider(color=divider_color),
                        ft.Text("Información de la Cita", weight="bold", color=section_title_color),
                        self._build_date_time_controls(),
                        ft.Text("Notas:", weight="bold", color=section_title_color),
                        self.notes_field, 
                        ft.Divider(color=divider_color),
                        ft.Text("Tratamientos", weight="bold", color=section_title_color),
                        self._build_search_treatment_row(),
                        self.treatments_column,
                        self._build_action_buttons()
                    ], 
                    spacing=20,
                    expand=True),
                    padding=20,
                    expand=True,
                    bgcolor=main_content_bgcolor
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            padding=0
        )

def appointment_form_view(page: ft.Page, appointment_id: Optional[int] = None):
    """Función de fábrica para crear la vista del formulario de citas."""
    return AppointmentFormView(page, appointment_id).build_view()
