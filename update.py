import requests
import time
import os
import smtplib
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

            urls_a_verificar = []
            urls_file = 'urls.txt'
            try:
                with open(urls_file, 'r', encoding='utf-8') as f:
                    # Leemos cada línea, quitamos espacios en blanco y omitimos líneas vacías
                    urls_a_verificar = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"🚨 Alerta: El archivo '{urls_file}' no fue encontrado. No se verificarán URLs.")

            if not urls_a_verificar:
                print("No hay URLs en el archivo para verificar.")
                
            failed_sites = []

            for url in urls_a_verificar:
                try:
                    response = requests.get(url, timeout=10)
                    if response.ok:
                        print(f"✅ {url} -> Correcto (Status: {response.status_code})")
                    else:
                        error_message = f"Status: {response.status_code}"
                        print(f"🚨 {url} -> Alerta ({error_message})")
                        failed_sites.append((url, error_message))
                except (requests.ConnectionError, requests.Timeout) as e:
                    error_message = "Error de conexión/timeout"
                    print(f"🚨 {url} -> Alerta ({error_message})")
                    failed_sites.append((url, error_message))

            if failed_sites:
                summary_message = "🚨 ¡Alerta! Se detectaron fallos en los siguientes sitios:\n\n"
                summary_message += "\n".join([f"- {site}: {reason}" for site, reason in failed_sites])
                
                # Enviar notificaciones
                send_telegram_notification(summary_message)
                #send_email_notification("🚨 Alerta de Monitoreo: Sitios web con fallos", summary_message)
        
        time.sleep(600) # Espera 10 minutos para la siguiente verificación
