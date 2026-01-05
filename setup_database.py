import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Configuración de rutas
BASE_DIR = r'p:\webcheck'
URLS_FILE = os.path.join(BASE_DIR, 'urls.txt')

# Configuración de Base de Datos (MySQL)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "monitoreo")

def inicializar_db():
    """Crea la base de datos y la tabla si no existen."""
    # Conexión al servidor MySQL para crear la DB
    conn_server = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor_server = conn_server.cursor()
    cursor_server.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cursor_server.close()
    conn_server.close()

    # Conexión a la base de datos específica
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    # Estructura de la tabla para MySQL
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sitios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) DEFAULT 'sitio',
            url VARCHAR(500) NOT NULL UNIQUE,
            activo BOOLEAN DEFAULT 1,
            estado VARCHAR(255) DEFAULT 'Pendiente',
            tiempo_respuesta FLOAT DEFAULT 0,
            ultima_revision DATETIME
        )
    ''')

    # Tabla para el historial de revisiones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sitio_id INT,
            estado VARCHAR(255),
            tiempo_respuesta FLOAT,
            fecha DATETIME,
            FOREIGN KEY (sitio_id) REFERENCES sitios(id) ON DELETE CASCADE
        )
    ''')

    # Intentar agregar la columna si la tabla ya existe (migración para DB existente)
    try:
        cursor.execute("ALTER TABLE sitios ADD COLUMN tiempo_respuesta FLOAT DEFAULT 0")
    except mysql.connector.Error:
        pass  # La columna probablemente ya existe, ignoramos el error

    conn.commit()
    return conn

def importar_urls(conn):
    """Lee el archivo de texto e inserta nuevas URLs."""
    if not os.path.exists(URLS_FILE):
        print(f"No se encontró el archivo: {URLS_FILE}")
        return

    with open(URLS_FILE, 'r') as f:
        # Leemos las líneas ignorando las vacías
        urls = [line.strip() for line in f if line.strip()]

    cursor = conn.cursor()
    nuevos = 0
    for url in urls:
        # INSERT IGNORE es específico de MySQL para ignorar duplicados
        cursor.execute("INSERT IGNORE INTO sitios (url) VALUES (%s)", (url,))
        if cursor.rowcount > 0:
            nuevos += 1
    
    conn.commit()
    print(f"Proceso completado. Se agregaron {nuevos} sitios nuevos a la base de datos.")

def limpiar_historial(conn):
    """Elimina registros del historial con más de 30 días de antigüedad."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial WHERE fecha < DATE_SUB(NOW(), INTERVAL 30 DAY)")
    eliminados = cursor.rowcount
    conn.commit()
    if eliminados > 0:
        print(f"Mantenimiento: Se eliminaron {eliminados} registros antiguos del historial.")

if __name__ == '__main__':
    try:
        conn = inicializar_db()
        importar_urls(conn)
        limpiar_historial(conn)
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error de conexión a MySQL: {err}")
        print("Asegúrate de configurar DB_HOST, DB_USER, DB_PASSWORD, DB_NAME en .env")
