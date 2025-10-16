import os
from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import psycopg2
import hashlib
from datetime import datetime
from functools import wraps

# Configuración de la base de datos
# Detectar si estamos en Docker o ejecutando localmente


def get_db_host():
    """Detecta el host de la base de datos según el entorno"""
    db_host = os.environ.get("DB_HOST", "bd")
    # Si DB_HOST no está definido o es 'bd', intentar localhost para tests locales
    if db_host == "bd":
        try:
            # Intentar conectar a localhost:5432 primero (para tests locales)
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", 5432))
            sock.close()
            if result == 0:
                return "localhost"
        except Exception:
            pass
    return db_host


DB_CONFIG = {
    "host": get_db_host(),
    "database": os.environ.get("DB_NAME", "DMN-pec1"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "postgres"),
    "port": int(os.environ.get("DB_PORT", 5432)),
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)
app.secret_key = "postgres"


def get_db_connection():
    """Establece conexión con la base de datos"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_session(
            autocommit=True, isolation_level="READ COMMITTED"
        )  # Fuerza autocommit y aislamiento seguro
        return conn
    except psycopg2.Error as e:
        print(f"Error conectando a la base de datos: {e}")
        return str(e)


def init_db():
    """Inicializa la tabla pacientes si no existe y la tabla citas"""
    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        print(f"Error inicializando la base de datos: {conn}")
        return
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS medicos (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                especialidad VARCHAR(255),
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pacientes (
                id SERIAL PRIMARY KEY,
                medico_id INT REFERENCES medicos(id) ON DELETE CASCADE,
                nombre VARCHAR(255) NOT NULL,
                edad INTEGER,
                email VARCHAR(255),
                telefono VARCHAR(50),
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS citas (
                id SERIAL PRIMARY KEY,
                paciente_id INT REFERENCES pacientes(id) ON DELETE CASCADE,
                medico_id INT REFERENCES medicos(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                hora TIME NOT NULL,
                motivo TEXT,
                cancelada BOOLEAN DEFAULT FALSE
            );
        """
        )
        conn.commit()
        cursor.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"Error inicializando la base de datos: {e}")


# FUNCIONES AUXILIARES


def hash_password(password):
    """Genera hash de la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_next_medico_id():
    """Obtiene el siguiente ID disponible para médicos"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM medicos")
            next_id = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return next_id
        except psycopg2.Error as e:
            print(f"Error obteniendo siguiente ID: {e}")
            return 1
    return 1


def login_required(f):
    """Decorador que requiere que el médico esté autenticado"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "medico_id" not in session:
            return redirect(url_for("index"))

        # Verificar que el medico_id existe en la base de datos
        conn = get_db_connection()
        if isinstance(conn, psycopg2.extensions.connection):
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nombre FROM medicos WHERE id = %s",
                    (session["medico_id"],),
                )
                medico = cursor.fetchone()
                cursor.close()
                conn.close()

                if not medico:
                    # Médico no existe en BD, limpiar sesión
                    session.clear()
                    return redirect(url_for("index"))

                # Actualizar nombre en sesión si existe
                session["medico_nombre"] = medico[1]

            except Exception as e:
                session.clear()
                return redirect(url_for("index"))
        else:
            # Error de conexión
            return redirect(url_for("index"))

        return f(*args, **kwargs)

    return decorated_function


def obtener_citas_medico(medico_id):
    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return [], f"Error conexión obtener_citas_medico: {conn}"
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT fecha, hora, motivo, id FROM citas WHERE medico_id = %s ORDER BY fecha, hora",
            (medico_id,),
        )
        citas = cursor.fetchall()
        cursor.close()
        conn.close()
        return citas, None
    except Exception as e:
        return [], f"Error en obtener_citas_medico: {e}"


def obtener_pacientes_medico(medico_id):
    conn = get_db_connection()
    if not conn:
        return [], "Error de conexión a la base de datos"

    try:
        cursor = conn.cursor()
        # Cambiar consulta para obtener TODOS los pacientes del médico, no solo los que tienen citas
        cursor.execute(
            """
            SELECT id, nombre, edad, email, telefono, historial, fecha_registro 
            FROM pacientes
            WHERE medico_id = %s
            ORDER BY nombre;
        """,
            (medico_id,),
        )
        pacientes = cursor.fetchall()
        cursor.close()
        conn.close()
        return pacientes, None
    except Exception as e:
        return [], str(e)


def buscar_paciente_por_id(medico_id, paciente_id):
    """Busca un paciente específico por ID que pertenezca al médico"""
    conn = get_db_connection()
    if not conn:
        return [], "Error de conexión a la base de datos"

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre, edad, email, telefono, historial, fecha_registro 
            FROM pacientes
            WHERE medico_id = %s AND id = %s
        """,
            (medico_id, paciente_id),
        )
        paciente = cursor.fetchone()
        cursor.close()
        conn.close()

        if paciente:
            return [paciente], None
        else:
            return [], "Paciente no encontrado"
    except Exception as e:
        return [], str(e)


# RUTAS DE LA APLICACIÓN


@app.route("/")
def index():
    """Página principal con formularios de login y registro"""
    # Asegúrate de pasar las variables necesarias para evitar errores en el template
    return render_template(
        "index.html",
        show_register=request.args.get("show_register") == "1",
        message=None,
        success=None,
    )


@app.route("/login", methods=["POST"])
def login():
    """Maneja el inicio de sesión de médicos"""
    email = request.form["email"]
    password = request.form["password"]

    if not email or not password:
        return render_template(
            "index.html",
            message="Por favor completa todos los campos",
            success=False,
            show_register=False,
        )

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return render_template(
            "index.html",
            message=f"Error de conexión a la base de datos: {conn}",
            success=False,
            show_register=False,
        )

    try:
        cursor = conn.cursor()
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id, nombre, email FROM medicos WHERE email = %s AND password_hash = %s",
            (email, password_hash),
        )
        medico = cursor.fetchone()
        cursor.close()
        conn.close()

        if medico:
            # Login exitoso
            session["medico_id"] = medico[0]
            session["medico_nombre"] = medico[1]
            session["medico_email"] = medico[2]
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "index.html",
                message="Credenciales incorrectas",
                success=False,
                show_register=False,
            )
    except psycopg2.Error as e:
        return render_template(
            "index.html",
            message=f"Error en la base de datos: {e}",
            success=False,
            show_register=False,
        )


@app.route("/register", methods=["POST"])
def register():
    """Maneja el registro de nuevos médicos"""
    nombre = request.form["nombre"]
    email = request.form["email"]
    password = request.form["password"]
    especialidad = request.form.get("especialidad", "")

    if not all([nombre, email, password]):
        return render_template(
            "index.html",
            message="Por favor completa todos los campos obligatorios",
            success=False,
            show_register=True,
        )

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return render_template(
            "index.html",
            message=f"Error de conexión a la base de datos: {conn}",
            success=False,
            show_register=True,
        )

    try:
        cursor = conn.cursor()
        # Verificar si el email ya existe
        cursor.execute("SELECT id FROM medicos WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template(
                "index.html",
                message="Este email ya está registrado",
                success=False,
                show_register=True,
            )

        # Registrar nuevo médico
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO medicos (nombre, email, password_hash, especialidad) VALUES (%s, %s, %s, %s)",
            (nombre, email, password_hash, especialidad),
        )
        cursor.close()
        conn.close()

        return render_template(
            "index.html",
            message="Registro exitoso. Ahora puedes iniciar sesión.",
            success=True,
            show_register=False,
        )
    except psycopg2.Error as e:
        return render_template(
            "index.html",
            message=f"Error en el registro: {e}",
            success=False,
            show_register=True,
        )


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    """Dashboard del médico: ver pacientes, agregar pacientes y buscar por ID"""
    message = None
    success = None
    error_dashboard = None
    data_pacientes = []

    try:
        medico_id = session.get("medico_id")
        medico_nombre = session.get("medico_nombre")

        # Mensajes desde GET
        if request.method == "GET":
            message = request.args.get("mensaje")
            success = request.args.get("exito")
            if success is not None:
                success = success == "True"

        # Verificar si hay búsqueda por ID
        buscar_id = request.args.get("buscar_id")

        if buscar_id:
            # Búsqueda específica por ID
            try:
                paciente_id = int(buscar_id)
                pacientes, error_pacientes = buscar_paciente_por_id(
                    medico_id, paciente_id
                )
            except ValueError:
                pacientes = []
                error_pacientes = "ID inválido"
        else:
            # Obtener todos los pacientes del médico
            pacientes, error_pacientes = obtener_pacientes_medico(medico_id)

        for paciente in pacientes:
            (
                paciente_id,
                nombre,
                edad,
                email,
                telefono,
                historial,
                fecha_registro,
            ) = paciente

            # Obtener solo el conteo de citas para estadísticas básicas
            conn = get_db_connection()
            if not conn:
                citas_count = 0
            else:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM citas
                    WHERE medico_id = %s AND paciente_id = %s
                """,
                    (medico_id, paciente_id),
                )
                citas_count = cursor.fetchone()[0]
                cursor.close()
                conn.close()

            data_pacientes.append(
                {
                    "id": paciente_id,
                    "nombre": nombre,
                    "edad": edad,
                    "email": email,
                    "telefono": telefono,
                    "historial": historial,
                    "fecha_registro": fecha_registro,
                    "citas_count": citas_count,
                }
            )

    except Exception as e:
        error_dashboard = f"Error global en dashboard: {e}"

    return render_template(
        "dashboard.html",
        user_name=medico_nombre,
        pacientes=data_pacientes,
        message=message,
        success=success,
        error_dashboard=error_dashboard,
        fecha_hoy=datetime.now().strftime("%Y-%m-%d"),
    )


@app.route("/api/citas")
@login_required
def api_citas():
    """Devuelve las citas del usuario autenticado en formato JSON"""
    user_id = session["medico_id"]
    citas, error = obtener_citas_medico(user_id)

    if error:
        return jsonify({"error": error}), 500

    citas_json = [
        {"fecha": str(cita[0]), "hora": str(cita[1]), "motivo": cita[2], "id": cita[3]}
        for cita in citas
    ]
    return jsonify(citas_json)


@app.route("/cancelar_cita/<int:cita_id>", methods=["POST"])
@login_required
def cancelar_cita(cita_id):
    """Marca una cita como cancelada para el médico autenticado"""
    medico_id = session["medico_id"]

    # Obtener parámetros de redirección
    redirect_to = request.form.get("redirect_to", "dashboard")
    paciente_id = request.form.get("paciente_id")

    conn = get_db_connection()

    if not isinstance(conn, psycopg2.extensions.connection):
        # Error de conexión
        if redirect_to == "historial" and paciente_id:
            return redirect(
                url_for(
                    "historial_paciente",
                    paciente_id=paciente_id,
                    mensaje="Error de conexión a la base de datos.",
                    exito=False,
                )
            )
        return redirect(
            url_for(
                "dashboard",
                mensaje="Error de conexión a la base de datos.",
                exito=False,
            )
        )

    try:
        cursor = conn.cursor()
        # Solo permite cancelar citas del médico autenticado
        cursor.execute(
            """
            UPDATE citas
            SET cancelada = TRUE
            WHERE id = %s AND medico_id = %s
        """,
            (cita_id, medico_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Redirigir según el origen
        if redirect_to == "historial" and paciente_id:
            return redirect(
                url_for(
                    "historial_paciente",
                    paciente_id=paciente_id,
                    mensaje="Cita cancelada correctamente.",
                    exito=True,
                )
            )
        return redirect(
            url_for("dashboard", mensaje="Cita cancelada correctamente.", exito=True)
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

        # Manejo de error con redirección apropiada
        if redirect_to == "historial" and paciente_id:
            return redirect(
                url_for(
                    "historial_paciente",
                    paciente_id=paciente_id,
                    mensaje=f"Error al cancelar la cita: {e}",
                    exito=False,
                )
            )
        return redirect(
            url_for("dashboard", mensaje=f"Error al cancelar la cita: {e}", exito=False)
        )


@app.route("/agregar_paciente", methods=["POST"])
@login_required
def agregar_paciente():
    """Agrega un paciente para el médico actual"""
    medico_id = session["medico_id"]

    nombre = request.form.get("nombre")
    edad = request.form.get("edad")
    email = request.form.get("email")
    telefono = request.form.get("telefono")
    fecha_registro = request.form.get("fecha_registro")
    historial = request.form.get("historial")

    if not (nombre and edad and email and fecha_registro):
        return redirect(
            url_for(
                "dashboard",
                mensaje="Por favor completa los campos obligatorios.",
                exito=False,
                mostrar_formulario="true",
            )
        )

    try:
        edad = int(edad)
    except ValueError:
        return redirect(
            url_for(
                "dashboard",
                mensaje="Edad inválida.",
                exito=False,
                mostrar_formulario="true",
            )
        )

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return redirect(
            url_for(
                "dashboard",
                mensaje=f"Error BD: {conn}",
                exito=False,
                mostrar_formulario="true",
            )
        )

    try:
        cursor = conn.cursor()
        # Insertar paciente con medico_id
        cursor.execute(
            """
            INSERT INTO pacientes (medico_id, nombre, edad, email, telefono, fecha_registro, historial)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
            (medico_id, nombre, edad, email, telefono, fecha_registro, historial),
        )
        paciente_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        # Éxito: ocultar formulario
        return redirect(
            url_for(
                "dashboard",
                mensaje=f"Paciente '{nombre}' agregado correctamente.",
                exito=True,
            )
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        # Error: mantener formulario visible
        return redirect(
            url_for(
                "dashboard",
                mensaje=f"Error al agregar paciente: {e}",
                exito=False,
                mostrar_formulario="true",
            )
        )


@app.route("/historial/<int:paciente_id>")
@login_required
def historial_paciente(paciente_id):
    """Muestra el historial completo de un paciente específico"""
    medico_id = session["medico_id"]
    medico_nombre = session["medico_nombre"]

    # Obtener información del paciente
    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return redirect(url_for("dashboard", mensaje=f"Error BD: {conn}", exito=False))

    try:
        cursor = conn.cursor()

        # Verificar que el paciente pertenece al médico
        cursor.execute(
            """
            SELECT id, nombre, edad, email, telefono, historial, fecha_registro
            FROM pacientes
            WHERE id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        paciente_data = cursor.fetchone()
        if not paciente_data:
            cursor.close()
            conn.close()
            return redirect(
                url_for(
                    "dashboard",
                    mensaje="Paciente no encontrado o no autorizado.",
                    exito=False,
                )
            )

        # Crear objeto paciente
        paciente = {
            "id": paciente_data[0],
            "nombre": paciente_data[1],
            "edad": paciente_data[2],
            "email": paciente_data[3],
            "telefono": paciente_data[4],
            "historial": paciente_data[5],
            "fecha_registro": paciente_data[6],
        }

        # Obtener todas las citas del paciente
        cursor.execute(
            """
            SELECT id, medico_id, fecha, hora, motivo, cancelada
            FROM citas
            WHERE paciente_id = %s AND medico_id = %s
            ORDER BY fecha DESC, hora DESC
        """,
            (paciente_id, medico_id),
        )

        citas = cursor.fetchall()

        # Calcular estadísticas
        citas_activas = sum(1 for cita in citas if not cita[5])
        citas_canceladas = sum(1 for cita in citas if cita[5])

        cursor.close()
        conn.close()

        # Obtener mensajes desde GET parameters
        message = request.args.get("mensaje")
        success = request.args.get("exito")
        if success is not None:
            success = success == "True"

        return render_template(
            "historial_paciente.html",
            paciente=paciente,
            citas=citas,
            citas_activas=citas_activas,
            citas_canceladas=citas_canceladas,
            medico_nombre=medico_nombre,
            fecha_hoy=datetime.now().strftime("%Y-%m-%d"),
            message=message,
            success=success,
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return redirect(
            url_for(
                "dashboard", mensaje=f"Error al obtener historial: {e}", exito=False
            )
        )


@app.route("/historial/<int:paciente_id>/agregar_cita", methods=["POST"])
@login_required
def agregar_cita_historial(paciente_id):
    """Agrega una nueva cita desde la vista de historial"""
    medico_id = session["medico_id"]

    fecha = request.form.get("fecha")
    hora = request.form.get("hora")
    motivo = request.form.get("motivo")

    if not (fecha and hora and motivo):
        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje="Por favor completa todos los campos.",
                exito=False,
                nueva_cita="true",
            )
        )

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje=f"Error BD: {conn}",
                exito=False,
                nueva_cita="true",
            )
        )

    try:
        cursor = conn.cursor()

        # Verificar que el paciente pertenece al médico
        cursor.execute(
            "SELECT id FROM pacientes WHERE id = %s AND medico_id = %s",
            (paciente_id, medico_id),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return redirect(
                url_for("dashboard", mensaje="Paciente no encontrado.", exito=False)
            )

        # Verificar si ya existe una cita con los mismos datos
        cursor.execute(
            """
            SELECT id FROM citas
            WHERE medico_id = %s AND paciente_id = %s AND fecha = %s AND hora = %s AND motivo = %s
        """,
            (medico_id, paciente_id, fecha, hora, motivo),
        )

        if cursor.fetchone():
            cursor.close()
            conn.close()
            return redirect(
                url_for(
                    "historial_paciente",
                    paciente_id=paciente_id,
                    mensaje="Ya existe una cita con esos datos.",
                    exito=False,
                    nueva_cita="true",
                )
            )

        # Crear la cita
        cursor.execute(
            """
            INSERT INTO citas (medico_id, paciente_id, fecha, hora, motivo)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (medico_id, paciente_id, fecha, hora, motivo),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje="Cita agendada correctamente.",
                exito=True,
            )
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje=f"Error al agendar cita: {e}",
                exito=False,
                nueva_cita="true",
            )
        )


@app.route("/eliminar_paciente/<int:paciente_id>", methods=["POST"])
@login_required
def eliminar_paciente(paciente_id):
    """Elimina un paciente y todas sus citas después de la confirmación"""
    medico_id = session["medico_id"]

    # Verificar confirmación
    confirmacion = request.form.get("confirmacion", "").strip().upper()
    if confirmacion != "ELIMINAR":
        return redirect(
            url_for("eliminar_paciente_confirmacion", paciente_id=paciente_id)
        )

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje=f"Error BD: {conn}",
                exito=False,
            )
        )

    try:
        cursor = conn.cursor()

        # Verificar que el paciente pertenece al médico y obtener nombre
        cursor.execute(
            """
            SELECT nombre FROM pacientes
            WHERE id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        paciente_data = cursor.fetchone()
        if not paciente_data:
            cursor.close()
            conn.close()
            return redirect(
                url_for(
                    "dashboard",
                    mensaje="Paciente no encontrado o no autorizado.",
                    exito=False,
                )
            )

        nombre_paciente = paciente_data[0]

        # Eliminar todas las citas del paciente (por CASCADE también se eliminan)
        cursor.execute(
            """
            DELETE FROM citas
            WHERE paciente_id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        # Eliminar el paciente
        cursor.execute(
            """
            DELETE FROM pacientes
            WHERE id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(
            url_for(
                "dashboard",
                mensaje=f"Paciente '{nombre_paciente}' eliminado correctamente junto con todas sus citas.",
                exito=True,
            )
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return redirect(
            url_for(
                "historial_paciente",
                paciente_id=paciente_id,
                mensaje=f"Error al eliminar paciente: {e}",
                exito=False,
            )
        )


@app.route("/eliminar_paciente/confirmacion/<int:paciente_id>")
@login_required
def eliminar_paciente_confirmacion(paciente_id):
    """Muestra la página de confirmación para eliminar un paciente"""
    medico_id = session["medico_id"]

    conn = get_db_connection()
    if not isinstance(conn, psycopg2.extensions.connection):
        return redirect(url_for("dashboard", mensaje=f"Error BD: {conn}", exito=False))

    try:
        cursor = conn.cursor()

        # Verificar que el paciente pertenece al médico
        cursor.execute(
            """
            SELECT id, nombre, edad, email, telefono, historial, fecha_registro
            FROM pacientes
            WHERE id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        paciente_data = cursor.fetchone()
        if not paciente_data:
            cursor.close()
            conn.close()
            return redirect(
                url_for(
                    "dashboard",
                    mensaje="Paciente no encontrado o no autorizado.",
                    exito=False,
                )
            )

        # Crear objeto paciente
        paciente = {
            "id": paciente_data[0],
            "nombre": paciente_data[1],
            "edad": paciente_data[2],
            "email": paciente_data[3],
            "telefono": paciente_data[4],
            "historial": paciente_data[5],
            "fecha_registro": paciente_data[6],
        }

        # Contar total de citas
        cursor.execute(
            """
            SELECT COUNT(*) FROM citas
            WHERE paciente_id = %s AND medico_id = %s
        """,
            (paciente_id, medico_id),
        )

        total_citas = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return render_template(
            "confirmar_eliminacion.html", paciente=paciente, total_citas=total_citas
        )

    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        return redirect(
            url_for(
                "dashboard", mensaje=f"Error al cargar confirmación: {e}", exito=False
            )
        )


@app.route("/logout")
def logout():
    """Cerrar sesión"""
    session.clear()
    return redirect(url_for("index"))


# EJECUCIÓN DE LA APLICACIÓN

if __name__ == "__main__":
    # Ejecutar una sola vez, sin reloader para evitar dobles cargas y pérdida de estado
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
