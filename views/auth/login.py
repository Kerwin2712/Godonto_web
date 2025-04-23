import flet as ft
from services.auth_service import authenticate_user
from utils.alerts import show_error
from utils.validators import validate_email

def login_view(page: ft.Page):
    """Vista de login para la aplicación"""
    
    def on_login(e):
        if not username.value or not password.value:
            show_error(page, "Complete todos los campos")
            return
            
        try:
            if authenticate_user(username.value, password.value):
                page.session.set("user", username.value)
                # Limpiar completamente la navegación
                page.views.clear()
                # Forzar una nueva instancia del dashboard
                page.go("/dashboard")
                # Esperar un ciclo de eventos para asegurar la renderización
                page.update()
            else:
                show_error(page, "Credenciales incorrectas")
        except Exception as e:
            show_error(page, f"Error de autenticación: {str(e)}")
        finally:
            password.value = ""
            page.update()

    # Componentes UI
    username = ft.TextField(
        label="Usuario",
        width=300,
        autofocus=True,
        keyboard_type=ft.KeyboardType.TEXT
    )
    
    password = ft.TextField(
        label="Contraseña",
        width=300,
        password=True,
        can_reveal_password=True
    )
    
    login_button = ft.ElevatedButton(
        "Iniciar sesión",
        on_click=on_login,
        width=300
    )
    
    return ft.View(
        "/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Iniciar sesión", 
                               size=24, 
                               weight=ft.FontWeight.BOLD,
                               text_align=ft.TextAlign.CENTER),
                        username,
                        password,
                        login_button,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                padding=40,
                border_radius=10,
                bgcolor=ft.colors.SURFACE_VARIANT,
                width=400,
                alignment=ft.alignment.center,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )