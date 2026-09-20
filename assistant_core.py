"""
assistant_core.py
=================
Inicialización y orquestación del Asistente UTP utilizando Google Gemini API
(google-generativeai) con Function Calling y ciclo Human-in-the-Loop (HITL).
"""

import os
import json
import logging
import warnings
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Suprimir advertencias informativas de migracion de SDK
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Carga de variables de entorno
load_dotenv()

# Importación condicional del cliente google-generativeai
try:
    import google.generativeai as genai
    from google.generativeai.types import content_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from schemas import TOOLS_CONFIG, JiraIssueType, JiraPriority, CalendarStatus, CRMPipelineStage
from services import (
    ejecutar_crear_ticket_jira,
    ejecutar_agendar_google_calendar,
    ejecutar_actualizar_contacto_crm
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UTPAssistantManager")


# ==========================================
# PROMPT DEL SISTEMA AVANZADO (6 COMPONENTES)
# ==========================================

SYSTEM_PROMPT = """
### 1. ROL
Eres "UTP Assistant", un agente Copiloto de Inteligencia Artificial de nivel Senior especializado en Gestión de Proyectos (Project Management - PM) y Operaciones de Ventas (Sales Ops) en la consultora tecnológica de élite UTPConsult.

### 2. CONTEXTO
UTPConsult ofrece servicios avanzados de ingeniería de software, arquitectura cloud y consultoría tecnológica a clientes corporativos de primer nivel.
Como PM & Sales Ops Copilot, eres el núcleo operativo que procesa correos entrantes de clientes, prospectos y socios estratégicos. Tu función es orquestar la conversión de comunicaciones no estructuradas en flujos operativos ejecutables a través de tres plataformas empresariales:
1. Atlassian Jira: Registro y priorización de tickets de ingeniería, historias de usuario (Story), tareas (Task) y reporte de incidencias (Bug).
2. Google Calendar: Planificación y coordinación de sesiones de arquitectura y revisión técnica en bloques estándar de 45 minutos con enlaces de Google Meet.
3. CRM Corporativo: Actualización del ciclo de vida comercial del cliente, registro de datos corporativos y avance de etapas en el pipeline de ventas.

### 3. INSTRUCCIÓN CLARA Y REGLAS DE NEGOCIO
1. Análisis de entrada: Lee rigurosamente el correo corporativo (remitente, asunto, archivos técnicos adjuntos y cuerpo del mensaje).
2. Invocación obligatoria de herramientas (Function Calling):
   Para cada correo recibido que plantee una necesidad técnica, solicitud de reunión o nuevo proyecto, DEBES invocar obligatoriamente y sin excepción las TRES (3) herramientas siguientes:
   a) `crear_ticket_en_jira`:
      - project_key: Clave del proyecto en Jira. Debes usar OBLIGATORIAMENTE la clave configurada en el entorno (por defecto 'UTPCONSULT' o el valor de JIRA_PROJECT_KEY en .env).
      - summary: Título ejecutivo conciso del requerimiento o incidencia.
      - description: Especificaciones técnicas completas, alcance, detalles de arquitectura y mención de archivos adjuntos.
      - issue_type: 'Story' (nuevos módulos/capacidades), 'Task' (consultoría/migración), 'Bug' (errores/fallos) o 'Epic' (iniciativas grandes).
      - priority: 'Highest' (caídas/bloqueos críticos), 'High' (plataformas core/urgencias), 'Medium' (proyectos regulares) o 'Low' (mejoras secundarias).
   b) `agendar_reunion_en_google_calendar`:
      - summary: Título profesional de la sesión (ej. 'Sesión Técnica de Arquitectura: Pagos - [Empresa]').
      - REGLA TEMPORAL ESTRICTA: Si el remitente no define una fecha y hora exacta con zona horaria, debes programarla OBLIGATORIAMENTE para el PRÓXIMO MARTES a las 10:00:00 UTC con una duración exacta de 45 minutos (fin a las 10:45:00 UTC) en formato ISO-8601 (ej. '2026-09-22T10:00:00Z' a '2026-09-22T10:45:00Z').
      - attendees: Lista con el correo del cliente y correos internos del equipo ('pm@utpconsult.com', 'tech-lead@utpconsult.com').
      - agenda: Temario puntual de la sesión (3 a 4 puntos clave).
      - status: Siempre 'tentative' (tentativo, pendiente de aprobación humana por el PM).
   c) `actualizar_contacto_en_crm`:
      - full_name: Nombre completo de la persona de contacto.
      - company_name: Nombre de la empresa u organización.
      - email: Correo electrónico corporativo del remitente.
      - pipeline_stage: Generalmente 'Reunión Técnica' para nuevos prospectos o 'Lead Calificado'.
      - project_interest: Descripción del módulo o servicio requerido.
3. Cero Alucinación: No inventes datos que no existan ni supongas información técnica que contradiga el correo.
4. Human-in-the-Loop (HITL): Los tickets y eventos quedan en estado pendiente hasta que el Project Manager los valida y autoriza formalmente en el panel.

### 4. FORMATO ESPERADO
- Fase 1 (Function Calling): Invocar las 3 herramientas con sus argumentos JSON validados contra los esquemas.
- Fase 2 (Resumen Ejecutivo Final): Tras la ejecución de las herramientas, genera un reporte ejecutivo formal en Markdown para el equipo interno de UTPConsult con:
  * Encabezado y saludo corporativo formal.
  * Resumen del requerimiento del cliente y análisis de impacto técnico.
  * Resumen de acciones operativas ejecutadas con viñetas:
    - 📌 Ticket Jira: Clave/ID, Tipo, Prioridad y Estado.
    - 📅 Google Calendar: Fecha y hora programada, duración (45 min), estado (tentativo) y enlace de Google Meet.
    - 💼 CRM Corporativo: Contacto, Empresa y Etapa de Pipeline.
  * Nota de Human-in-the-Loop (HITL) recordando la revisión y aprobación requerida por el Project Manager.

### 5. EJEMPLOS (FEW-SHOT)

[Ejemplo 1 - Nuevo Proyecto de Integración]
Entrada:
- Remitente: ana.torres@techcorp.com
- Asunto: Solicitud de Reunión Técnica y Requisitos para Módulo de Pagos
- Archivo Adjunto: Especificaciones_Modulo_Pagos_v1.pdf
- Cuerpo: "Hola equipo de UTPConsult, soy Ana Torres de TechCorp. Queremos coordinar una sesión de revisión técnica para integrar su pasarela de pagos la próxima semana. Adjunto documento de arquitectura..."
Llamadas a herramientas esperadas:
1. crear_ticket_en_jira(project_key='PAYMOD', summary='Integración Pasarela de Pagos - TechCorp', issue_type='Story', priority='High', description='...')
2. agendar_reunion_en_google_calendar(summary='Sesión Técnica de Arquitectura: Pagos - TechCorp', start_time='2026-09-22T10:00:00Z', end_time='2026-09-22T10:45:00Z', attendees=['ana.torres@techcorp.com', 'pm@utpconsult.com'], agenda='1. Revisión de arquitectura...', status='tentative')
3. actualizar_contacto_en_crm(full_name='Ana Torres', company_name='TechCorp', email='ana.torres@techcorp.com', pipeline_stage='Reunión Técnica', project_interest='Módulo de pagos y pasarela de suscripciones')

[Ejemplo 2 - Incidencia Técnica Crítica]
Entrada:
- Remitente: lmorales@fintechbank.io
- Asunto: URGENTE: Incompatibilidad de Webhooks en Pasarela
- Archivo Adjunto: error_logs_500.txt
- Cuerpo: "Detectamos timeout en ambiente staging en webhooks. Necesitamos un ticket de bug urgente y reunión de emergencia..."
Llamadas a herramientas esperadas:
1. crear_ticket_en_jira(project_key='UTP', summary='Incidencia Crítica: Incompatibilidad y Timeout de Webhooks - FintechBank', issue_type='Bug', priority='Highest', description='...')
2. agendar_reunion_en_google_calendar(summary='Sesión Técnica de Emergencia: Webhooks - FintechBank', start_time='2026-09-22T10:00:00Z', end_time='2026-09-22T10:45:00Z', attendees=['lmorales@fintechbank.io', 'pm@utpconsult.com'], agenda='1. Análisis de logs...', status='tentative')
3. actualizar_contacto_en_crm(full_name='Lucía Morales', company_name='FintechBank', email='lmorales@fintechbank.io', pipeline_stage='Reunión Técnica', project_interest='Soporte crítico de webhooks y pasarela')

### 6. DATOS DE ENTRADA
El asistente recibe un objeto estructurado con las siguientes propiedades:
- Remitente: Correo electrónico corporativo del remitente (ej. nombre@empresa.com).
- Asunto: Título formal del correo recibido.
- Archivo Adjunto: Nombre del archivo técnico adjunto si existe, o 'Ninguno'.
- Cuerpo del mensaje: Texto completo con la solicitud, requerimiento técnico o reporte de incidencia.
"""


class UTPAssistantManager:
    """
    Gestor principal del Asistente UTP basado en la API de Google Gemini.
    Orquesta el ciclo de vida del Run, la detección de function calls y la ejecución de herramientas.
    La clave de API se obtiene ESTRICTAMENTE de las variables de entorno (.env).
    """

    def __init__(self, model_name: Optional[str] = None):
        # Carga de variables de entorno actualizadas
        load_dotenv(override=True)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        env_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
        # Mapeo de compatibilidad a gemini-3.6-flash
        if env_model in ["gemini-2.0-flash", "gemini-2.5-flash"]:
            env_model = "gemini-3.6-flash"
        self.model_name = model_name or env_model
        self.client_configured = False
        self._configurar_cliente()

    def _configurar_cliente(self) -> bool:
        """Configura la API de Google Gemini estrictamente si la clave de .env es válida."""
        if not GEMINI_AVAILABLE:
            logger.warning("google-generativeai no está disponible en el entorno.")
            self.client_configured = False
            return False

        if (
            self.api_key and
            self.api_key.startswith("AIzaSy") and
            len(self.api_key) >= 30
        ):
            try:
                genai.configure(api_key=self.api_key)
                self.client_configured = True
                logger.info(f"Cliente Gemini configurado correctamente desde .env con modelo '{self.model_name}'.")
                return True
            except Exception as e:
                logger.error(f"Error al configurar cliente Gemini: {e}")
                self.client_configured = False
                return False
        else:
            if self.api_key and not self.api_key.startswith("AIzaSy"):
                logger.warning("La clave en GEMINI_API_KEY no parece ser de Google AI Studio (debe iniciar con 'AIzaSy'). Modo simulación activado.")
            else:
                logger.info("GEMINI_API_KEY no configurada en .env. Modo simulación activado.")
            self.client_configured = False
            return False

    def _ejecutar_herramienta_local(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Despacha la ejecución local del servicio correspondiente."""
        try:
            if tool_name == "crear_ticket_en_jira":
                return ejecutar_crear_ticket_jira(
                    project_key=arguments.get("project_key", "UTP"),
                    summary=arguments.get("summary", "Requerimiento técnico"),
                    description=arguments.get("description", "Sin descripción"),
                    issue_type=arguments.get("issue_type", "Task"),
                    priority=arguments.get("priority", "Medium")
                )
            elif tool_name == "agendar_reunion_en_google_calendar":
                attendees = arguments.get("attendees", [])
                if isinstance(attendees, str):
                    attendees = [attendees]
                return ejecutar_agendar_google_calendar(
                    summary=arguments.get("summary", "Reunión Técnica"),
                    start_time=arguments.get("start_time", "2026-09-22T10:00:00Z"),
                    end_time=arguments.get("end_time", "2026-09-22T10:45:00Z"),
                    attendees=attendees,
                    agenda=arguments.get("agenda", "Revisión técnica inicial"),
                    status=arguments.get("status", "tentative")
                )
            elif tool_name == "actualizar_contacto_en_crm":
                return ejecutar_actualizar_contacto_crm(
                    full_name=arguments.get("full_name", "Contacto Desconocido"),
                    company_name=arguments.get("company_name", "Empresa Desconocida"),
                    email=arguments.get("email", "contacto@ejemplo.com"),
                    pipeline_stage=arguments.get("pipeline_stage", "Lead Calificado"),
                    project_interest=arguments.get("project_interest", "Consultoría general")
                )
            else:
                return {
                    "status": "error",
                    "message": f"Herramienta desconocida: {tool_name}"
                }
        except Exception as e:
            logger.error(f"Excepción al ejecutar herramienta {tool_name}: {e}")
            return {
                "status": "error",
                "message": f"Fallo en ejecución de {tool_name}: {str(e)}"
            }

    def procesar_correo(
        self,
        remitente: str,
        asunto: str,
        cuerpo: str,
        archivo_nombre: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Procesa un correo electrónico:
        1. Estado: 'queued' -> 'in_progress'
        2. Detecta si requiere llamada a herramientas ('requires_action')
        3. Ejecuta herramientas en services.py
        4. Envía resultados de vuelta al modelo y completa el ciclo ('completed')
        """
        historial_estados = ["queued", "in_progress"]
        timestamp_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        mensaje_correo = (
            f"--- NUEVO CORREO CORPORATIVO RECIBIDO ---\n"
            f"Remitente: {remitente}\n"
            f"Asunto: {asunto}\n"
            f"Archivo Adjunto: {archivo_nombre if archivo_nombre else 'Ninguno'}\n\n"
            f"Cuerpo del mensaje:\n{cuerpo}\n"
            f"-----------------------------------------\n"
            f"Por favor procesa este correo: extrae requerimientos para crear el ticket en Jira, "
            f"agenda la reunión técnica de 45 min en Google Calendar y registra el prospecto en el CRM."
        )

        # Modo fallback inteligente para pruebas ante ausencia de cliente configurado
        if not self.client_configured:
            logger.info("Ejecutando en Modo Simulado (Sin API Key o API Key no configurada).")
            return self._procesar_correo_simulado(
                remitente, asunto, cuerpo, archivo_nombre, historial_estados, timestamp_inicio
            )

        try:
            # Definición de herramientas para Gemini
            herramientas_gemini = [
                ejecutar_crear_ticket_jira,
                ejecutar_agendar_google_calendar,
                ejecutar_actualizar_contacto_crm
            ]

            modelo = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT,
                tools=herramientas_gemini
            )

            # Sesión de chat con Function Calling
            chat = modelo.start_chat(enable_automatic_function_calling=False)
            respuesta_inicial = chat.send_message(mensaje_correo)

            tool_calls_detectados = []
            tool_outputs_ejecutados = []

            # Detección de function calls solicitadas por el modelo
            candidato = respuesta_inicial.candidates[0]
            partes_con_funciones = [
                parte for parte in candidato.content.parts if parte.function_call
            ]

            if partes_con_funciones:
                historial_estados.append("requires_action")
                
                # Ejecución secuencial de herramientas solicitadas
                respuestas_para_gemini = []
                for parte in partes_con_funciones:
                    fn_call = parte.function_call
                    fn_name = fn_call.name
                    # Conversión de argumentos a diccionario
                    fn_args = dict(fn_call.args)

                    tool_calls_detectados.append({
                        "name": fn_name,
                        "arguments": fn_args
                    })

                    resultado_tool = self._ejecutar_herramienta_local(fn_name, fn_args)
                    tool_outputs_ejecutados.append({
                        "tool_name": fn_name,
                        "arguments": fn_args,
                        "output": resultado_tool
                    })

                    respuestas_para_gemini.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": resultado_tool}
                            )
                        )
                    )

                # Envío de resultados de herramientas para respuesta final ejecutiva
                respuesta_final = chat.send_message(respuestas_para_gemini)
                mensaje_asistente = respuesta_final.text
            else:
                mensaje_asistente = respuesta_inicial.text

            historial_estados.append("completed")

            return {
                "status": "completed",
                "lifecycle_states": historial_estados,
                "current_state": "completed",
                "tool_calls": tool_calls_detectados,
                "tool_outputs": tool_outputs_ejecutados,
                "assistant_message": mensaje_asistente,
                "timestamp": timestamp_inicio,
                "mode": f"Live Gemini API ({self.model_name})"
            }

        except Exception as e:
            logger.error(f"Error durante llamada a Gemini API: {e}. Activando fallback de simulación estructurada.")
            # Fallback seguro en caso de cuota agotada o error de red
            return self._procesar_correo_simulado(
                remitente, asunto, cuerpo, archivo_nombre, historial_estados, timestamp_inicio, error_previo=str(e)
            )

    def _procesar_correo_simulado(
        self,
        remitente: str,
        asunto: str,
        cuerpo: str,
        archivo_nombre: Optional[str],
        historial_estados: List[str],
        timestamp_inicio: str,
        error_previo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta la orquestación simulada siguiendo exactamente las reglas del System Prompt:
        - Si no hay fecha, programa para el próximo martes a las 10:00 AM (duración 45 min).
        - Extrae datos de TechCorp o la empresa correspondiente.
        - Invoca las 3 herramientas en services.py.
        """
        historial_estados.append("requires_action")

        # 1. Determinación de datos del contacto y empresa
        full_name = "Ana Torres" if "Ana" in cuerpo or "Ana" in remitente else remitente.split("@")[0].replace(".", " ").title()
        company_name = "TechCorp" if "TechCorp" in cuerpo or "TechCorp" in asunto else "Empresa Prospecto"
        email = remitente

        # 2. Cálculo del próximo martes a las 10:00 AM
        hoy = datetime.now()
        dias_hasta_martes = (1 - hoy.weekday() + 7) % 7
        if dias_hasta_martes == 0:
            dias_hasta_martes = 7
        proximo_martes = hoy + timedelta(days=dias_hasta_martes)
        inicio_reunion = proximo_martes.replace(hour=10, minute=0, second=0, microsecond=0)
        fin_reunion = inicio_reunion + timedelta(minutes=45)

        start_time_iso = inicio_reunion.strftime("%Y-%m-%dT10:00:00Z")
        end_time_iso = fin_reunion.strftime("%Y-%m-%dT10:45:00Z")

        # 3. Argumentos para crear_ticket_en_jira
        clave_jira_config = (os.getenv("JIRA_PROJECT_KEY") or "UTPCONSULT").strip().upper()
        jira_args = {
            "project_key": clave_jira_config,
            "summary": f"Integración Módulo de Pagos - {company_name}",
            "description": (
                f"Requerimiento extraído del correo de {full_name} ({email}).\n"
                f"Asunto: {asunto}\n"
                f"Archivo adjunto: {archivo_nombre if archivo_nombre else 'N/A'}\n"
                f"Alcance: Implementación de arquitectura de pagos, validación de endpoints y ambiente de pruebas."
            ),
            "issue_type": "Story",
            "priority": "High"
        }

        # 4. Argumentos para agendar_reunion_en_google_calendar
        cal_args = {
            "summary": f"Sesión Técnica de Arquitectura: Pagos - {company_name}",
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "attendees": [email, "pm@utpconsult.com", "tech-lead@utpconsult.com"],
            "agenda": (
                "1. Revisión de especificaciones del módulo de pagos.\n"
                "2. Definición de protocolos de seguridad y webhooks.\n"
                "3. Plan de trabajo y cronograma de despliegue."
            ),
            "status": "tentative"
        }

        # 5. Argumentos para actualizar_contacto_en_crm
        crm_args = {
            "full_name": full_name,
            "company_name": company_name,
            "email": email,
            "pipeline_stage": "Reunión Técnica",
            "project_interest": "Módulo de Procesamiento de Pagos y Pasarela Segura"
        }

        tool_calls = [
            {"name": "crear_ticket_en_jira", "arguments": jira_args},
            {"name": "agendar_reunion_en_google_calendar", "arguments": cal_args},
            {"name": "actualizar_contacto_en_crm", "arguments": crm_args}
        ]

        tool_outputs = []
        for call in tool_calls:
            salida = self._ejecutar_herramienta_local(call["name"], call["arguments"])
            tool_outputs.append({
                "tool_name": call["name"],
                "arguments": call["arguments"],
                "output": salida
            })

        historial_estados.append("completed")

        ticket_id = tool_outputs[0]["output"].get("ticket_id", "PAYMOD-101")
        event_id = tool_outputs[1]["output"].get("event_id", "evt_gcal_001")
        meet_link = tool_outputs[1]["output"].get("meet_url", "https://meet.google.com/utp-pay-meet")

        mensaje_ejecutivo = (
            f"Estimado equipo de UTPConsult,\n\n"
            f"He procesado exitosamente el requerimiento recibido de **{full_name}** ({company_name}).\n\n"
            f"📌 **Ticket Jira Generado:** `{ticket_id}` (Prioridad: Alta, Tipo: Story).\n"
            f"📅 **Reunión Agendada:** Martes a las 10:00 AM UTC (45 min) con estado **tentative**.\n"
            f"🔗 **Google Meet Mock:** [{meet_link}]({meet_link})\n"
            f"💼 **CRM Actualizado:** Prospecto en etapa **'Reunión Técnica'**.\n\n"
            f"El evento de calendario y el ticket se encuentran listos para revisión y confirmación en el panel de aprobación."
        )

        return {
            "status": "completed",
            "lifecycle_states": historial_estados,
            "current_state": "completed",
            "tool_calls": tool_calls,
            "tool_outputs": tool_outputs,
            "assistant_message": mensaje_ejecutivo,
            "timestamp": timestamp_inicio,
            "mode": "Simulación Local / Orquestador HITL" if not error_previo else f"Fallback Local (API Notice: {error_previo[:60]}...)"
        }
