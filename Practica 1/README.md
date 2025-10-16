# Práctica 1 - Automatización y Despliegue con Git Hooks y GitHub Actions 

**Asignatura:** Despliegue y Automatización

**Alumnos:**
- Amanda María Aroutin Allocca
- Eduardo Sebastian Lukacs Sandru

**Fecha:** 02 de noviembre de 2025

---

Este proyecto fue desarrollado para la empresa ficticia **Tech4Health**, que necesita un módulo de gestión de pacientes para clínicas médicas que desean digitalizar procesos básicos. 

La aplicación es un **microservicio REST** implementado con Flask que permite:
- Registrar médicos y pacientes 
- Consultar pacientes por ID
- Gestionar citas médicas
- Eliminar pacientes

---

## Especificaciones

- **Lenguaje:** Python con Flask
- **Base de datos:** PostgreSQL
- **Arquitectura:** Microservicios con Docker Compose
- **Testing:** pytest con tests unitarios e integración
- **Automatización:** Git hooks locales para validación de código

---

## Cómo ejecutar la aplicación

### Prerrequisitos
- Docker
- Docker Compose

### Pasos para iniciar la aplicación

1. **Navegar al directorio del proyecto:**
   ```bash
   cd "Practica 1"
   ```

2. **Construir y levantar todos los contenedores:**
   ```bash
   docker-compose up --build
   ```
   
   O para ejecutar en segundo plano:
   ```bash
   docker-compose up --build -d
   ```

3. **Verificar que los contenedores están ejecutándose:**
   ```bash
   docker-compose ps
   ```

### URLs de acceso
- **Frontend (Nginx)**: http://localhost:8080
- **Backend (Flask)**: http://localhost:5001
- **Base de datos**: Puerto 5432

---

## Comandos útiles
```bash
# Detener la aplicación
docker-compose down

# Ver logs de los contenedores
docker-compose logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs bd

# Reconstruir sin caché
docker-compose build --no-cache
docker-compose up --build
```

---

## Estructura del proyecto

```
Practica 1/
├── .git/
│   └── hooks/
│       ├── pre-commit
│       ├── post-commit
│       ├── pre-push
│       └── post-push
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── README.md
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── test_integration.py
│       ├── test_unit.py
├── bd/
│   └── init.sql
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── static/
│   │   └── css/
│   │       ├── dashboard.css
│   │       └── style.css
│   └── templates/
│       ├── confirmar_eliminacion.html
│       ├── dashboard.html
│       ├── historial_paciente.html
│       └── index.html
└── images/
```

---

## Cómo se ejecutan los tests

### Tests básicos con pytest
```bash
cd backend
python -m pytest -v
```

### Tests específicos
```bash
# Solo tests unitarios
python -m pytest tests/test_unit.py -v

# Solo tests de integración
python -m pytest tests/test_integration.py -v
```

### Información de los tests
- **Tests unitarios:** 14 tests en `test_unit.py`
- **Tests de integración:** 16 tests en `test_integration.py`
- **Total:** 30 tests
- **Framework:** pytest

---

## Qué hacen los hooks configurados

El proyecto incluye 4 Git hooks automáticos para garantizar la calidad del código:

### 1. Pre-commit Hook
**Archivo:** `.git/hooks/pre-commit`

- Ejecuta `black --check .` para verificar formato de código
- Ejecuta `flake8 .` para verificar linting  
- Ejecuta `pytest` para verificar que todos los tests pasen
- **Bloquea el commit** si alguna verificación falla

**Cuándo se ejecuta:** Antes de cada commit

### 2. Post-commit Hook  
**Archivo:** `.git/hooks/post-commit`

- Registra información del commit en `commit_log.txt`
- Guarda timestamp, hash del commit, autor y mensaje
- Mantiene un historial local de commits realizados

**Cuándo se ejecuta:** Después de cada commit exitoso

### 3. Pre-push Hook
**Archivo:** `.git/hooks/pre-push`

- Ejecuta la suite completa de tests con `pytest -v`
- **Bloquea el push** si algún test falla
- Asegura que el código esté listo para integración

**Cuándo se ejecuta:** Antes de hacer push al repositorio remoto

### 4. Post-push Hook
**Archivo:** `.git/hooks/post-push`

- Confirma que el push fue exitoso
- Muestra información del último commit enviado
- Sugiere actualizar documentación si es necesario

**Cuándo se ejecuta:** Después de push exitoso

---

## Pipeline CI/CD con GitHub Actions

El proyecto incluye un **workflow automatizado** que se ejecuta en GitHub Actions para garantizar la calidad y despliegue del código.

### Archivo de configuración
**Ubicación:** `.github/workflows/ci.yml`

### ¿Cuándo se ejecuta?
- **Push** a las ramas `main` o `master`
- **Pull Requests** hacia `main` o `master`

### Jobs del pipeline

#### 1. **Job Test**
- **Propósito:** Verificar calidad del código
- **Pasos:**
  - Configurar entorno Python 3.11
  - Instalar dependencias del backend
  - Ejecutar suite completa de tests con `pytest -v`
- **Bloqueo:** Si fallan los tests, no continúa al siguiente job

#### 2. **Job Build & Deploy** 
- **Condición:** Solo se ejecuta si el job Test pasa exitosamente
- **Restricción:** Solo en push a rama `main`
- **Pasos:**
  - Construir imágenes Docker con `docker-compose build`
  - Desplegar aplicación con `docker-compose up -d`
  - Verificar que la aplicación responde en puerto 8080
  - Confirmar despliegue exitoso

### Flujo completo
```
Push a main → Tests → Build → Deploy → Verificación → ✅
```

### Ventajas del pipeline
- **Automatización completa:** Tests y despliegue sin intervención manual
- **Calidad garantizada:** Solo código que pasa tests llega a producción  
- **Feedback inmediato:** Notificaciones instantáneas de éxito/fallo
- **Reproducibilidad:** Mismo proceso en cada despliegue

---

## Verificación de tests

Los tests han sido ejecutados exitosamente verificando el correcto funcionamiento de la aplicación:

![Ejecución exitosa de todos los tests](./images/Captura%20de%20tests.png)

Como se puede observar en la captura, los 30 tests (14 unitarios + 16 de integración) pasan correctamente, confirmando que:
- Todas las funciones del backend funcionan según lo esperado
- Los endpoints de la API responden correctamente
- La validación de datos y manejo de errores es adecuada
- El sistema está listo para despliegue

---

## Enlace al repositorio de GitHub

https://github.com/amandaaroutin/DyA-Practica1

