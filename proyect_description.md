# Evalify AI - Especificacion Funcional y Tecnica (MVP)

## 1. Resumen Ejecutivo

Evalify AI es un chatbot orientado a apoyar una comparacion inicial de 2 a 3 proveedores en una conversacion guiada.

La solucion combina:

- informacion que el usuario pega en el chat o carga en PDF,
- evidencia publica obtenida en internet,
- y un pipeline determinista con estado persistente por sesion.

El resultado final entrega una salida clara y util para una decision preliminar:

- diferencias,
- similitudes,
- ventajas,
- desventajas,
- conclusion,
- y un score simple por proveedor.

## 2. Objetivo del Sistema

Permitir que un usuario no tecnico pueda comparar rapidamente proveedores usando evidencia combinada (documento + web) sin tener que estructurar manualmente toda la informacion.

El sistema esta disenado para una evaluacion exploratoria, no para reemplazar un proceso formal de procurement.

## 3. Alcance del MVP

Incluye:

- comparacion de minimo 2 y maximo 3 proveedores por sesion,
- definicion de hasta 3 criterios por parte del usuario,
- adicion automatica del criterio reputacion,
- lectura de PDF para incorporar contenido,
- busqueda web por criterio para enriquecer evidencia,
- analisis individual por proveedor y comparacion consolidada,
- persistencia de estado por `thread_id` con SQLite.

No incluye:

- autenticacion/autorizacion,
- panel administrativo,
- despliegue cloud productivo,
- modelos de scoring avanzados de negocio.

## 4. Requerimientos Funcionales

1. Interaccion conversacional para construir comparacion.
2. Ingesta de informacion por chat y por PDF.
3. Restriccion de 2 a 3 proveedores por sesion.
4. Captura de hasta 3 criterios de comparacion definidos por usuario.
5. Enriquecimiento web por criterio + reputacion.
6. Analisis estructurado por criterio para cada proveedor.
7. Resumen final con diferencias, ventajas, desventajas y conclusion.
8. Persistencia de contexto para retomar la sesion.
9. Trazabilidad de evidencia web por criterio.

## 5. Flujo Conversacional Implementado

### 5.1 Ingesta

- El usuario envia mensaje con informacion de proveedores, o carga PDF via `/upload`.
- El contenido cargado se incorpora como `pending_inputs` para fusionarse en la sesion.

### 5.2 Definicion de proveedores y criterios

- El sistema valida que existan al menos 2 proveedores.
- Si faltan criterios, solicita hasta 3 criterios.
- Si detecta mas de 3 proveedores, recorta a los primeros 3.

### 5.3 Enriquecimiento web

- Para cada proveedor busca evidencia por criterio.
- Agrega reputacion como criterio obligatorio.
- Para reputacion ejecuta subconsultas tematicas (`reviews`, `prensa`, `foros`).

### 5.4 Analisis individual

- Evalua cada criterio con clasificacion `alto`, `medio` o `bajo`.
- Conserva evidencia y origen (`documento` o `web`).

### 5.5 Comparacion consolidada

- Genera resumen final con estructura fija.
- Calcula score simple por proveedor (`alto=3`, `medio=2`, `bajo=1`).

## 6. Herramientas Funcionales Integradas por el Chatbot

Cumpliendo la consigna de integrar al menos 2 herramientas, el sistema usa:

1. Lectura de documentos PDF.
- Extrae texto para incorporarlo al estado conversacional.
- Implementado en `backend/app/integrations/pdf_reader.py`.

2. Busqueda web con Tavily.
- Consulta evidencia publica por criterio y reputacion.
- Implementado en `backend/app/integrations/tavily_client.py`.

Adicionalmente, se usa salida estructurada de LLM para extraer proveedores/criterios y producir comparaciones coherentes.

## 7. Arquitectura de Solucion

### 7.1 Estructura de repositorio

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes.py
│   │   ├── config.py
│   │   ├── integrations/
│   │   ├── schemas/
│   │   └── services/
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

### 7.2 Backend

- Framework HTTP: FastAPI.
- Orquestacion conversacional: LangGraph.
- Persistencia de sesion: SqliteSaver (`langgraph-checkpoint-sqlite`).
- Integraciones externas: OpenAI + Tavily + PDF reader.
- Endpoints: `/health`, `/chat`, `/upload`, `/session/{thread_id}`.

### 7.3 Frontend

- React + Vite.
- Interfaz de chat minimalista.
- Envio de mensajes a `/chat`.
- Carga de PDF desde el compositor a `/upload`.
- Resolucion automatica de backend por host o `VITE_API_BASE_URL`.

## 8. Estado de Sesion y Persistencia

El estado por `thread_id` persiste en SQLite e incluye:

- entrada/salida actual,
- estado del flujo,
- criterios,
- proveedores,
- resultado final,
- inputs pendientes de fusion.

Ejemplo simplificado:

```json
{
  "input": "compara A y B por precio y soporte",
  "estado": "analisis",
  "criterios": ["precio", "soporte"],
  "proveedores": [...],
  "resultado_final": null,
  "pending_inputs": []
}
```

## 9. API del Backend

### `GET /health`
- Verificacion de salud del servicio.

### `POST /chat`
- Entrada: `{ "thread_id": "...", "message": "..." }`
- Salida: respuesta conversacional + estado + criterios + proveedores + resultado final (si existe).

### `POST /upload`
- Form-data: `thread_id`, `provider_name` (opcional), `text` (opcional), `file` PDF (opcional).
- Reglas: debe enviarse al menos `text` o `file`.

### `GET /session/{thread_id}`
- Recupera snapshot de sesion persistida.

## 10. Stack y Dependencias Relevantes

Backend:

- Python 3.11+
- fastapi
- uvicorn
- langgraph
- langgraph-checkpoint-sqlite
- langchain-openai
- langchain-core
- langchain-community
- langchain-tavily
- pypdf
- httpx
- python-dotenv
- python-multipart

Frontend:

- Node 20+
- React 18
- Vite 5
- @vitejs/plugin-react

## 11. Configuracion de Entorno

Archivo: `backend/.env`

Variables clave:

```bash
OPENAI_API_KEY=...
OPENAI_MODEL=o4-mini
OPENAI_EXTRACTION_MODEL=gpt-4.1-mini
TAVILY_API_KEY=...
CHECKPOINT_DB_PATH=comparaciones.db
CORS_ALLOW_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://localhost:5173,http://127.0.0.1:5173
LOG_LEVEL=INFO
```

## 12. Ejecucion

### 12.1 Local sin Docker

Backend:

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

### 12.2 Docker Compose (local)

```bash
cp backend/.env.example backend/.env
docker compose up --build -d
```

Servicios:

- Backend: http://localhost:8000
- Frontend: http://localhost:8080

## 13. Observabilidad y Calidad

Observabilidad:

- logging en ciclo de vida (`main.py`), rutas (`routes.py`), integraciones y nodos del grafo.

Calidad:

- pruebas en `backend/tests` para rutas, helpers de grafo y cliente OpenAI.

## 14. Entregables de la Consigna

- Proyecto dockerizado: cumplido (`docker-compose.yml` + Dockerfiles de backend/frontend).
- Codigo documentado: parcialmente cumplido (documentacion externa fuerte; mejorar docstrings inline si se requiere criterio estricto).
- README de ejecucion: cumplido.
- Despliegue web: opcional, no incluido en este MVP.
