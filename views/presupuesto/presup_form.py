import flet as ft
from services.client_service import ClientService
from utils.alerts import show_success, show_error
from datetime import datetime
import logging
from services.budget_service import BudgetService
import os

logger = logging.getLogger(__name__)

def presup_view(page: ft.Page, client_id: int = None):
    """Vista de presupuesto para la aplicación"""

    # Configurar el FilePicker para la descarga
    file_picker = ft.FilePicker()
    page.overlay.append(file_picker) # Añadir el FilePicker al overlay de la página
    page.update() # Asegurarse de que el overlay se actualice

    treatment_items_column = ft.Column()
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
    

    def update_total_amount():
        total = 0.0
        for control in treatment_items_column.controls:
            try:
                # Accedemos directamente a los campos guardados en data
                quantity = float(control.data['quantity_field'].value) if control.data['quantity_field'].value else 0
                price = float(control.data['price_field'].value) if control.data['price_field'].value else 0
                total += quantity * price
            except ValueError:
                pass
        total_amount_text.value = f"Total: ${total:,.2f}"
        page.update()

    def add_treatment_item(e=None, treatment="", quantity="1", price="0.00"):
        key = f"item_{len(treatment_items_column.controls)}_{datetime.now().timestamp()}"
        
        treatment_field = ft.TextField(
            label="Tratamiento",
            value=treatment,
            expand=True
        )
        
        quantity_field = ft.TextField(
            label="Cantidad",
            value=quantity,
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: update_total_amount()
        )
        
        price_field = ft.TextField(
            label="Precio Unitario ($)",
            value=price,
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: update_total_amount()
        )

        remove_button = ft.IconButton(
            icon=ft.icons.DELETE,
            on_click=lambda e: remove_treatment_item(e, key)
        )

        treatment_item_row = ft.Container(
            content=ft.Row(
                [
                    treatment_field,
                    quantity_field,
                    price_field,
                    remove_button
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            ),
            padding=ft.padding.only(bottom=10),
            data={
                "key": key,
                "treatment_field": treatment_field,
                "quantity_field": quantity_field,
                "price_field": price_field
            }
        )
        treatment_items_column.controls.append(treatment_item_row)
        update_total_amount()
        page.update()

    def remove_treatment_item(e, key_to_remove):
        treatment_items_column.controls[:] = [
            item for item in treatment_items_column.controls
            if not (isinstance(item, ft.Container) and item.data and item.data.get("key") == key_to_remove)
        ]
        update_total_amount()
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

        budget_items = []
        for control in treatment_items_column.controls:
            try:
                treatment = control.data['treatment_field'].value
                quantity = float(control.data['quantity_field'].value) if control.data['quantity_field'].value else 0
                price = float(control.data['price_field'].value) if control.data['price_field'].value else 0
                
                if treatment and quantity > 0 and price >= 0:
                    budget_items.append({
                        "treatment": treatment,
                        "quantity": quantity,
                        "price": price
                    })
            except ValueError:
                show_error(page, "Asegúrate de que la cantidad y el precio sean números válidos.")
                return

        if not budget_items:
            show_error(page, "Debe añadir al menos un tratamiento al presupuesto.")
            return

        budget_data = {
            "client_name": client_name,
            "client_cedula": client_cedula,
            "items": budget_items,
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            # Generar y guardar el PDF
            pdf_path = BudgetService.generate_pdf(budget_data)
            page.go("/clients")
            show_success(page, f"Presupuesto guardado exitosamente en: {pdf_path}")
            
        except Exception as ex:
            logger.error(f"Error al generar el PDF del presupuesto: {ex}")
            show_error(page, f"Error al generar el presupuesto: {ex}")

    # Inicializar con un tratamiento vacío
    add_treatment_item()

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
            ft.Column(
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
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        ],
        #padding=20,
        expand=True,
        alignment=ft.alignment.top_center,
        spacing=0
    )