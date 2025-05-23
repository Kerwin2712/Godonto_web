import flet as ft
from services.client_service import ClientService # Import ClientService
from utils.alerts import show_success, show_error # Assuming you have these utilities
import datetime # Import datetime for date handling
import logging # Import logging
from services.budget_service import BudgetService

logger = logging.getLogger(__name__)

def presup_view(page: ft.Page, client_id: int = None):
    """Vista de presupuesto para la aplicación"""

    # UI Controls for dynamic treatment items
    treatment_items_column = ft.Column()
    total_amount_text = ft.Text("Total: $0.00", size=18, weight=ft.FontWeight.BOLD)

    # TextFields for client information
    client_name_field = ft.TextField(
        label="Cliente",
        width=400,
        read_only=True if client_id else False, # Make read-only if client_id is present
        autofocus=True if not client_id else False,
        keyboard_type=ft.KeyboardType.TEXT
    )
    client_cedula_field = ft.TextField(
        label="Cédula",
        width=200,
        read_only=True if client_id else False,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    

    def add_treatment_item(e=None, treatment="", quantity="1", price="0.00"):
        # Unique key for each item to allow removal
        key = f"item_{len(treatment_items_column.controls)}" 
        
        treatment_field = ft.TextField(label="Tratamiento", expand=True, value=treatment, data=key)
        quantity_field = ft.TextField(
            label="Cantidad", 
            width=100, 
            keyboard_type=ft.KeyboardType.NUMBER, 
            value=quantity,
            on_change=update_total,
            data=key
        )
        price_field = ft.TextField(
            label="Precio Unitario", 
            width=150, 
            keyboard_type=ft.KeyboardType.NUMBER, 
            prefix_text="$", 
            value=f"{float(price):.2f}",
            on_change=update_total,
            data=key
        )
        
        def remove_item(e):
            for control in treatment_items_column.controls:
                if isinstance(control, ft.Row) and control.controls[0].data == key:
                    treatment_items_column.controls.remove(control)
                    break
            update_total()
            page.update()

        item_row = ft.Row(
            controls=[
                treatment_field,
                quantity_field,
                price_field,
                ft.IconButton(ft.icons.DELETE, on_click=remove_item, tooltip="Eliminar item")
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
            data=key # Store key in the row itself for easier lookup
        )
        treatment_items_column.controls.append(item_row)
        update_total()
        page.update()

    def update_total(e=None):
        total = 0.0
        for item_row in treatment_items_column.controls:
            if isinstance(item_row, ft.Row):
                try:
                    quantity = float(item_row.controls[1].value)
                    price = float(item_row.controls[2].value)
                    total += quantity * price
                except ValueError:
                    # Ignore invalid numbers for now, or show an error
                    pass
        total_amount_text.value = f"Total: ${total:,.2f}"
        page.update()

    def load_client_data(client_id):
        try:
            client = ClientService.get_client_by_id(client_id)
            if client:
                client_name_field.value = client.name
                client_cedula_field.value = client.cedula
                page.update()
            else:
                show_error(page, "Cliente no encontrado.")
                logger.warning(f"Client with ID {client_id} not found for budget form.")
        except Exception as e:
            show_error(page, f"Error al cargar datos del cliente: {e}")
            logger.error(f"Error loading client data for budget form (ID: {client_id}): {e}")

    # Call load_client_data if client_id is provided
    if client_id:
        # We need to ensure the page is ready before calling this,
        # or call it after the view is added to the page.
        # For simplicity, we can call it directly, but in a more complex
        # app, you might defer it with page.add_init_handler or similar.
        load_client_data(client_id)


    def on_submit(e):
        # Gather all data
        budget_data = {
            "client_name": client_name_field.value,
            "client_cedula": client_cedula_field.value,
            "items": []
        }
        
        for item_row in treatment_items_column.controls:
            if isinstance(item_row, ft.Row):
                try:
                    item = {
                        "treatment": item_row.controls[0].value,
                        "quantity": float(item_row.controls[1].value),
                        "price": float(item_row.controls[2].value)
                    }
                    budget_data["items"].append(item)
                except ValueError:
                    show_error(page, "Por favor, ingrese valores numéricos válidos para cantidad y precio.")
                    return
        
        if not budget_data["client_name"] or not budget_data["client_cedula"] or not budget_data["date"]:
            show_error(page, "Los campos Cliente y Cédula son obligatorios.")
            return

        if not budget_data["items"]:
            show_error(page, "Debe añadir al menos un tratamiento.")
            return

        try:
            # Llama al servicio para generar el PDF
            pdf_filename = f"presupuesto_{budget_data['client_cedula']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
            pdf_path = BudgetService.generate_pdf(budget_data, output_path=pdf_filename)

            show_success(page, f"Presupuesto creado. PDF generado.")

            # Generar enlace de descarga (solo funcionará si el archivo es accesible desde el servidor web)
            # Suponiendo que el archivo se guarda en una carpeta estática accesible, por ejemplo 'static/presupuestos/'
            # Ajusta la ruta según tu configuración real
            download_url = f"/static/presupuestos/{pdf_filename}"

            # Mostrar el enlace de descarga en la página
            dialog_pre = ft.AlertDialog(
                title=ft.Text("Presupuesto generado"),
                content=ft.Column([
                    ft.Text("El presupuesto se generó correctamente."),
                    ft.TextButton(
                    "Descargar PDF",
                    url=download_url,
                    icon=ft.icons.DOWNLOAD,
                    style=ft.ButtonStyle(color=ft.colors.BLUE)
                    )
                ])
            )
            page.open(dialog_pre)
            dialog_pre.open = True
            page.update()

            logger.info(f"Budget data collected and PDF generated: {budget_data}")

            # No redirigir automáticamente, dejar que el usuario descargue el PDF
        except Exception as ex:
            show_error(page, f"Error al generar presupuesto: {str(ex)}")
            logger.error(f"Error generating budget: {ex}", exc_info=True)


    return ft.View(
        "/presupuesto",
        controls=[
            ft.AppBar(
                title=ft.Text("Crear Presupuesto", weight=ft.FontWeight.BOLD),
                center_title=False,
                bgcolor=ft.colors.SURFACE_VARIANT,
                leading=ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    tooltip="Volver a Clientes",
                    on_click=lambda _: page.go("/clients")
                ),
            ),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Detalles del Cliente", size=18, weight=ft.FontWeight.BOLD),
                        ft.ResponsiveRow(
                            controls=[
                                ft.Column(col={"sm":12, "md":6}, controls=[client_name_field]),
                                ft.Column(col={"sm":12, "md":3}, controls=[client_cedula_field]),
                            ],
                            spacing=10
                        ),
                        ft.Divider(height=20),
                        ft.Text("Items del Presupuesto", size=18, weight=ft.FontWeight.BOLD),
                        treatment_items_column,
                        ft.FilledButton(
                            icon=ft.icons.ADD,
                            text="Añadir Tratamiento",
                            on_click=add_treatment_item,
                            width=200
                        ),
                        ft.Divider(height=20),
                        ft.Container(
                            content=total_amount_text,
                            alignment=ft.alignment.center_right,
                            padding=ft.padding.only(right=10, top=10)
                        ),
                        ft.Container(
                            content=ft.FilledButton(
                                "Generar Presupuesto y PDF",
                                on_click=on_submit,
                                icon=ft.icons.PICTURE_AS_PDF,
                                expand=True
                            ),
                            margin=ft.margin.only(top=20),
                            alignment=ft.alignment.center
                        )
                    ],
                    spacing=15,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=20,
                expand=True,
                alignment=ft.alignment.top_center
            )
        ],
        spacing=0,
        padding=0,
    )