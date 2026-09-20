# 📖 Guía Oficial de Obtención de Credenciales y APIs — UTP Assistant

Esta guía detalla paso a paso cómo obtener las credenciales, claves de API y tokens requeridos para conectar **UTP Assistant** con los servicios reales de **Google Gemini**, **Atlassian Jira Cloud** y **Google Calendar**.

> **Nota de Resiliencia:** Si decides no configurar alguna credencial externa (o si falla la conexión), UTP Assistant activará automáticamente el **Modo Simulación Fallback**, garantizando que el flujo de trabajo, el Function Calling y la interfaz Human-in-the-Loop funcionen al 100%.

---

## 1. 🤖 Google Gemini API (Obligatorio en `.env` para IA Real)

Permite que el asistente orqueste la extracción de requerimientos, la inferencia de parámetros y el Function Calling real con los modelos `gemini-2.0-flash`, `gemini-1.5-flash` o `gemini-1.5-pro`.

### Pasos para obtener tu API Key gratuita:
1. Accede a **Google AI Studio**:  
   👉 [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Inicia sesión con tu cuenta personal o corporativa de Google.
3. Haz clic en el botón azul **"Create API key"** (o "Crear clave de API").
4. Elige la opción **"Create API key in new project"** (o selecciona un proyecto existente de Google Cloud).
5. Copia la clave generada (tiene el formato `AIzaSy...`).
6. Abre tu archivo `.env` en la raíz del proyecto y configura:
   ```ini
   GEMINI_API_KEY=AIzaSyTuClaveRealGeneradaAqui
   GEMINI_MODEL=gemini-2.0-flash
   ```
7. *(Opcional)* En la barra lateral de la aplicación web, haz clic en **"🔄 Recargar Variables de .env"** para aplicar los cambios en caliente.

---

## 2. 🎫 Atlassian Jira Cloud (Conexión Real para Tickets)

Permite registrar automáticamente historias de usuario (Story), tareas (Task) y errores (Bug) en tu tablero Jira real bajo la metodología ágil de UTPConsult.

### Pasos para obtener credenciales de Jira Cloud:
1. **Instancia de Jira Cloud:**
   - Si tu empresa o tú ya tienen Jira Cloud, tu URL tiene la estructura: `https://tu-organizacion.atlassian.net`.
   - Si no tienes una, puedes crear una instancia gratuita en:  
     👉 [https://www.atlassian.com/software/jira/free](https://www.atlassian.com/software/jira/free)
2. **Crear o identificar tu proyecto en Jira:**
   - En tu Jira, crea un proyecto tipo **Scrum** o **Kanban**.
   - Asigna una clave al proyecto, por ejemplo: `PAYMOD` (Módulo de Pagos) o `UTP`.
3. **Generar un Token de API de Atlassian:**
   - Inicia sesión y ve al portal de seguridad de Atlassian:  
     👉 [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
   - Haz clic en **"Crear token de API"** (Create API token).
   - Escribe una etiqueta (ejemplo: `utp-assistant-integration`).
   - Haz clic en **"Crear"** y copia el token generado de inmediato.
4. **Configurar tu archivo `.env`:**
   ```ini
   JIRA_URL=https://tu-organizacion.atlassian.net
   JIRA_EMAIL=tu_correo_de_atlassian@ejemplo.com
   JIRA_API_TOKEN=ATATT3xFfGF0... (tu token de Atlassian)
   JIRA_PROJECT_KEY=PAYMOD
   ```
   *(Nota: El sistema también reconoce alias como `JIRA_CORREO` y `JIRA_TOKEN`).*

---

## 3. 📅 Google Calendar API v3 (Conexión Real con Service Account)

Permite programar automáticamente sesiones de arquitectura de 45 minutos en tu calendario y generar enlaces de **Google Meet**.

### Método Oficial: Cuenta de Servicio (Service Account)

Para que el Asistente pueda agendar reuniones de manera autónoma en segundo plano sin pedir inicio de sesión interactivo en el navegador cada vez, Google requiere una **Cuenta de Servicio (Service Account)** (un archivo JSON que contiene `"type": "service_account"`).

> ⚠️ **Importante (Diferencia clave):**  
> Asegúrate de crear una **Cuenta de Servicio** y NO un *ID de cliente de OAuth 2.0* (este último tiene `"web": {"client_id": ...}` y está pensado para login visual de usuarios, no para bots backend).

---

#### Paso 1: Habilitar la API en Google Cloud
1. Ingresa a Google Cloud Console:  
   👉 [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Selecciona tu proyecto (o crea uno nuevo, ej: `UTP-Assistant-Calendar`).
3. En el menú lateral, ve a **"APIs y Servicios"** ➔ **"Biblioteca"**.
4. Busca **"Google Calendar API"** y haz clic en **"Habilitar"**.

#### Paso 2: Crear la Cuenta de Servicio y Descargar la Clave JSON
1. Ve a **"APIs y Servicios"** ➔ **"Credenciales"**.
2. Haz clic en **"Crear credenciales"** ➔ **"Cuenta de servicio"**.
3. Asigna un nombre: `calendar-bot` y presiona **"Crear y continuar"** ➔ **"Listo"**.
4. Haz clic sobre la cuenta de servicio recién creada en la lista (tendrá un correo del tipo `calendar-bot@tu-proyecto.iam.gserviceaccount.com`).
5. Ve a la pestaña **"Claves"** ➔ **"Agregar clave"** ➔ **"Crear clave nueva"**.
6. Selecciona el formato **JSON** y haz clic en **"Crear"**. Se descargará un archivo `.json` a tu computadora.

#### Paso 3: ⚠️ Paso Vital — Compartir tu Calendario con el Bot
1. Copia la dirección de correo de la cuenta de servicio (`calendar-bot@tu-proyecto.iam.gserviceaccount.com`).
2. Entra a tu calendario personal o corporativo:  
   👉 [https://calendar.google.com/](https://calendar.google.com/)
3. En la columna izquierda, ubica tu calendario, haz clic en los 3 puntos verticales ➔ **"Configuración y uso compartido"**.
4. Baja a la sección **"Compartir con personas o grupos específicos"** y haz clic en **"Agregar personas"**.
5. Pega el correo de la cuenta de servicio (`calendar-bot@...`).
6. En permisos, selecciona obligatoriamente: **"Realizar cambios en eventos"** (Make changes to events).
7. Haz clic en **"Enviar"**.

---

### Configuración en `.env` (Tienes dos opciones):

#### 🚀 Opción 2: JSON inline como Base64 (Recomendado si no deseas montar archivos)
Esta opción codifica el contenido del archivo JSON a una sola línea Base64, ideal para entornos contenerizados o cuando se gestionan credenciales solo por variables de entorno.

**1. Generar la cadena Base64 desde la terminal:**
- **En Windows (PowerShell):**
  ```powershell
  [Convert]::ToBase64String([IO.File]::ReadAllBytes("service_account.json")) | Set-Clipboard
  ```
  *(El comando copiará automáticamente el string Base64 al portapapeles de Windows).*
- **En Linux / macOS:**
  ```bash
  base64 -w 0 service_account.json
  ```

**2. Pegar en tu archivo `.env`:**
```ini
GOOGLE_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_B64="eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsICJwcm9qZWN0X2lkIjog..."
```

*En el código Python de `services.py`, esto se decodifica y autentica automáticamente:*
```python
import base64, json
creds_dict = json.loads(base64.b64decode(os.environ["GOOGLE_SERVICE_ACCOUNT_B64"]))
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"]
)
```

---

#### 📁 Opción 1: Poner la ruta del archivo
Coloca el archivo descargado en la carpeta del proyecto como `service_account.json` y configura en tu `.env`:
```ini
GOOGLE_CALENDAR_ID=primary
GOOGLE_APPLICATION_CREDENTIALS=service_account.json
# o: GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
```

---

## 4. 👥 CRM Corporativo (Sin Conexión Real — Por Diseño)

Por especificación del proyecto, el CRM **no requiere conexión a un CRM externo**:
- Los prospectos, etapas de embudo (*'Reunión Técnica'*, *'Lead Calificado'*) y cotizaciones se gestionan en la base de datos simulada en memoria (`SimulatedDatabase` en `services.py`).
- No necesitas configurar tokens ni APIs para el CRM; se actualiza y visualiza automáticamente en vivo en el panel interactivo.

---

## 5. 📋 Resumen del archivo `.env` completo

Tu archivo `.env` final debe lucir similar a este:

```ini
# ==============================================================================
# CONFIGURACIÓN UTP ASSISTANT
# ==============================================================================

# 1. GEMINI API (Obligatorio en .env)
GEMINI_API_KEY=AIzaSyBxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-2.0-flash

# 2. ATLASSIAN JIRA CLOUD
JIRA_URL=https://tu-organizacion.atlassian.net
JIRA_EMAIL=tu_usuario@utp.edu.pe
JIRA_API_TOKEN=AQ.Ab8RN6...
JIRA_PROJECT_KEY=PAYMOD

# 3. GOOGLE CALENDAR API (Opción 2 Base64)
GOOGLE_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_B64="eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIs..."
```

---

## 6. 🧪 Verificación y Diagnóstico en Vivo

Una vez configuradas tus credenciales:
1. Abre la aplicación en [http://localhost:8501](http://localhost:8501).
2. En la barra lateral izquierda, pulsa **"🔄 Recargar Variables de .env"**.
3. Observa las tarjetas del **Estado de Conexiones**:
   - `🟢 Google Gemini: API Real (.env) - Modelo: gemini-2.0-flash`
   - `🟢 Atlassian Jira: API Cloud Real`
   - `🟢 Google Calendar: API v3 Real (Base64)`
   - `🔵 CRM Corporativo: Simulado en Memoria`
4. Procesa el **Caso Oficial de Ana Torres** y comprueba cómo se crean los tickets en Jira y se agendan los eventos en Google Calendar en tiempo real.

