# backend/tests/test_unit.py
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from unittest.mock import patch, MagicMock
from app import (
    app,
    hash_password,
    get_next_medico_id,
    get_db_connection,
    init_db,
    obtener_citas_medico,
    obtener_pacientes_medico,
    buscar_paciente_por_id,
    get_db_host,
)


# ==========================================
# TESTS BÁSICOS DE RUTAS Y FUNCIONES
# ==========================================

def test_home_route():
    """Verifica que la ruta raíz responda correctamente."""
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code in (200, 302)


def test_login_page():
    """Verifica que la página de login se carga correctamente."""
    with app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert b"email" in response.data.lower()


def test_hash_password():
    """Verifica que la función de hash funciona correctamente."""
    password = "test123"
    hashed = hash_password(password)
    assert hashed is not None
    assert len(hashed) == 64  # SHA256 produce 64 caracteres
    assert hashed != password  # El hash debe ser diferente al password original


def test_get_next_medico_id():
    """Verifica que la función get_next_medico_id retorna un número válido."""
    next_id = get_next_medico_id()
    assert isinstance(next_id, int)
    assert next_id >= 1


def test_get_db_host():
    """Verifica que get_db_host retorna un host válido."""
    host = get_db_host()
    assert host is not None
    assert isinstance(host, str)
    assert host in ["bd", "localhost"]


# ==========================================
# TESTS DE CONEXIÓN A BASE DE DATOS
# ==========================================

@patch("app.psycopg2.connect")
def test_get_db_connection_success(mock_connect):
    """Verifica conexión exitosa a la base de datos."""
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn

    conn = get_db_connection()

    assert conn == mock_conn
    mock_connect.assert_called_once()
    mock_conn.set_session.assert_called_once()


@patch("app.psycopg2.connect")
def test_get_db_connection_failure(mock_connect):
    """Verifica manejo de error en conexión a BD."""
    mock_connect.side_effect = psycopg2.Error("Connection failed")

    result = get_db_connection()

    assert isinstance(result, str)
    assert "Connection failed" in result


@patch("app.get_db_connection")
def test_init_db_success(mock_get_conn):
    """Verifica inicialización exitosa de la base de datos."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__class__ = psycopg2.extensions.connection
    mock_get_conn.return_value = mock_conn

    init_db()

    assert mock_cursor.execute.call_count == 3  # 3 tablas
    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


# ==========================================
# TESTS DE OPERACIONES CON CITAS
# ==========================================

@patch("app.get_db_connection")
def test_obtener_citas_medico_success(mock_get_conn):
    """Verifica obtención exitosa de citas de un médico."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__class__ = psycopg2.extensions.connection
    mock_get_conn.return_value = mock_conn

    citas_mock = [
        ("2024-10-15", "10:00:00", "Consulta general", 1),
        ("2024-10-16", "14:30:00", "Revisión", 2),
    ]
    mock_cursor.fetchall.return_value = citas_mock

    citas, error = obtener_citas_medico(1)

    assert error is None
    assert len(citas) == 2
    assert citas == citas_mock
    mock_cursor.execute.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()


@patch("app.get_db_connection")
def test_obtener_citas_medico_error(mock_get_conn):
    """Verifica manejo de error al obtener citas."""
    mock_get_conn.return_value = "Error de conexión"

    citas, error = obtener_citas_medico(1)

    assert citas == []
    assert "Error conexión" in error


# ==========================================
# TESTS DE OPERACIONES CON PACIENTES
# ==========================================

@patch("app.get_db_connection")
def test_obtener_pacientes_medico_success(mock_get_conn):
    """Verifica obtención exitosa de pacientes de un médico."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    pacientes_mock = [
        (
            1,
            "Amanda Aroutin",
            21,
            "amanda@email.com",
            "123456789",
            "Historial 1",
            "2024-01-01",
        ),
        (
            2,
            "Eduardo Lukacs",
            20,
            "edu@email.com",
            "987654321",
            "Historial 2",
            "2024-01-02",
        ),
    ]
    mock_cursor.fetchall.return_value = pacientes_mock

    pacientes, error = obtener_pacientes_medico(1)

    assert error is None
    assert len(pacientes) == 2
    assert pacientes == pacientes_mock
    mock_cursor.execute.assert_called_once()


@patch("app.get_db_connection")
def test_obtener_pacientes_medico_error(mock_get_conn):
    """Verifica manejo de error al obtener pacientes."""
    mock_get_conn.return_value = None

    pacientes, error = obtener_pacientes_medico(1)

    assert pacientes == []
    assert "Error de conexión" in error


@patch("app.get_db_connection")
def test_buscar_paciente_por_id_success(mock_get_conn):
    """Verifica búsqueda exitosa de paciente por ID."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    paciente_mock = (
        1,
        "Amanda Aroutin",
        21,
        "amanda@email.com",
        "123456789",
        "Historial",
        "2024-01-01",
    )
    mock_cursor.fetchone.return_value = paciente_mock

    pacientes, error = buscar_paciente_por_id(1, 1)

    assert error is None
    assert len(pacientes) == 1
    assert pacientes[0] == paciente_mock


@patch("app.get_db_connection")
def test_buscar_paciente_por_id_not_found(mock_get_conn):
    """Verifica búsqueda de paciente no encontrado."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = mock_conn

    mock_cursor.fetchone.return_value = None

    pacientes, error = buscar_paciente_por_id(1, 999)

    assert pacientes == []
    assert error == "Paciente no encontrado"
