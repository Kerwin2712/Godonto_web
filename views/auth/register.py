import flet as ft
from services.auth_service import AuthService
from services.client_service import ClientService
from utils.alerts import show_error, show_success
from utils.validators import validate_email, validate_cedula, validate_phone
from Godonto_Desk.Godonto_web.core.config import settings
#print
def register_view(page: ft.Page):
    """Vista de registro con selección de tipo de usuario"""
    
    def select_role(e):
        if role_selector.value == "admin":
            page.go("/register/admin")
        elif role_selector.value == "client":
            page.go("/register/client")
    
    role_selector = ft.Dropdown(
        label="Tipo de usuario",
        options=[
            ft.dropdown.Option("admin", "Administrador"),
            ft.dropdown.Option("client", "Cliente")
        ],
        width=300
    )
    
    return ft.View(
        "/register",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Seleccione tipo de registro", size=20),
                        role_selector,
                        ft.ElevatedButton("Continuar", on_click=select_role)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=40,
                width=400
            )
        ]
    )

def admin_register_view(page: ft.Page):
    """Registro para administradores"""
    secret_key = ft.TextField(label="Clave secreta de administración", password=True)
    email = ft.TextField(label="Email")
    cedula = ft.TextField(label="Cédula")
    password = ft.TextField(label="Contraseña", password=True)
    
    def register_admin(e):
        if secret_key.value != settings.ADMIN_SECRET_KEY:
            show_error(page, "Clave secreta inválida")
            return
        
        # Resto de validaciones...
        success = AuthService.register_admin(
            email=email.value,
            cedula=cedula.value,
            password=password.value
        )
        
        if success:
            show_success(page, "Administrador registrado!")
            page.go("/login")
    
    return ft.View(
        "/register/admin",
        controls=[
            ft.Container(
                ft.Column([
                    ft.Text("Registro de Administrador", size=20),
                    secret_key,
                    email,
                    cedula,
                    password,
                    ft.ElevatedButton("Registrar", on_click=register_admin)
                ]),
                padding=40,
                width=400
            )
        ]
    )

def client_register_view(page: ft.Page):
    """Registro para clientes"""
    access_key = ft.TextField(label="Clave de acceso")
    cedula = ft.TextField(label="Cédula")
    email = ft.TextField(label="Email")
    
    def verify_access(e):
        if not ClientService.validate_access_key(access_key.value):
            show_error(page, "Clave de acceso inválida")
            return
        
        client = ClientService.get_client_by_cedula(cedula.value)
        if client:
            page.go(f"/register/client/form?cedula={cedula.value}")
        else:
            page.go("/register/client/form")
    
    return ft.View(
        "/register/client",
        controls=[
            ft.Container(
                ft.Column([
                    ft.Text("Registro de Cliente - Paso 1", size=20),
                    access_key,
                    cedula,
                    email,
                    ft.ElevatedButton("Verificar", on_click=verify_access)
                ]),
                padding=40,
                width=400
            )
        ]
    )

def client_register_form_view(page: ft.Page):
    """Formulario final para clientes"""
    name = ft.TextField(label="Nombre")
    phone = ft.TextField(label="Teléfono")
    password = ft.TextField(label="Contraseña", password=True)
    
    def submit(e):
        # Validar y guardar
        success = AuthService.register_client(
            cedula=page.query.get("cedula"),
            email=page.query.get("email"),
            password=password.value,
            name=name.value,
            phone=phone.value
        )
        
        if success:
            show_success(page, "Registro completado!")
            page.go("/login")
    
    return ft.View(
        "/register/client/form",
        controls=[
            ft.Container(
                ft.Column([
                    ft.Text("Complete sus datos", size=20),
                    name,
                    phone,
                    password,
                    ft.ElevatedButton("Finalizar", on_click=submit)
                ]),
                padding=40,
                width=400
            )
        ]
    )