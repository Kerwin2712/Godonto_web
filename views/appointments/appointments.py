import flet as ft
from datetime import datetime, time
from services.appointment_service import AppointmentService, get_appointment_treatments
from utils.alerts import AlertManager
from models.appointment import Appointment

class AppointmentsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.appointment_service = AppointmentService()
        
        # Estado de la vista (eliminamos current_page y items_per_page ya que no hay paginación)
        self.total_items = 0 # Todavía útil para conteo, pero no para paginación
        self.filters = {
            'date_from': None,
            'date_to': None,
            'status': None,
            'search_term': None
        }
        
        # Componentes UI
        self.appointment_grid = ft.GridView(
            expand=True,
            runs_count=3,
            max_extent=400,
            child_aspect_ratio=1.2,
            spacing=15,
            run_spacing=15,
        )
        
        # Inicializar componentes
        self._init_date_pickers()
        self._init_search_controls()
        
        # Cargar datos iniciales
        self.update_appointments()

    def _init_date_pickers(self):
        """Inicializa los selectores de fecha"""
        self.date_picker_from = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=self._handle_date_from_change
        )
        
        self.date_picker_to = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=self._handle_date_to_change
        )
        
        self.page.overlay.extend([self.date_picker_from, self.date_picker_to])
        
        self.date_from_button = ft.ElevatedButton(
            "Desde",
            icon=ft.icons.CALENDAR_MONTH,
            on_click=lambda e: self.page.open(self.date_picker_from),
        )
        
        self.date_to_button = ft.ElevatedButton(
            "Hasta",
            icon=ft.icons.CALENDAR_MONTH,
            on_click=lambda e: self.page.open(self.date_picker_to),
        )

    def _init_search_controls(self):
        """Inicializa los controles de búsqueda mejorados"""
        self.search_bar = ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.BLUE_ACCENT,
            bar_hint_text="Buscar por nombre o cédula",
            view_hint_text="Filtrar citas...",
            bar_leading=ft.Icon(ft.icons.SEARCH),
            controls=[],
            width=300,
            expand=True,
            on_change=self._handle_search_change,
            on_submit=lambda e: self._handle_search_submit(e)
        )
        
        self.status_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option("Todas"),
                ft.dropdown.Option("pending", "Pendiente"),
                ft.dropdown.Option("completed", "Completada"),
                ft.dropdown.Option("cancelled", "Cancelada")
            ],
            value="Todas",
            on_change=lambda e: self.update_filters(),
            width=150
        )

    def update_filters(self):
        """Actualiza los filtros basados en los controles UI"""
        self.filters.update({
            'search_term': self.search_bar.value if self.search_bar.value else None,
            'status': self.status_dropdown.value if self.status_dropdown.value != "Todas" else None
        })
        self.update_appointments()

    def apply_search_filter(self, term):
        """Aplica un filtro de búsqueda"""
        self.search_bar.value = term
        self.search_bar.close_view(term)
        self.update_filters()

    def clear_date_filters(self, e):
        """Limpia los filtros de fecha"""
        self.filters['date_from'] = None
        self.filters['date_to'] = None
        self.date_from_button.text = "Desde"
        self.date_to_button.text = "Hasta"
        self.update_appointments()

    def update_appointments(self):
        """Actualiza la lista de citas con los filtros actuales"""
        # Eliminamos limit y offset para obtener todas las citas
        appointments = self.appointment_service.get_appointments(
            filters=self.filters
        )
        self.total_items = self.appointment_service.count_appointments(self.filters)
        self._render_appointments(appointments)

    def _render_appointments(self, appointments):
        """Renderiza las citas en el grid"""
        self.appointment_grid.controls.clear()
        
        if not appointments:
            self._render_empty_state()
            return
            
        for appt in appointments:
            self.appointment_grid.controls.append(
                self._build_appointment_card(appt)
            )
        
        self.page.update()

    def _render_empty_state(self):
        """Muestra estado cuando no hay citas"""
        self.appointment_grid.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.INFO_OUTLINE, size=40),
                    ft.Text("No se encontraron citas", 
                           text_align=ft.TextAlign.CENTER)
                ], 
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                col={"sm": 12, "md": 6, "lg": 4},
                alignment=ft.alignment.center
            )
        )
        self.page.update()

    def _build_appointment_card(self, appointment: Appointment):
        """Construye una tarjeta de cita individual"""
        # Obtener los tratamientos asociados a la cita
        treatments = get_appointment_treatments(appointment.id)
        
        # Construir la lista de controles para los tratamientos y calcular el total
        treatments_controls = []
        total_price = 0.0
        if treatments:
            treatments_controls.append(ft.Divider(height=1))
            treatments_controls.append(ft.Text("Tratamientos:", size=12, weight=ft.FontWeight.BOLD))
            for t in treatments:
                item_total = t.get('price', 0.0) * t.get('quantity', 1)
                total_price += item_total
                treatments_controls.append(
                    ft.Text(f"- {t['name']} ({t.get('quantity', 1)}): ${item_total:.2f}", size=12)
                )
            treatments_controls.append(ft.Divider(height=1))
            treatments_controls.append(
                ft.Text(f"Total Tratamientos: ${total_price:.2f}", size=14, weight=ft.FontWeight.BOLD)
            )
        else:
            treatments_controls.append(ft.Text("Sin tratamientos", size=12, italic=True))

        # Añadir la sección de notas
        notes_controls = []
        if appointment.notes:
            notes_controls.append(ft.Divider(height=1))
            notes_controls.append(ft.Text("Notas:", size=12, weight=ft.FontWeight.BOLD))
            notes_controls.append(ft.Text(appointment.notes, size=12, selectable=True))
        else:
            notes_controls.append(ft.Divider(height=1))
            notes_controls.append(ft.Text("Sin notas", size=12, italic=True))

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.ListTile(
                        title=ft.Text(appointment.client_name, 
                                     weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"Cédula: {appointment.client_cedula}"),
                        # Añadir un menú de opciones aquí
                        trailing=ft.PopupMenuButton(
                            icon=ft.icons.MORE_VERT,
                            items=[
                                ft.PopupMenuItem(
                                    text="Editar",
                                    icon=ft.icons.EDIT,
                                    on_click=lambda e, a=appointment: self.edit_appointment(a.id)
                                ),
                                ft.PopupMenuItem(
                                    text="Eliminar",
                                    icon=ft.icons.DELETE,
                                    on_click=lambda e, a=appointment: self.confirm_delete(a.id, a.client_name)
                                ),
                            ]
                        )
                    ),
                    ft.Divider(height=1),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.CALENDAR_TODAY, size=16),
                                ft.Text(appointment.date.strftime('%d/%m/%Y'), size=14)
                            ]),
                            ft.Row([
                                ft.Icon(ft.icons.ACCESS_TIME, size=16),
                                # Asegúrate de que appointment.time sea un objeto datetime.time o str
                                ft.Text(appointment.time.strftime('%H:%M') if isinstance(appointment.time, time) else appointment.time, size=14)
                            ]),
                            ft.Row([
                                ft.Icon(ft.icons.INFO_OUTLINE, size=16),
                                ft.Text(appointment.status.capitalize(), 
                                       color=self._get_status_color(appointment.status),
                                       size=14)
                            ]),
                            # Sección de tratamientos
                            *treatments_controls,
                            # Sección de notas
                            *notes_controls
                        ], spacing=5),
                        padding=ft.padding.symmetric(horizontal=10)
                    ),
                ], spacing=5),
                padding=10,
            ),
            elevation=8,
            col={"sm": 12, "md": 6, "lg": 4}
        )

    def _get_status_color(self, status):
        """Obtiene el color según el estado de la cita"""
        status_colors = {
            'pending': ft.colors.ORANGE,
            'completed': ft.colors.GREEN,
            'cancelled': ft.colors.RED
        }
        return status_colors.get(status.lower(), ft.colors.GREY)

    def edit_appointment(self, appointment_id):
        """Navega al formulario de edición"""
        self.page.go(f"/appointment_form/{appointment_id}")

    def confirm_delete(self, appointment_id, client_name):
        """Muestra confirmación para eliminar cita"""
        AlertManager.show_confirmation(
            page=self.page,
            title="Confirmar eliminación",
            content=f"¿Eliminar cita con {client_name}?",
            on_confirm=lambda: self._delete_appointment(appointment_id, client_name)
        )

    def _delete_appointment(self, appointment_id, client_name):
        """Elimina una cita"""
        try:
            self.appointment_service.delete_appointment(appointment_id)
            self.update_appointments()
            AlertManager.show_success(self.page, f"Cita con {client_name} eliminada")
        except Exception as e:
            AlertManager.show_error(self.page, f"Error al eliminar: {str(e)}")

    def _handle_date_from_change(self, e):
        """Maneja el cambio en la fecha de inicio"""
        if self.date_picker_from.value:
            self.filters['date_from'] = self.date_picker_from.value
            self.date_from_button.text = self.date_picker_from.value.strftime("%d/%m/%Y")
            self.update_appointments()

    def _handle_date_to_change(self, e):
        """Maneja el cambio en la fecha de fin"""
        if self.date_picker_to.value:
            self.filters['date_to'] = self.date_picker_to.value
            self.date_to_button.text = self.date_picker_to.value.strftime("%d/%m/%Y")
            self.update_appointments()

    def _build_search_row(self):
        """Construye la fila de búsqueda mejorada"""
        return ft.ResponsiveRow([
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 4},
                controls=[
                    ft.Row([
                        self.search_bar,
                        ft.IconButton(
                            icon=ft.icons.CLEAR,
                            tooltip="Limpiar búsqueda",
                            on_click=self._reset_search,
                            icon_color=ft.colors.GREY_600
                        )
                    ], spacing=5)
                ]
            ),
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 3},
                controls=[
                    ft.Row([
                        self.date_from_button,
                        self.date_to_button,
                        ft.IconButton(
                            ft.icons.CLEAR,
                            tooltip="Limpiar fechas",
                            on_click=self.clear_date_filters
                        )
                    ], spacing=5)
                ]
            ),
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 3},
                controls=[self.status_dropdown]
            ),
            ft.Column(
                col={"sm": 12, "md": 6, "lg": 2},
                controls=[
                    ft.ElevatedButton(
                        "Nueva Cita",
                        icon=ft.icons.ADD,
                        on_click=lambda e: self.page.go("/appointment_form"),
                        expand=True
                    )
                ]
            )
        ], spacing=10)

    def _handle_search_change(self, e):
        """Maneja el cambio en la búsqueda"""
        search_term = e.control.value.strip()
        if not search_term:
            self.search_bar.controls = []
            self.page.update()
            return
        
        # Actualizar filtros inmediatamente mientras se escribe
        self.filters['search_term'] = search_term if search_term else None
        self.update_appointments()
    
    def _handle_search_submit(self, e):
        """Maneja la búsqueda al presionar Enter"""
        if self.search_bar.controls and len(self.search_bar.controls) > 0:
            self.search_bar.close_view(self.search_bar.value)
        self.update_filters()
    
    def _reset_search(self, e):
        """Resetea la búsqueda"""
        self.search_bar.value = ""
        self.search_bar.controls = []
        self.filters['search_term'] = None
        self.update_appointments()
    
    def build_view(self):
        """Construye la vista completa y la hace responsive"""
        return ft.View(
            "/appointments",
            controls=[
                ft.AppBar(
                    title=ft.Text("Gestión de Citas", weight="bold"),
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        tooltip="Volver al Dashboard",
                        on_click=lambda e: self.page.go("/dashboard"),
                    )
                ),
                ft.ResponsiveRow([
                    ft.Column(
                        col={"sm": 12, "md": 12, "lg": 12},
                        controls=[
                            ft.Container(
                                content=ft.Column([
                                    # Fila de búsqueda y filtros
                                    self._build_search_row(),
                                    
                                    # Grid de citas
                                    ft.Container(
                                        content=ft.Column([
                                            self.appointment_grid,
                                        ]),
                                        padding=ft.padding.only(top=20),
                                        expand=True
                                    )
                                ], spacing=20),
                                padding=20,
                                expand=True
                            )
                        ]
                    )
                ]),
            ],
            scroll=ft.ScrollMode.AUTO,
            padding=0
        )


def appointments_view(page: ft.Page):
    """Función de fábrica para crear la vista de citas"""
    return AppointmentsView(page).build_view()
