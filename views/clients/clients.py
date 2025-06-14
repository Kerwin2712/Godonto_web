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
        
        self.search_bar = self._build_search_bar()
        self.client_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        
        self.load_clients()
    
    def _build_search_bar(self):
        return ft.SearchBar(
            view_elevation=4,
            divider_color=ft.colors.GREY_300,
            bar_hint_text="Buscar por nombre o cédula...",
            view_hint_text="Filtrar clientes...",
            bar_leading=ft.Icon(ft.icons.SEARCH),
            controls=[],
            width=300,
            expand=True,
            on_change=self._handle_search_change,
            on_submit=lambda e: self._handle_search_submit(e)
        )
    
    def _handle_search_change(self, e):
        search_term = e.control.value.strip()
        
        if not search_term:
            self.update_clients()
            self.search_bar.controls.clear()
            self.search_bar.update()
            return
        
        filtered_clients = self.client_service.get_all_clients(search_term)
        
        self.update_clients(filtered_clients)
        
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
    
    def _handle_search_submit(self, e):
        if self.search_bar.open and self.search_bar.controls:
            self.search_bar.close_view(e.control.value)
        self._handle_search_change(e)
    
    def _build_view_controls(self):
        return ft.ResponsiveRow(
            controls=[
                ft.Column(
                    col={"sm": 12, "md": 8},
                    controls=[
                        ft.Row(
                            controls=[
                                self.search_bar,
                                ft.IconButton(
                                    icon=ft.icons.CLEAR,
                                    tooltip="Limpiar",
                                    on_click=lambda e: self._reset_search(e),
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
        return ft.IconButton(
            icon=icon,
            tooltip=tooltip,
            on_click=on_click,
            icon_color=color or ft.colors.BLUE_700,
        )
    
    def _build_client_card(self, client: Client):
        return ft.ResponsiveRow(
            controls=[
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            controls=[
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
                                                                    on_click=lambda e, c=client: self.page.go(f"/clients/{c.id}/history"), # RUTA ACTUALIZADA
                                                                ),
                                                                ft.PopupMenuItem(
                                                                    text="Cuentas",
                                                                    icon=ft.icons.ATTACH_MONEY,
                                                                    on_click=lambda e, c=client: self._show_payments(c)
                                                                ),
                                                                ft.PopupMenuItem(),
                                                                ft.PopupMenuItem(
                                                                    text="Generar Presupuesto",
                                                                    icon=ft.icons.PICTURE_AS_PDF,
                                                                    on_click=lambda e, c=client: self.page.go(f"/presupuesto/{c.id}")
                                                                ),
                                                                ft.PopupMenuItem(),
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
                
                initial_summary = payment_service.get_payment_summary(client.id)
                initial_pending_debt = initial_summary.get('total_pending_debt', 0.0)
                
                success, message = payment_service.create_payment(
                    client_id=client.id,
                    amount=amount,
                    method=method,
                    notes=notes
                )
                
                if success:
                    new_summary = payment_service.get_payment_summary(client.id)
                    new_pending_debt = new_summary.get('total_pending_debt', 0.0)
                    
                    debt_applied_by_this_payment = initial_pending_debt - new_pending_debt
                    
                    if debt_applied_by_this_payment > 0.001:
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
                    self.load_clients()
                    close_dialog(e)
                else:
                    show_error(self.page, message)
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
        amount_field = ft.TextField(label="Monto", keyboard_type=ft.KeyboardType.NUMBER)
        description_field = ft.TextField(label="Descripción", multiline=True)
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
                    due_date=due_date
                )
                show_success(self.page, f"Deuda de ${amount:,.2f} registrada para {client.name}")
                self.load_clients()
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

    def _show_payments(self, client):
        try:
            payments = PaymentService().get_client_payments(client.id)
            debts = PaymentService().get_client_debts(client.id)
            
            content_column = ft.Column(scroll=ft.ScrollMode.AUTO, height=400)
            
            if payments:
                content_column.controls.append(ft.Text("PAGOS RECIENTES", weight="bold"))
                for payment in payments:
                    content_column.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.ATTACH_MONEY, color=ft.colors.GREEN),
                            title=ft.Text(f"${payment['amount']:,.2f}"),
                            subtitle=ft.Text(f"{payment['method']} - {payment['payment_date'].strftime('%d/%m/%Y %H:%M')}"),
                            trailing=ft.PopupMenuButton(
                                icon=ft.icons.MORE_VERT,
                                items=[
                                    ft.PopupMenuItem(
                                        text="Eliminar Pago",
                                        icon=ft.icons.DELETE,
                                        on_click=lambda e, p=payment: self._confirm_delete_payment(p, client)
                                    ),
                                ]
                            )
                        )
                    )
            else:
                content_column.controls.append(ft.Text("No hay pagos registrados", italic=True))
            
            content_column.controls.append(ft.Divider())
            
            if debts:
                content_column.controls.append(ft.Text("DEUDAS", weight="bold"))
                for debt in debts:
                    debt_status_color = ft.colors.RED if debt['status'] == 'pending' and (debt['amount'] - debt['paid_amount']) > 0.01 else ft.colors.GREEN
                    status_text = "Pendiente"
                    if debt['status'] == 'paid':
                        status_text = "Pagada"
                    elif debt['status'] == 'pending' and (debt['amount'] - debt['paid_amount']) <= 0.01:
                        status_text = "Pagada (Aplicado)"
                    elif debt['status'] == 'pending':
                        status_text = f"Pendiente (${debt['amount'] - debt['paid_amount']:,.2f} restantes)"

                    content_column.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.icons.MONEY_OFF, color=debt_status_color),
                            title=ft.Text(f"${debt['amount']:,.2f} ({status_text})"),
                            subtitle=ft.Text(f"Descripción: {debt['description']} - Creada: {debt['created_at'].strftime('%d/%m/%Y')} - Vence: {debt['due_date'].strftime('%d/%m/%Y') if debt['due_date'] else 'N/A'} - Pagado: ${debt['paid_amount']:,.2f}"),
                            trailing=ft.PopupMenuButton( # Añadido el botón de menú para deudas
                                icon=ft.icons.MORE_VERT,
                                items=[
                                    ft.PopupMenuItem(
                                        text="Eliminar Deuda",
                                        icon=ft.icons.DELETE,
                                        on_click=lambda e, d=debt: self._confirm_delete_debt(d, client)
                                    ),
                                ]
                            )
                        )
                    )
            else:
                content_column.controls.append(ft.Text("No hay deudas registradas", italic=True))
            
            def close_dialog(e):
                dialog.open = False
                self.page.update()
            
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(f"Historial de {client.name}"),
                content=content_column,
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
    
    def _confirm_delete_payment(self, payment: dict, client: Client):
        def delete_confirmed(e):
            if e.control.data:
                self._delete_payment(payment, client)
            if self.page.dialog and self.page.dialog.open:
                self.page.dialog.open = False
                self.page.update()

        dialog_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        dialog_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación de Pago", color=dialog_text_color),
            content=ft.Text(f"¿Está seguro de que desea eliminar el pago de ${payment['amount']:,.2f} realizado el {payment['payment_date'].strftime('%d/%m/%Y %H:%M')}?", color=dialog_text_color),
            actions=[
                ft.TextButton("No", on_click=delete_confirmed, data=False,
                              style=ft.ButtonStyle(color=dialog_text_color)),
                ft.FilledButton("Sí", on_click=delete_confirmed, data=True, 
                                style=ft.ButtonStyle(bgcolor=ft.colors.RED_500)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=dialog_bg_color
        )
        self.page.open(self.page.dialog)
        self.page.update()

    def _delete_payment(self, payment: dict, client: Client):
        try:
            success, message = PaymentService().delete_payment(payment['id'])
            if success:
                show_success(self.page, message)
                # Recargar la lista de clientes para actualizar la vista de cuentas
                self._show_payments(client) 
                if self.page.dialog and self.page.dialog.open:
                    self.page.dialog.open = False
                    self.page.update()

            else:
                show_error(self.page, message)
        except Exception as e:
            logger.error(f"Error al eliminar pago: {str(e)}")
            show_error(self.page, f"Error al eliminar pago: {str(e)}")
    
    def _confirm_delete_debt(self, debt: dict, client: Client):
        def delete_confirmed(e):
            if e.control.data:
                self._delete_debt(debt, client)
            if self.page.dialog and self.page.dialog.open:
                self.page.dialog.open = False
                self.page.update()

        dialog_bg_color = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        dialog_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        self.page.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación de Deuda", color=dialog_text_color),
            content=ft.Text(f"¿Está seguro de que desea eliminar la deuda de ${debt['amount']:,.2f} con descripción '{debt['description']}'?", color=dialog_text_color),
            actions=[
                ft.TextButton("No", on_click=delete_confirmed, data=False,
                              style=ft.ButtonStyle(color=dialog_text_color)),
                ft.FilledButton("Sí", on_click=delete_confirmed, data=True, 
                                style=ft.ButtonStyle(bgcolor=ft.colors.RED_500)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=dialog_bg_color
        )
        self.page.open(self.page.dialog)
        self.page.update()

    def _delete_debt(self, debt: dict, client: Client):
        try:
            success, message = PaymentService().delete_debt(debt['id'])
            if success:
                show_success(self.page, message)
                # Recargar la vista de cuentas del cliente para reflejar el cambio
                self._show_payments(client) 
                if self.page.dialog and self.page.dialog.open:
                    self.page.dialog.open = False
                    self.page.update()
            else:
                show_error(self.page, message)
        except Exception as e:
            logger.error(f"Error al eliminar deuda: {str(e)}")
            show_error(self.page, f"Error al eliminar deuda: {str(e)}")

    def _build_appbar(self):
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
        self.all_clients = self.client_service.get_all_clients(search_term)
        self.update_clients()
    
    def update_clients(self, clients=None):
        display_clients = clients or self.all_clients
        self.client_list.controls = [
            self._build_client_card(client) for client in display_clients
        ]
        self.page.update()
    
    def _filter_clients(self, e):
        search_term = e.control.value.strip()
        
        if not search_term:
            self.update_clients()
            self.search_bar.controls.clear()
            self.search_bar.update()
            return
        
        filtered_clients = self.client_service.get_all_clients(search_term)
        
        self.update_clients(filtered_clients)
        
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
        self.search_bar.value = f"{client.name} - {client.cedula}"
        self.search_bar.close_view(self.search_bar.value)
        self.update_clients([client])
        self.search_bar.controls.clear()
        self.search_bar.update()
    
    def _open_search_view(self, e):
        self.search_bar.open_view()
    
    def _reset_search(self, e):
        self.search_bar.value = ""
        self.search_bar.controls.clear()
        self.search_bar.update()
        self.update_clients()
    
    def _create_pdf(self, client: Client):
        pass
    
    def _edit_client(self, client: Client):
        self.page.go(f"/client_form/{client.id}")
    
    def _delete_client(self, client: Client):
        def check_dependencies():
            has_appointments = ClientService.has_appointments(client.id)
            has_payments_or_debts = ClientService.has_payments_or_debts(client.id)
            
            if has_appointments or has_payments_or_debts:
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

        dlg_confirm_dependencies = ft.AlertDialog(
            modal=True,
            title=ft.Text("Registros asociados encontrados"),
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.open(dlg_main)
        dlg_main.open = True
        self.page.update()
    
    def build_view(self):
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
    return ClientsView(page).build_view()

