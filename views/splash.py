import flet as ft
import time
import threading
import logging
from core.database import Database
from services.appointment_service import AppointmentService
from services.preference_service import PreferenceService

logger = logging.getLogger(__name__)

class SplashView(ft.View):
    def __init__(self, page: ft.Page, on_complete):
        super().__init__(route="/splash", padding=0)
        self.page = page
        self.on_complete = on_complete
        self.bgcolor = ft.colors.SURFACE_VARIANT
        
        self.logo = ft.Image(
            src="icons/logo.png", # Asegúrate de que esta ruta sea correcta o usa un icono
            width=150,
            height=150,
            fit=ft.ImageFit.CONTAIN,
            opacity=0,
            animate_opacity=1000,
        )
        
        self.progress_bar = ft.ProgressBar(
            width=200,
            color="blue",
            bgcolor="white",
            value=0,
            opacity=0,
            animate_opacity=500,
        )
        
        self.status_text = ft.Text(
            "Iniciando...",
            size=14,
            color=ft.colors.ON_SURFACE_VARIANT,
            opacity=0,
            animate_opacity=500,
            text_align=ft.TextAlign.CENTER
        )

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        self.logo,
                        ft.Container(height=20),
                        self.progress_bar,
                        ft.Container(height=10),
                        self.status_text,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ft.alignment.center,
                expand=True,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=[ft.colors.PRIMARY_CONTAINER, ft.colors.SURFACE],
                ),
            )
        ]

    def did_mount(self):
        # Iniciar animación de entrada
        self.logo.opacity = 1
        self.progress_bar.opacity = 1
        self.status_text.opacity = 1
        self.update()
        
        # Iniciar carga en segundo plano
        threading.Thread(target=self._run_initialization, daemon=True).start()

    def _run_initialization(self):
        try:
            self._update_status("Conectando a la base de datos...", 0.2)
            # Simular un pequeño delay para que se vea la animación si es muy rápido
            time.sleep(0.5) 
            Database.initialize()
            
            self._update_status("Verificando citas pendientes...", 0.6)
            AppointmentService.cancel_past_pending_appointments()
            
            self._update_status("Cargando módulos...", 0.8)
            # Aquí podríamos precargar otros módulos si fuera necesario
            time.sleep(0.5)

            self._update_status("Cargando preferencias...", 0.9)
            user_id_for_preferences = 1 # Esto debería venir de algún lado, pero por ahora hardcoded como en main.py
            saved_theme = PreferenceService.get_user_theme(user_id_for_preferences)
            self.page.theme_mode = ft.ThemeMode.DARK if saved_theme == 'dark' else ft.ThemeMode.LIGHT
            self.page.update()

            self._update_status("¡Listo!", 1.0)
            time.sleep(0.5)
            
            # Navegar al login en el hilo principal
            self.page.run_task(self._complete_loading)
            
        except Exception as e:
            logger.error(f"Error durante la inicialización: {e}")
            self._update_status(f"Error: {str(e)}", 0.0)
            # Aquí podrías mostrar un botón de reintentar o salir

    def _update_status(self, text, progress):
        self.status_text.value = text
        self.progress_bar.value = progress
        self.update()

    async def _complete_loading(self):
        self.on_complete()
