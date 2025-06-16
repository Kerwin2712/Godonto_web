# views/clients/history.py
import flet as ft
from services.history_service import HistoryService
from services.treatment_service import TreatmentService
from utils.alerts import show_success, show_error
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ClientHistoryView:
    def __init__(self, page: ft.Page, client_id: int):
        self.page = page
        self.client_id = client_id
        self.history_service = HistoryService()
        self.treatment_service = TreatmentService()
        self.client_history = None
        self.selected_treatment_for_add = None # Para el combobox de añadir tratamiento

        # Componentes UI
        self.client_info_card = ft.Card()
        self.medical_records_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        # Cambiado de client_treatments_list a all_client_treatments_list
        self.all_client_treatments_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.appointments_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.quotes_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Controles para añadir nuevo tratamiento al historial del cliente
        self.new_history_treatment_dropdown = ft.Dropdown(
            label="Seleccionar Tratamiento",
            hint_text="Buscar y seleccionar tratamiento",
            options=[],
            on_change=self._on_treatment_selected,
            expand=True
        )
        self.new_history_treatment_notes = ft.TextField(
            label="Notas del tratamiento (opcional)", 
            multiline=True, 
            min_lines=2, 
            max_lines=5, 
            expand=True
        )
        self.new_history_treatment_date_picker = ft.DatePicker(
            first_date=datetime(2000, 1, 1),
            last_date=datetime.now()
        )
        self.page.overlay.append(self.new_history_treatment_date_picker)
        
        self.new_history_treatment_date_text = ft.Text("Fecha del tratamiento: Hoy")
        self.new_medical_record_title = ft.TextField(label="Título/Descripción", multiline=True)
        self.new_medical_record_reason = ft.TextField(label="Motivo de la visita", multiline=True)
        self.new_medical_record_diagnosis = ft.TextField(label="Diagnóstico", multiline=True)
        self.new_medical_record_procedures = ft.TextField(label="Procedimientos realizados", multiline=True)
        self.new_medical_record_prescription = ft.TextField(label="Prescripción", multiline=True)
        self.new_medical_record_notes = ft.TextField(label="Notas adicionales", multiline=True)
        
        self.new_medical_record_next_appointment_picker = ft.DatePicker(
            first_date=datetime.now(),
            last_date=datetime(2030, 12, 31)
        )
        self.page.overlay.append(self.new_medical_record_next_appointment_picker)
        self.new_medical_record_next_appointment_text = ft.Text("Próxima cita: N/A")

        self.load_history_data()

    def _on_treatment_selected(self, e):
        """Maneja la selección de un tratamiento del dropdown."""
        # El valor del dropdown es el ID del tratamiento
        if e.control.value:
            try:
                self.selected_treatment_for_add = int(e.control.value)
            except ValueError:
                self.selected_treatment_for_add = None
        else:
            self.selected_treatment_for_add = None
        self.page.update()

    def _pick_new_history_treatment_date(self, e):
        """Abre el DatePicker para la fecha del tratamiento de historial."""
        self.new_history_treatment_date_picker.on_change = self._update_new_history_treatment_date_text
        self.new_history_treatment_date_picker.on_dismiss = lambda _: self.page.update()
        self.new_history_treatment_date_picker.open = True
        self.page.update()

    def _update_new_history_treatment_date_text(self, e):
        """Actualiza el texto de la fecha del tratamiento de historial."""
        if self.new_history_treatment_date_picker.value:
            self.new_history_treatment_date_text.value = (
                f"Fecha del tratamiento: {self.new_history_treatment_date_picker.value.strftime('%d/%m/%Y')}"
            )
        else:
            self.new_history_treatment_date_text.value = "Fecha del tratamiento: Hoy"
        self.page.update()

    def _pick_new_medical_record_next_appointment_date(self, e):
        """Abre el DatePicker para la próxima cita del registro médico."""
        self.new_medical_record_next_appointment_picker.on_change = self._update_new_medical_record_next_appointment_text
        self.new_medical_record_next_appointment_picker.on_dismiss = lambda _: self.page.update()
        self.new_medical_record_next_appointment_picker.open = True
        self.page.update()

    def _update_new_medical_record_next_appointment_text(self, e):
        """Actualiza el texto de la próxima cita del registro médico."""
        if self.new_medical_record_next_appointment_picker.value:
            self.new_medical_record_next_appointment_text.value = (
                f"Próxima cita: {self.new_medical_record_next_appointment_picker.value.strftime('%d/%m/%Y')}"
            )
        else:
            self.new_medical_record_next_appointment_text.value = "Próxima cita: N/A"
        self.page.update()

    def _add_client_treatment(self, e, treatment_id_to_add: Optional[int] = None,
                           appointment_id_to_add: Optional[int] = None, # <-- NUEVO PARÁMETRO
                           quote_id_to_add: Optional[int] = None,       # <-- NUEVO PARÁMETRO
                           quantity_to_mark_completed: int = 1):        # <-- NUEVO PARÁMETRO (por defecto 1)
        """Añade un tratamiento directamente al historial del cliente o marca uno como completado."""
        if treatment_id_to_add is None and self.selected_treatment_for_add is None:
            show_error(self.page, "Por favor, seleccione un tratamiento.")
            return
        
        # Usar el treatment_id pasado por argumento si existe, de lo contrario, el seleccionado en el dropdown
        final_treatment_id = treatment_id_to_add if treatment_id_to_add is not None else self.selected_treatment_for_add

        notes = self.new_history_treatment_notes.value
        if treatment_id_to_add is not None: # Si se está marcando como completado desde un elemento existente
            found_treatment = next((t for t in self.client_history["all_client_treatments"]
                                    if t['id'] == treatment_id_to_add and
                                    t.get('appointment_id') == appointment_id_to_add and
                                    t.get('quote_id') == quote_id_to_add), None)
            if found_treatment:
                original_notes = found_treatment.get('notes', '')
                source_origin = found_treatment.get('source', 'N/A')
                notes_prefix = f"Completado (origen: {source_origin})."
                notes = f"{notes_prefix} {original_notes}" if original_notes else notes_prefix
            else:
                notes = "Completado."
        else: # Si es una adición manual desde el dropdown
            notes = self.new_history_treatment_notes.value


        treatment_date = self.new_history_treatment_date_picker.value.date() if self.new_history_treatment_date_picker.value else date.today()
        # Si se está marcando un tratamiento ya existente, la fecha debe ser hoy si no se ha seleccionado otra
        if treatment_id_to_add is not None and self.new_history_treatment_date_picker.value is None:
            treatment_date = date.today()

        success, message = self.history_service.add_client_treatment(
            client_id=self.client_id,
            treatment_id=final_treatment_id,
            notes=notes,
            treatment_date=treatment_date,
            appointment_id=appointment_id_to_add, # <-- PASAR ESTE VALOR
            quote_id=quote_id_to_add,             # <-- PASAR ESTE VALOR
            quantity_to_mark_completed=quantity_to_mark_completed # <-- PASAR ESTE VALOR
        )

        if success:
            show_success(self.page, message)
            self.load_history_data() # Síncrono ahora
            # Limpiar campos solo si fue una adición manual
            if treatment_id_to_add is None:
                self.new_history_treatment_dropdown.value = None
                self.new_history_treatment_notes.value = ""
                self.new_history_treatment_date_picker.value = None
                self.new_history_treatment_date_text.value = "Fecha del tratamiento: Hoy"
            self.page.update()
        else:
            show_error(self.page, message)

    def _add_medical_record(self, e):
        """Añade un nuevo registro médico."""
        description = self.new_medical_record_title.value
        reason_for_visit = self.new_medical_record_reason.value
        diagnosis = self.new_medical_record_diagnosis.value
        procedures_performed = self.new_medical_record_procedures.value
        prescription = self.new_medical_record_prescription.value
        notes = self.new_medical_record_notes.value
        next_appointment_date = self.new_medical_record_next_appointment_picker.value.date() if self.new_medical_record_next_appointment_picker.value else None

        if not description:
            show_error(self.page, "La descripción/título del registro médico es obligatoria.")
            return

        success, message = self.history_service.add_medical_record(
            client_id=self.client_id,
            description=description,
            reason_for_visit=reason_for_visit,
            diagnosis=diagnosis,
            procedures_performed=procedures_performed,
            prescription=prescription,
            notes=notes,
            next_appointment_date=next_appointment_date
        )

        if success:
            show_success(self.page, message)
            self.load_history_data() # Síncrono ahora
            # Limpiar campos
            self.new_medical_record_title.value = ""
            self.new_medical_record_reason.value = ""
            self.new_medical_record_diagnosis.value = ""
            self.new_medical_record_procedures.value = ""
            self.new_medical_record_prescription.value = ""
            self.new_medical_record_notes.value = ""
            self.new_medical_record_next_appointment_picker.value = None
            self.new_medical_record_next_appointment_text.value = "Próxima cita: N/A"
            self.page.update()
        else:
            show_error(self.page, message)

    def _delete_client_treatment(self, e, treatment_record_id: int):
        """Confirma y elimina un tratamiento de client_treatments."""
        def confirm_delete(dialog_e):
            if dialog_e.control.data: # Si se confirmó
                success, message = self.history_service.delete_client_treatment(treatment_record_id)
                if success:
                    show_success(self.page, message)
                    self.load_history_data() # Síncrono ahora
                else:
                    show_error(self.page, message)
            self.page.close(confirm_dialog)

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación"),
            content=ft.Text("¿Está seguro de que desea eliminar este tratamiento del historial del cliente?"),
            actions=[
                ft.TextButton("No", on_click=confirm_delete, data=False),
                ft.TextButton("Sí", on_click=confirm_delete, data=True, style=ft.ButtonStyle(color=ft.colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(confirm_dialog)
        self.page.update()


    def _delete_medical_record(self, e, record_id: int):
        """Confirma y elimina un registro de historial médico."""
        def confirm_delete(dialog_e):
            if dialog_e.control.data: # Si se confirmó
                success, message = self.history_service.delete_medical_record(record_id)
                if success:
                    show_success(self.page, message)
                    self.load_history_data() # Síncrono ahora
                else:
                    show_error(self.page, message)
            self.page.close(confirm_dialog)

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Eliminación"),
            content=ft.Text("¿Está seguro de que desea eliminar este registro médico?"),
            actions=[
                ft.TextButton("No", on_click=confirm_delete, data=False),
                ft.TextButton("Sí", on_click=confirm_delete, data=True, style=ft.ButtonStyle(color=ft.colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(confirm_dialog)
        self.page.update()


    def load_history_data(self): # Ya no es asíncrona
        """Carga todos los datos del historial del cliente."""
        self.client_history = self.history_service.get_client_full_history(self.client_id)
        
        if not self.client_history["client_info"]:
            show_error(self.page, "Cliente no encontrado.")
            self.page.go("/clients") # Redirigir si el cliente no existe
            return
        
        self._update_client_info_card()
        self._update_medical_records_list()
        self._update_all_client_treatments_list() # Usar la nueva función
        self._update_appointments_list()
        self._update_quotes_list()
        self._populate_treatment_dropdown() # Esta función también fue ajustada para ser síncrona si es necesario
        self.page.update()

    def _populate_treatment_dropdown(self):
        """Rellena el dropdown de tratamientos."""
        all_treatments = self.treatment_service.get_all_treatments(active_only=True)
        self.new_history_treatment_dropdown.options = [
            ft.dropdown.Option(
                key=str(t.id), # Key debe ser string para Dropdown
                text=f"{t.name} (${t.price:,.2f})"
            ) for t in all_treatments
        ]
        self.page.update()

    def _update_client_info_card(self):
        """Actualiza la tarjeta de información del cliente."""
        client = self.client_history["client_info"]
        if client:
            self.client_info_card.content = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(client.name, weight="bold", size=20),
                        ft.Text(f"Cédula: {client.cedula}", size=16),
                        ft.Text(f"Teléfono: {client.phone}", size=16),
                        ft.Text(f"Email: {client.email}", size=16),
                        ft.Text(f"Dirección: {client.address if client.address else 'N/A'}", size=16),
                        ft.Text(f"Registrado el: {client.created_at.strftime('%d/%m/%Y')}", size=14, color=ft.colors.GREY_600)
                    ],
                    spacing=8
                ),
                padding=20
            )
        else:
            self.client_info_card.content = ft.Text("No se pudo cargar la información del cliente.")
        self.page.update()
    
    def _update_medical_records_list(self):
        """Actualiza la lista de registros médicos."""
        self.medical_records_list.controls.clear()
        if self.client_history["medical_records"]:
            for record in self.client_history["medical_records"]:
                self.medical_records_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row([
                                        ft.Text(f"Fecha: {record['record_date'].strftime('%d/%m/%Y %H:%M')}", weight="bold"),
                                        ft.IconButton(
                                            icon=ft.icons.DELETE,
                                            icon_color=ft.colors.RED_500,
                                            tooltip="Eliminar registro médico",
                                            on_click=lambda e, r_id=record['id']: self._delete_medical_record(e, r_id)
                                        )
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                    ft.Text(f"Descripción: {record['description']}"),
                                    ft.Text(f"Motivo: {record['reason_for_visit'] if record['reason_for_visit'] else 'N/A'}"),
                                    ft.Text(f"Diagnóstico: {record['diagnosis'] if record['diagnosis'] else 'N/A'}"),
                                    ft.Text(f"Procedimientos: {record['procedures_performed'] if record['procedures_performed'] else 'N/A'}"),
                                    ft.Text(f"Prescripción: {record['prescription'] if record['prescription'] else 'N/A'}"),
                                    ft.Text(f"Notas: {record['notes'] if record['notes'] else 'N/A'}"),
                                    ft.Text(f"Próxima cita: {record['next_appointment_date'].strftime('%d/%m/%Y') if record['next_appointment_date'] else 'N/A'}"),
                                ],
                                spacing=5
                            ),
                            padding=15
                        ),
                        margin=ft.margin.symmetric(vertical=5)
                    )
                )
        else:
            self.medical_records_list.controls.append(ft.Text("No hay registros médicos."))
        self.page.update()

    def _update_all_client_treatments_list(self):
        """Actualiza la lista unificada de tratamientos (pendientes y completados)."""
        self.all_client_treatments_list.controls.clear()
        if self.client_history["all_client_treatments"]:
            for ct in self.client_history["all_client_treatments"]:
                status_color = ft.colors.GREEN_700 if ct['status'] == 'completed' else ft.colors.AMBER_700
                
                # Calcular cantidades para el texto del estado
                completed_qty = ct.get('completed_quantity', 0)
                total_qty = ct.get('total_quantity', 1)
                
                status_text = f"Completado ({completed_qty} de {total_qty})"
                if completed_qty < total_qty:
                    status_text = f"Pendiente ({completed_qty} de {total_qty})"

                # Definir notes_display y date_display dentro del bucle
                notes_display = f"Notas: {ct['notes']}" if ct['notes'] else "Notas: N/A"
                date_display = f"Fecha: {ct['treatment_date'].strftime('%d/%m/%Y')}" if ct['treatment_date'] else "Fecha: N/A"

                actions = []
                if completed_qty < total_qty:
                    actions.append(
                        ft.IconButton(
                            icon=ft.icons.CHECK_CIRCLE,
                            icon_color=ft.colors.GREEN_500,
                            tooltip=f"Marcar 1 unidad como Completada", # El tooltip ahora es más genérico
                            on_click=lambda e, 
                                            _treatment_id=ct['id'],
                                            _appointment_id=ct.get('appointment_id'), # Pasar appointment_id
                                            _quote_id=ct.get('quote_id'):             # Pasar quote_id
                                self._add_client_treatment(e, 
                                                            treatment_id_to_add=_treatment_id, 
                                                            appointment_id_to_add=_appointment_id, 
                                                            quote_id_to_add=_quote_id,
                                                            quantity_to_mark_completed=1) # Marca 1 unidad por click
                        )
                    )
                # Modificación aquí: el botón de eliminar se muestra si el tratamiento está 'completed'
                # y tiene un 'client_treatment_record_id' (es decir, está en la tabla client_treatments)
                if ct['status'] == 'completed' and ct['client_treatment_record_id'] is not None:
                    actions.append(
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color=ft.colors.RED_500,
                            tooltip="Eliminar tratamiento de historial",
                            on_click=lambda e, tr_id=ct['client_treatment_record_id']: self._delete_client_treatment(e, tr_id)
                        )
                    )

                self.all_client_treatments_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Row([
                                        ft.Text(f"Tratamiento: {ct['name']}", weight="bold"),
                                        ft.Text(f"Estado: {status_text}", color=status_color), # Usar el status_text actualizado
                                        ft.Row(actions)
                                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                    ft.Text(f"Precio: ${ct['price']:,.2f}"),
                                    # Mostrar la cantidad completada y total aquí
                                    ft.Text(f"Cantidad: {completed_qty} / {total_qty}"), 
                                    ft.Text(notes_display),
                                    ft.Text(date_display),
                                    ft.Text(f"Origen: {ct['source'].capitalize()}", size=12, color=ft.colors.GREY_500)
                                ],
                                spacing=5
                            ),
                            padding=15
                        ),
                        margin=ft.margin.symmetric(vertical=5)
                    )
                )
        else:
            self.all_client_treatments_list.controls.append(ft.Text("No hay tratamientos de historial registrados para este cliente."))
        self.page.update()

    def _update_appointments_list(self):
        """Actualiza la lista de citas del cliente."""
        self.appointments_list.controls.clear()
        if self.client_history["appointments"]:
            for appointment in self.client_history["appointments"]:
                # Modificado para incluir la cantidad si está disponible en los tratamientos de la cita
                treatments_text = ", ".join([f"{t['name']} (x{t.get('quantity', 1)})" for t in appointment['treatments']]) if appointment['treatments'] else "Sin tratamientos"
                self.appointments_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"Cita ID: {appointment['id']}", weight="bold"),
                                    ft.Text(f"Fecha: {appointment['date'].strftime('%d/%m/%Y')} {appointment['time']}"),
                                    ft.Text(f"Estado: {appointment['status'].capitalize()}"),
                                    ft.Text(f"Tratamientos: {treatments_text}"),
                                    ft.Text(f"Notas: {appointment['notes'] if appointment['notes'] else 'N/A'}"),
                                ],
                                spacing=5
                            ),
                            padding=15
                        ),
                        margin=ft.margin.symmetric(vertical=5)
                    )
                )
        else:
            self.appointments_list.controls.append(ft.Text("No hay citas registradas para este cliente."))
        self.page.update()

    def _update_quotes_list(self):
        """Actualiza la lista de presupuestos del cliente."""
        self.quotes_list.controls.clear()
        if self.client_history["quotes"]:
            for quote in self.client_history["quotes"]:
                treatments_text = ", ".join([f"{t['name']} (x{t['quantity']})" for t in quote['treatments']]) if quote['treatments'] else "Sin tratamientos"
                self.quotes_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text(f"Presupuesto ID: {quote['id']}", weight="bold"),
                                    ft.Text(f"Fecha: {quote['quote_date'].strftime('%d/%m/%Y')}"),
                                    ft.Text(f"Total: ${quote['total_amount']:,.2f}"),
                                    ft.Text(f"Estado: {quote['status'].capitalize()}"),
                                    ft.Text(f"Tratamientos: {treatments_text}"),
                                    ft.Text(f"Notas: {quote['notes'] if quote['notes'] else 'N/A'}"),
                                ],
                                spacing=5
                            ),
                            padding=15
                        ),
                        margin=ft.margin.symmetric(vertical=5)
                    )
                )
        else:
            self.quotes_list.controls.append(ft.Text("No hay presupuestos registrados para este cliente."))
        self.page.update()

    def build_view(self):
        """Construye la vista completa del historial médico."""
        return ft.View(
            f"/clients/{self.client_id}/history",
            controls=[
                ft.AppBar(
                    title=ft.Text(f"Historial de {self.client_history['client_info'].name if self.client_history and self.client_history['client_info'] else 'Cliente'}", weight=ft.FontWeight.BOLD),
                    center_title=False,
                    bgcolor=ft.colors.SURFACE_VARIANT,
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        tooltip="Volver a Clientes",
                        on_click=lambda _: self.page.go("/clients")
                    ),
                    actions=[
                        ft.IconButton(
                            icon=ft.icons.REFRESH,
                            tooltip="Recargar Historial",
                            on_click=lambda _: self.load_history_data() # Síncrono ahora
                        )
                    ]
                ),
                ft.Container(
                    expand=True,
                    padding=ft.padding.all(15),
                    content=ft.Column(
                        controls=[
                            # Información del Cliente
                            ft.Text("Información del Cliente", size=22, weight="bold"),
                            self.client_info_card,
                            ft.Divider(height=20),

                            # Tratamientos del Historial (Directos al Cliente y Pendientes de Citas/Presupuestos)
                            ft.Text("Tratamientos del Historial", size=22, weight="bold"),
                            ft.Container(self.all_client_treatments_list, expand=True, height=250),
                            ft.Divider(height=20),

                            # Añadir tratamiento al historial del cliente (Movido debajo de la lista de tratamientos)
                            ft.ExpansionTile(
                                title=ft.Text("Añadir Tratamiento al Historial del Cliente", weight="bold"),
                                leading=ft.Icon(ft.icons.MEDICAL_SERVICES),
                                controls=[
                                    self.new_history_treatment_dropdown,
                                    self.new_history_treatment_notes,
                                    ft.Row([
                                        ft.ElevatedButton(
                                            "Seleccionar Fecha",
                                            icon=ft.icons.CALENDAR_MONTH,
                                            on_click=self._pick_new_history_treatment_date
                                        ),
                                        self.new_history_treatment_date_text
                                    ]),
                                    ft.ElevatedButton("Añadir Tratamiento", on_click=self._add_client_treatment),
                                ]
                            ),
                            ft.Divider(height=20),

                            # Secciones de Historial (resto)
                            ft.Text("Registros Médicos", size=22, weight="bold"),
                            ft.Container(self.medical_records_list, expand=True, height=250),
                            ft.Divider(height=20),
                            
                            # Añadir nuevo registro médico (Movido aquí)
                            ft.ExpansionTile(
                                title=ft.Text("Añadir Nuevo Registro Médico", weight="bold"),
                                leading=ft.Icon(ft.icons.ADD_BOX),
                                controls=[
                                    self.new_medical_record_title,
                                    self.new_medical_record_reason,
                                    self.new_medical_record_diagnosis,
                                    self.new_medical_record_procedures,
                                    self.new_medical_record_prescription,
                                    self.new_medical_record_notes,
                                    ft.Row([
                                        ft.ElevatedButton(
                                            "Seleccionar Próxima Cita",
                                            icon=ft.icons.CALENDAR_MONTH,
                                            on_click=self._pick_new_medical_record_next_appointment_date
                                        ),
                                        self.new_medical_record_next_appointment_text
                                    ]),
                                    ft.ElevatedButton("Guardar Registro Médico", on_click=self._add_medical_record),
                                ]
                            ),
                            ft.Divider(height=20),

                            ft.Text("Citas del Cliente", size=22, weight="bold"),
                            ft.Container(self.appointments_list, expand=True, height=250),
                            ft.Divider(height=20),

                            ft.Text("Presupuestos del Cliente", size=22, weight="bold"),
                            ft.Container(self.quotes_list, expand=True, height=250),
                        ],
                        spacing=20,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        scroll=ft.ScrollMode.ADAPTIVE
                    )
                )
            ],
            scroll=ft.ScrollMode.ADAPTIVE
        )

def client_history_view(page: ft.Page, client_id: int):
    """Función de fábrica para crear la vista de historial del cliente."""
    return ClientHistoryView(page, client_id).build_view()

