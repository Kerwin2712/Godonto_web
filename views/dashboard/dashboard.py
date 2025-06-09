import flet as ft
from datetime import datetime
from core.database import Database
from services.appointment_service import AppointmentService, get_appointment_treatments, get_appointment_by_id # Importar get_appointment_by_id
from services.client_service import ClientService
from services.stats_service import StatsService
from services.payment_service import PaymentService # Importar PaymentService
from utils.date_utils import format_date
from utils.widgets import build_stat_card
import logging

logger = logging.getLogger(__name__)


class DashboardView:
    def __init__(self, page: ft.Page):
        self.page = page
        # Suscribirse a eventos
        AppointmentService().subscribe(self)
        self.current_date = datetime.now()
        self.upcoming_appointments = []
        self.recent_clients = []
        self.stats = {}
        
        # Inicializar servicios
        self.appointment_service = AppointmentService()
        self.client_service = ClientService()
        self.stats_service = StatsService()
        self.payment_service = PaymentService() # Inicializar PaymentService
        
        # Cargar datos iniciales
        self.load_data()
    
    def on_event(self, event_type, data):
        """Maneja eventos de actualización"""
        if event_type == 'APPOINTMENT_STATUS_CHANGED':
            # Recargar datos
            self.load_data()
            
            # Actualizar la vista actual si estamos en el dashboard
            if self.page.views and self.page.views[-1].route == "/dashboard":
                self.page.views[-1] = self.build_view()
            
            self.page.update()
    
    def load_data(self):
        """Carga todos los datos necesarios para el dashboard"""
        logger.info("Cargando datos para el dashboard...")
        try:
            self.upcoming_appointments = self.appointment_service.get_upcoming_appointments(limit=5)
            logger.info(f"Citas próximas cargadas: {len(self.upcoming_appointments)}")
            self.recent_clients = self.client_service.get_recent_clients(limit=5)
            logger.info(f"Clientes recientes cargados: {len(self.recent_clients)}")
            self.stats = self.stats_service.get_dashboard_stats()
            logger.info(f"Estadísticas cargadas: {self.stats}")
        except Exception as e:
            logger.error(f"Error al cargar datos del dashboard: {str(e)}")
            raise

    def build_view(self):
        """Construye la vista completa del dashboard"""
        try:
            # Asegurar que los datos estén cargados
            if not self.upcoming_appointments or not self.stats:
                self.load_data()
                
            view = ft.View(
                "/dashboard",
                controls=[
                    self._build_appbar(),
                    ft.SafeArea(
                        self._build_main_content(),
                        expand=True
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                padding=0,
                spacing=0
            )
            return view
        except Exception as e:
            logger.error(f"Error al construir el dashboard: {str(e)}")
            # Vista de error alternativa
            return ft.View(
                "/dashboard",
                controls=[
                    ft.AppBar(title=ft.Text("Error")),
                    ft.Text("Ocurrió un error al cargar el dashboard. Por favor intente nuevamente."),
                    ft.ElevatedButton("Recargar", on_click=lambda e: self.page.go("/dashboard"))
                ]
            )

    def _build_appbar(self):
        """Construye la barra de aplicación con botón de cerrar sesión"""
        return ft.AppBar(
            title=ft.Text("Inicio"),
            bgcolor=ft.colors.BLUE_700,
            color=ft.colors.WHITE,
            automatically_imply_leading=False,
            leading=ft.PopupMenuButton(
                icon=ft.icons.MENU,
                tooltip="Menú",
                items=[
                    ft.PopupMenuItem(
                        text="Ajustes",
                        icon=ft.icons.SETTINGS,
                        on_click=lambda e: self.page.go("/settings")  # Asume que tendrás una ruta de ajustes
                    ),
                    ft.PopupMenuItem(
                        text="Salir",
                        icon=ft.icons.LANGUAGE,
                        on_click=lambda e: self.page.go("/login")
                    ),
                    ft.PopupMenuItem(
                        text="Temas",
                        icon=ft.icons.COLOR_LENS,
                        on_click=lambda e: self._show_theme_options()
                    )
                ]
            ),
            actions=[
                ft.IconButton(
                    icon=ft.icons.LOGOUT,
                    tooltip="Cerrar sesión",
                    on_click=lambda e: self.page.go("/login"),
                )
            ]
        )

    def _show_theme_options(self):
        """Muestra opciones de tema"""
        # Crear una variable para mantener el estado del tema seleccionado
        selected_theme = ft.Ref[ft.ThemeMode]()
        selected_theme.current = self.page.theme_mode
        
        def change_theme(e):
            # Aplicar el tema seleccionado
            self.page.theme_mode = selected_theme.current
            self._show_success(f"Tema cambiado a {'Claro' if selected_theme.current == ft.ThemeMode.LIGHT else 'Oscuro'}")
            theme_dialog.open = False
            self.page.update()
        
        def on_theme_change(e):
            # Actualizar la referencia cuando cambia la selección
            selected_theme.current = theme_dropdown.value
        
        theme_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option(ft.ThemeMode.LIGHT, "Claro"),
                ft.dropdown.Option(ft.ThemeMode.DARK, "Oscuro"),
            ],
            value=self.page.theme_mode,
            width=200,
            on_change=on_theme_change
        )
        
        theme_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Seleccionar Tema"),
            content=ft.Column([
                theme_dropdown,
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page.close(theme_dialog)),
                ft.TextButton("Aplicar", on_click=change_theme),
            ],
        )
        self.page.open(theme_dialog)
        theme_dialog.open = True
        self.page.update()
    
    def _build_main_content(self):
        """Construye el contenido principal del dashboard"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    self._build_header(),
                    self._build_stats_row(),
                    self._build_content_sections()
                ],
                spacing=25,
                expand=True,
                scroll=ft.ScrollMode.AUTO
            ),
            padding=20,
            expand=True
        )

    def _build_header(self):
        """Construye el encabezado con fecha actual"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text("Panel Principal", size=24, weight="bold"),
                    ft.Text(format_date(self.current_date)),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.only(bottom=15)
        )

    def _build_stats_row(self):
        """Construye la fila de estadísticas"""
        return ft.Container(
            content=ft.Row(
                controls=[
                    build_stat_card("Citas Hoy", self.stats.get('appointments_today', 0), 
                            ft.icons.CALENDAR_TODAY, ft.colors.BLUE_400),
                    build_stat_card("Clientes Nuevos", self.stats.get('new_clients_today', 0), 
                            ft.icons.PERSON_ADD, ft.colors.GREEN_400),
                    build_stat_card("Pendientes", self.stats.get('pending_payments', 0), 
                            ft.icons.PAYMENTS, ft.colors.AMBER_400),
                    build_stat_card("Ingresos", f"${self.stats.get('revenue_today', 0):,.2f}", 
                            ft.icons.ATTACH_MONEY, ft.colors.PURPLE_400)
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=15
            ),
            padding=ft.padding.symmetric(vertical=10)
        )

    def _build_content_sections(self):
        """Construye las secciones de contenido principal"""
        return ft.ResponsiveRow(
            controls=[
                ft.Column(
                    col={"sm": 12, "md": 7}, 
                    controls=[self._build_appointments_section()]
                ),
                ft.Column(
                    col={"sm": 12, "md": 5}, 
                    controls=[self._build_clients_section()],
                    scroll=ft.ScrollMode.AUTO
                )
            ],
            spacing=20,
            expand=True
        )

    def _build_appointments_section(self):
        """Construye la sección de citas"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=self._build_section_header( # Envuelto en Container
                        "Próximas Citas", 
                        "Agregar Cita", 
                        "/appointment_form"
                    )),
                    ft.Divider(height=10),
                    ft.Container(content=self._build_appointment_actions()), # Envuelto en Container
                    ft.Divider(height=10),
                    *[self._build_appointment_card(appt) for appt in self.upcoming_appointments]
                ],
                spacing=15,
                expand=True
            ),
            padding=10,
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.GREY_50,
            expand=True
        )

    def _build_client_card(self, client):
        """Construye una tarjeta horizontal para cada cliente"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.PERSON),
                            title=ft.Text(client.name, size=14),
                            subtitle=ft.Text(f"Cédula: {client.cedula}", size=12),
                        ),
                        ft.Text(f"Tel: {client.phone}", size=12),
                        ft.Text(format_date(client.created_at), size=10)
                    ],
                    spacing=5,
                    tight=True
                ),
                padding=10,
                width=200
            ),
            elevation=1,
            height=110
        )
    
    def _build_clients_section(self):
        """Construye la sección de clientes en disposición horizontal"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=self._build_section_header( # Envuelto en Container
                        "Clientes Recientes", 
                        "Agregar Cliente", 
                        "/client_form"
                    )),
                    ft.Divider(height=10),
                    self._build_client_actions(), # ft.Row es compatible, no necesita Container adicional aquí.
                    ft.Divider(height=5),
                    ft.Container(
                        content=ft.Row(
                            controls=[self._build_client_card(client) for client in self.recent_clients],
                            scroll=ft.ScrollMode.AUTO,
                            spacing=15
                        ),
                        height=120
                    )
                ],
                spacing=15,
                expand=True
            ),
            padding=10,
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.GREY_50,
            expand=True
        )

    def _build_section_header(self, title: str, button_text: str, route: str):
        """
        Construye un encabezado de sección responsive.

        Args:
            title (str): El título que se mostrará en el encabezado.
            button_text (str): El texto que se mostrará en el botón.
            route (str): La ruta a la que se navegará al hacer clic en el botón.

        Returns:
            ft.ResponsiveRow: Un contenedor responsive que incluye un título y un botón.
        """
        return ft.ResponsiveRow(
            controls=[
                ft.Text(title, size=19, weight="bold", col={"sm": 12, "md": 8}, color=ft.colors.BLACK),
                ft.ElevatedButton(
                    button_text,
                    icon=ft.icons.ADD,
                    on_click=lambda e: self.page.go(route),
                    style=ft.ButtonStyle(
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=10)
                    ),
                    col={"sm": 12, "md": 4}
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10
        )

    def _build_appointment_actions(self):
        """Construye los botones de acción para citas"""
        return ft.ResponsiveRow(
            controls=[
                ft.ElevatedButton(
                    "Ver Todas las Citas",
                    icon=ft.icons.LIST,
                    on_click=lambda e: self.page.go("/appointments"),
                    col={"sm": 6, "md": 4},
                    style=ft.ButtonStyle(
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=10)
                    )
                ),
                ft.ElevatedButton(
                    "Ver Calendario",
                    icon=ft.icons.CALENDAR_VIEW_MONTH,
                    on_click=lambda e: self.page.go("/calendar"),
                    col={"sm": 6, "md": 4},
                    style=ft.ButtonStyle(
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=10)
                    )
                ),
                ft.ElevatedButton(
                    "Ver Reportes",
                    icon=ft.icons.ANALYTICS,
                    on_click=lambda e: self.page.go("/reports"),
                    col={"sm": 6, "md": 4},
                    style=ft.ButtonStyle(
                        padding=15,
                        shape=ft.RoundedRectangleBorder(radius=10)
                    )
                )
            ],
            spacing=10
        )

    def _build_client_actions(self):
        """Construye los botones de acción para clientes, incluyendo el de tratamientos"""
        return ft.Row([
            ft.ElevatedButton(
                "Ver Todos los Clientes",
                icon=ft.icons.PEOPLE,
                on_click=lambda e: self.page.go("/clients"),
                style=ft.ButtonStyle(
                    padding=15,
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
            ),
            ft.ElevatedButton(
                "Ver Tratamientos",
                icon=ft.icons.MEDICAL_SERVICES,
                on_click=lambda e: self.page.go("/treatments"),
                style=ft.ButtonStyle(
                    padding=15,
                    shape=ft.RoundedRectangleBorder(radius=10)
                )
            )
        ], spacing=10)

    def _build_appointment_card(self, appointment):
        if not appointment or not hasattr(appointment, 'client_name'):
            return ft.Card(content=ft.Text("Datos de cita no disponibles"))
        
        try:
            status_color = {
                'pending': ft.colors.ORANGE,
                'completed': ft.colors.GREEN,
                'cancelled': ft.colors.RED
            }.get(appointment.status, ft.colors.BLUE)
            
            time_str = appointment.time.strftime("%H:%M") if hasattr(appointment, 'time') else "--:--"
            
            treatments = get_appointment_treatments(appointment.id)
            
            treatments_controls = []
            if treatments:
                treatments_controls.append(ft.Divider(height=1))
                treatments_controls.append(ft.Text("Tratamientos:", size=12, weight=ft.FontWeight.BOLD))
                for t in treatments:
                    treatments_controls.append(
                        ft.Text(f"- {t['name']} (${t['price']:.2f})", size=12)
                    )
            else:
                treatments_controls.append(ft.Text("Sin tratamientos", size=12, italic=True))

            return ft.Card(
                content=ft.Column([
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.ACCESS_TIME, color=status_color),
                        title=ft.Text(appointment.client_name or "Cliente no disponible"),
                        subtitle=ft.Text(f"{time_str} - {appointment.status.capitalize() if appointment.status else 'Sin estado'}"),
                    ),
                    ft.Container(
                        content=ft.Column(treatments_controls, spacing=2),
                        padding=ft.padding.only(left=16, right=16, bottom=10)
                    ),
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                self._build_appointment_menu(appointment)
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            expand=True,
                        ),
                        padding=ft.padding.only(top=5, right=10, bottom=5),
                    ),
                ]),
                elevation=1
            )
        except Exception as e:
            logger.error(f"Error al construir tarjeta de cita: {str(e)}")
            return ft.Card(content=ft.Text("Error al mostrar cita"))

    def _build_appointment_menu(self, appointment):
        """Construye el menú de opciones para una cita"""
        return ft.PopupMenuButton(
            icon=ft.icons.MORE_VERT,
            items=[
                ft.PopupMenuItem(
                    text="Completar",
                    on_click=lambda e: self._confirm_status_change(
                        appointment.id, "completed", appointment.client_name)
                ),
                ft.PopupMenuItem(
                    text="Cancelar",
                    on_click=lambda e: self._confirm_status_change(
                        appointment.id, "cancelled", appointment.client_name)
                ),
                ft.PopupMenuItem(
                    text="Editar",
                    on_click=lambda e: self.page.go(f"/appointment_form/{appointment.id}")
                ),
                ft.PopupMenuItem(
                    text="Eliminar",
                    icon=ft.icons.DELETE,
                    # Eliminado icon_color, ya que no es un argumento válido para PopupMenuItem
                    on_click=lambda e: self._confirm_delete_appointment(appointment.id, appointment.client_name)
                )
            ]
        )

    def _confirm_status_change(self, appointment_id, new_status, client_name):
        """Muestra confirmación para cambiar estado de cita"""
        def handle_confirm(e):
            self._change_appointment_status(appointment_id, new_status)
            e.control.page.dialog.open = False # Acceso directo al diálogo de la página
            e.control.page.update()
        
        self.page.dialog = ft.AlertDialog( # Asegura que el diálogo esté en el overlay de la página
            modal=True,
            title=ft.Text("Confirmar acción"),
            content=ft.Text(f"¿Marcar cita con {client_name} como {new_status}?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(e.control.page.dialog, "open", False)),
                ft.TextButton("Confirmar", on_click=handle_confirm),
            ],
        )
        self.page.open(self.page.dialog) # Abre el diálogo desde la página
        self.page.update()

    def _change_appointment_status(self, appointment_id, new_status):
        """Cambia el estado de una cita"""
        try:
            success = self.appointment_service.update_appointment_status(appointment_id, new_status)
            if success:
                # Si la cita fue cancelada, intentar borrar la deuda asociada
                if new_status == 'cancelled':
                    appointment_details = get_appointment_by_id(appointment_id) # Obtener detalles completos
                    if appointment_details and hasattr(appointment_details, 'client_id'):
                        client_id = appointment_details.client_id
                        treatments = get_appointment_treatments(appointment_id)
                        for t in treatments:
                            debt_description_prefix = f"Tratamiento: {t['name']}"
                            debt_deleted = self.payment_service.delete_debt_by_description_and_client(client_id, debt_description_prefix)
                            if debt_deleted:
                                logger.info(f"Deuda '{debt_description_prefix}' para cliente {client_id} eliminada al cancelar cita {appointment_id}.")
                            else:
                                logger.warning(f"No se encontró deuda '{debt_description_prefix}' para eliminar o falló la eliminación para cliente {client_id} al cancelar cita {appointment_id}.")
                    else:
                        logger.warning(f"No se pudo obtener client_id para la cita {appointment_id} al intentar borrar la deuda.")


                # Recargar datos y actualizar vista
                self.load_data()
                # Forzar actualización de todas las vistas relevantes
                current_route = self.page.views[-1].route if self.page.views else ""
                # Si estamos en el dashboard, actualizamos la vista actual
                if current_route == "/dashboard":
                    self.page.views[-1] = self.build_view()
                self.page.update()
                # Mostrar confirmación
                self._show_success(f"Estado actualizado a {new_status.capitalize()}")
            else:
                self._show_error("No se pudo actualizar el estado")
        except Exception as e:
            logger.error(f"Error al actualizar: {str(e)}")
            self._show_error(f"Error al actualizar: {str(e)}")

    def _confirm_delete_appointment(self, appointment_id: int, client_name: str):
        """Muestra un diálogo de confirmación antes de eliminar una cita."""
        def delete_confirmed(e):
            if e.control.data: # Si el botón "Sí" fue presionado
                self._delete_appointment(appointment_id)
            e.control.page.dialog.open = False # Acceso directo al diálogo de la página
            e.control.page.update()

        self.page.dialog = ft.AlertDialog( # Asegura que el diálogo esté en el overlay de la página
            modal=True,
            title=ft.Text("Confirmar Eliminación de Cita"),
            content=ft.Text(f"¿Está seguro de que desea eliminar la cita de {client_name}? Esta acción no se puede deshacer."),
            actions=[
                ft.TextButton("No", on_click=delete_confirmed, data=False),
                ft.FilledButton("Sí", on_click=delete_confirmed, data=True, style=ft.ButtonStyle(bgcolor=ft.colors.RED_500)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(self.page.dialog) # Abre el diálogo desde la página
        self.page.update()

    def _delete_appointment(self, appointment_id: int):
        """Elimina una cita."""
        try:
            success, message = self.appointment_service.delete_appointment(appointment_id)
            if success:
                self.load_data() # Recargar los datos del dashboard
                current_route = self.page.views[-1].route if self.page.views else ""
                if current_route == "/dashboard":
                    self.page.views[-1] = self.build_view() # Actualizar la vista del dashboard
                self.page.update()
                self._show_success(message)
            else:
                self._show_error(message)
        except Exception as e:
            logger.error(f"Error al eliminar cita: {e}")
            self._show_error(f"Error al eliminar cita: {e}")


    def _show_success(self, message):
        """Muestra un mensaje de éxito"""
        self.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=ft.colors.GREEN,
        )
        self.page.open(self.snack_bar)
        self.page.update()
    
    def _show_error(self, message):
        """Muestra un mensaje de error"""
        dlg = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: setattr(dlg, "open", False))
],
        )
        self.page.open(dlg)
        dlg.open = True
        self.page.update()


def dashboard_view(page: ft.Page):
    """Función de fábrica para la vista del dashboard"""
    dashboard = DashboardView(page)
    return dashboard.build_view()
