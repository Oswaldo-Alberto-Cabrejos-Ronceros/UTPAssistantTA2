"""
app.py
======
Interfaz interactiva en Streamlit para UTP Assistant con Google Gemini API,
Function Calling y orquestación Human-in-the-Loop (HITL).
"""

import streamlit as st
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from assistant_core import UTPAssistantManager
from services import (
    db,
    obtener_estado_bd,
    reiniciar_bd,
    confirmar_reunion_calendar,
    aprobar_ticket_jira
)

# ==========================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="UTP Assistant - PM & Sales Ops Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS modernos y profesionales
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        color: #64748B;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    
    .card-box {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    
    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .pill-queued { background-color: #334155; color: #CBD5E1; }
    .pill-in_progress { background-color: #1E3A8A; color: #93C5FD; }
    .pill-requires_action { background-color: #854D0E; color: #FDE047; }
    .pill-completed { background-color: #065F46; color: #6EE7B7; }
    
    .hitl-container {
        border-left: 4px solid #F59E0B;
        background: rgba(245, 158, 11, 0.08);
        padding: 1rem 1.2rem;
        border-radius: 0 10px 10px 0;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# ==========================================
if "ultimo_resultado" not in st.session_state:
    st.session_state.ultimo_resultado = None

if "pm_aprobado_calendar" not in st.session_state:
    st.session_state.pm_aprobado_calendar = False

if "pm_aprobado_jira" not in st.session_state:
    st.session_state.pm_aprobado_jira = False

if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


# ==========================================
# CASOS DE CORREO PREDEFINIDOS
# ==========================================
CORREOS_PREDEFINIDOS = {
    "⭐ Caso Oficial: Ana Torres (TechCorp - Módulo Pagos)": {
        "remitente": "ana.torres@techcorp.com",
        "asunto": "Solicitud de Reunión Técnica y Requisitos para Módulo de Pagos",
        "archivo": "Especificaciones_Modulo_Pagos_v1.pdf",
        "cuerpo": (
            "Estimado equipo de UTPConsult,\n\n"
            "Espero que se encuentren muy bien. Mi nombre es Ana Torres, Líder de Arquitectura Digital "
            "en TechCorp. Nos gustaría coordinar una sesión de revisión técnica para integrar su pasarela "
            "de pagos en nuestra nueva plataforma de suscripciones.\n\n"
            "Adjunto el documento con la arquitectura requerida y los flujos esperados. "
            "Quisiéramos agendar la sesión para el próximo martes en la mañana si tienen disponibilidad. "
            "Agradeceré confirmar la agenda y registrar nuestros datos corporativos para la propuesta comercial.\n\n"
            "Saludos cordiales,\n"
            "Ana Torres\n"
            "TechCorp Enterprise Solutions"
        )
    },
    "💼 Caso 2: Carlos Vega (RetailPro - Consultoría Cloud)": {
        "remitente": "carlos.vega@retailpro.pe",
        "asunto": "Requerimiento de Modernización de Infraestructura Cloud",
        "archivo": "Diagrama_AWS_Actual.png",
        "cuerpo": (
            "Hola UTPConsult,\n\n"
            "Les escribe Carlos Vega de RetailPro. Estamos buscando apoyo especializado para migrar "
            "nuestra base de datos relacional a microservicios en la nube. "
            "Requerimos una reunión de 45 minutos con su equipo de ingeniería la próxima semana para "
            "revisar el dimensionamiento y emitir una cotización técnica.\n\n"
            "Quedamos atentos a la convocatoria.\n"
            "Carlos Vega - CTO RetailPro"
        )
    },
    "🚨 Caso 3: Lucía Morales (FintechBank - Incidencia Crítica)": {
        "remitente": "lmorales@fintechbank.io",
        "asunto": "URGENTE: Incompatibilidad de Webhooks en Pasarela",
        "archivo": "error_logs_500.txt",
        "cuerpo": (
            "Estimado soporte de UTPConsult,\n\n"
            "Detectamos que los webhooks de confirmación están arrojando timeout en ambiente staging. "
            "Solicitamos abrir un ticket de máxima prioridad (Bug) para que el equipo dev lo revise "
            "y una sesión técnica de emergencia para revisar los logs adjuntos.\n\n"
            "Atentamente,\n"
            "Lucía Morales - Operaciones FintechBank"
        )
    }
}


# ==========================================
# BARRA LATERAL (CONFIGURACIÓN Y BASES DE DATOS)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Configuración del Asistente")
    
    api_key_input = st.text_input(
        "Gemini API Key:",
        value=st.session_state.gemini_api_key,
        type="password",
        help="Introduce tu clave de Google AI Studio. Si está vacía o inválida, se ejecutará el orquestador en modo simulación estructurada."
    )
    if api_key_input != st.session_state.gemini_api_key:
        st.session_state.gemini_api_key = api_key_input

    modelo_seleccionado = st.selectbox(
        "Modelo de Gemini:",
        options=["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"],
        index=0
    )
    st.session_state.gemini_model = modelo_seleccionado

    if st.session_state.gemini_api_key and st.session_state.gemini_api_key != "tu_api_key_de_gemini_aqui":
        st.success("🟢 Clave de API configurada")
    else:
        st.info("ℹ️ Modo Simulado Activo (Ingresa tu API Key para llamadas directas a Gemini)")

    st.markdown("---")
    st.markdown("### 🗄️ Bases de Datos Simuladas en Vivo")
    
    col_btn_reset, _ = st.columns([1, 1])
    with col_btn_reset:
        if st.button("🔄 Reiniciar Datos", help="Limpia todos los registros mock"):
            reiniciar_bd()
            st.session_state.ultimo_resultado = None
            st.session_state.pm_aprobado_calendar = False
            st.session_state.pm_aprobado_jira = False
            st.rerun()

    estado_bd = obtener_estado_bd()

    # Métricas de BD
    m1, m2, m3 = st.columns(3)
    m1.metric("Jira", estado_bd["total_tickets_jira"])
    m2.metric("Calendar", estado_bd["total_eventos_calendar"])
    m3.metric("CRM", estado_bd["total_contactos_crm"])

    # Pestañas con detalles
    tab_jira, tab_cal, tab_crm = st.tabs(["🎫 Jira", "📅 Calendar", "👥 CRM"])

    with tab_jira:
        if estado_bd["tickets"]:
            for t in estado_bd["tickets"]:
                estado_badge = "🟢 Aprobado PM" if t.get("aprobado_pm") else "🟡 Pendiente PM"
                st.markdown(f"**[{t['id']}] {t['summary']}**")
                st.caption(f"Tipo: `{t['issue_type']}` | Prioridad: `{t['priority']}` | {estado_badge}")
                st.markdown(f"[Ver en Jira Mock]({t['url']})")
                st.divider()
        else:
            st.caption("No hay tickets creados aún.")

    with tab_cal:
        if estado_bd["eventos"]:
            for ev in estado_bd["eventos"]:
                status_icon = "🟢 Confirmada" if ev["status"] == "confirmed" else "🟠 Tentativa (HITL)"
                st.markdown(f"**{ev['summary']}**")
                st.caption(f"Inicio: `{ev['start_time']}`\nFin: `{ev['end_time']}`")
                st.caption(f"Estado: {status_icon}")
                st.markdown(f"[🔗 Enlace Google Meet]({ev['meet_url']})")
                st.divider()
        else:
            st.caption("No hay reuniones agendadas aún.")

    with tab_crm:
        if estado_bd["contactos"]:
            for c in estado_bd["contactos"]:
                st.markdown(f"**{c['full_name']}** ({c['company_name']})")
                st.caption(f"📧 `{c['email']}`")
                st.caption(f"Etapa: **{c['pipeline_stage']}**")
                st.caption(f"Interés: *{c['project_interest']}*")
                st.divider()
        else:
            st.caption("No hay contactos en CRM aún.")


# ==========================================
# CUERPO PRINCIPAL DE LA APLICACIÓN
# ==========================================
st.markdown('<div class="main-title">UTP Assistant — Hub de Operaciones y HITL</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Automatización inteligente de correos corporativos con Function Calling '
    '(Jira, Google Calendar y CRM) y Aprobación Human-in-the-Loop.</div>',
    unsafe_allow_html=True
)

col_izq, col_der = st.columns([1, 1], gap="large")

# ==========================================
# COLUMNA IZQUIERDA: BANDEJA DE CORREOS
# ==========================================
with col_izq:
    st.markdown("### 📥 Bandeja de Entrada Corporativa")
    
    opcion_correo = st.selectbox(
        "Cargar correo de ejemplo:",
        options=list(CORREOS_PREDEFINIDOS.keys()),
        index=0
    )
    datos_correo = CORREOS_PREDEFINIDOS[opcion_correo]

    with st.form("form_correo"):
        st.markdown("**Detalles del Mensaje a Procesar:**")
        remitente_input = st.text_input("Remitente (Email):", value=datos_correo["remitente"])
        asunto_input = st.text_input("Asunto:", value=datos_correo["asunto"])
        archivo_input = st.text_input("Archivo Adjunto:", value=datos_correo["archivo"])
        cuerpo_input = st.text_area("Cuerpo del Correo:", value=datos_correo["cuerpo"], height=200)

        boton_procesar = st.form_submit_button(
            "⚡ Procesar con UTP Assistant",
            use_container_width=True,
            type="primary"
        )

    if boton_procesar:
        with st.spinner("🤖 UTP Assistant ejecutando ciclo del Run y Function Calling..."):
            # Inicializar orquestador
            manager = UTPAssistantManager(
                api_key=st.session_state.gemini_api_key,
                model_name=st.session_state.gemini_model
            )
            resultado = manager.procesar_correo(
                remitente=remitente_input,
                asunto=asunto_input,
                cuerpo=cuerpo_input,
                archivo_nombre=archivo_input
            )
            st.session_state.ultimo_resultado = resultado
            st.session_state.pm_aprobado_calendar = False
            st.session_state.pm_aprobado_jira = False
            st.toast("¡Correo procesado con éxito!", icon="✅")
            st.rerun()


# ==========================================
# COLUMNA DERECHA: ORQUESTACIÓN Y CONTROL HITL
# ==========================================
with col_der:
    st.markdown("### ⚙️ Orquestación del Run y Control Human-in-the-Loop")

    resultado = st.session_state.ultimo_resultado

    if resultado is None:
        st.info("👈 Selecciona un correo y pulsa **'⚡ Procesar con UTP Assistant'** para iniciar el flujo de Function Calling.")
    else:
        # 1. MONITOR DE ESTADOS DEL RUN
        st.markdown("#### 1. Ciclo de Vida del Run")
        estados_cols = st.columns(4)
        nombres_estados = ["queued", "in_progress", "requires_action", "completed"]
        
        for idx, est_nombre in enumerate(nombres_estados):
            activo = est_nombre in resultado.get("lifecycle_states", [])
            with estados_cols[idx]:
                if activo:
                    st.markdown(f'<span class="status-pill pill-{est_nombre}">● {est_nombre}</span>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<span class="status-pill pill-queued" style="opacity:0.4;">○ {est_nombre}</span>', unsafe_allow_html=True)

        st.caption(f"⏱️ **Ejecutado a las:** {resultado.get('timestamp')} | **Modo:** `{resultado.get('mode')}`")

        # 2. HERRAMIENTAS INVOCADAS (FUNCTION CALLING)
        st.markdown("#### 2. Herramientas Detectadas y Argumentos JSON")
        tool_outputs = resultado.get("tool_outputs", [])

        if tool_outputs:
            for item in tool_outputs:
                nombre = item["tool_name"]
                args = item["arguments"]
                output = item["output"]

                with st.expander(f"🔧 `{nombre}` — Resultado: {output.get('status', 'ok')}", expanded=True):
                    col_arg, col_out = st.columns(2)
                    with col_arg:
                        st.markdown("**Argumentos enviados:**")
                        st.json(args)
                    with col_out:
                        st.markdown("**Respuesta del Servicio:**")
                        st.json(output)
        else:
            st.warning("No se registraron llamadas a herramientas en este ciclo.")

        # 3. COMPONENTE HUMAN-IN-THE-LOOP (HITL)
        st.markdown("#### 3. Human-in-the-Loop (HITL) — Revisión y Aprobación del PM")
        
        # Encontrar datos de Jira y Calendar en los outputs
        ticket_info = next((t["output"] for t in tool_outputs if t["tool_name"] == "crear_ticket_en_jira"), None)
        calendar_info = next((t["output"] for t in tool_outputs if t["tool_name"] == "agendar_reunion_en_google_calendar"), None)

        st.markdown("""
        <div class="hitl-container">
            <strong>⚠️ Validación Requerida por el Project Manager:</strong><br>
            Antes de confirmar la sesión de arquitectura con el cliente y pasar el ticket al sprint activo, 
            el PM debe revisar los parámetros generados y autorizar el despacho.
        </div>
        """, unsafe_allow_html=True)

        col_hitl_cal, col_hitl_jira = st.columns(2)

        with col_hitl_cal:
            if calendar_info:
                event_id = calendar_info.get("event_id")
                st.markdown(f"**Reunión:** `{event_id}`")
                st.caption(f"Horario: {calendar_info.get('start_time')} a {calendar_info.get('end_time')}")
                
                if st.session_state.pm_aprobado_calendar:
                    st.success("✅ Reunión Confirmada en Calendar")
                else:
                    if st.button("🤝 Confirmar Reunión en Calendar", key="btn_confirm_cal", use_container_width=True):
                        confirmar_reunion_calendar(event_id)
                        st.session_state.pm_aprobado_calendar = True
                        st.toast("Reunión confirmada oficialmente en Google Calendar", icon="📅")
                        st.rerun()

        with col_hitl_jira:
            if ticket_info:
                ticket_id = ticket_info.get("ticket_id")
                st.markdown(f"**Ticket:** `{ticket_id}`")
                st.caption(f"Tipo: {ticket_info.get('issue_type')} | Prioridad: {ticket_info.get('priority')}")
                
                if st.session_state.pm_aprobado_jira:
                    st.success("✅ Ticket Aprobado para Sprint Activo")
                else:
                    if st.button("🚀 Aprobar Ticket Jira para Sprint", key="btn_approve_jira", use_container_width=True):
                        aprobar_ticket_jira(ticket_id)
                        st.session_state.pm_aprobado_jira = True
                        st.toast("Ticket aprobado y pasado a desarrollo en Jira", icon="🎫")
                        st.rerun()

        # 4. NOTIFICACIÓN EJECUTIVA FINAL
        st.markdown("#### 4. Resumen Ejecutivo Interno (Generado por Asistente)")
        mensaje_final = resultado.get("assistant_message", "")
        st.info(mensaje_final)
