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
├── .env.example              # Variables de entorno requeridas
├── requirements.txt          # Dependencias oficiales fijadas
├── schemas.py                # Modelos Pydantic v2 y declaraciones de herramientas
├── services.py               # Servicios mock en memoria para Jira, Calendar y CRM
├── assistant_core.py         # Orquestador del Asistente con Gemini y Function Calling
├── app.py                    # Aplicación web Streamlit con panel HITL
└── README.md                 # Documentación técnica
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

### 3. Configurar la clave de API de Gemini:
Crea un archivo `.env` basado en `.env.example`:
```bash
copy .env.example .env
```
Edita `.env` con tu clave de [Google AI Studio](https://aistudio.google.com/app/apikey):
```ini
GEMINI_API_KEY=tu_api_key_aqui
GEMINI_MODEL=gemini-1.5-flash
```
*(Nota: La aplicación también permite ingresar o probar la API Key directamente en el panel lateral de Streamlit, e incluye modo de fallback simulado si aún no cuentas con una).*

---

## 🖥️ Ejecución de la Aplicación

Ejecuta Streamlit con el intérprete de Python:
```bash
py -3.12 -m streamlit run app.py
```

La interfaz se abrirá en tu navegador en `http://localhost:8501`.

---

## 🧪 Caso de Prueba Oficial (Verificación)

1. En la columna izquierda, selecciona el correo:
   **⭐ Caso Oficial: Ana Torres (TechCorp - Módulo Pagos)**
2. Haz clic en **"⚡ Procesar con UTP Assistant"**.
3. Observa en la columna derecha:
   - Los estados del Run: `queued` ➔ `in_progress` ➔ `requires_action` ➔ `completed`.
   - Las 3 herramientas detectadas e invocadas con sus argumentos JSON.
   - La tarjeta **HITL**: Haz clic en **"🤝 Confirmar Reunión en Calendar"** y **"🚀 Aprobar Ticket Jira para Sprint"**.
   - La notificación ejecutiva final generada para el equipo interno.
4. En la barra lateral izquierda, observa cómo se actualizan en vivo los contadores y registros de **Jira**, **Calendar** y **CRM**.
