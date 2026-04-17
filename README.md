# Evalify AI

Chatbot de apoyo para comparar de forma inicial 2 o 3 proveedores a partir de informacion cargada en PDF o pegada en conversacion, enriquecida con evidencia web.

## Que hace

Evalify AI guia una sesion conversacional para:

1. reunir informacion de proveedores,
2. capturar criterios de evaluacion,
3. enriquecer evidencia con busqueda web,
4. generar un resumen comparativo claro con:
- diferencias,
- similitudes,
- ventajas,
- desventajas,
- conclusion,
- score simple por proveedor.

## Criterios funcionales clave

- Minimo 2 y maximo 3 proveedores por sesion.
- Hasta 3 criterios definidos por el usuario.
- Criterio reputacion agregado automaticamente.
- Persistencia de sesion por `thread_id` usando SQLite.

## Herramientas integradas

Se integran al menos dos herramientas funcionales dentro del flujo del chatbot:

1. Lectura de PDF para extraer informacion de proveedores.
2. Busqueda web (Tavily) para enriquecer criterios y reputacion.

## Arquitectura

Monorepo con dos componentes:

- `backend/`: FastAPI + LangGraph + OpenAI + Tavily + SQLite
- `frontend/`: React + Vite (chat y carga de PDF)

```text
.
├── backend/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
└── docker-compose.yml
```

## Requisitos

Para Docker (recomendado):

- Docker
- Docker Compose

Para desarrollo local sin Docker:

- Python 3.11+
- Node 20+

## Variables de entorno

Crear `backend/.env` usando como base `backend/.env.example`.

Variables principales:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=o4-mini
OPENAI_EXTRACTION_MODEL=gpt-4.1-mini
TAVILY_API_KEY=...
CHECKPOINT_DB_PATH=comparaciones.db
CORS_ALLOW_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173
LOG_LEVEL=INFO
```

## Despliegue local con Docker

### 1) Preparar entorno

```bash
cp backend/.env.example backend/.env
```

Si en tu equipo Docker requiere privilegios:

```bash
sudo cp backend/.env.example backend/.env
```

### 2) Levantar stack

```bash
docker compose up --build -d
```

o con sudo:

```bash
sudo docker compose up --build -d
```

### 3) Verificar servicios

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

### 4) Accesos

- Frontend: http://localhost:8080
- Backend: http://localhost:8000

### 5) Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

### 6) Apagar

```bash
docker compose down
```

Para eliminar volumen SQLite tambien:

```bash
docker compose down -v
```

## Ejecucion local sin Docker

### Backend

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir:

- http://localhost:5173

## Uso rapido del chatbot

1. Abre la interfaz web.
2. Carga PDF(s) de proveedores desde el boton de archivo o pega contexto en chat.
3. Especifica proveedores y criterios (maximo 3 criterios).
4. Solicita la comparacion.
5. Revisa diferencias, ventajas, desventajas y conclusion.

## API principal

- `GET /health`
- `POST /chat`
- `POST /upload`
- `GET /session/{thread_id}`

## Pruebas

Desde `backend/`:

```bash
python -m pytest -q
```

## Troubleshooting rapido

1. Error de CORS en frontend local (5173):
- Verifica `CORS_ALLOW_ORIGINS` en `backend/.env`.
- Reinicia backend para recargar variables.

2. Error de Vite por version de Node:
- Usa Node 20+ (Vite 5 no funciona con Node 10).

3. Problemas de permisos Docker:
- Usa comandos con `sudo` o agrega tu usuario al grupo `docker`.

## Estado del despliegue web

- Despliegue cloud publico: no incluido en este MVP (opcional).
