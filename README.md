# Godonto  
Sistema de gestión de citas para clínicas odontológicas.  

## Tecnologías  
- Python 3.10  
- Flet (UI)  
- PostgreSQL (Base de datos)  

## Instalación  
1. Clona el repositorio:  
   ```bash
   git clone https://github.com/tu-usuario/Godonto.git
   ```

2. Crea el entorno virtual:  
   ```bash
   python -m venv venv
   ```

3. Activa el entorno virtual:  
   ```bash
   .\venv\Scripts\activate
   ```

4. Instala las dependencias:  
   ```bash
   pip install -r requirements.txt  
   ```

5. Crea la base de datos:  
   ```bash
   psql -U postgres -c "CREATE DATABASE godonto;"
   ```  

6. Crea un las variables de entorno:
   ```bash
   DB_HOST = localhost
   DB_NAME= godonto
   DB_USER= tu_user
   DB_PASSWORD = tu_pass
   DB_PORT=5432
   ```

7. Crea las tablas:
   ```bash
   psql -U postgres -d godonto -f database/backup.sql
   ```

8. Crea un usuario en la tabla users:
   ```bash
   INSERT INTO users (username, password_hash, email, is_admin, is_verified, is_active) VALUES ('admin', 'password', 'admin@example.com', True, True, True);
   ```

9. Ejecuta el programa: 
   ```bash
   python main.py
   ```

## Creación de Ejecutable e Instalador

Para empaquetar la aplicación y crear un instalador distribuible de Windows (.exe):

### 1. Compilar el Ejecutable con PyInstaller

Ejecuta el siguiente comando en la raíz del proyecto para generar la carpeta de distribución (`dist/Godonto`):

```powershell
.\venv\Scripts\python -m PyInstaller -y --noconsole --name "Godonto" --add-data "assets;assets" --icon "icons/favicon.ico" main.py
```

### 2. Copiar Archivo de Configuración .env

Para que el ejecutable compilado localice las credenciales de la base de datos en su versión empaquetada, copia el archivo `.env` a la carpeta de compilación:

```powershell
Copy-Item -Path ".env" -Destination "dist\Godonto\.env"
```

### 3. Crear el Instalador con Inno Setup

1. Instala [Inno Setup Compiler](https://www.jrsoftware.org/isdl.php).
2. Abre el archivo de configuración [godonto_installer.iss](file:///c:/Users/EQUIPO%20DELL/Documents/GitHub/Proyectos_Python/Godonto_Desk/Godonto_web/godonto_installer.iss) ubicado en la raíz del proyecto.
3. Presiona **F9** o haz clic en el botón de compilar verde en la barra superior de Inno Setup.
4. El instalador autoejecutable final se generará automáticamente en la carpeta `installer/godonto_setup_v1.0.0.exe`, listo para ser instalado en otras computadoras con Windows.