import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
import logging
from .config import settings

# Configuración del logger para este módulo
logger = logging.getLogger(__name__)

class Database:
    _connection_pool = None

    # En database.py, modifica el método initialize:
    @classmethod
    def initialize(cls):
        try:
            db_config = settings.DB_CONFIG
            logger.info(f"Intentando conectar a: {db_config['host']}")  # Para ver en logs
            
            # Prueba primero una conexión simple
            test_conn = psycopg2.connect(**db_config)
            test_conn.close()
            
            # Si funciona, crea el pool
            cls._connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **db_config
            )
            logger.info("Pool de conexiones creado exitosamente")
            
        except Exception as e:
            logger.error(f"Error de conexión DB: {str(e)}")
            raise ConnectionError(f"Error configurando pool: {str(e)}")

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Obtiene una conexión del pool"""
        if cls._connection_pool is None:
            cls.initialize()
        
        conn = cls._connection_pool.getconn()
        try:
            yield conn
        except Exception as e:
            logger.error(f"Error en la conexión: {str(e)}")
            raise
        finally:
            cls._connection_pool.putconn(conn)

    @classmethod
    @contextmanager
    def get_cursor(cls):
        """Obtiene un cursor de la base de datos"""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error en transacción: {str(e)}")
                raise
            finally:
                cursor.close()

    @classmethod
    def close_all_connections(cls):
        """Cierra todas las conexiones del pool"""
        if cls._connection_pool:
            cls._connection_pool.closeall()
            logger.info("Todas las conexiones de la base de datos cerradas")

# Alias para compatibilidad con el código existente
get_db = Database.get_cursor