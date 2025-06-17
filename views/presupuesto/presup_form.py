import flet as ft
from services.client_service import ClientService
from utils.alerts import show_success, show_error
from datetime import datetime, date
import logging
from services.budget_service import BudgetService
from services.quote_service import QuoteService
from services.treatment_service import TreatmentService
from typing import Optional, List # Importar Optional y List para tipos

import os
import asyncio # Necesario para asyncio.sleep

logger = logging.getLogger(__name__)

class PresupFormView:
    def __init__(self, page: ft.Page, client_id: Optional[int] = None, quote_id: Optional[int] = None):
        self.page = page
        self.client_id = client_id
        self.quote_id = quote_id # Para almacenar el ID del presupuesto una vez guardado o si es edición
        self._temp_pdf_data: Optional[dict] = None # Para almacenar datos temporales para el PDF

        # Configurar el FilePicker para la descarga con un handler de resultado
        self.file_picker = ft.FilePicker(on_result=self._on_file_picker_result)
        self.page.overlay.append(self.file_picker) # Añadir el FilePicker al overlay de la página
        self.page.update() # Asegurarse de que el overlay se actualice

        # Lista para almacenar los tratamientos seleccionados con cantidad
        # Cada elemento será un diccionario: {'id': ..., 'name': ..., 'price': ..., 'quantity': ...}
        self.selected_treatments: List[dict] = []
        self.treatments_column = ft.Column() # Columna para mostrar los tratamientos seleccionados
        self.total_amount_text = ft.Text("Total: $0.00", size=18, weight=ft.FontWeight.BOLD)
        self.discount_field = ft.TextField(
            label="Descuento ($)",
            value="0.00",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.RIGHT,
            on_change=self._on_discount_change, # Manejar cambios para recalcular el total
            on_focus=self._handle_discount_focus # Para limpiar el 0.00 al enfocar
        )
        self.current_discount = 0.0 # Variable para almacenar el descuento actual

        # Componente de búsqueda de clientes
        self.client_search = self._build_client_search()
        self.selected_client_text = ft.Text(
            "Ningún cliente seleccionado",
            italic=True,
            overflow=ft.TextOverflow.ELLIPSIS,
        )

        # Componente de búsqueda de tratamientos
        self.treatment_search = self._build_treatment_search()

        # Referencias a los botones de acción
        self.save_budget_button_ref = ft.Ref[ft.FilledButton]()
        self.download_pdf_button_ref = ft.Ref[ft.FilledButton]()

        # Cargar datos si se proporcionó un quote_id (modo edición)
        if self.quote_id:
            self.page.run_task(self._load_quote_data)
        elif self.client_id: # Cargar datos del cliente si es un presupuesto nuevo con cliente preseleccionado
            self.page.run_task(self._load_client_data)
        
        # Inicializar la visualización de tratamientos (vacía al principio o se llenará al cargar quote_data)
        self._update_treatments_display()
        self._update_total_amount() # Asegurarse de que el total inicial sea 0.00


    async def _load_quote_data(self):
        """Carga los datos de un presupuesto existente para edición."""
        try:
            quote_data = QuoteService.get_quote(self.quote_id)
            if quote_data:
                # Cargar cliente
                self.select_client(quote_data['client_id'], quote_data['client_name'], quote_data['client_cedula'])

                # Cargar tratamientos
                self.selected_treatments = [
                    {
                        'id': t['id'],
                        'name': t['name'],
                        'price': t['price'],
                        'quantity': t['quantity'],
                        # Generar clave única al cargar, si no existe.
                        # Esto es vital para manejar tratamientos de la BD que no tienen esta clave.
                        'unique_key': f"{t['id']}-{idx}-{datetime.now().timestamp()}" 
                    } for idx, t in enumerate(quote_data.get('treatments', []))
                ]
                self._update_treatments_display()
                
                # Cargar descuento y actualizar el campo de texto
                self.current_discount = float(quote_data.get('discount', 0.0))
                self.discount_field.value = f"{self.current_discount:.2f}"
                self.discount_field.update()

                self._update_total_amount()

                # Habilitar botones de guardar y PDF
                if self.save_budget_button_ref.current:
                    self.save_budget_button_ref.current.disabled = False
                if self.download_pdf_button_ref.current:
                    self.download_pdf_button_ref.current.disabled = False
                self.page.update()

            else:
                show_error(self.page, f"Presupuesto con ID {self.quote_id} no encontrado.")
                # Si no se encuentra, resetear el formulario
                self.quote_id = None
                self.client_id = None
                self._reset_client_search()
                self.selected_treatments = []
                self._update_treatments_display()
                self._update_total_amount()
                self.page.update()

        except Exception as e:
            logger.error(f"Error al cargar datos del presupuesto {self.quote_id}: {e}")
            show_error(self.page, f"Error al cargar presupuesto: {e}")
            # En caso de error, también resetear para evitar estados inconsistentes
            self.quote_id = None
            self.client_id = None
            self._reset_client_search()
            self.selected_treatments = []
            self._update_treatments_display()
            self._update_total_amount()
            self.page.update()

    def _build_client_search(self):
        """Construye el componente de búsqueda de clientes responsive."""
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
            controls=[],
            expand=True,
            on_change=self.handle_client_search_change,
            on_submit=self.handle_client_search_submit,
            bar_text_style=ft.TextStyle(color=view_text_color)
        )

    def _build_search_client_row(self):
        """Fila de búsqueda responsive con botones de acción para clientes. (Adaptado de appointment_form)"""
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

    def handle_client_search_change(self, e):
        """Maneja el cambio en la búsqueda de clientes, actualizando los resultados en el SearchBar."""
        search_term = e.control.value.strip()

        list_tile_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        list_tile_subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        if len(search_term) < 1:
            e.control.controls = []
            e.control.update()
            return

        try:
            # Usar ClientService para buscar clientes
            clients = ClientService.get_all_clients(search_term=search_term) 
            e.control.controls = [
                ft.ListTile(
                    title=ft.Text(f"{client.name}", color=list_tile_title_color),
                    subtitle=ft.Text(f"Cédula: {client.cedula}", color=list_tile_subtitle_color),
                    on_click=lambda ev, id=client.id, name=client.name, cedula=client.cedula: self.select_client(id, name, cedula),
                    data=(client.id, client.name, client.cedula)
                ) for client in clients
            ]
            e.control.update()
            self.page.update()
        except Exception as ex:
            logger.error(f"Error en búsqueda de clientes: {str(ex)}")
            show_error(self.page, f"Error en búsqueda de clientes: {str(ex)}")

    def handle_client_search_submit(self, e):
        """Maneja la selección directa con Enter en la búsqueda de clientes. (Adaptado de appointment_form)"""
        if self.client_search.controls and len(self.client_search.controls) > 0:
            selected_data = self.client_search.controls[0].data
            self.select_client(selected_data[0], selected_data[1], selected_data[2])

    def select_client(self, client_id, name, cedula):
        """Selecciona un cliente de los resultados y actualiza la UI. (Adaptado de appointment_form)"""
        self.client_id = client_id # Establecer el client_id de la clase
        self.client_search.value = f"{name} - {cedula}"
        self.selected_client_text.value = f"{name} (Cédula: {cedula})"
        self.selected_client_text.style = None
        self.selected_client_text.color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        self.client_search.close_view()
        self.page.update()
        # Si ya hay un cliente seleccionado, habilitar el botón de guardar
        if self.save_budget_button_ref.current:
            self.save_budget_button_ref.current.disabled = False
        # Si ya hay un quote_id (es una edición), también se puede habilitar el botón de PDF
        if self.download_pdf_button_ref.current and self.quote_id is not None and self.selected_treatments: # Añadir check para tratamientos
             self.download_pdf_button_ref.current.disabled = False
        self.page.update()


    def _reset_client_search(self):
        """Resetea la búsqueda de clientes y la selección. (Adaptado de appointment_form)"""
        self.client_search.value = ""
        self.client_search.controls = []
        self.client_id = None # Reiniciar el client_id
        self.selected_client_text.value = "Ningún cliente seleccionado"
        self.selected_client_text.style = ft.TextStyle(italic=True)
        self.selected_client_text.color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        self.client_search.close_view()
        # Deshabilitar ambos botones cuando no hay cliente seleccionado
        if self.save_budget_button_ref.current:
            self.save_budget_button_ref.current.disabled = True
        if self.download_pdf_button_ref.current:
            self.download_pdf_button_ref.current.disabled = True
        self.page.update()


    async def _load_client_data(self):
        """Carga los datos del cliente si es una edición (o si se pasó client_id)"""
        try:
            client_data = ClientService.get_client_by_id(self.client_id)
            if client_data:
                # Usar el método select_client para actualizar la UI consistentemente
                self.select_client(client_data.id, client_data.name, client_data.cedula)
            else:
                show_error(self.page, "Cliente no encontrado.")
                self._reset_client_search() # Limpiar la selección si no se encuentra
        except Exception as e:
            logger.error(f"Error al cargar datos del cliente: {e}")
            show_error(self.page, f"Error al cargar cliente: {e}")

    def _build_treatment_search(self):
        """Componente para buscar tratamientos"""
        divider_color = ft.colors.GREEN_400 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREEN_700
        bar_leading_icon_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        view_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE

        return ft.SearchBar(
            view_elevation=4,
            divider_color=divider_color,
            bar_hint_text="Buscar tratamientos existentes...",
            view_hint_text="Seleccione un tratamiento existente...",
            bar_leading=ft.IconButton(
                icon=ft.icons.SEARCH,
                on_click=lambda e: self.treatment_search.open_view(),
                icon_color=bar_leading_icon_color
            ),
            controls=[],
            expand=True,
            on_change=self._handle_treatment_search_change,
            on_submit=self._handle_treatment_search_submit,
            bar_text_style=ft.TextStyle(color=view_text_color)
        )

    def _handle_treatment_search_change(self, e):
        """Maneja el cambio en la búsqueda de tratamientos existentes"""
        search_term = e.control.value.strip()

        list_tile_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        list_tile_subtitle_color = ft.colors.GREY_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_200

        if len(search_term) < 1:
            e.control.controls = []
            e.control.update()
            return

        try:
            treatments = TreatmentService.get_all_treatments(search_term=search_term)
            e.control.controls = [
                ft.ListTile(
                    title=ft.Text(t.name, color=list_tile_title_color),
                    subtitle=ft.Text(f"${t.price:.2f}", color=list_tile_subtitle_color),
                    on_click=lambda ev, t=t: self._select_treatment(t.id, t.name, t.price),
                    data={'id': t.id, 'name': t.name, 'price': t.price}
                ) for t in treatments
            ]
            e.control.update()
            self.page.update()
        except Exception as ex:
            logger.error(f"Error en búsqueda de tratamientos: {str(ex)}")
            show_error(self.page, f"Error en búsqueda de tratamientos: {str(ex)}")

    def _handle_treatment_search_submit(self, e):
        """Maneja la selección con Enter desde la barra de búsqueda"""
        if e.control.controls and len(e.control.controls) > 0:
            selected_data = e.control.controls[0].data
            self._select_treatment(selected_data['id'], selected_data['name'], selected_data['price'])
        self.treatment_search.value = ""
        self.treatment_search.controls = []
        self.treatment_search.close_view()
        self.page.update()

    def _select_treatment(self, treatment_id: int, name: str, price: float):
        """Selecciona un tratamiento existente y lo añade a la lista"""
        if any(t['id'] == treatment_id for t in self.selected_treatments if t['id'] is not None):
            show_error(self.page, "Este tratamiento ya ha sido añadido al presupuesto.")
            self.treatment_search.close_view()
            self.page.update()
            return

        # Generar una clave única al añadir un nuevo tratamiento
        self.selected_treatments.append({'id': treatment_id, 'name': name, 'price': price, 'quantity': 1, 'unique_key': f"{treatment_id}-{len(self.selected_treatments)}-{datetime.now().timestamp()}"})
        self._update_treatments_display()
        self.treatment_search.value = ""
        self.treatment_search.controls = []
        self.treatment_search.close_view()
        self.page.update()
        self._update_total_amount()

    def _update_total_amount(self):
        """Actualiza el monto total del presupuesto, aplicando el descuento."""
        subtotal = sum(item['price'] * item['quantity'] for item in self.selected_treatments if 'price' in item and 'quantity' in item)
        final_total = subtotal - self.current_discount
        if final_total < 0:
            final_total = 0
        self.total_amount_text.value = f"Total: ${final_total:,.2f}"
        self.page.update()

    def _on_discount_change(self, e: ft.ControlEvent):
        """Maneja el cambio en el campo de descuento."""
        try:
            new_discount = float(e.control.value) if e.control.value.strip() else 0.0
            if new_discount < 0:
                show_error(self.page, "El descuento no puede ser negativo.")
                e.control.value = f"{self.current_discount:.2f}"
                e.control.update()
                return
            self.current_discount = new_discount
            self._update_total_amount()
        except ValueError:
            show_error(self.page, "Por favor, introduce un número válido para el descuento.")
            e.control.value = f"{self.current_discount:.2f}"
            e.control.update()

    def _handle_discount_focus(self, e: ft.ControlEvent):
        """Maneja el foco en el campo de descuento para limpiar el valor por defecto."""
        if e.control.value == "0.00":
            e.control.value = ""
            e.control.update()


    def _remove_treatment(self, unique_key: str):
        """Elimina un tratamiento de la lista de seleccionados por su clave única"""
        self.selected_treatments = [t for t in self.selected_treatments if t.get('unique_key') != unique_key]
        self._update_treatments_display()
        self._update_total_amount()
        self.page.update()
        # Si no quedan tratamientos o el presupuesto no ha sido guardado, deshabilitar el botón de PDF
        if self.download_pdf_button_ref.current:
            self.download_pdf_button_ref.current.disabled = (not self.selected_treatments) or (self.quote_id is None)
            self.page.update()

    def _get_treatment_by_unique_key(self, unique_key: str) -> Optional[dict]:
        """Obtiene un tratamiento de selected_treatments por su unique_key."""
        for item in self.selected_treatments:
            if item.get('unique_key') == unique_key:
                return item
        return None

    def _handle_treatment_name_change(self, e: ft.ControlEvent, item_unique_key: str):
        """Maneja el cambio en el nombre de un tratamiento."""
        item = self._get_treatment_by_unique_key(item_unique_key)
        if item:
            item['name'] = e.control.value
            self.page.update()

    def _handle_treatment_price_change(self, e: ft.ControlEvent, item_unique_key: str):
        """Maneja el cambio en el precio de un tratamiento."""
        item = self._get_treatment_by_unique_key(item_unique_key)
        if item:
            try:
                new_price = float(e.control.value) if e.control.value.strip() else 0.0
                if new_price < 0:
                    show_error(self.page, "El precio no puede ser negativo.")
                    e.control.value = f"{item['price']:.2f}"
                    e.control.update()
                    return

                item['price'] = new_price
                self._update_total_amount()
            except ValueError:
                show_error(self.page, "Por favor, introduce un número válido para el precio.")
                e.control.value = f"{item['price']:.2f}"
                e.control.update()

    def _handle_treatment_price_focus(self, e: ft.ControlEvent):
        """Maneja el foco en el campo de precio."""
        if e.control.value == "0.00":
            e.control.value = ""
            e.control.update()

    def _handle_treatment_quantity_change(self, e: ft.ControlEvent, item_unique_key: str, quantity_field_ref: ft.Ref[ft.TextField]):
        """Maneja el cambio en la cantidad de un tratamiento."""
        item = self._get_treatment_by_unique_key(item_unique_key)
        if item:
            try:
                new_quantity = int(e.control.value) if e.control.value.strip() else 0
                if new_quantity <= 0:
                    show_error(self.page, "La cantidad debe ser mayor a 0.")
                    new_quantity = 1
                    quantity_field_ref.current.value = str(new_quantity)
                    quantity_field_ref.current.update()
                
                item['quantity'] = new_quantity
                self._update_total_amount()
            except ValueError:
                show_error(self.page, "Por favor, introduce un número entero válido para la cantidad.")
                e.control.value = str(item['quantity'])
                e.control.update()

    def _increment_treatment_quantity(self, e: ft.ControlEvent, item_unique_key: str, quantity_field_ref: ft.Ref[ft.TextField]):
        """Incrementa la cantidad de un tratamiento."""
        item = self._get_treatment_by_unique_key(item_unique_key)
        if item:
            item['quantity'] += 1
            quantity_field_ref.current.value = str(item['quantity'])
            quantity_field_ref.current.update()
            self._update_total_amount()

    def _decrement_treatment_quantity(self, e: ft.ControlEvent, item_unique_key: str, quantity_field_ref: ft.Ref[ft.TextField]):
        """Decrementa la cantidad de un tratamiento."""
        item = self._get_treatment_by_unique_key(item_unique_key)
        if item:
            if item['quantity'] > 1:
                item['quantity'] -= 1
                quantity_field_ref.current.value = str(item['quantity'])
                quantity_field_ref.current.update()
            else:
                show_error(self.page, "La cantidad no puede ser menor a 1.")
            self._update_total_amount()


    def _update_treatments_display(self):
        """Actualiza la visualización de los tratamientos seleccionados en la columna"""
        self.treatments_column.controls.clear()

        treatment_card_bgcolor = ft.colors.GREY_100 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_700
        treatment_card_text_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        icon_color_delete = ft.colors.RED_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.RED_300
        icon_color_quantity = ft.colors.BLUE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_300

        if not self.selected_treatments:
            self.treatments_column.controls.append(
                ft.Text(
                    "Ningún tratamiento seleccionado para el presupuesto.",
                    italic=True,
                    color=treatment_card_text_color
                )
            )
        else:
            for idx, t in enumerate(self.selected_treatments):
                # Asegurar que cada tratamiento tenga una unique_key.
                # Esto es crucial si se carga desde la DB donde 'unique_key' no existe inicialmente.
                if 'unique_key' not in t:
                    t['unique_key'] = f"{t.get('id', 'new')}-{idx}-{datetime.now().timestamp()}"

                # Usa Ref para cada TextField de cantidad.
                # También refs para name y price para consistencia, aunque no sean estrictamente necesarios para este bug.
                name_field_ref = ft.Ref[ft.TextField]()
                price_field_ref = ft.Ref[ft.TextField]()
                quantity_field_ref = ft.Ref[ft.TextField]() # Esta es la clave para la cantidad

                self.treatments_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.TextField(
                                                ref=name_field_ref, # Asignar la referencia
                                                label="Nombre del Tratamiento",
                                                value=t['name'],
                                                expand=True,
                                                on_change=lambda e, key=t['unique_key']: self._handle_treatment_name_change(e, key),
                                                read_only=t['id'] is not None # Solo lectura si viene de la DB
                                            ),
                                            ft.TextField(
                                                ref=price_field_ref, # Asignar la referencia
                                                label="Precio ($)",
                                                value=f"{t['price']:.2f}",
                                                width=120,
                                                keyboard_type=ft.KeyboardType.NUMBER,
                                                on_change=lambda e, key=t['unique_key']: self._handle_treatment_price_change(e, key),
                                                on_focus=self._handle_treatment_price_focus,
                                                read_only=t['id'] is not None # Solo lectura si viene de la DB
                                            ),
                                        ],
                                        spacing=10
                                    ),
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.icons.REMOVE,
                                                on_click=lambda e, key=t['unique_key'], q_ref=quantity_field_ref: self._decrement_treatment_quantity(e, key, q_ref),
                                                tooltip="Disminuir cantidad",
                                                icon_color=icon_color_quantity
                                            ),
                                            ft.TextField(
                                                ref=quantity_field_ref, # Asignar la referencia aquí
                                                label="Cantidad",
                                                value=str(t['quantity']),
                                                width=100,
                                                keyboard_type=ft.KeyboardType.NUMBER,
                                                on_change=lambda e, key=t['unique_key'], q_ref=quantity_field_ref: self._handle_treatment_quantity_change(e, key, q_ref),
                                                text_align=ft.TextAlign.CENTER,
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.ADD,
                                                on_click=lambda e, key=t['unique_key'], q_ref=quantity_field_ref: self._increment_treatment_quantity(e, key, q_ref),
                                                tooltip="Aumentar cantidad",
                                                icon_color=icon_color_quantity
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.DELETE,
                                                icon_color=icon_color_delete,
                                                on_click=lambda e, key=t['unique_key']: self._remove_treatment(key),
                                                tooltip="Eliminar tratamiento"
                                            )
                                        ],
                                        spacing=10,
                                        alignment=ft.MainAxisAlignment.END
                                    )
                                ],
                                spacing=5
                            ),
                            padding=10,
                            bgcolor=treatment_card_bgcolor,
                            border_radius=5
                        ),
                        margin=ft.margin.only(bottom=5),
                        elevation=1
                    )
                )
        self.page.update()

    def add_new_treatment_item(self, e=None):
        """Añade un nuevo item de tratamiento vacío para que el usuario lo rellene"""
        # Asegurarse de que el nuevo tratamiento también tenga una unique_key
        self.selected_treatments.append({'id': None, 'name': '', 'price': 0.0, 'quantity': 1, 'unique_key': f"new-{len(self.selected_treatments)}-{datetime.now().timestamp()}"})
        self._update_treatments_display()
        self._update_total_amount()
        self.page.update()

    def _validate_budget_data(self) -> bool:
        """Valida los datos del presupuesto antes de guardar o generar PDF."""
        if self.client_id is None:
            show_error(self.page, "Por favor, seleccione un cliente para generar el presupuesto.")
            return False

        if not self.selected_treatments:
            show_error(self.page, "Debe añadir al menos un tratamiento al presupuesto.")
            return False

        for item in self.selected_treatments:
            if not item['name'].strip():
                show_error(self.page, "Todos los tratamientos deben tener un nombre.")
                return False
            # Validar que el precio sea un número y no negativo
            try:
                price = float(item['price'])
                if price < 0:
                    show_error(self.page, f"El precio para '{item['name']}' no puede ser negativo.")
                    return False
                item['price'] = price # Asegurar que el tipo sea float después de la validación
            except ValueError:
                show_error(self.page, f"El precio para '{item['name']}' no es un número válido.")
                return False

            # Validar que la cantidad sea un entero positivo
            try:
                quantity = int(item['quantity'])
                if quantity <= 0:
                    show_error(self.page, f"La cantidad para '{item['name']}' debe ser un entero positivo.")
                    return False
                item['quantity'] = quantity # Asegurar que el tipo sea int después de la validación
            except ValueError:
                show_error(self.page, f"La cantidad para '{item['name']}' no es un número entero válido.")
                return False
        
        # Validar el descuento
        try:
            discount = float(self.discount_field.value)
            if discount < 0:
                show_error(self.page, "El descuento no puede ser negativo.")
                return False
        except ValueError:
            show_error(self.page, "El valor del descuento no es un número válido.")
            return False

        return True

    async def _save_budget(self, e):
        """Guarda o actualiza el presupuesto en la base de datos."""
        if not self._validate_budget_data():
            return

        try:
            # Obtener el descuento del campo de texto
            discount_to_save = float(self.discount_field.value)

            if self.quote_id: # Es una edición
                success = QuoteService.update_quote(
                    quote_id=self.quote_id,
                    client_id=self.client_id,
                    treatments=self.selected_treatments,
                    expiration_date=None, # Siempre None ya que se eliminó el campo
                    notes=None, # Siempre None ya que se eliminó el campo
                    discount=discount_to_save # Pasar el descuento
                )
                if success:
                    show_success(self.page, f"Presupuesto #{self.quote_id} actualizado exitosamente.")
                else:
                    show_error(self.page, f"No se pudo actualizar el presupuesto #{self.quote_id}.")
            else: # Es un presupuesto nuevo
                self.quote_id = QuoteService.create_quote(
                    client_id=self.client_id,
                    treatments=self.selected_treatments,
                    expiration_date=None, # Siempre None ya que se eliminó el campo
                    notes=None, # Siempre None ya que se eliminó el campo
                    discount=discount_to_save # Pasar el descuento
                )

                if self.quote_id:
                    show_success(self.page, f"Presupuesto #{self.quote_id} guardado exitosamente.")
            
            # Habilitar el botón de PDF solo si el presupuesto se ha guardado/actualizado
            if self.quote_id and self.download_pdf_button_ref.current:
                self.download_pdf_button_ref.current.disabled = False
                self.page.update()

        except Exception as ex:
            logger.error(f"Error al guardar/actualizar presupuesto: {ex}")
            show_error(self.page, f"Error al guardar/actualizar presupuesto: {ex}")

    async def _generate_pdf_and_download(self, e):
        """Prepara los datos y abre el diálogo para guardar el PDF."""
        if not self._validate_budget_data():
            return

        if self.quote_id is None:
            show_error(self.page, "Primero debe guardar el presupuesto para poder generar el PDF.")
            return

        try:
            # Obtener detalles completos del presupuesto y cliente para el PDF
            quote_details = QuoteService.get_quote(self.quote_id)
            client_info = ClientService.get_client_by_id(self.client_id) # Obtener info completa del cliente

            if not quote_details or not client_info:
                show_error(self.page, "Error: No se pudieron obtener los detalles completos del presupuesto o del cliente para generar el PDF.")
                return

            # Preparar los ítems para el PDF, asegurando que todos los campos existan
            items_for_pdf = [
                {
                    "treatment": item.get('name', 'N/A'),
                    "quantity": item.get('quantity', 0),
                    "price": item.get('price', 0.0)
                } for item in quote_details.get('treatments', [])
            ]
            
            self._temp_pdf_data = {
                "quote_id": quote_details['id'],
                "client_name": client_info.name,
                "client_cedula": client_info.cedula,
                "client_phone": client_info.phone,
                "client_email": client_info.email,
                "client_address": client_info.address,
                "items": items_for_pdf,
                "date": quote_details['quote_date'], # Usar la fecha del presupuesto desde la BD
                "total_amount": quote_details['total_amount'],
                "discount": quote_details.get('discount', 0.0) # Incluir el descuento en los datos del PDF
            }

            # Abrir el diálogo para guardar el archivo. El resultado se manejará en _on_file_picker_result
            if self.file_picker and hasattr(self.file_picker, 'save_file') and callable(self.file_picker.save_file):
                self.file_picker.save_file(
                    file_name=f"presupuesto_{client_info.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf",
                    allowed_extensions=["pdf"]
                )
                self.page.update() # Asegurarse de que la UI se actualice después de abrir el diálogo
            else:
                logger.error(f"Error: self.file_picker o su método save_file no está disponible. self.file_picker: {self.file_picker}")
                show_error(self.page, "Error interno: El sistema de guardado de archivos no está listo.")

        except Exception as e:
            logger.error(f"Error al iniciar generación de PDF para presupuesto {self.quote_id}: {e}")
            show_error(self.page, f"Error al preparar el PDF: {e}")

    async def _on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Maneja el resultado del diálogo de FilePicker (la ruta seleccionada)."""
        logger.info(f"Resultado del FilePicker: {e.path}")
        if e.path:
            if self._temp_pdf_data:
                try:
                    BudgetService.generate_pdf_to_path(e.path, self._temp_pdf_data)
                    show_success(self.page, f"PDF generado exitosamente en {e.path}")
                    self._temp_pdf_data = None # Limpiar datos temporales
                except Exception as ex:
                    logger.error(f"Error al generar PDF en _on_file_picker_result: {ex}")
                    show_error(self.page, f"Error al generar PDF: {ex}")
            else:
                show_error(self.page, "Error: Datos del presupuesto no disponibles para generar el PDF.")
        else:
            show_error(self.page, "Operación de guardado de PDF cancelada.")

    def build_view(self):
        """Construye y devuelve la vista del formulario de presupuesto."""
        appbar_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_900
        appbar_text_color = ft.colors.WHITE
        main_content_bgcolor = ft.colors.WHITE if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_800
        section_title_color = ft.colors.BLACK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.WHITE
        divider_color = ft.colors.GREY_300 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_GREY_600
        # Colores para los botones de acción
        save_button_bgcolor = ft.colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.BLUE_900
        download_button_bgcolor = ft.colors.PURPLE_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.PURPLE_800
        button_color = ft.colors.WHITE

        self._update_treatments_display() # Asegurarse de que la visualización de tratamientos inicial se renderice

        # Determinar el estado inicial de los botones al construir la vista
        # El botón de guardar estará habilitado si ya hay un client_id o un quote_id (para edición)
        initial_save_disabled = (self.client_id is None) and (self.quote_id is None)
        # El botón de PDF estará deshabilitado inicialmente si no hay quote_id o tratamientos
        initial_pdf_disabled = (self.quote_id is None) or (not self.selected_treatments)
        # Si se navega a un presupuesto existente, habilitar el PDF si hay quote_id y tratamientos
        if self.quote_id and self.selected_treatments:
            initial_pdf_disabled = False

        return ft.View(
            # Ajustar la ruta para incluir quote_id si está presente
            f"/presupuesto/{self.quote_id}/{self.client_id}" if self.quote_id else (f"/presupuesto/{self.client_id}" if self.client_id else "/presupuesto"),
            controls=[
                ft.AppBar(
                    title=ft.Text("Generar Presupuesto", color=appbar_text_color),
                    bgcolor=appbar_bgcolor,
                    leading=ft.IconButton(
                        icon=ft.icons.ARROW_BACK,
                        on_click=lambda e: self.page.go("/clients"),
                        tooltip="Volver a Clientes",
                        icon_color=appbar_text_color
                    )
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Seleccionar Cliente", weight="bold", color=section_title_color),
                            self._build_search_client_row(), # Fila de búsqueda de clientes
                            ft.Divider(color=divider_color),
                            ft.Text("Tratamientos", weight="bold", color=section_title_color),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column([
                                        self.treatment_search
                                    ], col={"xs":12, "md":9}),
                                    ft.Column([
                                        ft.FilledButton(
                                            icon=ft.icons.ADD,
                                            text="Añadir Nuevo",
                                            on_click=self.add_new_treatment_item,
                                            expand=True,
                                            style=ft.ButtonStyle(bgcolor=ft.colors.GREEN_500 if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.colors.GREEN_800,
                                                                 color=ft.colors.WHITE)
                                        ),
                                    ], col={"xs":12, "md":3})
                                ],
                                spacing=10,
                                run_spacing=10
                            ),
                            self.treatments_column,
                            ft.Divider(color=divider_color),
                            ft.Container(
                                content=ft.Row([
                                    self.discount_field, # Campo para el descuento
                                    ft.VerticalDivider(),
                                    self.total_amount_text,
                                ], alignment=ft.MainAxisAlignment.END),
                                alignment=ft.alignment.center_right,
                                padding=ft.padding.only(right=10, top=10)
                            ),
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column(col={"xs": 12, "sm": 6}, alignment=ft.MainAxisAlignment.END,
                                        controls=[
                                            ft.FilledButton(
                                                ref=self.save_budget_button_ref,
                                                text="Guardar Presupuesto",
                                                on_click=self._save_budget,
                                                icon=ft.icons.SAVE,
                                                expand=True,
                                                style=ft.ButtonStyle(bgcolor=save_button_bgcolor, color=button_color),
                                                disabled=initial_save_disabled # Usar estado calculado
                                            )
                                        ]
                                    ),
                                    ft.Column(col={"xs": 12, "sm": 6}, alignment=ft.MainAxisAlignment.START,
                                        controls=[
                                            ft.FilledButton(
                                                ref=self.download_pdf_button_ref,
                                                text="Descargar PDF",
                                                on_click=lambda e: self.page.run_task(self._generate_pdf_and_download, e), # Asegurar llamada asíncrona
                                                icon=ft.icons.DOWNLOAD,
                                                expand=True,
                                                style=ft.ButtonStyle(bgcolor=download_button_bgcolor, color=button_color),
                                                disabled=initial_pdf_disabled # Usar estado calculado
                                            )
                                        ]
                                    )
                                ], spacing=10
                            )
                        ],
                        spacing=20,
                        expand=True,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER
                    ),
                    padding=20,
                    expand=True,
                    bgcolor=main_content_bgcolor
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            padding=0
        )

def presup_view(page: ft.Page, client_id: Optional[int] = None, quote_id: Optional[int] = None):
    """Función de fábrica para crear la vista del formulario de presupuesto"""
    return PresupFormView(page, client_id=client_id, quote_id=quote_id).build_view()
