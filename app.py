from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
import os
import math
from functools import wraps
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_flash_messages'  # Necesario para mensajes de alerta

# Configuración de Base de Datos (MySQL)
DB_HOST = os.getenv("DB_HOST", default="")
DB_USER = os.getenv("DB_USER", default="")
DB_PASSWORD = os.getenv("DB_PASSWORD", default="")
DB_NAME = os.getenv("DB_NAME", default="")

# Configuración de Usuario Admin
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", default="")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", default="")

def login_required(f):
    """Decorador para restringir acceso a usuarios logueados."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Debes iniciar sesión para acceder.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """Establece conexión con la base de datos."""
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    return conn

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Maneja el inicio de sesión."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Bienvenido al dashboard.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('logged_in', None)
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    """Muestra la lista de sitios."""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True) # dictionary=True para acceder por nombre de columna
    
    # Obtener total de sitios para calcular páginas
    cursor.execute("SELECT COUNT(*) as count FROM sitios")
    total_sitios = cursor.fetchone()['count']
    total_pages = math.ceil(total_sitios / per_page)

    # Obtener registros de la página actual
    cursor.execute("SELECT * FROM sitios ORDER BY id ASC LIMIT %s OFFSET %s", (per_page, offset))
    sitios = cursor.fetchall()
    conn.close()
    return render_template('index.html', sitios=sitios, page=page, total_pages=total_pages)

@app.route('/add', methods=['POST'])
@login_required
def add_site():
    """Agrega un nuevo sitio."""
    nombre = request.form['nombre']
    url = request.form['url']
    if url:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO sitios (nombre, url) VALUES (%s, %s)", (nombre, url))
            conn.commit()
            flash('Sitio agregado correctamente.')
        except mysql.connector.Error as err:
            flash(f'Error al agregar: {err}')
        finally:
            conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_site(id):
    """Edita un sitio existente."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form['nombre']
        url = request.form['url']
        # El checkbox envía valor solo si está marcado
        activo = 1 if 'activo' in request.form else 0

        cursor.execute("UPDATE sitios SET nombre = %s, url = %s, activo = %s WHERE id = %s", (nombre, url, activo, id))
        conn.commit()
        conn.close()
        flash('Sitio actualizado correctamente.')
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM sitios WHERE id = %s", (id,))
    sitio = cursor.fetchone()
    conn.close()
    
    if sitio:
        return render_template('edit.html', sitio=sitio)
    else:
        flash('Sitio no encontrado.')
        return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_site(id):
    """Elimina un sitio existente."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM sitios WHERE id = %s", (id,))
        conn.commit()
        flash('Sitio eliminado correctamente.')
    except mysql.connector.Error as err:
        flash(f'Error al eliminar: {err}')
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/history/<int:id>')
@login_required
def site_history(id):
    """Muestra el historial de tiempos de respuesta de un sitio."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener información del sitio
    cursor.execute("SELECT * FROM sitios WHERE id = %s", (id,))
    sitio = cursor.fetchone()
    
    if not sitio:
        conn.close()
        flash('Sitio no encontrado.')
        return redirect(url_for('index'))

    # Obtener historial ordenado por fecha
    cursor.execute("SELECT fecha, tiempo_respuesta FROM historial WHERE sitio_id = %s ORDER BY fecha ASC", (id,))
    historial = cursor.fetchall()
    conn.close()
    
    # Preparar datos para Chart.js (Listas simples)
    labels = [h['fecha'].strftime('%Y-%m-%d %H:%M') for h in historial]
    data = [h['tiempo_respuesta'] for h in historial]
    
    return render_template('history.html', sitio=sitio, labels=labels, data=data)

@app.route('/api/sites')
def api_sites():
    """Retorna el estado de los sitios en formato JSON."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM sitios")
    sitios = cursor.fetchall()
    conn.close()

    for sitio in sitios:
        if sitio['ultima_revision']:
            sitio['ultima_revision'] = sitio['ultima_revision'].strftime('%d-%m-%Y %H:%M:%S')

    return jsonify(sitios)

if __name__ == '__main__':
    # Ejecutar en modo debug para desarrollo
    app.run(debug=True, host='0.0.0.0', port=5000)