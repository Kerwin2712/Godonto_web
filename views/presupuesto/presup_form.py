import flet as ft
from services.client_service import ClientService
from utils.alerts import show_success, show_error
from datetime import datetime
import logging
from services.budget_service import BudgetService
from services.quote_service import QuoteService
from services.treatment_service import TreatmentService
import os

logger = logging.getLogger(__name__)

def presup_view(page: ft.Page, client_id: int = None):
    """Vista de presupuesto para la aplicación"""

    # Configurar el FilePicker para la descarga
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker) # Añadir el FilePicker al overlay de la página
    page.update() # Asegurarse de que el overlay se actualice

    # Lista para almacenar los tratamientos seleccionados con cantidad
    # Cada elemento será un diccionario: {'id': ..., 'name': ..., 'price': ..., 'quantity': ...}
    selected_treatments = []
    treatments_column = ft.Column() # Columna para mostrar los tratamientos seleccionados
    total_amount_text = ft.Text("Total: $0.00", size=18, weight=ft.FontWeight.BOLD)

    client_name_field = ft.TextField(
        label="Cliente",
        width=400,
        autofocus=True,
        keyboard_type=ft.KeyboardType.TEXT
    )
    client_cedula_field = ft.TextField(
        label="Cédula",
        width=200,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    
    # Componente de búsqueda de tratamientos
    treatment_search = ft.SearchBar(
        view_elevation=4,
        divider_color=ft.colors.GREEN_400,
        bar_hint_text="Buscar tratamientos existentes...",
        view_hint_text="Seleccione un tratamiento existente...",
        bar_leading=ft.IconButton(
            icon=ft.icons.SEARCH,
            on_click=lambda e: treatment_search.open_view()
        ),
        controls=[],
        expand=True,
        on_change=lambda e: handle_treatment_search_change(e),
        on_submit=lambda e: handle_treatment_search_submit(e) # Keep this for Enter key
    )

    def handle_treatment_search_change(e):
        """Maneja el cambio en la búsqueda de tratamientos existentes"""
        search_term = e.control.value.strip()
        
        if len(search_term) < 1:
            e.control.controls = []
            e.control.update()
            return

        try:
            treatments = TreatmentService.get_all_treatments(search_term=search_term)
            e.control.controls = [
                ft.ListTile(
                    title=ft.Text(t.name),
                    subtitle=ft.Text(f"${t.price:.2f}"),
                    on_click=lambda e, t=t: select_treatment(t.id, t.name, t.price),
                    data={'id': t.id, 'name': t.name, 'price': t.price}
                ) for t in treatments
            ]
            e.control.update()
            page.update()
        except Exception as ex:
            logger.error(f"Error en búsqueda de tratamientos: {str(ex)}")
            show_error(page, f"Error en búsqueda de tratamientos: {str(ex)}")
    
    def handle_treatment_search_submit(e):
        """Maneja la selección con Enter desde la barra de búsqueda"""
        if e.control.controls and len(e.control.controls) > 0:
            selected_data = e.control.controls[0].data
            select_treatment(selected_data['id'], selected_data['name'], selected_data['price'])
        # Si no hay resultados de búsqueda, no hace nada especial aquí;
        # se confía en el botón "Añadir Tratamiento Nuevo (Manual)" para nuevas entradas.
        treatment_search.value = ""
        treatment_search.close_view()
        page.update()
    
    def select_treatment(treatment_id: int, name: str, price: float):
        """Selecciona un tratamiento existente y lo añade a la lista"""
        # Verificar si el tratamiento ya está seleccionado
        if any(t['id'] == treatment_id for t in selected_treatments if t['id'] is not None):
            show_error(page, "Este tratamiento ya ha sido añadido al presupuesto.")
            treatment_search.close_view()
            page.update()
            return

        selected_treatments.append({'id': treatment_id, 'name': name, 'price': price, 'quantity': 1})
        _update_treatments_display() # Actualizar la visualización
        treatment_search.value = "" # Limpiar el campo de búsqueda
        treatment_search.controls = [] # Limpiar los resultados
        treatment_search.close_view()
        page.update()
    
    def _update_total_amount():
        """Actualiza el monto total del presupuesto"""
        total = sum(item['price'] * item['quantity'] for item in selected_treatments if 'price' in item and 'quantity' in item)
        total_amount_text.value = f"Total: ${total:,.2f}"
        page.update()

    def _remove_treatment(unique_key: str):
        """Elimina un tratamiento de la lista de seleccionados por su clave única"""
        nonlocal selected_treatments # Se usa 'nonlocal' para referirse a la variable del ámbito superior
        # Filtra la lista para remover el item con la clave única
        selected_treatments = [t for t in selected_treatments if t.get('unique_key') != unique_key]
        _update_treatments_display()
        _update_total_amount()
        page.update()

    def _update_treatments_display():
        """Actualiza la visualización de los tratamientos seleccionados en la columna"""
        treatments_column.controls.clear() # Limpiar controles existentes

        if not selected_treatments:
            treatments_column.controls.append(
                ft.Text(
                    "Ningún tratamiento seleccionado para el presupuesto.",
                    italic=True,
                    color=ft.colors.BLACK
                )
            )
        else:
            for idx, t in enumerate(selected_treatments):
                # Asegurarse de que cada item tenga una clave única para fines de UI
                if 'unique_key' not in t:
                    t['unique_key'] = f"{t.get('id', 'new')}-{idx}-{datetime.now().timestamp()}"

                # Referencias para los campos de texto dentro de la tarjeta
                name_field_ref = ft.Ref[ft.TextField]()
                price_field_ref = ft.Ref[ft.TextField]()
                quantity_field_ref = ft.Ref[ft.TextField]()

                def on_name_change(e, item_unique_key=t['unique_key']):
                    """Maneja el cambio de nombre de un tratamiento individual"""
                    for item in selected_treatments:
                        if item.get('unique_key') == item_unique_key:
                            item['name'] = e.control.value
                            break
                    # No necesita actualizar total, solo el nombre

                def on_price_change(e, item_unique_key=t['unique_key']):
                    """Maneja el cambio de precio de un tratamiento individual"""
                    try:
                        # Si el valor está vacío, se asume 0.0
                        new_price = float(e.control.value) if e.control.value.strip() else 0.0
                        if new_price < 0:
                            show_error(page, "El precio no puede ser negativo.")
                            e.control.value = str(t['price']) if 'price' in t else "0.00"
                            e.control.update()
                            return

                        for item in selected_treatments:
                            if item.get('unique_key') == item_unique_key:
                                item['price'] = new_price
                                break
                        _update_total_amount() # Recalcular total
                    except ValueError:
                        show_error(page, "Por favor, introduce un número válido para el precio.")
                        e.control.value = str(t['price']) if 'price' in t else "0.00"
                        e.control.update()

                def on_price_focus(e):
                    """Borra el contenido del campo de precio si es el valor por defecto '0.00'"""
                    if e.control.value == "0.00":
                        e.control.value = ""
                        e.control.update()
                        
                def on_quantity_change(e, item_unique_key=t['unique_key']):
                    """Maneja el cambio de cantidad de un tratamiento individual"""
                    try:
                        # Si el valor está vacío, se asume 0
                        new_quantity = int(e.control.value) if e.control.value.strip() else 0
                        if new_quantity <= 0:
                            show_error(page, "La cantidad debe ser mayor a 0.")
                            e.control.value = "1" # Restablecer a 1 si es inválido
                            new_quantity = 1
                            e.control.update()
                        
                        for item in selected_treatments:
                            if item.get('unique_key') == item_unique_key:
                                item['quantity'] = new_quantity
                                break
                        _update_total_amount() # Recalcular total
                    except ValueError:
                        show_error(page, "Por favor, introduce un número entero válido para la cantidad.")
                        e.control.value = str(t['quantity']) if 'quantity' in t else "1"
                        e.control.update()

                def increment_quantity(e, item_unique_key): 
                    for item in selected_treatments:
                        if item.get('unique_key') == item_unique_key:
                            item['quantity'] += 1
                            quantity_field_ref.current.value = str(item['quantity'])
                            quantity_field_ref.current.update()
                            break
                    _update_total_amount()

                def decrement_quantity(e, item_unique_key): 
                    for item in selected_treatments:
                        if item.get('unique_key') == item_unique_key:
                            if item['quantity'] > 1: # No permitir cantidad menor a 1
                                item['quantity'] -= 1
                                quantity_field_ref.current.value = str(item['quantity'])
                                quantity_field_ref.current.update()
                            else:
                                show_error(page, "La cantidad no puede ser menor a 1.")
                            break
                    _update_total_amount()


                treatments_column.controls.append(
                    ft.Card(
                        content=ft.Container(
                            content=ft.Column( # Usar Column para apilar los campos de texto
                                [
                                    ft.Row(
                                        [
                                            ft.TextField(
                                                ref=name_field_ref,
                                                label="Nombre del Tratamiento",
                                                value=t['name'],
                                                expand=True,
                                                on_change=on_name_change,
                                                # Si tiene ID, es un tratamiento existente y no se debería editar el nombre/precio
                                                read_only=t['id'] is not None 
                                            ),
                                            ft.TextField(
                                                ref=price_field_ref,
                                                label="Precio ($)",
                                                value=f"{t['price']:.2f}",
                                                width=120,
                                                keyboard_type=ft.KeyboardType.NUMBER,
                                                on_change=on_price_change,
                                                on_focus=on_price_focus, # Añadido on_focus
                                                # Si tiene ID, es un tratamiento existente y no se debería editar el nombre/precio
                                                read_only=t['id'] is not None 
                                            ),
                                        ],
                                        spacing=10
                                    ),
                                    ft.Row(
                                        [
                                            ft.IconButton(
                                                icon=ft.icons.REMOVE,
                                                on_click=lambda e: decrement_quantity(e, t['unique_key']), 
                                                tooltip="Disminuir cantidad"
                                            ),
                                            ft.TextField(
                                                ref=quantity_field_ref,
                                                label="Cantidad",
                                                value=str(t['quantity']),
                                                width=100,
                                                keyboard_type=ft.KeyboardType.NUMBER,
                                                on_change=on_quantity_change,
                                                text_align=ft.TextAlign.CENTER,
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.ADD,
                                                on_click=lambda e: increment_quantity(e, t['unique_key']), 
                                                tooltip="Aumentar cantidad"
                                            ),
                                            ft.IconButton(
                                                icon=ft.icons.DELETE,
                                                icon_color=ft.colors.RED_500,
                                                on_click=lambda e, key=t['unique_key']: _remove_treatment(key),
                                                tooltip="Eliminar tratamiento"
                                            )
                                        ],
                                        spacing=10,
                                        alignment=ft.MainAxisAlignment.END
                                    )
                                ],
                                spacing=5
                            ),
                            padding=10
                        ),
                        margin=ft.margin.only(bottom=5)
                    )
                )
        page.update()
    
    def add_new_treatment_item(e=None):
        """Añade un nuevo item de tratamiento vacío para que el usuario lo rellene"""
        # Añade un diccionario con id=None para indicar que es un tratamiento nuevo
        selected_treatments.append({'id': None, 'name': '', 'price': 0.0, 'quantity': 1})
        _update_treatments_display()
        _update_total_amount() # No cambia el total si el precio es 0, pero es buena práctica
        page.update()


    # Si se proporciona client_id, cargar datos del cliente
    if client_id:
        try:
            client_data = ClientService.get_client_by_id(client_id)
            if client_data:
                client_name_field.value = client_data.name
                client_cedula_field.value = client_data.cedula
            else:
                show_error(page, "Cliente no encontrado.")
        except Exception as e:
            logger.error(f"Error al cargar datos del cliente: {e}")
            show_error(page, f"Error al cargar cliente: {e}")

    async def on_submit(e):
        client_name = client_name_field.value
        client_cedula = client_cedula_field.value
        
        if not client_name or not client_cedula:
            show_error(page, "Por favor, complete el nombre del cliente y la cédula.")
            return

        if not selected_treatments:
            show_error(page, "Debe añadir al menos un tratamiento al presupuesto.")
            return

        # Validar tratamientos antes de guardar
        valid_treatments_for_quote = []
        for item in selected_treatments:
            if not item['name'].strip():
                show_error(page, "Todos los tratamientos deben tener un nombre.")
                return
            # Se ha ajustado la validación de precio y cantidad para permitir 0 si el campo está vacío.
            # Aquí se valida que, si no está vacío, sea un número válido y no negativo.
            if not isinstance(item['price'], (int, float)) or item['price'] < 0:
                show_error(page, f"El precio para '{item['name']}' no es válido.")
                return
            if not isinstance(item['quantity'], int) or item['quantity'] <= 0:
                show_error(page, f"La cantidad para '{item['name']}' no es válida (debe ser un entero positivo).")
                return
            valid_treatments_for_quote.append(item)


        try:
            # Para la creación del presupuesto, necesitamos el client_id.
            if not client_id:
                # En un escenario real, aquí buscarías el cliente por nombre/cédula
                # y si no existe, lo crearías y obtendrías su ID.
                # Por ahora, si no hay client_id, no se puede guardar.
                show_error(page, "Error: No se ha proporcionado un ID de cliente válido. No se puede crear el presupuesto.")
                return

            # Crear presupuesto en la base de datos usando QuoteService
            # QuoteService.create_quote ya llama a TreatmentService.create_treatment_if_not_exists
            # para guardar tratamientos nuevos si no existen.
            quote_id = QuoteService.create_quote(
                client_id=client_id,
                treatments=valid_treatments_for_quote,
                notes="Presupuesto generado desde la aplicación"
            )
            
            if quote_id:
                # Preparar los ítems para BudgetService.generate_pdf
                # Mapear 'name' a 'treatment' para que coincida con la expectativa de generate_pdf
                items_for_pdf = [
                    {
                        "treatment": item['name'],
                        "quantity": item['quantity'],
                        "price": item['price']
                    } for item in valid_treatments_for_quote
                ]

                # Generar PDF
                pdf_path = BudgetService.generate_pdf({
                    "quote_id": quote_id,
                    "client_name": client_name,
                    "client_cedula": client_cedula,
                    "items": items_for_pdf, # Usar la lista con la clave 'treatment'
                    "date": datetime.now().strftime("%Y-%m-%d")
                })
                
                show_success(page, f"Presupuesto #{quote_id} guardado exitosamente y PDF generado en {pdf_path}")
                page.go("/clients") # O a donde sea apropiado después de guardar
            else:
                show_error(page, "No se pudo crear el presupuesto en la base de datos.")
            
        except Exception as ex:
            logger.error(f"Error al guardar presupuesto: {ex}")
            show_error(page, f"Error al guardar presupuesto: {ex}")

    # Inicializar la visualización de tratamientos (vacía al principio)
    _update_treatments_display()

    # Contenido principal del formulario
    main_content = ft.Column(
        [
            ft.Text("Información del Cliente", size=20, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    client_name_field,
                    client_cedula_field,
                ],
                spacing=15
            ),
            ft.Divider(height=20),
            ft.Text("Tratamientos", size=20, weight=ft.FontWeight.BOLD),
            treatment_search, # Barra de búsqueda de tratamientos existentes
            ft.FilledButton(
                icon=ft.icons.ADD,
                text="Añadir Tratamiento Nuevo",
                on_click=add_new_treatment_item, # Nuevo botón para añadir manualmente
                width=300
            ),
            treatments_column, # Columna para mostrar tratamientos seleccionados (ahora editables)
            ft.Divider(height=20),
            ft.Container(
                content=total_amount_text,
                alignment=ft.alignment.center_right,
                padding=ft.padding.only(right=10, top=10)
            ),
            ft.Container(
                content=ft.FilledButton(
                    "Generar Presupuesto y Descargar PDF",
                    on_click=on_submit,
                    icon=ft.icons.DOWNLOAD,
                    expand=True
                ),
                margin=ft.margin.only(top=20),
                alignment=ft.alignment.center
            )
        ],
        spacing=15,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO, # Añadir scrollbar aquí
        expand=True
    )

    return ft.Column(
        [
            ft.AppBar(
                title=ft.Text("Generar Presupuesto"),
                bgcolor=ft.colors.SURFACE_VARIANT,
                leading=ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    on_click=lambda e: page.go("/clients")
                )
            ),
            main_content # El contenido principal ahora tiene scroll
        ],
        expand=True,
        alignment=ft.alignment.top_center,
        spacing=0
    )
