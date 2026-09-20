# UTP Assistant — Copiloto PM & Sales Ops con Google Gemini API y Streamlit

Solución inteligente de automatización de correos electrónicos corporativos utilizando la **API de Google Gemini**, **Function Calling** y un flujo de aprobación **Human-in-the-Loop (HITL)** para Project Managers en **UTPConsult**.

---

## 🚀 Características Principales

1. **Extracción y Orquestación Inteligente:**
   - Procesa correos entrantes, detecta remitente, asunto, cuerpo y archivos adjuntos técnicos.
   - Extrae requerimientos técnicos y genera especificaciones para desarrollo.
2. **Function Calling Modular con Gemini:**
   - `crear_ticket_en_jira`: Registra tickets con clave de proyecto, tipo (Story, Bug, Task, Epic) y prioridad.
   - `agendar_reunion_en_google_calendar`: Programa reuniones técnicas en bloques de 45 minutos (por defecto el próximo martes a las 10:00 AM UTC si no se especifica) con enlace Google Meet generado.
   - `actualizar_contacto_en_crm`: Registra el prospecto y avanza la etapa comercial (ej. *Reunión Técnica*).
3. **Flujo Human-in-the-Loop (HITL):**
   - El PM revisa el ticket de Jira y el evento tentativo de Google Calendar antes de confirmarlos formalmente en las bases de datos.
4. **Bases de Datos Simuladas en Vivo:**
   - Panel lateral interactivo en Streamlit con métricas y visualizador en tiempo real de tickets de Jira, eventos de Calendar y prospectos de CRM.

---

## 📁 Estructura del Proyecto

```
tarea academica 2/
├── .env.example                 # Variables de entorno y plantilla de configuración
├── .env                         # Variables de entorno locales (Gemini, Jira, Calendar)
├── requirements.txt             # Dependencias oficiales del sistema
├── schemas.py                   # Modelos Pydantic v2 y declaraciones de herramientas
├── services.py                  # Integraciones reales (Jira Cloud, Google Calendar) y Mocks
├── assistant_core.py            # Orquestador con SYSTEM_PROMPT (6 componentes) y Gemini 2.0
├── app.py                       # Aplicación web Streamlit moderna y amigable con HITL
├── GUIA_CREDENCIALES_Y_APIS.md  # Manual paso a paso para obtener APIs y credenciales
└── README.md                    # Documentación técnica del proyecto
```

---

## 🛠️ Instalación y Configuración

### 1. Clonar o navegar al directorio del proyecto:
```bash
cd "c:\Users\CyberMax\OneDrive\Documentos\Herramientas TI Curso\tarea academica 2"
```

### 2. Instalar dependencias:
```bash
py -3.12 -m pip install -r requirements.txt
```

### 3. Configurar variables de entorno en `.env`:
Copia la plantilla y edita tu archivo `.env`:
```ini
# GOOGLE GEMINI API (Cargada obligatoriamente desde .env)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.0-flash

# ATLASSIAN JIRA CLOUD (Conexión Real con Fallback automático)
JIRA_URL=https://tu-organizacion.atlassian.net
JIRA_EMAIL=tu_correo@utp.edu.pe
JIRA_API_TOKEN=tu_api_token_aqui
JIRA_PROJECT_KEY=PAYMOD

# GOOGLE CALENDAR API (Conexión Real con Service Account)
GOOGLE_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
```
*(Para instrucciones detalladas de cómo generar cada una, consulta [`GUIA_CREDENCIALES_Y_APIS.md`](./GUIA_CREDENCIALES_Y_APIS.md) o la pestaña **📖 Guía de Credenciales** dentro de la app).*

---

## 🖥️ Ejecución de la Aplicación

Ejecuta Streamlit con el intérprete de Python:
```bash
py -3.12 -m streamlit run app.py
```

La interfaz se abrirá en tu navegador en `http://localhost:8501`.

---

## 🧠 Arquitectura del Prompt del Sistema (SYSTEM_PROMPT)

El prompt del Asistente en [`assistant_core.py`](./assistant_core.py) cuenta con los 6 componentes requeridos:
1. **Rol:** Copiloto Senior de Project Management & Sales Ops en UTPConsult.
2. **Contexto:** Orquestación entre Jira, Google Calendar y CRM para clientes corporativos.
3. **Instrucción clara:** Invocación obligatoria de las 3 herramientas, regla de agendamiento temporal por defecto (próximo martes a las 10:00 AM UTC, 45 min) y cero alucinación.
4. **Formato esperado:** Invocación JSON de herramientas y reporte ejecutivo final en Markdown para el PM.
5. **Ejemplos (Few-Shot):** Casos estructurados de integración y reporte de bugs con entradas y llamadas esperadas.
6. **Datos de entrada:** Definición explícita de Remitente, Asunto, Archivo Adjunto y Cuerpo.

---

## 🧪 Caso de Prueba Oficial (Verificación)

1. En la columna izquierda, selecciona el correo:
   **⭐ Caso 1 (Oficial): Ana Torres (TechCorp — Módulo de Pagos)**
2. Haz clic en **"⚡ Procesar con UTP Assistant"**.
3. Observa en la columna derecha:
   - Los estados del Run: `queued` ➔ `in_progress` ➔ `requires_action` ➔ `completed`.
   - Las 3 herramientas detectadas e invocadas con sus argumentos JSON y tipo de conexión (Real o Simulación Fallback).
   - La tarjeta **HITL**: Haz clic en **"🤝 Confirmar Reunión en Calendar"** y **"🚀 Aprobar Ticket para Sprint"**.
   - La notificación ejecutiva final generada para el equipo interno.
4. En la barra lateral izquierda, observa cómo se actualizan en vivo los contadores y registros de **Jira**, **Calendar** y **CRM**.
