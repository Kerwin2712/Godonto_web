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

2. Instala las dependencias:  
   ```bash
   pip install -r requirements.txt  
   ```
3. Crea la base de datos:  
   ```bash
   psql -U postgres -c "CREATE DATABASE godonto;"
   ```  
4. Crea un las variables de entorno:
   ```bash
   DB_HOST = localhost
   DB_NAME= godonto
   DB_USER= tu_user
   DB_PASSWORD = tu_pass
   DB_PORT=5432
   ```
6. Crea las tablas:
   ```bash
   psql -U postgres -d godonto -f database/backup.sql
   ```
7. Crea un usuario en la tabla users:
   ```bash
   INSERT INTO users (username, password_hash, email, is_admin, is_verified, is_active) VALUES ('admin', 'password', 'admin@example.com', True, True, True);
   ```
8. Ejecuta el programa: 
   ```bash
   python main.py
   ```