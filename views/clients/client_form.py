import flet as ft
from core.database import get_db
from utils.validators import validate_email, validate_phone, validate_cedula
from utils.alerts import show_success, show_error
from typing import Optional

class ClientFormView:
    def __init__(self, page: ft.Page, client_id: Optional[int] = None):
        self.page = page
        self.client_id = client_id
        
        # Campos del formulario
        self.name = ft.TextField(label="Nombre completo*", autofocus=True)
        self.cedula = ft.TextField(
            label="Cédula*",
            hint_text="Ej: 1234567890",
            on_change=lambda e: self.handle_validation(e, validate_cedula)
        )
        self.phone = ft.TextField(
            label="Teléfono",
            on_change=lambda e: self.handle_validation(e, validate_phone)
        )
        self.email = ft.TextField(
            label="Email",
            on_change=lambda e: self.handle_validation(e, validate_email)
        )
        
        # Cargar datos si es edición
        self.load_client_data()

    def handle_validation(self, e, validator):
        """Maneja la validación de campos"""
        error = validator(e.control.value)
        if error:
            e.control.error_text = error
        else:
            e.control.error_text = None
        self.page.update()
    
    def load_client_data(self):
        """Carga los datos del cliente si es una edición"""
        if self.client_id:
            with get_db() as cursor:
                cursor.execute(
                    "SELECT name, cedula, phone, email FROM clients WHERE id = %s", 
                    (self.client_id,)
                )
                if client := cursor.fetchone():
                    self.name.value, self.cedula.value, self.phone.value, self.email.value = client
    
    def save_client(self, e):
        """Guarda o actualiza un cliente"""
        # Validar campos obligatorios
        if not self.name.value or not self.cedula.value:
            show_error(self.page, "Nombre y cédula son obligatorios")
            return
        
        try:
            with get_db() as cursor:
                if self.client_id:
                    cursor.execute(
                        """UPDATE clients 
                        SET name=%s, cedula=%s, phone=%s, email=%s, updated_at=NOW()
                        WHERE id=%s""",
                        (self.name.value, self.cedula.value, self.phone.value, self.email.value, self.client_id)
                    )
                    success_message = "Cliente actualizado con éxito"
                else:
                    cursor.execute(
                        """INSERT INTO clients (name, cedula, phone, email) 
                        VALUES (%s, %s, %s, %s)""",
                        (self.name.value, self.cedula.value, self.phone.value, self.email.value)
                    )
                    success_message = "Cliente creado con éxito"
            
            show_success(self.page, success_message)
            self.page.go("/clients")
            
        except Exception as e:
            show_error(self.page, f"Error al guardar: {str(e)}")
    
    def build_view(self):
        """Construye y devuelve la vista del formulario"""
        return ft.View(
            "/client_form" if self.client_id is None else f"/client_form/{self.client_id}",
            controls=[
                ft.AppBar(
                    title=ft.Text("Nuevo Cliente" if not self.client_id else "Editar Cliente"),
                    leading=ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    on_click=lambda e: self.page.go("/quotes"),
                    tooltip="Volver al Dashboard"
                    )
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Información del Cliente", size=20, weight="bold"),
                        ft.Divider(),
                        ft.ResponsiveRow([
                            ft.Column(col={"xs": 12}, controls=[self.name]),
                            ft.Column(col={"xs": 12}, controls=[self.cedula]),
                            ft.Column(col={"xs": 12}, controls=[self.phone]),
                            ft.Column(col={"xs": 12}, controls=[self.email]),
                        ], spacing=10),
                        ft.ResponsiveRow([
                            ft.Column(col={"xs": 12, "sm": 6}, alignment=ft.MainAxisAlignment.END,
                                controls=[
                                    ft.ElevatedButton(
                                        "Guardar", 
                                        on_click=self.save_client,
                                        icon=ft.icons.SAVE,
                                        expand=True
                                    )
                                ]
                            ),
                            ft.Column(col={"xs": 12, "sm": 6}, alignment=ft.MainAxisAlignment.START,
                                controls=[
                                    ft.TextButton(
                                        "Cancelar", 
                                        on_click=lambda e: self.page.go("/dashboard"),
                                        icon=ft.icons.CANCEL,
                                        expand=True
                                    )
                                ]
                            )
                        ], spacing=10)
                    ], spacing=20),
                    padding=20,
                    alignment=ft.alignment.top_left
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            padding=10
        )

def client_form_view(page: ft.Page, client_id: Optional[int] = None):
    """Función de fábrica para crear la vista del formulario de cliente"""
    return ClientFormView(page, client_id).build_view()