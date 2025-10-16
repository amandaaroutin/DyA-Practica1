CREATE TABLE IF NOT EXISTS medicos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    especialidad VARCHAR(255),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pacientes (
    id SERIAL PRIMARY KEY,
    medico_id INT REFERENCES medicos(id) ON DELETE CASCADE,
    nombre VARCHAR(255) NOT NULL,
    edad INTEGER,
    email VARCHAR(255),
    telefono VARCHAR(20),
    historial TEXT,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citas (
    id SERIAL PRIMARY KEY,
    paciente_id INT REFERENCES pacientes(id) ON DELETE CASCADE,
    medico_id INT REFERENCES medicos(id) ON DELETE CASCADE,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    motivo TEXT,
    cancelada BOOLEAN DEFAULT FALSE
);

