"""
schemas.py
==========
Definición de esquemas de herramientas y modelos Pydantic para UTP Assistant.
Define las especificaciones de:
1. crear_ticket_en_jira
2. agendar_reunion_en_google_calendar
3. actualizar_contacto_en_crm
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. ENUMERACIONES TIPADAS
# ==========================================

class JiraIssueType(str, Enum):
    TASK = "Task"
    STORY = "Story"
    BUG = "Bug"
    EPIC = "Epic"


class JiraPriority(str, Enum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class CalendarStatus(str, Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"


class CRMPipelineStage(str, Enum):
    LEAD_CALIFICADO = "Lead Calificado"
    REUNION_TECNICA = "Reunión Técnica"
    PROPUESTA_NEGOCIACION = "Propuesta en Negociación"
    CIERRE_GANADO = "Cierre Ganado"


# ==========================================
# 2. MODELOS PYDANTIC (VALIDACIÓN DE ENTRADA)
# ==========================================

class CrearTicketJiraSchema(BaseModel):
    project_key: str = Field(
        ...,
        description="Clave del proyecto en Jira, por ejemplo 'PAYMOD' o 'UTP'."
    )
    summary: str = Field(
        ...,
        description="Título o resumen conciso del ticket."
    )
    description: str = Field(
        ...,
        description="Descripción detallada de los requisitos técnicos o incidencia."
    )
    issue_type: JiraIssueType = Field(
        ...,
        description="Tipo de issue en Jira: Task, Story, Bug o Epic."
    )
    priority: JiraPriority = Field(
        ...,
        description="Nivel de prioridad: Highest, High, Medium, Low."
    )


class AgendarReunionCalendarSchema(BaseModel):
    summary: str = Field(
        ...,
        description="Título o asunto de la reunión en Google Calendar."
    )
    start_time: str = Field(
        ...,
        description="Fecha y hora de inicio en formato ISO-8601 (ej. '2026-09-22T10:00:00Z')."
    )
    end_time: str = Field(
        ...,
        description="Fecha y hora de fin en formato ISO-8601 (duración recomendada: 45 minutos)."
    )
    attendees: List[str] = Field(
        ...,
        description="Lista de correos electrónicos de los participantes."
    )
    agenda: str = Field(
        ...,
        description="Puntos clave y orden del día para la sesión técnica."
    )
    status: CalendarStatus = Field(
        default=CalendarStatus.TENTATIVE,
        description="Estado de la reunión: 'tentative' (para revisión PM) o 'confirmed'."
    )


class ActualizarContactoCRMSchema(BaseModel):
    full_name: str = Field(
        ...,
        description="Nombre completo del contacto o prospecto."
    )
    company_name: str = Field(
        ...,
        description="Nombre de la empresa u organización del contacto."
    )
    email: str = Field(
        ...,
        description="Correo electrónico corporativo del contacto."
    )
    pipeline_stage: CRMPipelineStage = Field(
        ...,
        description="Etapa del embudo: Lead Calificado, Reunión Técnica, Propuesta en Negociación, Cierre Ganado."
    )
    project_interest: str = Field(
        ...,
        description="Resumen de los intereses técnicos o proyecto solicitado."
    )


# ==========================================
# 3. ESQUEMA DE DECLARACIONES DE HERRAMIENTAS
# ==========================================

TOOLS_CONFIG = [
    {
        "name": "crear_ticket_en_jira",
        "description": "Crea un nuevo ticket de desarrollo o tarea técnica en Jira.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_key": {
                    "type": "string",
                    "description": "Clave del proyecto en Jira (ej. 'PAYMOD', 'UTP')."
                },
                "summary": {
                    "type": "string",
                    "description": "Resumen conciso del requerimiento técnico."
                },
                "description": {
                    "type": "string",
                    "description": "Descripción completa de especificaciones, alcance o requisitos."
                },
                "issue_type": {
                    "type": "string",
                    "enum": ["Task", "Story", "Bug", "Epic"],
                    "description": "Tipo de ticket técnico."
                },
                "priority": {
                    "type": "string",
                    "enum": ["Highest", "High", "Medium", "Low"],
                    "description": "Nivel de prioridad asignado."
                }
            },
            "required": ["project_key", "summary", "description", "issue_type", "priority"]
        }
    },
    {
        "name": "agendar_reunion_en_google_calendar",
        "description": "Agenda una reunión técnica en Google Calendar en bloques de 45 minutos.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Título descriptivo del evento de calendario."
                },
                "start_time": {
                    "type": "string",
                    "description": "Fecha y hora de inicio en formato ISO-8601 (ej. '2026-09-22T10:00:00Z')."
                },
                "end_time": {
                    "type": "string",
                    "description": "Fecha y hora de finalización en formato ISO-8601."
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Correos electrónicos de los invitados."
                },
                "agenda": {
                    "type": "string",
                    "description": "Agenda y temas a tratar durante la reunión."
                },
                "status": {
                    "type": "string",
                    "enum": ["tentative", "confirmed"],
                    "description": "Estado del evento ('tentative' para revisión HITL o 'confirmed')."
                }
            },
            "required": ["summary", "start_time", "end_time", "attendees", "agenda", "status"]
        }
    },
    {
        "name": "actualizar_contacto_en_crm",
        "description": "Crea o actualiza el registro de un prospecto/contacto en el CRM corporativo.",
        "parameters": {
            "type": "object",
            "properties": {
                "full_name": {
                    "type": "string",
                    "description": "Nombre y apellido del contacto."
                },
                "company_name": {
                    "type": "string",
                    "description": "Empresa a la que pertenece el contacto."
                },
                "email": {
                    "type": "string",
                    "description": "Dirección de correo electrónico válida."
                },
                "pipeline_stage": {
                    "type": "string",
                    "enum": [
                        "Lead Calificado",
                        "Reunión Técnica",
                        "Propuesta en Negociación",
                        "Cierre Ganado"
                    ],
                    "description": "Etapa actual en el pipeline comercial."
                },
                "project_interest": {
                    "type": "string",
                    "description": "Módulo o tecnología de interés del prospecto."
                }
            },
            "required": ["full_name", "company_name", "email", "pipeline_stage", "project_interest"]
        }
    }
]
