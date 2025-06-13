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
from views.presupuesto.presup_form import presup_view
from views.presupuesto.quotes import quotes_view
from views.tretment.treatments import treatments_view
import os
from services.preference_service import PreferenceService # Importar el nuevo servicio

# Configuración de logging
# Directorio alternativo para logs (ej: AppData/Local)
log_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'GodontoClinic', 'logs')
os.makedirs(log_dir, exist_ok=True)  # Crea el directorio si no existe

log_file = os.path.join(log_dir, 'godonto.log')

# Configuración de logging
logging.basicConfig(
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Muestra logs en consola
    ],  # Nueva ubicación con permisos
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main(page: ft.Page):
    # Configuración inicial de la página
    #page.logger.setLevel(ft.LoggingLevel.DEBUG)
    page.title = settings.APP_NAME
    page.padding = 0
    page.window_width = 1200
    page.window_height = 800
    
    # Cargar la preferencia de tema al iniciar
    # Asumimos un user_id fijo (por ejemplo, 1) si no hay un sistema de autenticación
    # De lo contrario, este user_id debería venir de la sesión del usuario autenticado
    user_id_for_preferences = 1 
    saved_theme = PreferenceService.get_user_theme(user_id_for_preferences)
    page.theme_mode = ft.ThemeMode.DARK if saved_theme == 'dark' else ft.ThemeMode.LIGHT
    logger.info(f"Tema inicial cargado para el usuario {user_id_for_preferences}: {page.theme_mode}")


    # Manejar el cierre de la ventana
    def window_event(e):
        if e.data == "close":
            logger.info("Cerrando aplicación...")
            Database.close_all_connections()
            page.close()
    
    page.window_prevent_close = True
    page.on_window_event = window_event
    
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
        if page and not page.close:
            page.open(error_dialog)
            error_dialog.open = True
            page.update()

    def route_change(e):
        """Manejador de rutas síncrono"""
        try:
            current_route = page.route

            # Limpiar todas las vistas actuales (excepto la primera si es el login inicial)
            # Esto evita la acumulación de vistas en la pila.
            if len(page.views) > 1: # Si hay más de una vista (ej. no es la primera vez en el login)
                page.views.pop() # Eliminar la vista actual de la pila
            else: # Si es la primera vista o la única, limpiar toda la pila
                page.views.clear()

            # CRÍTICO: Limpiar explícitamente el overlay de la página.
            # Esto elimina cualquier FilePicker, SearchBar, DatePicker, etc.
            # que hayan sido añadidos por vistas anteriores y se encuentren en el overlay.
            page.overlay.clear()
            page.update() # Asegurarse de que la página se actualice después de limpiar el overlay


            try:
                if page.route == "/login":
                    page.views.append(login_view(page))
                elif page.route == "/dashboard":
                    page.views.append(dashboard_view(page))
                elif page.route == "/treatments":
                    page.views.append(treatments_view(page))
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
                elif page.route == "/presupuesto" or page.route.startswith("/presupuesto/"):
                    client_id = None
                    quote_id = None 
                    route_parts = page.route.split("/")
                    if len(route_parts) > 2:
                        try:
                            if len(route_parts) > 3:
                                quote_id = int(route_parts[2])
                                client_id = int(route_parts[3])
                            else: 
                                client_id = int(route_parts[2])
                        except (IndexError, ValueError):
                            logger.error(f"Error al parsear ID de presupuesto o cliente de la ruta: {page.route}")
                    page.views.append(presup_view(page, client_id, quote_id)) 
                elif page.route == "/appointment_form" or page.route.startswith("/appointment_form/"):
                    appointment_id = None
                    if page.route.startswith("/appointment_form/"):
                        try:
                            appointment_id = int(page.route.split("/")[2])
                        except (IndexError, ValueError):
                            logger.error(f"Error {IndexError}: {str(ValueError)}")
                    page.views.append(appointment_form_view(page, appointment_id))
                elif page.route == "/quotes": 
                    page.views.append(quotes_view(page))
                elif page.route == "/calendar":
                    page.views.append(calendar_view(page))
                elif page.route == "/reports":
                    page.views.append(reports_view(page))
                
                page.update()
                
            except Exception as view_error:
                logger.error(f"Error al cargar la vista: {str(view_error)}")
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
        try:
            Database.initialize()
            ft.app(target=main, view=ft.AppView.FLET_APP)
        finally:
            Database.close_all_connections()
    except Exception as e:
        logger.critical(f"Error crítico al iniciar la aplicación: {e}")
        raise
