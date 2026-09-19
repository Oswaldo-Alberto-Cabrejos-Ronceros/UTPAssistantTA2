"""
scratch/test_pipeline.py
Verificación de extremo a extremo de schemas, services y assistant_core.
"""
import sys
from schemas import (
    CrearTicketJiraSchema,
    AgendarReunionCalendarSchema,
    ActualizarContactoCRMSchema,
    JiraIssueType,
    JiraPriority,
    CalendarStatus,
    CRMPipelineStage,
    TOOLS_CONFIG
)
from services import (
    ejecutar_crear_ticket_jira,
    ejecutar_agendar_google_calendar,
    ejecutar_actualizar_contacto_crm,
    confirmar_reunion_calendar,
    aprobar_ticket_jira,
    obtener_estado_bd,
    reiniciar_bd
)
from assistant_core import UTPAssistantManager

def test_schemas():
    print("=== Test 1: Schemas ===")
    ticket = CrearTicketJiraSchema(
        project_key="PAYMOD",
        summary="Integración Pagos",
        description="Detalle técnico",
        issue_type=JiraIssueType.STORY,
        priority=JiraPriority.HIGH
    )
    assert ticket.project_key == "PAYMOD"
    
    cal = AgendarReunionCalendarSchema(
        summary="Sesión Técnica",
        start_time="2026-09-22T10:00:00Z",
        end_time="2026-09-22T10:45:00Z",
        attendees=["ana@techcorp.com"],
        agenda="Revisión",
        status=CalendarStatus.TENTATIVE
    )
    assert cal.status == "tentative"

    crm = ActualizarContactoCRMSchema(
        full_name="Ana Torres",
        company_name="TechCorp",
        email="ana@techcorp.com",
        pipeline_stage=CRMPipelineStage.REUNION_TECNICA,
        project_interest="Pasarela de pagos"
    )
    assert crm.email == "ana@techcorp.com"
    print("[OK] Schemas y validaciones Pydantic OK")
    print(f"[OK] Herramientas declaradas en TOOLS_CONFIG: {len(TOOLS_CONFIG)}")

def test_services():
    print("\n=== Test 2: Services & DB ===")
    reiniciar_bd()
    res_jira = ejecutar_crear_ticket_jira(
        project_key="PAYMOD",
        summary="Módulo Pagos",
        description="Reqs",
        issue_type="Story",
        priority="High"
    )
    assert res_jira["status"] == "success"
    ticket_id = res_jira["ticket_id"]

    res_cal = ejecutar_agendar_google_calendar(
        summary="Reunión Técnica",
        start_time="2026-09-22T10:00:00Z",
        end_time="2026-09-22T10:45:00Z",
        attendees=["ana@techcorp.com"],
        agenda="Temas",
        status="tentative"
    )
    assert res_cal["status"] == "success"
    event_id = res_cal["event_id"]

    res_crm = ejecutar_actualizar_contacto_crm(
        full_name="Ana Torres",
        company_name="TechCorp",
        email="ana@techcorp.com",
        pipeline_stage="Reunión Técnica",
        project_interest="Pasarela"
    )
    assert res_crm["status"] == "success"

    # HITL approvals
    assert confirmar_reunion_calendar(event_id) is True
    assert aprobar_ticket_jira(ticket_id) is True

    bd = obtener_estado_bd()
    assert bd["total_tickets_jira"] == 1
    assert bd["total_eventos_calendar"] == 1
    assert bd["total_contactos_crm"] == 1
    print("[OK] Services y flujo HITL OK")

def test_assistant_manager():
    print("\n=== Test 3: Assistant Manager Orquestacion ===")
    reiniciar_bd()
    manager = UTPAssistantManager()
    resultado = manager.procesar_correo(
        remitente="ana.torres@techcorp.com",
        asunto="Solicitud de Reunion Tecnica y Requisitos para Modulo de Pagos",
        cuerpo="Hola UTPConsult, soy Ana Torres de TechCorp. Quisieramos agendar el proximo martes...",
        archivo_nombre="Especificaciones_Modulo_Pagos_v1.pdf"
    )
    assert resultado["status"] == "completed"
    assert "queued" in resultado["lifecycle_states"]
    assert "requires_action" in resultado["lifecycle_states"]
    assert "completed" in resultado["lifecycle_states"]
    assert len(resultado["tool_calls"]) == 3
    assert len(resultado["tool_outputs"]) == 3
    print("[OK] Ciclo del Run y Function Calling orquestado correctamente")
    print("[OK] Mensaje generado preview:", resultado["assistant_message"][:100], "...")

if __name__ == "__main__":
    test_schemas()
    test_services()
    test_assistant_manager()
    print("\n[EXITO] TODOS LOS TESTS PASARON SATISFACTORIAMENTE.")
