import os
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, Any
import flet as ft

load_dotenv()

class Config:
    """Configuración base de la aplicación"""
    # Configuración general
    APP_NAME: str = "Godonto"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-for-dev")
    
    # Configuración de la base de datos
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "godonto_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    
    # Configuración de la aplicación Flet
    FLET_PORT: int = int(os.getenv("FLET_PORT", "8500"))
    FLET_VIEW: str = os.getenv("FLET_VIEW", "WEB_BROWSER")
    
    # Configuración de autenticación
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hora
    
    # Rutas de la aplicación
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    STATIC_DIR: Path = BASE_DIR / "static"
    
    # Configuración de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "godonto.log")
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Retorna la configuración de la base de datos como diccionario"""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD
        }
    
    @property
    def FLET_VIEW(self) -> ft.AppView:
        view_mapping = {
            "WEB_BROWSER": ft.AppView.WEB_BROWSER,
            "FLET_APP": ft.AppView.FLET_APP,
            "FLET_APP_WEB": ft.AppView.FLET_APP_WEB
        }
        return view_mapping.get(os.getenv("FLET_VIEW", "WEB_BROWSER"), ft.AppView.WEB_BROWSER)

# Instancia de configuración para importar
settings = Config()