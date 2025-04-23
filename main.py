import flet as ft
import logging
from core.config import settings
from core.database import Database
from views.auth.login import login_view
from views.dashboard.dashboard import dashboard_view
from views.clients.clients import clients_view
from views.appointments.appointments import appointments_view
from views.calendar.calendar import calendar_view
from views.reports.reports import reports_view
from views.clients.client_form import client_form_view
from views.appointments.appointment_form import appointment_form_view

# Configuración de logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=settings.LOG_FILE if settings.LOG_FILE else None
)
logger = logging.getLogger(__name__)

def main(page: ft.Page):
    # Configuración inicial de la página
    page.title = settings.APP_NAME
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window_width = 1200
    page.window_height = 800
    
    def handle_error(e: Exception):
        """Manejo centralizado de errores mejorado"""
        logger.error(f"Error en la aplicación: {str(e)}", exc_info=True)
        
        error_msg = str(e)
        if "Null check" in error_msg:
            error_msg = "Error interno: datos faltantes. Por favor recargue la página."
        
        def close_dialog(e):
            error_dialog.open = False
            page.update()
            page.go("/dashboard")  # Redirigir a una ruta segura
        
        error_dialog = ft.AlertDialog(
            modal=True, 
            title=ft.Text("Error", color="red"),
            content=ft.Column([
                ft.Text(error_msg),
                ft.Text("Disculpe las molestias.", size=12)
            ], tight=True),
            actions=[
                ft.TextButton("OK", on_click=close_dialog),
            ],
        )
        
        # Asegurarse de que la página existe
        if page and not page.destroyed:
            page.open(error_dialog)
            error_dialog.open = True
            page.update()

    def route_change(e):
        """Manejador de rutas síncrono"""
        try:
            print(f"Cambiando a ruta: {page.route}")  # Debug
            # Mantener solo la última vista si es el dashboard
            if page.route == "/dashboard" and page.views:
                page.views.clear()
            
            # Asegurarse de que siempre haya una vista
            if not page.views:
                page.views.append(ft.View("/", [ft.ProgressRing()]))
            
            current_route = page.route
            
            try:
                if page.route == "/login":
                    page.views.append(login_view(page))
                elif page.route == "/dashboard":
                    page.views.append(dashboard_view(page))
                elif page.route == "/clients":
                    page.views.append(clients_view(page))
                elif page.route == "/client_form" or page.route.startswith("/client_form/"):
                    client_id = None
                    if len(current_route.split("/")) > 2:
                        try:
                            client_id = int(current_route.split("/")[2])
                        except ValueError:
                            pass
                    page.views.append(client_form_view(page, client_id))
                elif page.route == "/appointments":
                    page.views.append(appointments_view(page))
                elif page.route == "/appointment_form" or page.route.startswith("/appointment_form/"):
                    appointment_id = None
                    if page.route.startswith("/appointment_form/"):
                        try:
                            appointment_id = int(page.route.split("/")[2])
                        except (IndexError, ValueError):
                            pass
                    page.views.append(appointment_form_view(page, appointment_id))
                elif page.route == "/calendar":
                    page.views.append(calendar_view(page))
                elif page.route == "/reports":
                    page.views.append(reports_view(page))
                
                print(f"Vistas después de cambio: {page.views}")  # Debug
                page.update()
                
            except Exception as view_error:
                logger.error(f"Error al cargar la vista: {str(view_error)}")
                # Vista de error genérica
                page.views.append(
                    ft.View(
                        current_route,
                        [ft.Text("Error al cargar la página"), ft.ElevatedButton("Volver", on_click=lambda _: page.go("/dashboard"))]
                    )
                )
                page.update()
        except Exception as e:
            logger.error(f"Error en route_change: {str(e)}", exc_info=True)
            handle_error(e)
    
    # Configurar manejadores de eventos
    page.on_route_change = route_change
    page.on_error = lambda e: handle_error(e)
    
    # Iniciar con la ruta de login
    page.go("/login")
    
    # Cerrar conexiones al salir
    page.on_close = Database.close_all_connections

if __name__ == "__main__":
    try:
        # Inicializar la base de datos
        Database.initialize()
        
        ft.app(
            target=main, 
            view=settings.FLET_VIEW,
            port=settings.FLET_PORT
        )
    except Exception as e:
        logger.critical(f"Error crítico al iniciar la aplicación: {e}")
        raise