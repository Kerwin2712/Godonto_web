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
        """Inicializa el pool de conexiones a la base de datos"""
        
        try:
            db_config = settings.get_database_config()
            logger.info(f"Intentando conectar a la base de datos con config: {db_config}")
            cls._connection_pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=db_config["host"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"],
                port=db_config["port"]
            )
            cls._initialized = True
            logger.info("Pool de conexiones a la base de datos inicializado correctamente")
            
            # Registrar el cierre al salir
            #atexit.register(cls.close_all_connections)
            
            # Test connection
            with cls.get_cursor() as cur:
                cur.execute("SELECT 1")
                logger.info("Conexión a la base de datos verificada correctamente")
        except Exception as e:
            logger.critical(f"No se pudo conectar a la base de datos: {str(e)}")
            raise ConnectionError(f"No se pudo conectar a la base de datos: {str(e)}")

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Obtiene una conexión del pool"""
        if not cls._initialized:
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
        if cls._connection_pool and cls._initialized:
            try:
                cls._connection_pool.closeall()
                logger.info("Todas las conexiones de la base de datos cerradas")
                cls._initialized = False
            except Exception as e:
                logger.error(f"Error al cerrar conexiones: {str(e)}")

#atexit.register(Database.close_all_connections)

# Alias para compatibilidad con el código existente
get_db = Database.get_cursor