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
# SERVICIOS DE HERRAMIENTAS (TOOL EXECUTORS)
# ==========================================

def ejecutar_crear_ticket_jira(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str,
    priority: str
) -> Dict[str, Any]:
    """
    Crea un ticket de desarrollo en Jira (Simulado).

    Args:
        project_key: Clave del proyecto (ej. PAYMOD, UTP).
        summary: Título del requerimiento.
        description: Detalles y especificaciones.
        issue_type: Task, Story, Bug, Epic.
        priority: Highest, High, Medium, Low.

    Returns:
        dict con status, ticket_id, issue_url y datos registrados.
    """
    try:
        ticket_id = db.next_jira_id(project_key)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        issue_url = f"https://jira.utpconsult.atlassian.net/browse/{ticket_id}"

        registro = {
            "id": ticket_id,
            "project_key": project_key.upper(),
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "priority": priority,
            "status": "Backlog (Pendiente Revisión PM)",
            "aprobado_pm": False,
            "url": issue_url,
            "created_at": created_at
        }
        db.jira_tickets.append(registro)

        return {
            "status": "success",
            "message": f"Ticket {ticket_id} registrado exitosamente en Jira.",
            "ticket_id": ticket_id,
            "issue_url": issue_url,
            "summary": summary,
            "issue_type": issue_type,
            "priority": priority,
            "estado_actual": "Backlog"
        }
    except Exception as e:
        logger.error(f"Error al crear ticket en Jira: {e}")
        return {
            "status": "error",
            "message": f"Fallo en creación de ticket Jira: {str(e)}"
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
    Agenda una reunión en Google Calendar (Simulado).

    Args:
        summary: Asunto de la reunión.
        start_time: Fecha y hora de inicio (ISO-8601).
        end_time: Fecha y hora de fin (ISO-8601).
        attendees: Lista de correos de los participantes.
        agenda: Temario o puntos a tratar.
        status: 'tentative' o 'confirmed'.

    Returns:
        dict con status, event_id, meet_link, fecha confirmada y detalles.
    """
    try:
        event_uuid = uuid.uuid4().hex[:8]
        event_id = f"evt_gcal_{event_uuid}"
        meet_code = f"utp-{uuid.uuid4().hex[:3]}-{uuid.uuid4().hex[:4]}"
        meet_url = f"https://meet.google.com/{meet_code}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        registro = {
            "id": event_id,
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
            "agenda": agenda,
            "status": status,
            "meet_url": meet_url,
            "created_at": created_at
        }
        db.calendar_events.append(registro)

        return {
            "status": "success",
            "message": f"Reunión '{summary}' programada con estado '{status}'.",
            "event_id": event_id,
            "start_time": start_time,
            "end_time": end_time,
            "attendees_count": len(attendees),
            "meet_url": meet_url,
            "agenda_preview": agenda[:120] + "..." if len(agenda) > 120 else agenda
        }
    except Exception as e:
        logger.error(f"Error al agendar reunión en Calendar: {e}")
        return {
            "status": "error",
            "message": f"Fallo al agendar reunión en Google Calendar: {str(e)}"
        }


def ejecutar_actualizar_contacto_crm(
    full_name: str,
    company_name: str,
    email: str,
    pipeline_stage: str,
    project_interest: str
) -> Dict[str, Any]:
    """
    Crea o actualiza un contacto en el CRM corporativo (Simulado).

    Args:
        full_name: Nombre completo.
        company_name: Empresa del contacto.
        email: Correo electrónico corporativo.
        pipeline_stage: Etapa en el pipeline comercial.
        project_interest: Interés técnico o módulo solicitado.

    Returns:
        dict con status, lead_id, pipeline_stage y timestamp.
    """
    try:
        # Verificar si el contacto ya existe por correo
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
                "updated_at": updated_at
            }
            db.crm_contacts.append(registro)
            accion = "creado"

        return {
            "status": "success",
            "message": f"Contacto {full_name} ({company_name}) {accion} con éxito en CRM.",
            "lead_id": lead_id,
            "pipeline_stage": pipeline_stage,
            "company_name": company_name,
            "email": email
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
    """Actualiza el estado de una reunión de 'tentative' a 'confirmed' por el PM."""
    for evento in db.calendar_events:
        if evento["id"] == event_id:
            evento["status"] = "confirmed"
            evento["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
    return False


def aprobar_ticket_jira(ticket_id: str) -> bool:
    """Marca el ticket como Aprobado para Sprint Activo por el PM."""
    for ticket in db.jira_tickets:
        if ticket["id"] == ticket_id:
            ticket["aprobado_pm"] = True
            ticket["status"] = "Selected for Development"
            ticket["approved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True
    return False


def obtener_estado_bd() -> Dict[str, Any]:
    """Retorna una instantánea del estado de los 3 servicios simulados."""
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
