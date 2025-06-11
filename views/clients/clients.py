import flet as ft
from services.client_service import ClientService
from utils.alerts import show_error, show_success
from models.client import Client
from services.appointment_service import AppointmentService
from services.payment_service import PaymentService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ClientsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.client_service = ClientService()
        self.all_clients = []
        
        # Componentes UI
        self.search_bar = self._build_search_bar()
        self.client_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        
        # Cargar datos iniciales
        self.load_clients()
    
    def _build_search_bar(self):
        """Construye el componente SearchBar responsive con búsqueda en tiempo real"""
        return ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.GREY_300,
            bar_hint_text="Buscar por nombre o cédula...",
            view_hint_text="Filtrar clientes...",
            bar_leading=ft.Icon(ft.icons.SEARCH),
            controls=[],
            width=300,
            expand=True,
            on_change=self._handle_search_change,  # Cambio clave para búsqueda en tiempo real
            on_submit=lambda e: self._handle_search_submit(e)
        )
    
    def _handle_search_change(self, e):
        """Maneja el cambio en la búsqueda en tiempo real"""
        search_term = e.control.value.strip()
        
        if not search_term:
            # Si no hay término de búsqueda, mostrar todos los clientes
            self.update_clients()
            return
        
        # Usar el servicio para buscar con unaccent
        filtered_clients = self.client_service.get_all_clients(search_term)
        
        # Actualizar la lista de clientes mostrados
        self.update_clients(filtered_clients)
        
        # Actualizar las sugerencias del SearchBar
        self.search_bar.controls = [
            ft.ListTile(
                title=ft.Text(c.name),
                subtitle=ft.Text(f"Cédula: {c.cedula}"),
                on_click=lambda e, c=c: self._select_client(c),
                data=c
            )
            for c in filtered_clients[:10]  # Limitar a 10 sugerencias
        ]
        self.search_bar.update()
    
    def _handle_search_submit(self, e):
        """Maneja la búsqueda al presionar Enter"""
        if self.search_bar.controls and len(self.search_bar.controls) > 0:
            self.search_bar.close_view(self.search_bar.value)
        self._handle_search_change(e)  # Reutilizamos la misma lógica
    
    def _build_view_controls(self):
        """Construye los controles superiores responsive"""
        return ft.ResponsiveRow(
            controls=[
                # Search bar y botones
                ft.Column(
                    col={"sm": 12, "md": 8},
                    controls=[
                        ft.Row(
                            controls=[
                                self.search_bar,
                                ft.IconButton(
                                    icon=ft.icons.CLEAR,
                                    tooltip="Limpiar",
                                    on_click=lambda e: self._reset_search(),
                                    icon_color=ft.colors.GREY_600
                                ),
                            ],
                            spacing=5,
                            alignment=ft.MainAxisAlignment.START,
                            expand=True,
                        )
                    ],
                    expand=True
                ),
                # Botón de nuevo cliente
                ft.Column(
                    col={"sm": 12, "md": 4},
                    controls=[
                        ft.FilledButton(
                            icon=ft.icons.ADD,
                            text="Nuevo Cliente",
                            on_click=lambda e: self.page.go("/client_form"),
                            expand=True,
                            height=45
                        )
                    ],
                    alignment=ft.MainAxisAlignment.END
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )
    
    def _build_icon_button(self, icon, tooltip, on_click, color=None):
        """Helper para construir botones de icono"""
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=on_click,
            icon_color=color or ft.colors.BLUE_700,
        )
    
    def _build_client_card(self, client: Client):
        """Construye una tarjeta de cliente responsive"""
        return ft.ResponsiveRow(
            controls=[
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
                                # Primera fila: Información básica
                                ft.ResponsiveRow(
                                    controls=[
                                        ft.Column(
                                            col={"sm": 12, "md": 8},
                                            controls=[
                                                ft.Text(client.name, weight="bold", size=16),
                                                ft.Text(f"Cédula: {client.cedula}", size=14),
                                                ft.Text(f"Tel: {client.phone}", size=14),
                                            ],
                                            spacing=5,
                                        ),
                                        # Segunda columna: Botones de acción
                                        ft.Column(
                                            col={"sm": 12, "md": 4},
                                            controls=[
                                                ft.Row(
                                                    controls=[
                                                        ft.PopupMenuButton(
                                                            icon=ft.icons.MORE_VERT,
                                                            items=[
                                                                ft.PopupMenuItem(
                                                                    text="Registrar Pago",
                                                                    icon=ft.icons.PAYMENT,
                                                                    on_click=lambda e, c=client: self._show_payment_dialog(c)
                                                                ),
                                                                ft.PopupMenuItem(
                                                                    text="Registrar Deuda",
                                                                    icon=ft.icons.MONEY_OFF,
                                                                    on_click=lambda e, c=client: self._show_debt_dialog(c)
                                                                ),
                                                                ft.PopupMenuItem(
                                                                    text="Ver Historial",
                                                                    icon=ft.icons.HISTORY,
                                                                    on_click=lambda e, c=client: self._show_history(c)
                                                                ),
                                                                ft.PopupMenuItem(),
                                                                ft.PopupMenuItem(
                                                                    text="Generar Presupuesto",
                                                                    icon=ft.icons.PICTURE_AS_PDF,
                                                                    on_click=lambda e, c=client: self.page.go(f"/presupuesto/{c.id}")
                                                                ),
                                                                ft.PopupMenuItem(),  # Separador
                                                                ft.PopupMenuItem(
                                                                    text="Editar",
                                                                    icon=ft.icons.EDIT,
                                                                    on_click=lambda e, c=client: self._edit_client(c)
                                                                ),
                                                                ft.PopupMenuItem(
                                                                    text="Eliminar",
                                                                    icon=ft.icons.DELETE,
                                                                    on_click=lambda e, c=client: self._delete_client(c)
                                                                ),
                                                            ]
                                                        )
                                                    ],
                                                    alignment=ft.MainAxisAlignment.END
                                                )
                                            ]
                                        )
                                    ],
                                    spacing=10,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                                ),
                                # Email (se muestra en una línea separada en móviles)
                                ft.ResponsiveRow(
                                    controls=[
                                        ft.Column(
                                            col={"sm": 12},
                                            controls=[
                                                ft.Text(client.email, size=14),
                                            ]
                                        )
                                    ]
                                )
                            ],
                            spacing=10,
                        ),
                        padding=15,
                    ),
                    elevation=1,
                    margin=ft.margin.symmetric(vertical=5),
                )
            ]
        )
    
    def _show_payment_dialog(self, client):
        """Muestra diálogo para registrar un pago y aplica a deudas pendientes."""
        
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
                
                # Obtener el resumen de deudas pendientes antes del pago
                # Ahora usamos 'total_pending_debt'
                initial_summary = payment_service.get_payment_summary(client.id)
                initial_pending_debt = initial_summary.get('total_pending_debt', 0.0)
                
                # Registrar el pago (que ahora incluye la lógica de aplicación a deudas)
                success, message = payment_service.create_payment(
                    client_id=client.id,
                    amount=amount,
                    method=method,
                    notes=notes
                )
                
                if success:
                    # Obtener el nuevo resumen para el mensaje de feedback
                    new_summary = payment_service.get_payment_summary(client.id)
                    new_pending_debt = new_summary.get('total_pending_debt', 0.0)
                    
                    debt_applied_by_this_payment = initial_pending_debt - new_pending_debt
                    
                    if debt_applied_by_this_payment > 0.001: # Usar una pequeña tolerancia para flotantes
                        msg = f"Pago de ${amount:,.2f} registrado. Se aplicó ${debt_applied_by_this_payment:,.2f} a deudas pendientes."
                        if new_pending_debt > 0:
                            msg += f" Saldo pendiente de deudas: ${new_pending_debt:,.2f}"
                        else:
                            msg += " Todas las deudas pendientes han sido cubiertas."
                    else:
                        msg = f"Pago de ${amount:,.2f} registrado para {client.name}."
                        if initial_pending_debt > 0:
                            msg += f" Aún quedan deudas pendientes: ${initial_pending_debt:,.2f}."
                        else:
                            msg += " No había deudas pendientes a las cuales aplicar el pago."

                    show_success(self.page, msg)
                    self.load_clients() # Recargar clientes para actualizar la vista de deudas/pagos
                    close_dialog(e)
                else:
                    show_error(self.page, message) # Mostrar el mensaje de error del servicio
            except ValueError:
                show_error(self.page, "Ingrese un monto válido")
            except Exception as e:
                logger.error(f"Error al registrar pago: {str(e)}")
                show_error(self.page, f"Error al registrar pago: {str(e)}")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Registrar Pago para {client.name}"),
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

    def _show_debt_dialog(self, client):
        """Muestra diálogo para registrar una deuda"""
        
        amount_field = ft.TextField(label="Monto", keyboard_type=ft.KeyboardType.NUMBER)
        description_field = ft.TextField(label="Descripción", multiline=True)
        # Añadir un DatePicker para due_date
        due_date_picker = ft.DatePicker(
            first_date=datetime.now(),
            last_date=datetime(2030, 12, 31)
        )
        self.page.overlay.append(due_date_picker)
        due_date_text = ft.Text("Seleccionar Fecha de Vencimiento (opcional)")
        
        def pick_due_date(e):
            due_date_picker.on_change = lambda _: update_due_date_text()
            self.page.open(due_date_picker)
            self.page.update()

        def update_due_date_text():
            if due_date_picker.value:
                due_date_text.value = f"Vence: {due_date_picker.value.strftime('%d/%m/%Y')}"
            else:
                due_date_text.value = "Seleccionar Fecha de Vencimiento (opcional)"
            self.page.update()
        
        def close_dialog(e):
            dialog.open = False
            # Remover el datepicker del overlay cuando se cierra el diálogo
            if due_date_picker in self.page.overlay:
                self.page.overlay.remove(due_date_picker)
            self.page.update()
        
        def handle_submit(e):
            try:
                amount = float(amount_field.value)
                description = description_field.value
                due_date = due_date_picker.value.date() if due_date_picker.value else None
                
                PaymentService().create_debt(
                    client_id=client.id,
                    amount=amount,
                    description=description,
                    due_date=due_date # Pasar la fecha de vencimiento
                )
                show_success(self.page, f"Deuda de ${amount:,.2f} registrada para {client.name}")
                self.load_clients() # Recargar clientes para actualizar la vista
                close_dialog(e)
            except ValueError:
                show_error(self.page, "Ingrese un monto válido")
            except Exception as e:
                show_error(self.page, f"Error al registrar deuda: {str(e)}")
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Registrar Deuda para {client.name}"),
            content=ft.Column([
                amount_field,
                description_field,
                ft.Row([
                    ft.ElevatedButton("Fecha de Vencimiento", on_click=pick_due_date, icon=ft.icons.CALENDAR_TODAY),
                    due_date_text
                ], alignment=ft.MainAxisAlignment.START)
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dialog),
                ft.TextButton("Registrar", on_click=handle_submit)
            ]
        )
        self.page.open(dialog)
        dialog.open = True
        self.page.update()

    def _show_history(self, client):
        """Muestra el historial de pagos y deudas del cliente"""
        
        try:
            # Obtener datos del historial
            payments = PaymentService().get_client_payments(client.id)
            debts = PaymentService().get_client_debts(client.id) # Usar la función actualizada
            
            # Construir contenido
            content = ft.Column(scroll=ft.ScrollMode.AUTO, height=400) # Añadir altura fija para scroll
            
            # Sección de pagos
            if payments:
                content.controls.append(ft.Text("PAGOS RECIENTES", weight="bold"))
                for payment in payments:
                    content.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.ATTACH_MONEY, color=ft.colors.GREEN),
                            title=ft.Text(f"${payment['amount']:,.2f}"),
                            subtitle=ft.Text(f"{payment['method']} - {payment['payment_date'].strftime('%d/%m/%Y %H:%M')}")
                        )
                    )
            else:
                content.controls.append(ft.Text("No hay pagos registrados", italic=True))
            
            content.controls.append(ft.Divider())
            
            # Sección de deudas
            if debts:
                content.controls.append(ft.Text("DEUDAS", weight="bold"))
                for debt in debts:
                    debt_status_color = ft.colors.RED if debt['status'] == 'pending' and (debt['amount'] - debt['paid_amount']) > 0.01 else ft.colors.GREEN
                    status_text = "Pendiente"
                    if debt['status'] == 'paid':
                        status_text = "Pagada"
                    elif debt['status'] == 'pending' and (debt['amount'] - debt['paid_amount']) <= 0.01:
                        status_text = "Pagada (Aplicado)" # Si el monto pagado cubre casi todo y sigue pendiente
                    elif debt['status'] == 'pending':
                        status_text = f"Pendiente (${debt['amount'] - debt['paid_amount']:,.2f} restantes)"

                    content.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.MONEY_OFF, color=debt_status_color),
                            title=ft.Text(f"${debt['amount']:,.2f} ({status_text})"),
                            subtitle=ft.Text(f"Descripción: {debt['description']} - Creada: {debt['created_at'].strftime('%d/%m/%Y')} - Vence: {debt['due_date'].strftime('%d/%m/%Y') if debt['due_date'] else 'N/A'} - Pagado: ${debt['paid_amount']:,.2f}")
                        )
                    )
            else:
                content.controls.append(ft.Text("No hay deudas registradas", italic=True))
            
            def close_dialog(e):
                dialog.open = False
                self.page.update()
            
            # Mostrar diálogo
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Historial de {client.name}"),
                content=content,
                actions=[
                    ft.TextButton("Cerrar", on_click=close_dialog)
                ]
            )
            self.page.open(dialog)
            dialog.open = True
            self.page.update()
            
        except Exception as e:
            logger.error(f"Error al cargar historial de {client.name}: {str(e)}")
            show_error(self.page, f"Error al cargar historial: {str(e)}")
    
    def _build_appbar(self):
        """Construye la barra de aplicación responsive"""
        return ft.AppBar(
            title=ft.Text("Gestión de Clientes", weight=ft.FontWeight.BOLD),
            center_title=False,
            bgcolor=ft.colors.SURFACE_VARIANT,
            automatically_imply_leading=False,
            leading=ft.IconButton(
                icon=ft.icons.ARROW_BACK,
                tooltip="Volver al Dashboard",
                on_click=lambda _: self.page.go("/dashboard")
            ),
            actions=[
                ft.IconButton(
                    icon=ft.icons.REFRESH,
                    tooltip="Recargar clientes",
                    on_click=lambda _: self.load_clients()
                )
            ]
        )
    
    def load_clients(self, search_term=None):
        """Carga los clientes desde el servicio"""
        self.all_clients = self.client_service.get_all_clients(search_term)
        self.update_clients()
    
    def update_clients(self, clients=None):
        """Actualiza la lista de clientes mostrados"""
        display_clients = clients or self.all_clients
        self.client_list.controls = [
            self._build_client_card(client) for client in display_clients
        ]
        self.page.update()
    
    def _filter_clients(self, e):
        """Filtra clientes en tiempo real según término de búsqueda"""
        search_term = e.control.value.strip()
        
        if not search_term:
            self.update_clients()
            return
        
        # Usar el servicio para buscar con unaccent
        filtered_clients = self.client_service.get_all_clients(search_term)
        
        # Actualizar la lista de clientes mostrados
        self.update_clients(filtered_clients)
        
        # Actualizar las sugerencias del SearchBar
        self.search_bar.controls = [
            ft.ListTile(
                title=ft.Text(c.name),
                subtitle=ft.Text(f"Cédula: {c.cedula}"),
                on_click=lambda e, c=c: self._select_client(c),
                data=c
            )
            for c in filtered_clients[:10]
        ]
        self.search_bar.update()
    
    def _select_client(self, client: Client):
        """Selecciona un cliente del search bar"""
        self.search_bar.value = f"{client.name} - {client.cedula}"
        self.search_bar.close_view(self.search_bar.value)
        self.update_clients([client])
    
    def _open_search_view(self, e):
        """Abre la vista de sugerencias del search bar"""
        self.search_bar.open_view()
    
    def _reset_search(self, e):
        """Resetea la búsqueda y muestra todos los clientes"""
        self.search_bar.value = ""
        self.search_bar.controls = []
        self.update_clients()
        self.page.update()
    
    def _create_pdf(self, client: Client):
        pass
    
    def _edit_client(self, client: Client):
        """Navega al formulario de edición"""
        self.page.go(f"/client_form/{client.id}")
    
    def _delete_client(self, client: Client):
        """Muestra confirmación para eliminar cliente con verificación de dependencias"""
        def check_dependencies():
            has_appointments = ClientService.has_appointments(client.id)
            has_payments_or_debts = ClientService.has_payments_or_debts(client.id)
            
            if has_appointments or has_payments_or_debts:
                # Mostrar diálogo de confirmación para dependencias
                message = f"El cliente {client.name} tiene "
                dependencies = []
                if has_appointments:
                    dependencies.append("citas programadas")
                if has_payments_or_debts:
                    dependencies.append("pagos/deudas asociados")
                
                message += " y ".join(dependencies) + ".\n¿Desea eliminar todos estos registros también?"
                
                dlg_confirm_dependencies.content = ft.Text(message)
                dlg_confirm_dependencies.actions = [
                    ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(dlg_confirm_dependencies)),
                    ft.TextButton(
                        "Eliminar todo", 
                        on_click=lambda e: [
                            _delete_client_with_dependencies(client), 
                            _close_dialog(dlg_confirm_dependencies)
                        ],
                        style=ft.ButtonStyle(color=ft.colors.RED)
                    )
                ]
                self.page.open(dlg_confirm_dependencies)
                dlg_confirm_dependencies.open = True
                self.page.update()
            else:
                # No hay dependencias, proceder con eliminación normal
                _delete_client_confirmed(client)

        def _delete_client_confirmed(client: Client):
            try:
                if self.client_service.delete_client(client.id):
                    self.all_clients.remove(client)
                    self.update_clients()
                    show_success(self.page, f"Cliente {client.name} eliminado")
                else:
                    show_error(self.page, "No se pudo eliminar el cliente")
            except Exception as e:
                show_error(self.page, f"Error al eliminar: {str(e)}")

        def _delete_client_with_dependencies(client: Client):
            try:
                if self.client_service.delete_client_with_dependencies(client.id):
                    self.all_clients.remove(client)
                    self.update_clients()
                    show_success(
                        self.page, 
                        f"Cliente {client.name} y todos sus registros asociados eliminados"
                    )
                else:
                    show_error(self.page, "No se pudo eliminar el cliente y sus registros")
            except Exception as e:
                show_error(self.page, f"Error al eliminar: {str(e)}")

        def _close_dialog(dialog):
            dialog.open = False
            self.page.update()

        # Diálogo principal
        dlg_main = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar eliminación"),
            content=ft.Text(
                f"¿Está seguro de eliminar al cliente {client.name}?\n"
                f"Cédula: {client.cedula}\n"
                f"Esta acción no se puede deshacer."
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: _close_dialog(dlg_main)),
                ft.TextButton(
                    "Confirmar", 
                    on_click=lambda e: [_close_dialog(dlg_main), check_dependencies()],
                    style=ft.ButtonStyle(color=ft.colors.RED)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # Diálogo para dependencias (se crea pero no se muestra todavía)
        dlg_confirm_dependencies = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registros asociados encontrados"),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(dlg_main)
        dlg_main.open = True
        self.page.update()
    
    def build_view(self):
        """Construye la vista completa responsive"""
        return ft.View(
            "/clients",
            controls=[
                self._build_appbar(),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._build_view_controls(),
                            ft.Divider(height=20),
                            ft.Container(
                                content=self.client_list,
                                expand=True,
                                padding=ft.padding.symmetric(horizontal=10),
                            ),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    expand=True,
                ),
            ],
            spacing=0,
            padding=0,
        )


def clients_view(page: ft.Page):
    """Función de fábrica para crear la vista de clientes"""
    return ClientsView(page).build_view()
