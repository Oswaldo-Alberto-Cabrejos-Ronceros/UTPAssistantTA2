"""
services.py
===========
Implementaciones de servicios simulados (mocks enriquecidos) para Jira,
Google Calendar y CRM corporativo.
Almacena el estado en memoria para permitir visualización en vivo y aprobación HITL.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid
import logging

logger = logging.getLogger("UTP_Services")

# ==========================================
# BASE DE DATOS EN MEMORIA (STATE STORAGE)
# ==========================================

class SimulatedDatabase:
    def __init__(self):
        self.jira_tickets: List[Dict[str, Any]] = []
        self.calendar_events: List[Dict[str, Any]] = []
        self.crm_contacts: List[Dict[str, Any]] = []
        self._jira_counter = 100
        self._crm_counter = 200

    def reset(self):
        """Reinicia todos los registros simulados."""
        self.jira_tickets.clear()
        self.calendar_events.clear()
        self.crm_contacts.clear()
        self._jira_counter = 100
        self._crm_counter = 200

    def next_jira_id(self, project_key: str) -> str:
        self._jira_counter += 1
        prefix = (project_key or "UTP").upper().strip()
        return f"{prefix}-{self._jira_counter}"

    def next_crm_id(self) -> str:
        self._crm_counter += 1
        return f"LEAD-{self._crm_counter}"


# Instancia singleton de la base de datos simulada
db = SimulatedDatabase()


# ==========================================
# CONEXIONES REALES Y FALLBACKS INTELIGENTES
# ==========================================

import os
import json
import base64
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# Importación de librerías de Google Calendar
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build as build_google_service
    GOOGLE_CALENDAR_LIB_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_LIB_AVAILABLE = False


def _obtener_cliente_google_calendar():
    """
    Intenta inicializar el cliente oficial de Google Calendar v3.
    Soporta dos métodos de autenticación:
    1. Opción 2 (Base64 inline): GOOGLE_SERVICE_ACCOUNT_B64
    2. Opción 1 (Ruta al archivo): GOOGLE_APPLICATION_CREDENTIALS o GOOGLE_SERVICE_ACCOUNT_FILE
    """
    if not GOOGLE_CALENDAR_LIB_AVAILABLE:
        return None, "Librerías de Google Calendar (googleapiclient/google-auth) no disponibles."

    scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events"
    ]

    # --- OPCIÓN 2: JSON INLINE COMO BASE64 O STRING DIRECTO ---
    b64_creds = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_B64") or
        os.getenv("GOOGLE_CALENDAR_B64") or
        os.getenv("GOOGLE_CALENDAR_CREDENTIALS_B64") or
        os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON") or
        ""
    ).strip().strip('"').strip("'")

    # Detección de contenido JSON directo en variable de archivo
    sa_env_raw = (os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or "").strip()
    if sa_env_raw.startswith("{") and sa_env_raw.endswith("}"):
        b64_creds = sa_env_raw

    if b64_creds and b64_creds != "tu_service_account_en_base64_aqui" and len(b64_creds) > 30:
        try:
            # Caso A: Viene como JSON directo en texto plano
            if b64_creds.startswith("{"):
                creds_dict = json.loads(b64_creds)
            else:
                # Caso B: Viene codificado en Base64
                raw_json = base64.b64decode(b64_creds).decode("utf-8")
                creds_dict = json.loads(raw_json)

            # Validación de Service Account ("type": "service_account")
            if creds_dict.get("type") == "service_account":
                creds = service_account.Credentials.from_service_account_info(
                    creds_dict,
                    scopes=scopes
                )
                service = build_google_service("calendar", "v3", credentials=creds, cache_discovery=False)
                logger.info("Google Calendar autenticado exitosamente usando Service Account (Opción 2).")
                return service, None
            else:
                tipo_detectado = creds_dict.get("type") or list(creds_dict.keys())[0] if creds_dict else "desconocido"
                error_msg = (
                    f"El JSON proporcionado es de tipo '{tipo_detectado}' (ej. OAuth Client ID 'web'), "
                    f"pero Google Calendar API para backend requiere una Cuenta de Servicio (Service Account) "
                    f"con '\"type\": \"service_account\"'. Consulta GUIA_CREDENCIALES_Y_APIS.md."
                )
                logger.warning(error_msg)
                return None, error_msg
        except Exception as e:
            logger.error(f"Error al decodificar o autenticar credenciales de Google Calendar: {e}")
            return None, f"Error en credenciales inline de Google Calendar: {str(e)}"

    # --- OPCIÓN 1: RUTA A ARCHIVO JSON (GOOGLE_APPLICATION_CREDENTIALS / GOOGLE_SERVICE_ACCOUNT_FILE) ---
    service_account_file = (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or
        "service_account.json"
    ).strip().strip('"').strip("'")
    
    if os.path.exists(service_account_file):
        try:
            creds = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=scopes
            )
            service = build_google_service("calendar", "v3", credentials=creds, cache_discovery=False)
            logger.info(f"Google Calendar autenticado exitosamente desde archivo '{service_account_file}' (Opción 1).")
            return service, None
        except Exception as e:
            return None, f"Error al autenticar Service Account desde archivo: {str(e)}"

    return None, (
        "No se encontraron credenciales de Google Calendar en .env "
        "(Configura GOOGLE_SERVICE_ACCOUNT_B64 [Opción 2] o GOOGLE_APPLICATION_CREDENTIALS [Opción 1])."
    )


def ejecutar_crear_ticket_jira(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str,
    priority: str
) -> Dict[str, Any]:
    """
    Crea un ticket en Jira.
    Si las credenciales en .env están presentes (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN),
    realiza una llamada real a la API REST de Atlassian Jira Cloud.
    Si no están configuradas o falla la llamada, conmuta automáticamente a Simulación Fallback.
    """
    jira_url = (os.getenv("JIRA_URL") or os.getenv("JIRA_DOMINIO") or "").strip().rstrip("/")
    jira_email = (os.getenv("JIRA_EMAIL") or os.getenv("JIRA_CORREO") or "").strip()
    jira_api_token = (os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_TOKEN") or "").strip()

    # Clave de proyecto definida en variables de entorno
    project_key_env = (os.getenv("JIRA_PROJECT_KEY") or "").strip()
    if project_key_env:
        project_key = project_key_env

    # Normalización de prefijo de protocolo HTTPS
    if jira_url and not jira_url.startswith("http://") and not jira_url.startswith("https://"):
        jira_url = f"https://{jira_url}"

    # Validación de presencia de credenciales completas de Jira
    tiene_credenciales_jira = (
        bool(jira_url) and
        bool(jira_email) and
        bool(jira_api_token) and
        "tu-dominio" not in jira_url and
        "tu_jira" not in jira_api_token
    )

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if tiene_credenciales_jira:
        try:
            endpoint = f"{jira_url}/rest/api/3/issue"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            # Normalización de tipo de issue para Jira Cloud
            issue_type_clean = issue_type if issue_type in ["Task", "Story", "Bug", "Epic"] else "Task"

            # Formato Atlassian Document Format (ADF) para API v3
            payload = {
                "fields": {
                    "project": {
                        "key": project_key.upper().strip()
                    },
                    "summary": summary,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {
                        "name": issue_type_clean
                    }
                }
            }

            response = requests.post(
                endpoint,
                auth=HTTPBasicAuth(jira_email, jira_api_token),
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code in (200, 201):
                data = response.json()
                real_key = data.get("key", f"{project_key}-REAL")
                real_url = f"{jira_url}/browse/{real_key}"

                registro = {
                    "id": real_key,
                    "project_key": project_key.upper(),
                    "summary": summary,
                    "description": description,
                    "issue_type": issue_type_clean,
                    "priority": priority,
                    "status": "Backlog (En Jira Cloud Real)",
                    "aprobado_pm": False,
                    "url": real_url,
                    "is_real": True,
                    "created_at": created_at
                }
                db.jira_tickets.append(registro)

                logger.info(f"Ticket {real_key} creado exitosamente en Jira Cloud Real.")
                return {
                    "status": "success",
                    "modo": "real",
                    "message": f"Ticket {real_key} creado exitosamente en Jira Cloud Real.",
                    "ticket_id": real_key,
                    "issue_url": real_url,
                    "summary": summary,
                    "issue_type": issue_type_clean,
                    "priority": priority,
                    "estado_actual": "Backlog",
                    "conexion": "Jira Cloud REST API v3 (Conexión Real)"
                }
            else:
                resp_txt = response.text
                if "target project doesn't exist" in resp_txt:
                    motivo_fallback = f"El proyecto con clave '{project_key}' no existe en tu Jira ({jira_url}). Crea un proyecto con clave '{project_key}' en Jira o actualiza JIRA_PROJECT_KEY en .env."
                elif response.status_code == 401:
                    motivo_fallback = f"Error de autenticación 401 en Jira. Verifica que JIRA_EMAIL ({jira_email}) y JIRA_API_TOKEN sean válidos."
                else:
                    motivo_fallback = f"Respuesta HTTP {response.status_code} de Jira API ({resp_txt[:120]})"
                
                logger.warning(
                    f"Fallo en API de Jira (HTTP {response.status_code}): {motivo_fallback}. "
                    f"Activando fallback a simulación."
                )
        except Exception as e:
            logger.warning(f"Excepción al conectar con Jira Real: {e}. Activando fallback a simulación.")
            motivo_fallback = f"Error de conexión de red o timeout ({str(e)})"
    else:
        motivo_fallback = "Credenciales de Jira no configuradas en .env (JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN)"

    # --- FALLBACK A BASE DE DATOS SIMULADA ---
    ticket_id = db.next_jira_id(project_key)
    issue_url = f"https://jira.utpconsult.atlassian.net/browse/{ticket_id}"

    registro = {
        "id": ticket_id,
        "project_key": project_key.upper(),
        "summary": summary,
        "description": description,
        "issue_type": issue_type,
        "priority": priority,
        "status": "Backlog (Simulación Fallback - Pendiente PM)",
        "aprobado_pm": False,
        "url": issue_url,
        "is_real": False,
        "created_at": created_at,
        "motivo_simulacion": motivo_fallback
    }
    db.jira_tickets.append(registro)

    return {
        "status": "success",
        "modo": "simulacion",
        "message": f"Ticket {ticket_id} registrado en Base Simulada (Fallback). Motivo: {motivo_fallback}",
        "ticket_id": ticket_id,
        "issue_url": issue_url,
        "summary": summary,
        "issue_type": issue_type,
        "priority": priority,
        "estado_actual": "Backlog (Simulado)",
        "conexion": "Simulación Local en Memoria (Fallback Activo)",
        "nota_pm": motivo_fallback
    }


def ejecutar_agendar_google_calendar(
    summary: str,
    start_time: str,
    end_time: str,
    attendees: List[str],
    agenda: str,
    status: str = "tentative"
) -> Dict[str, Any]:
    """
    Agenda una reunión técnica.
    Si está configurada una Service Account y Calendar ID en .env, realiza una llamada
    real a la API v3 de Google Calendar e intenta generar un enlace de Google Meet.
    Si no está configurada o falla la API, conmuta automáticamente a Simulación Fallback.
    """
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()
    cliente_cal, error_auth = _obtener_cliente_google_calendar()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if cliente_cal is not None:
        try:
            # Lista de correos limpios
            attendees_limpios = [c.strip() for c in attendees if c and c.strip()]
            participantes_texto = ", ".join(attendees_limpios) if attendees_limpios else "Sin participantes adicionales"

            # Identificador único de conferencia para Google Meet
            req_meet_id = f"utp-{uuid.uuid4().hex[:8]}"
            meet_fallback_url = f"https://meet.google.com/utp-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}"

            descripcion_completa = (
                f"Participantes Convocados:\n{participantes_texto}\n\n"
                f"Agenda de la Sesión:\n{agenda}\n\n"
                f"Agendado automáticamente por UTP Assistant (HITL)."
            )

            # Nota: Las Service Accounts estándar en cuentas @gmail.com no pueden invitar 'attendees'
            # sin 'Domain-Wide Delegation'. Por ello, se registran en la descripción para garantizar creación 100% exitosa.
            cuerpo_evento = {
                "summary": summary,
                "description": descripcion_completa,
                "start": {
                    "dateTime": start_time if "T" in start_time else f"{start_time}T10:00:00Z",
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time if "T" in end_time else f"{end_time}T10:45:00Z",
                    "timeZone": "UTC"
                },
                "status": "tentative",
                "conferenceData": {
                    "createRequest": {
                        "requestId": req_meet_id,
                        "conferenceSolutionKey": {"type": "hangoutsMeet"}
                    }
                }
            }

            try:
                # Creación de evento con solicitud de Google Meet
                evento_creado = cliente_cal.events().insert(
                    calendarId=calendar_id,
                    body=cuerpo_evento,
                    conferenceDataVersion=1
                ).execute()
            except Exception as e_meet:
                logger.warning(f"No se pudo adjuntar Google Meet nativo ({e_meet}). Creando evento estándar...")
                # Fallback sin conferenceData para compatibilidad con cuentas personales
                cuerpo_evento.pop("conferenceData", None)
                cuerpo_evento["description"] = f"{descripcion_completa}\n\n🔗 Enlace de Sesión: {meet_fallback_url}"
                evento_creado = cliente_cal.events().insert(
                    calendarId=calendar_id,
                    body=cuerpo_evento
                ).execute()

            real_event_id = evento_creado.get("id")
            html_link = evento_creado.get("htmlLink", "")
            
            # Enlace de Google Meet generado
            meet_link = ""
            conf_data = evento_creado.get("conferenceData", {})
            for ep in conf_data.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meet_link = ep.get("uri", "")
                    break

            if not meet_link:
                meet_link = meet_fallback_url

            registro = {
                "id": real_event_id,
                "summary": summary,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "agenda": agenda,
                "status": status,
                "meet_url": meet_link,
                "calendar_url": html_link,
                "is_real": True,
                "created_at": created_at
            }
            db.calendar_events.append(registro)

            logger.info(f"¡Evento {real_event_id} creado exitosamente en Google Calendar Real ({calendar_id})!")
            return {
                "status": "success",
                "modo": "real",
                "message": f"Reunión '{summary}' programada exitosamente en Google Calendar Real.",
                "event_id": real_event_id,
                "start_time": start_time,
                "end_time": end_time,
                "attendees_count": len(attendees),
                "meet_url": meet_link,
                "calendar_url": html_link,
                "agenda_preview": agenda[:120] + "..." if len(agenda) > 120 else agenda,
                "conexion": f"Google Calendar API v3 (Conexión Real en {calendar_id})"
            }
        except Exception as e:
            logger.warning(f"Excepción al agendar en Google Calendar Real: {e}. Activando fallback a simulación.")
            motivo_fallback = f"Error en Google Calendar API ({str(e)})"
    else:
        motivo_fallback = error_auth or "Credenciales de Google Calendar no configuradas en .env"

    # --- FALLBACK A BASE DE DATOS SIMULADA ---
    event_uuid = uuid.uuid4().hex[:8]
    event_id = f"evt_gcal_{event_uuid}"
    meet_code = f"utp-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}"
    meet_url = f"https://meet.google.com/{meet_code}"

    registro = {
        "id": event_id,
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "attendees": attendees,
        "agenda": agenda,
        "status": status,
        "meet_url": meet_url,
        "is_real": False,
        "created_at": created_at,
        "motivo_simulacion": motivo_fallback
    }
    db.calendar_events.append(registro)

    return {
        "status": "success",
        "modo": "simulacion",
        "message": f"Reunión '{summary}' programada en Modo Simulado (Fallback). Motivo: {motivo_fallback}",
        "event_id": event_id,
        "start_time": start_time,
        "end_time": end_time,
        "attendees_count": len(attendees),
        "meet_url": meet_url,
        "agenda_preview": agenda[:120] + "..." if len(agenda) > 120 else agenda,
        "conexion": "Simulación Local en Memoria (Fallback Activo)",
        "nota_pm": motivo_fallback
    }


def ejecutar_actualizar_contacto_crm(
    full_name: str,
    company_name: str,
    email: str,
    pipeline_stage: str,
    project_interest: str
) -> Dict[str, Any]:
    """
    Crea o actualiza un contacto en el CRM corporativo.
    Por diseño y requerimiento explícito del proyecto, el CRM opera
    exclusivamente en Modo Simulado en memoria (sin conexión real).
    """
    try:
        contacto_existente = next((c for c in db.crm_contacts if c["email"].lower() == email.lower()), None)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if contacto_existente:
            contacto_existente["full_name"] = full_name
            contacto_existente["company_name"] = company_name
            contacto_existente["pipeline_stage"] = pipeline_stage
            contacto_existente["project_interest"] = project_interest
            contacto_existente["updated_at"] = updated_at
            lead_id = contacto_existente["id"]
            accion = "actualizado"
        else:
            lead_id = db.next_crm_id()
            registro = {
                "id": lead_id,
                "full_name": full_name,
                "company_name": company_name,
                "email": email,
                "pipeline_stage": pipeline_stage,
                "project_interest": project_interest,
                "created_at": updated_at,
                "updated_at": updated_at,
                "is_real": False
            }
            db.crm_contacts.append(registro)
            accion = "creado"

        return {
            "status": "success",
            "modo": "simulacion",
            "message": f"Contacto {full_name} ({company_name}) {accion} con éxito en CRM Mock.",
            "lead_id": lead_id,
            "pipeline_stage": pipeline_stage,
            "company_name": company_name,
            "email": email,
            "conexion": "CRM Simulado en Memoria (Por diseño)"
        }
    except Exception as e:
        logger.error(f"Error al actualizar contacto en CRM: {e}")
        return {
            "status": "error",
            "message": f"Fallo al registrar contacto en CRM: {str(e)}"
        }


# ==========================================
# FUNCIONES DE SOPORTE HUMAN-IN-THE-LOOP (HITL)
# ==========================================

def confirmar_reunion_calendar(event_id: str) -> bool:
    """
    Actualiza el estado de una reunión de 'tentative' a 'confirmed' por el PM.
    Si el evento es real, intenta confirmar el estado en Google Calendar API v3.
    """
    for evento in db.calendar_events:
        if evento["id"] == event_id:
            evento["status"] = "confirmed"
            evento["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Actualización en Google Calendar para eventos reales
            if evento.get("is_real"):
                try:
                    cliente_cal, _ = _obtener_cliente_google_calendar()
                    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary").strip()
                    if cliente_cal:
                        cliente_cal.events().patch(
                            calendarId=calendar_id,
                            eventId=event_id,
                            body={"status": "confirmed"}
                        ).execute()
                        logger.info(f"Evento real {event_id} confirmado en Google Calendar API.")
                except Exception as e:
                    logger.warning(f"No se pudo actualizar status en Google Calendar remoto: {e}")

            return True
    return False


def aprobar_ticket_jira(ticket_id: str) -> bool:
    """
    Marca el ticket como Aprobado para Sprint Activo por el PM.
    Actualiza el estado local y en memoria.
    """
    for ticket in db.jira_tickets:
        if ticket["id"] == ticket_id:
            ticket["aprobado_pm"] = True
            ticket["status"] = "Selected for Development"
            ticket["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
    return False


def obtener_diagnostico_conexiones() -> Dict[str, Dict[str, Any]]:
    """
    Evalúa y reporta el estado de configuración de cada servicio externo.
    Útil para mostrar el panel de conectividad en la interfaz de usuario.
    """
    # 1. Gemini
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_configurado = bool(gemini_key) and gemini_key != "tu_api_key_de_gemini_aqui"

    # 2. Jira
    jira_url = (os.getenv("JIRA_URL") or os.getenv("JIRA_DOMINIO") or "").strip().rstrip("/")
    jira_email = (os.getenv("JIRA_EMAIL") or os.getenv("JIRA_CORREO") or "").strip()
    jira_token = (os.getenv("JIRA_API_TOKEN") or os.getenv("JIRA_TOKEN") or "").strip()
    jira_configurado = (
        bool(jira_url) and
        bool(jira_email) and
        bool(jira_token) and
        "tu-dominio" not in jira_url and
        "tu_jira" not in jira_token
    )

    # 3. Google Calendar
    b64_creds = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_B64") or
        os.getenv("GOOGLE_CALENDAR_B64") or
        os.getenv("GOOGLE_CALENDAR_CREDENTIALS_B64") or
        ""
    ).strip().strip('"').strip("'")
    tiene_b64 = bool(b64_creds) and b64_creds != "tu_service_account_en_base64_aqui" and len(b64_creds) > 30

    sa_file = (
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE") or
        "service_account.json"
    ).strip().strip('"').strip("'")
    tiene_archivo = os.path.exists(sa_file)

    cal_configurado = (tiene_b64 or tiene_archivo) and GOOGLE_CALENDAR_LIB_AVAILABLE
    if tiene_b64:
        tipo_cal = "API v3 Real (Base64)"
        detalle_cal = "Autenticación Base64 inline (Opción 2)"
    elif tiene_archivo:
        tipo_cal = "API v3 Real (Archivo)"
        detalle_cal = f"Archivo: {sa_file} (Opción 1)"
    else:
        tipo_cal = "Simulación Fallback"
        detalle_cal = "Configura GOOGLE_SERVICE_ACCOUNT_B64 en .env"

    return {
        "gemini": {
            "activo": gemini_configurado,
            "tipo": "API Real (.env)" if gemini_configurado else "Modo Simulado",
            "detalle": f"Modelo: {os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}" if gemini_configurado else "Falta GEMINI_API_KEY en .env"
        },
        "jira": {
            "activo": jira_configurado,
            "tipo": "API Cloud Real" if jira_configurado else "Simulación Fallback",
            "detalle": f"{jira_url}" if jira_configurado else "Faltan credenciales JIRA_* en .env"
        },
        "calendar": {
            "activo": cal_configurado,
            "tipo": tipo_cal,
            "detalle": detalle_cal
        },
        "crm": {
            "activo": True,
            "tipo": "Simulado en Memoria",
            "detalle": "Operación local en memoria (por diseño)"
        }
    }


def obtener_estado_bd() -> Dict[str, Any]:
    """Retorna una instantánea del estado de los 3 servicios."""
    return {
        "total_tickets_jira": len(db.jira_tickets),
        "total_eventos_calendar": len(db.calendar_events),
        "total_contactos_crm": len(db.crm_contacts),
        "tickets": list(reversed(db.jira_tickets)),
        "eventos": list(reversed(db.calendar_events)),
        "contactos": list(reversed(db.crm_contacts))
    }


def reiniciar_bd():
    """Limpia el almacén de datos en memoria."""
    db.reset()
