import requests
import time
import os
import smtplib
import mysql.connector
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración de Notificaciones (Telegram) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Configuración de Notificaciones (Email) ---
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# --- Configuración de Base de Datos (MySQL) ---
DB_HOST = os.getenv("DB_HOST", default="")
DB_USER = os.getenv("DB_USER", default="")
DB_PASSWORD = os.getenv("DB_PASSWORD", default="")
DB_NAME = os.getenv("DB_NAME", default="")

def send_email_notification(subject, body):
    """Envía una notificación por correo electrónico usando Gmail."""
    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, RECIPIENT_EMAIL]):
        print("Faltan credenciales de correo. No se enviará email.")
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
            print("Notificación por correo enviada.")
    except Exception as e:
        print(f"Error al enviar correo: {e}")

def send_telegram_notification(message):
    """Envía un mensaje a un chat de Telegram a través de un bot."""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("Faltan credenciales de Telegram. No se enviará notificación.")
        return
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(api_url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message})
        response.raise_for_status()
        print("Notificación de Telegram enviada.")
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar notificación de Telegram: {e}")


while True:
        print(f"--- Iniciando verificación (Horario activo): {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        try:
            # Primero, verificamos la conexión a internet general
            requests.get('https://www.google.com', timeout=5)
        except (requests.ConnectionError, requests.Timeout):
            print("Sin conexión a internet.")
        else:
            print("Con conexión a internet.")

            sitios = []
            conn = None
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME
                )
                cursor = conn.cursor(dictionary=True)
                # Seleccionamos solo los sitios activos
                cursor.execute("SELECT id, url FROM sitios WHERE activo = 1")
                sitios = cursor.fetchall()
            except mysql.connector.Error as err:
                print(f"Error al conectar a la base de datos: {err}")

            if not sitios:
                print("No hay sitios activos para verificar en la base de datos.")
                
            failed_sites = []

            for sitio in sitios:
                url = sitio['url']
                site_id = sitio['id']
                nuevo_estado = "Pendiente"
                tiempo_respuesta = 0

                try:
                    response = requests.get(url, timeout=10)
                    tiempo_respuesta = response.elapsed.total_seconds()
                    if response.ok:
                        print(f"✅ {url} -> Correcto (Status: {response.status_code})")
                        nuevo_estado = f"{response.status_code} OK"
                    else:
                        error_message = f"Status: {response.status_code}"
                        print(f"🚨 {url} -> Alerta ({error_message})")
                        failed_sites.append((url, error_message))
                        nuevo_estado = f"Error {response.status_code}"
                except (requests.ConnectionError, requests.Timeout) as e:
                    error_message = "Error de conexión/timeout"
                    print(f"🚨 {url} -> Alerta ({error_message})")
                    failed_sites.append((url, error_message))
                    nuevo_estado = "Error Conexión"

                # Actualizar estado en la base de datos
                if conn and conn.is_connected():
                    try:
                        ahora = datetime.now()
                        # Actualizar estado actual (para el dashboard en tiempo real)
                        cursor.execute(
                            "UPDATE sitios SET estado = %s, ultima_revision = %s, tiempo_respuesta = %s WHERE id = %s",
                            (nuevo_estado, ahora, tiempo_respuesta, site_id)
                        )
                        # Guardar registro en el historial
                        cursor.execute(
                            "INSERT INTO historial (sitio_id, estado, tiempo_respuesta, fecha) VALUES (%s, %s, %s, %s)",
                            (site_id, nuevo_estado, tiempo_respuesta, ahora)
                        )
                        conn.commit()
                    except mysql.connector.Error as err:
                        print(f"Error al actualizar DB para {url}: {err}")

            if conn and conn.is_connected():
                cursor.close()
                conn.close()

            if failed_sites:
                summary_message = "🚨 ¡Alerta! Se detectaron fallos en los siguientes sitios:\n\n"
                summary_message += "\n".join([f"- {site}: {reason}" for site, reason in failed_sites])
                
                # Enviar notificaciones
                send_telegram_notification(summary_message)
                #send_email_notification("🚨 Alerta de Monitoreo: Sitios web con fallos", summary_message)
        
        time.sleep(600) # Espera 10 minutos para la siguiente verificación
