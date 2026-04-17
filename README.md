# Sistema de Comparación de Proveedores — Especificación Técnica (MVP)

---

## 1. Objetivo del Sistema

Desarrollar un agente conversacional (chatbot) para asistir a los usuarios en la evaluación inicial y comparación exploratoria de 2 a 3 proveedores de productos o servicios. El sistema analizará información cruda proporcionada por el usuario (texto o PDF) y la complementará con información pública obtenida en internet para generar un **análisis estructurado basado en evidencia** que facilite una evaluación comparativa inicial y apoye la toma de decisiones.

El sistema se enfocará en realizar una comparación exploratoria basada en criterios definidos por el usuario, combinando información proporcionada directamente con señales externas del mercado, como reputación o percepción del servicio.

---

## 2. Alcance y Herramientas

El sistema operará mediante una interfaz conversacional, limitando su alcance a comparaciones de un máximo de 3 proveedores por sesión para mantener el control del contexto y garantizar que el análisis generado por el modelo sea preciso y manejable.

### Herramientas del agente (las únicas que el LLM invoca directamente)

* **Lector de Documentos (PDF / Texto)**
  Herramienta encargada de procesar archivos cargados por el usuario, extrayendo el contenido textual de documentos PDF o texto plano para que pueda ser analizado por el sistema.

* **Motor de Búsqueda Web**
  Herramienta utilizada para consultar información pública sobre cada proveedor. Esta búsqueda permite complementar los datos proporcionados por el usuario con señales externas relevantes relacionadas con los criterios de evaluación definidos.

> **Nota importante:** La gestión del estado de sesión (proveedores ingresados, criterios definidos, resultados de búsqueda, análisis generados) **no es una herramienta del agente**. Es responsabilidad del framework de orquestación (LangGraph), que la maneja de forma determinista a través de su sistema de estado y checkpointing. Exponer la persistencia como herramienta al LLM introduciría no-determinismo donde debe haber control explícito del pipeline.

### Persistencia de Datos

El sistema utilizará el checkpointer nativo de LangGraph (`SqliteSaver`) para almacenar el estado de cada sesión de comparación. Cada sesión funcionará como un expediente único identificado por un `thread_id`, donde se registrará progresivamente toda la información generada durante el flujo del análisis.

Dentro de cada sesión se almacenarán:

* proveedores ingresados
* texto original extraído de documentos
* criterios definidos por el usuario
* resultados de búsquedas web
* análisis individual por proveedor
* resultado final de la comparación

Este enfoque elimina la necesidad de una base de datos externa para el MVP, manteniendo todo el contexto de la evaluación en el estado del grafo y permitiendo retomar la interacción en cualquier momento sin pérdida de información.

---

## 3. Requerimientos Funcionales (RF)

* **RF1 - Interfaz Conversacional**
  El sistema debe guiar al usuario mediante una interacción conversacional para la recolección de información de proveedores y la definición de criterios de evaluación.

* **RF2 - Ingesta Multimodal**
  Capacidad de recibir información de proveedores a través de texto escrito directamente en el chat o mediante la carga de documentos PDF.

* **RF3 - Límite de Entidades**
  El sistema restringirá el análisis comparativo a un mínimo de 2 y un máximo de 3 proveedores dentro de una misma sesión.

* **RF4 - Extracción de Entidades**
  El sistema procesará el texto crudo recibido para identificar y organizar la información correspondiente a cada proveedor.

* **RF5 - Definición de Criterios**
  El usuario podrá establecer hasta 3 criterios clave de evaluación que servirán como base para el análisis comparativo (por ejemplo precio, soporte o integraciones).

* **RF6 - Enriquecimiento de Datos**
  El sistema ejecutará búsquedas web automatizadas para complementar la información disponible sobre cada proveedor utilizando los criterios definidos por el usuario. Adicionalmente, el sistema evaluará obligatoriamente la reputación del proveedor como criterio adicional.

  La información obtenida deberá almacenarse como **observaciones textuales (evidencia)** asociadas a cada criterio, evitando su resumen prematuro.

* **RF7 - Síntesis Estructurada**
  El sistema generará un análisis final bajo un formato estructurado que incluya:

  * Diferencias
  * Similitudes
  * Ventajas
  * Desventajas
  * Conclusión orientada a apoyar una decisión inicial

  El sistema deberá basar todas las conclusiones exclusivamente en los resultados estructurados generados en el análisis individual, sin introducir información adicional.

* **RF8 - Persistencia del Contexto de Sesión**
  El sistema deberá almacenar el estado de cada sesión de comparación, incluyendo proveedores ingresados, criterios definidos, resultados de búsqueda y análisis generados, permitiendo continuar el flujo sin pérdida de información.

* **RF9 - Trazabilidad de Fuentes Externas**
  El sistema deberá conservar referencias básicas de las fuentes utilizadas durante las búsquedas web para identificar el origen de la información utilizada en el enriquecimiento del análisis.

---

## 4. Arquitectura del Flujo de Trabajo (Pipeline)

### Paso 1: Ingesta y Almacenamiento Temporal

Flujo del proceso:

```
texto / pdf
↓
extracción de texto
↓
almacenamiento en estado del grafo (LangGraph)
```

El sistema recibe información del proveedor en formato texto o documento. En caso de documentos PDF, el contenido es procesado para extraer texto plano. Este texto se almacena íntegramente dentro del estado de la sesión activa junto con la identificación del proveedor correspondiente.

El objetivo de esta etapa es conservar la información original proporcionada por el usuario para su uso posterior durante el análisis.

---

### Paso 2: Definición de Criterios de Evaluación

Flujo del proceso:

```
interacción conversacional con el usuario
↓
definición de criterios
↓
almacenamiento en estado del grafo (LangGraph)
```

El chatbot consulta al usuario qué aspectos desea priorizar al evaluar los proveedores.

**Reglas de negocio:**

* El sistema permitirá un máximo de 3 criterios definidos por el usuario.
* El nodo avanza automáticamente cuando el usuario ha confirmado sus criterios o cuando se detecta que ya están definidos en el estado actual.
* Los criterios se utilizarán posteriormente para orientar tanto el análisis de los proveedores como las búsquedas de información externa.

Estos criterios se almacenan en el estado de la sesión activa y se utilizan como referencia durante las siguientes etapas del análisis.

---

### Paso 3: Enriquecimiento vía Búsqueda Web

Flujo del proceso:

```
criterios definidos
+
proveedor
↓
generación de consultas de búsqueda
↓
recuperación de información pública
↓
almacenamiento de evidencia en estado del grafo
```

Para cada proveedor, el sistema ejecutará búsquedas web basadas en los criterios definidos por el usuario.

**Regla de negocio:**

* criterios del usuario (máximo 3)
* más 1 criterio obligatorio definido por el sistema: **reputación**
* Total máximo de consultas por proveedor: **4**

Ejemplo de consultas generadas para un proveedor:

* `proveedor + precios`
* `proveedor + soporte`
* `proveedor + integraciones`
* `proveedor + reputación`

**Resultado:**

La información obtenida se almacenará como **lista de observaciones relevantes (evidencia)** relacionadas con cada criterio evaluado. Estos resultados se almacenan en el estado de la sesión y se utilizarán durante el análisis individual de cada proveedor.

---

### Paso 4: Análisis Individual por Proveedor (Map)

Flujo del proceso:

```
texto extraído del proveedor
+
resultados de búsqueda web
+
criterios definidos
↓
análisis estructurado por proveedor
```

Para cada proveedor, el sistema genera un análisis individual utilizando:

* el texto original proporcionado por el usuario
* la información pública obtenida mediante búsqueda web
* los criterios definidos por el usuario más la reputación

**Salida:**

Se genera un resultado estructurado interno por criterio con el siguiente formato:

```json
"analisis_individual": {
  "precio": {
    "clasificacion": "alto | medio | bajo",
    "evidencia": "fragmento concreto del documento o fuente externa",
    "origen": "documento | web"
  },
  "soporte": {
    "clasificacion": "alto | medio | bajo",
    "evidencia": "fragmento concreto",
    "origen": "web"
  },
  "reputacion": {
    "clasificacion": "alto | medio | bajo",
    "evidencia": "observación basada en fuentes externas",
    "origen": "web"
  }
}
```

**Reglas:**

* Cada criterio debe incluir una clasificación discreta.
* Cada clasificación debe estar respaldada por evidencia explícita.
* No se permiten evaluaciones sin evidencia.

Este análisis permite organizar la información disponible de cada proveedor en una forma consistente antes de realizar la comparación. El resultado generado se almacena en el estado de la sesión.

---

### Paso 5: Comparación Consolidada (Reduce)

Flujo del proceso:

```
análisis individual de cada proveedor
↓
comparación entre proveedores
↓
generación del resultado final
```

La comparación se realiza en dos etapas:

**Comparación estructurada:**
El sistema compara las clasificaciones de cada proveedor por criterio, identificando diferencias, similitudes y posicionamientos relativos.

Opcionalmente, se podrá asignar un valor numérico a cada clasificación para obtener un score comparativo simple:

```
alto  = 3
medio = 2
bajo  = 1
```

**Generación del resultado final:**
El modelo genera la salida final utilizando exclusivamente los resultados de la comparación estructurada.

**Salida final al usuario:**

* Diferencias
* Similitudes
* Ventajas
* Desventajas
* Conclusión orientada a apoyar la decisión inicial del usuario

El resultado final se almacena como parte del estado de la sesión, permitiendo que el usuario pueda consultarlo nuevamente o continuar la conversación con nuevas preguntas relacionadas con la comparación realizada.

---

### Paso 6: Persistencia de Sesión y Orquestación del Agente

#### Estructura del Estado en LangGraph

El estado de cada sesión se define como un `TypedDict` que LangGraph gestiona y persiste automáticamente mediante `SqliteSaver`. No se requiere base de datos externa para el MVP.

Estructura del estado del grafo:

```python
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph

class ProveedorAnalisis(TypedDict):
    nombre: str
    texto_original: str
    busqueda_web: dict          # { criterio: [evidencia1, evidencia2, ...] }
    analisis_individual: dict   # { criterio: { clasificacion, evidencia, origen } }

class SessionState(TypedDict):
    session_id: str
    estado: str                 # ingesta | criterios | enriquecimiento | analisis | comparacion | fin
    criterios: List[str]
    proveedores: List[ProveedorAnalisis]
    resultado_final: Optional[dict]
```

Ejemplo del estado en un punto intermedio del flujo:

```json
{
  "session_id": "abc123",
  "estado": "analisis",
  "criterios": ["precio", "soporte", "integraciones"],
  "proveedores": [
    {
      "nombre": "Proveedor A",
      "texto_original": "...",
      "busqueda_web": {
        "precio": ["evidencia 1", "evidencia 2"],
        "soporte": ["evidencia 1"]
      },
      "analisis_individual": {
        "precio": {
          "clasificacion": "alto",
          "evidencia": "...",
          "origen": "web"
        }
      }
    }
  ],
  "resultado_final": null
}
```

#### Definición del Grafo

```
[ingesta] → [definir_criterios] → [enriquecer] → [analisis_individual] → [comparacion] → [fin]
                  ↑ (espera input usuario si los criterios no están completos)
```

Cada nodo opera sobre el estado de la sesión. LangGraph maneja las transiciones, la persistencia entre pasos y la capacidad de retomar el flujo desde cualquier punto mediante `thread_id`.

---

## 5. Tecnología y Dependencias

### Stack principal

| Componente | Librería | Versión |
|---|---|---|
| Orquestación del agente | `langgraph` | `^1.1.0` |
| Abstracciones LLM / prompts | `langchain-core` | `^1.2.29` |
| Lector de PDF | `langchain-community` + `pypdf` | `^0.4.1` / `^5.x` |
| Motor de búsqueda web | `langchain-tavily` | `^0.2.17` |
| Persistencia de sesión | `langgraph` (SqliteSaver, incluido) | — |
| Python | — | `>=3.11` |

### Instalación

```bash
pip install \
  langgraph==1.1.0 \
  langchain-core==1.2.29 \
  langchain-community==0.4.1 \
  langchain-tavily==0.2.17 \
  pypdf
```

### Variables de entorno requeridas

```bash
TAVILY_API_KEY=...         # Motor de búsqueda web
OPENAI_API_KEY=...         # o ANTHROPIC_API_KEY, según el LLM elegido
```

### Inicialización del checkpointer (persistencia de sesión)

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Para desarrollo y MVP: SQLite local, sin infraestructura adicional
checkpointer = SqliteSaver.from_conn_string("comparaciones.db")

graph = StateGraph(SessionState)
# ... definición de nodos y edges ...
app = graph.compile(checkpointer=checkpointer)

# Cada sesión se identifica por thread_id
config = {"configurable": {"thread_id": "sesion-usuario-001"}}
result = app.invoke(input_state, config=config)
```

---

## 6. Despliegue en Contenedor Docker

El agente se expondrá como una API HTTP para que un frontend de chat pueda consumirlo. Esta sección define la estructura mínima necesaria para levantar el sistema en un contenedor, sin entrar en configuraciones de producción.

### Exposición de la API

Se utilizará **FastAPI** como servidor HTTP. El agente recibe un mensaje del usuario y un `thread_id` (identificador de sesión), y devuelve la respuesta del agente. El `thread_id` es lo que permite al frontend mantener conversaciones persistentes por usuario.

```
POST /chat
Body: { "thread_id": "string", "message": "string" }
Response: { "response": "string" }
```

Estructura mínima del servidor:

```python
# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from langgraph.checkpoint.sqlite import SqliteSaver
# from graph import build_graph  ← grafo definido aparte

app = FastAPI()
checkpointer = SqliteSaver.from_conn_string("/data/comparaciones.db")
graph = build_graph(checkpointer)

class ChatRequest(BaseModel):
    thread_id: str
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    result = graph.invoke({"input": req.message}, config=config)
    return {"response": result["output"]}
```

### Estructura de archivos

```
/
├── main.py               # Servidor FastAPI
├── graph.py              # Definición del grafo LangGraph
├── tools/
│   ├── pdf_reader.py     # Herramienta de lectura de documentos
│   └── web_search.py     # Herramienta de búsqueda web
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Directorio para la base de datos SQLite persistente
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
services:
  agente:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - sqlite_data:/data      # Persiste la DB entre reinicios del contenedor
    env_file:
      - .env                   # TAVILY_API_KEY, OPENAI_API_KEY, etc.

volumes:
  sqlite_data:
```

### requirements.txt

```
langgraph==1.1.0
langchain-core==1.2.29
langchain-community==0.4.1
langchain-tavily==0.2.17
pypdf
fastapi
uvicorn[standard]
```

### Consideraciones para la conexión con el frontend

* El frontend deberá generar y mantener un `thread_id` por conversación (puede ser un UUID generado en el cliente).
* El endpoint `/chat` es stateless desde el punto de vista HTTP; el estado de la conversación vive en SQLite, recuperado automáticamente por LangGraph a partir del `thread_id`.
* Para subida de archivos PDF desde el frontend, se puede agregar un segundo endpoint `POST /upload` que reciba el archivo, lo guarde temporalmente y devuelva la ruta para que el agente lo procese en el siguiente mensaje. Creo que si es necesario, porque usaremos la carga desde el frontend.
* Para la creacion de las APIs, deberas seguir el estandar de OpenAPI. Mientras que para cosas de AI, deberas seguir las recomendaciones pertinentes, siguiendo fuentes oficiales.
* Usaremos openai para el proveedor de modelos de IA.
* El frontend puede conectarse al contenedor directamente por HTTP durante las pruebas locales (`http://localhost:8000`).

---

## 7. Cambios realizados en la implementación (organización MVP)

Se reorganizó la implementación para dejar una base limpia y escalable, manteniendo el alcance MVP.

### Arquitectura aplicada en backend

Se consolidó una arquitectura **modular monolith** con separación por capas:

* `app/api`: endpoints HTTP (`/chat`, `/upload`, `/session/{thread_id}`, `/health`)
* `app/services`: orquestación del flujo LangGraph (pipeline y nodos)
* `app/integrations`: adaptadores externos (OpenAI, Tavily, lector PDF)
* `app/schemas`: contratos y modelos tipados para API y dominio
* `app/core`: configuración centralizada

### Estructura técnica nueva

Se incorporó estructura profesional para continuidad del proyecto:

```
app/
├── main.py
├── api/
│   └── routes.py
├── core/
│   └── config.py
├── schemas/
│   ├── api.py
│   └── domain.py
├── services/
│   ├── formatter.py
│   └── graph_builder.py
└── integrations/
    ├── llm/openai_client.py
    ├── search/tavily_client.py
    └── documents/pdf_reader.py
```

### Ajustes de ejecución y despliegue

* Se migró el punto de entrada a `app.main:app`.
* Se actualizó `Dockerfile` para iniciar con `uvicorn app.main:app`.
* Se mantiene `docker-compose.yml`, `Dockerfile`, `requirements.txt` y `.env.example` en raíz, siguiendo convención estándar.

### Limpieza aplicada

* Se retiraron archivos legacy planos en raíz (`main.py`, `graph.py`, `schemas.py`).
* Se retiraron módulos legacy bajo `tools/` y se movieron a `app/integrations`.
* Se preservó el comportamiento funcional del MVP (misma lógica de negocio y mismo flujo general).