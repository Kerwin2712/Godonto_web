import flet as ft
from typing import Optional, Callable
from enum import Enum

class AlertType(Enum):
    """Tipos de alertas disponibles"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class AlertManager:
    """Clase para manejar todas las notificaciones y diálogos de la aplicación"""
    
    # Colores para cada tipo de alerta
    ALERT_COLORS = {
        AlertType.SUCCESS: ft.colors.GREEN_400,
        AlertType.ERROR: ft.colors.RED_400,
        AlertType.WARNING: ft.colors.AMBER_400,
        AlertType.INFO: ft.colors.BLUE_400
    }
    
    @staticmethod
    def show_snackbar(
        page: ft.Page,
        message: str,
        alert_type: AlertType = AlertType.INFO,
        duration: int = 3000,
        action: Optional[str] = "OK"
    ) -> None:
        """
        Muestra una notificación flotante (snackbar)
        
        Args:
            page: Instancia de la página Flet
            message: Mensaje a mostrar
            alert_type: Tipo de alerta (success, error, warning, info)
            duration: Duración en milisegundos
            action: Texto para el botón de acción (None para ocultar)
        """
        snack_bar = ft.SnackBar(
            content=ft.Text(message, color=ft.colors.WHITE),
            bgcolor=AlertManager.ALERT_COLORS.get(alert_type, ft.colors.BLUE_400),
            behavior=ft.SnackBarBehavior.FLOATING,
            duration=duration,
            action=action,
            action_color=ft.colors.WHITE if action else None
        )
        page.open(snack_bar)
        snack_bar.open = True
        page.update()

    @staticmethod
    def show_success(page: ft.Page, message: str) -> None:
        """Muestra un mensaje de éxito"""
        AlertManager.show_snackbar(page, message, AlertType.SUCCESS)

    @staticmethod
    def show_error(page: ft.Page, message: str) -> None:
        """Muestra un mensaje de error"""
        AlertManager.show_snackbar(page, message, AlertType.ERROR)

    @staticmethod
    def show_confirmation(
        page: ft.Page,
        title: str,
        content: str,
        confirm_text: str = "Confirmar",
        cancel_text: str = "Cancelar",
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None
    ) -> None:
        """
        Muestra un diálogo de confirmación modal
        
        Args:
            page: Instancia de la página Flet
            title: Título del diálogo
            content: Contenido/mensaje
            confirm_text: Texto para botón de confirmación
            cancel_text: Texto para botón de cancelación
            on_confirm: Función a ejecutar al confirmar
            on_cancel: Función a ejecutar al cancelar
        """
        def handle_response(e):
            dialog.open = False
            page.update()
            if e.control.text == confirm_text and on_confirm:
                on_confirm()
            elif e.control.text == cancel_text and on_cancel:
                on_cancel()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton(cancel_text, on_click=handle_response),
                ft.TextButton(confirm_text, on_click=handle_response),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dialog)
        dialog.open = True
        page.update()

    @staticmethod
    def show_alert(
        page: ft.Page,
        title: str,
        content: str,
        button_text: str = "OK",
        on_close: Optional[Callable] = None
    ) -> None:
        """
        Muestra un diálogo de alerta simple
        
        Args:
            page: Instancia de la página Flet
            title: Título del diálogo
            content: Contenido/mensaje
            button_text: Texto para el botón
            on_close: Función a ejecutar al cerrar
        """
        def handle_close(e):
            dialog.open = False
            page.update()
            if on_close:
                on_close()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(content),
            actions=[
                ft.TextButton(button_text, on_click=handle_close),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dialog)
        dialog.open = True
        page.update()


# Funciones de conveniencia (para mantener compatibilidad)
def show_success(page: ft.Page, message: str) -> None:
    """Muestra un mensaje de éxito (wrapper para AlertManager)"""
    AlertManager.show_success(page, message)

def show_error(page: ft.Page, message: str) -> None:
    """Muestra un mensaje de error (wrapper para AlertManager)"""
    AlertManager.show_error(page, message)

def show_snackbar(page: ft.Page, message: str, message_type: str = "info") -> None:
    """Muestra una notificación flotante (wrapper para AlertManager)"""
    AlertManager.show_snackbar(page, message, AlertType(message_type))

def show_confirmation_dialog(
    page: ft.Page,
    title: str,
    content: str,
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar",
    on_confirm: Optional[Callable] = None,
    on_cancel: Optional[Callable] = None
) -> None:
    """Muestra diálogo de confirmación (wrapper para AlertManager)"""
    AlertManager.show_confirmation(
        page, title, content, confirm_text, cancel_text, on_confirm, on_cancel
    )

def show_alert_dialog(
    page: ft.Page,
    title: str,
    content: str,
    button_text: str = "OK",
    on_close: Optional[Callable] = None
) -> None:
    """Muestra diálogo de alerta (wrapper para AlertManager)"""
    AlertManager.show_alert(page, title, content, button_text, on_close)