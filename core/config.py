import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any
import flet as ft
from urllib.parse import urlparse  # Nueva importación

load_dotenv()

class Config:
    """Configuración base de la aplicación"""
    # Configuración general
    APP_NAME: str = "Godonto"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-for-dev")
    
    # Configuración de la base de datos (MODIFICADO PARA RENDER)
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # Configuración de la base de datos (compatible con local y Render)
    @property
    def DB_CONFIG(self):
        # FORZAR uso de DATABASE_URL en producción
        if os.getenv('RENDER'):  # Variable automática en Render
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                raise ValueError("DATABASE_URL es requerida en Render")
            
            db_url = db_url.replace('postgres://', 'postgresql://')
            parsed = urlparse(db_url)
            
            return {
                'host': parsed.hostname,
                'database': parsed.path[1:],
                'user': parsed.username,
                'password': parsed.password,
                'port': parsed.port,
                'sslmode': 'require'
            }
        else:  # Desarrollo local
            return {
                'host': 'localhost',
                'database': 'godonto_db',
                'user': 'postgres',
                'password': '',
                'port': 5432,
                'sslmode': 'disable'
            }
    
    # Resto de la configuración permanece igual...
    FLET_PORT: int = int(os.getenv("FLET_PORT", "8500"))
    FLET_VIEW: str = os.getenv("FLET_VIEW", "WEB_BROWSER")
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    STATIC_DIR: Path = BASE_DIR / "static"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "godonto.log")
    
    @property
    def FLET_VIEW(self) -> ft.AppView:
        view_mapping = {
            "WEB_BROWSER": ft.AppView.WEB_BROWSER,
            "FLET_APP": ft.AppView.FLET_APP,
            "FLET_APP_WEB": ft.AppView.FLET_APP_WEB
        }
        return view_mapping.get(os.getenv("FLET_VIEW", "WEB_BROWSER"), ft.AppView.WEB_BROWSER)

settings = Config()