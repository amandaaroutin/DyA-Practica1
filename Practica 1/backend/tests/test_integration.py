import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import psycopg2
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    """Crea un cliente de pruebas de Flask."""
    with app.test_client() as client:
        yield client


# ==========================================
# TESTS BÁSICOS DE REGISTRO Y LOGIN
# ==========================================

def test_registro_medico_completo(client):
    """Prueba el flujo completo de registro de médico."""
    nuevo_medico = {
        "nombre": "Dr. Ana María",
        "email": "anamaria@hospital.com",
        "password": "password123",
        "especialidad": "Cardiología",
    }
    response = client.post("/register", data=nuevo_medico)
    assert response.status_code in (200, 302)


def test_login_medico(client):
    """Prueba el login de un médico."""
    # Primero registrar
    nuevo_medico = {
        "nombre": "Dr. Carlos Mario",
        "email": "carlosmario@hospital.com",
        "password": "password123",
        "especialidad": "Pediatría",
    }
    client.post("/register", data=nuevo_medico)

    # Luego hacer login
    login_data = {"email": "carlosmario@hospital.com", "password": "password123"}
    response = client.post("/login", data=login_data)
    assert response.status_code in (200, 302)


def test_logout(client):
    """Verifica que el logout funciona correctamente."""
    response = client.get("/logout")
    assert response.status_code == 302


# ==========================================
# TESTS SIN AUTENTICACIÓN (REDIRECCIÓN)
# ==========================================

def test_dashboard_sin_login(client):
    """Verifica que el dashboard requiere autenticación."""
    response = client.get("/dashboard")
    assert response.status_code == 302


def test_api_citas_sin_login(client):
    """Verifica que la API de citas requiere autenticación."""
    response = client.get("/api/citas")
    assert response.status_code == 302


@patch("app.get_db_connection")
def test_agregar_paciente_sin_login(mock_get_conn, client):
    """Verifica que agregar paciente requiere autenticación."""
    response = client.post(
        "/agregar_paciente",
        data={
            "nombre": "Test Paciente",
            "edad": "30",
            "email": "test@example.com",
            "telefono": "123456789",
            "fecha_registro": "2024-10-15",
            "historial": "Test historial",
        },
    )
    assert response.status_code == 302


def test_historial_sin_login(client):
    """Verifica que el historial requiere autenticación."""
    response = client.get("/historial/1")
    assert response.status_code == 302


def test_cancelar_cita_sin_login(client):
    """Verifica que cancelar cita requiere autenticación."""
    response = client.post("/cancelar_cita/1")
    assert response.status_code == 302


def test_eliminar_paciente_sin_login(client):
    """Verifica que eliminar paciente requiere autenticación."""
    response = client.post("/eliminar_paciente/1")
    assert response.status_code == 302


def test_eliminar_paciente_confirmacion_sin_login(client):
    """Verifica que la confirmación de eliminar requiere autenticación."""
    response = client.get("/eliminar_paciente/confirmacion/1")
    assert response.status_code == 302


# ==========================================
# TESTS CON AUTENTICACIÓN
# ==========================================

@patch("app.get_db_connection")
def test_dashboard_con_login(mock_get_conn, client):
    """Verifica acceso al dashboard con autenticación."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1, "Dr. Test")
    mock_cursor.fetchall.return_value = []
    mock_conn.__class__ = psycopg2.extensions.connection
    mock_get_conn.return_value = mock_conn

    with client.session_transaction() as sess:
        sess["medico_id"] = 1
        sess["medico_nombre"] = "Dr. Test"

    response = client.get("/dashboard")
    assert response.status_code == 200


@patch("app.get_db_connection")
def test_api_citas_con_login(mock_get_conn, client):
    """Verifica acceso a API de citas con autenticación."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1, "Dr. Test")
    mock_cursor.fetchall.return_value = []
    mock_conn.__class__ = psycopg2.extensions.connection
    mock_get_conn.return_value = mock_conn

    with client.session_transaction() as sess:
        sess["medico_id"] = 1
        sess["medico_nombre"] = "Dr. Test"

    response = client.get("/api/citas")
    assert response.status_code == 200
    assert response.content_type == "application/json"


# ==========================================
# TESTS DE VALIDACIÓN DE FORMULARIOS
# ==========================================

def test_login_campos_vacios(client):
    """Verifica validación de campos vacíos en login."""
    response = client.post("/login", data={"email": "", "password": ""})
    assert response.status_code == 200
    assert b"completa todos los campos" in response.data.lower()


def test_register_campos_vacios(client):
    """Verifica validación de campos vacíos en registro."""
    response = client.post(
        "/register", data={"nombre": "", "email": "", "password": ""}
    )
    assert response.status_code == 200
    assert b"completa todos los campos" in response.data.lower()


def test_login_credenciales_incorrectas(client):
    """Verifica manejo de credenciales incorrectas."""
    with patch("app.get_db_connection") as mock_get_conn:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        mock_conn.__class__ = psycopg2.extensions.connection
        mock_get_conn.return_value = mock_conn

        response = client.post(
            "/login", data={"email": "noexiste@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        assert b"credenciales incorrectas" in response.data.lower()


@patch("app.get_db_connection")
def test_register_email_duplicado(mock_get_conn, client):
    """Verifica manejo de email ya registrado."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)
    mock_conn.__class__ = psycopg2.extensions.connection
    mock_get_conn.return_value = mock_conn

    response = client.post(
        "/register",
        data={
            "nombre": "Dr. Test",
            "email": "existing@example.com",
            "password": "password123",
            "especialidad": "Medicina General",
        },
    )
    assert response.status_code == 200
    assert b"email ya est" in response.data.lower()
