"""
app.py
======
Interfaz interactiva y amigable en Streamlit para UTP Assistant:
- Google Gemini API (gemini-2.0-flash) con carga obligatoria desde .env.
- Function Calling automatizado para Jira, Google Calendar y CRM.
- Conexiones reales a Atlassian Jira Cloud y Google Calendar v3 con fallback resiliente.
- CRM en modo simulado en memoria (por diseño).
- Flujo Human-in-the-Loop (HITL) para autorización del Project Manager.
- Guía interactiva de obtención de credenciales y APIs.
"""

import streamlit as st
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno obligatoriamente desde .env
load_dotenv(override=True)

from assistant_core import UTPAssistantManager
from services import (
    db,
    obtener_estado_bd,
    reiniciar_bd,
    confirmar_reunion_calendar,
    aprobar_ticket_jira,
    obtener_diagnostico_conexiones
)

# ==========================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="UTP Assistant — PM & Sales Ops Copilot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# ESTILOS CSS MODERNOS Y HUMAN-FRIENDLY
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.1) 0%, rgba(124, 58, 237, 0.08) 100%);
        border: 1px solid rgba(124, 58, 237, 0.25);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.3rem;
    }
    
    .subtitle {
        color: #94A3B8;
        font-size: 1.02rem;
        line-height: 1.5;
        margin: 0;
    }
    
    .badge-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 8px;
    }
    
    .badge-active {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .badge-sim {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    
    .badge-info {
        background: rgba(59, 130, 246, 0.15);
        color: #93C5FD;
        border: 1px solid rgba(59, 130, 246, 0.3);
    }

    .service-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .service-card:hover {
        border-color: #38BDF8;
        transform: translateY(-2px);
    }
    
    .hitl-alert {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(217, 119, 6, 0.08) 100%);
        border-left: 5px solid #F59E0B;
        border-radius: 0 12px 12px 0;
        padding: 1.2rem 1.4rem;
        margin: 1.2rem 0;
    }

    .status-pill {
        display: inline-block;
        padding: 0.3rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .pill-queued { background-color: #334155; color: #CBD5E1; }
    .pill-in_progress { background-color: #1E3A8A; color: #93C5FD; }
    .pill-requires_action { background-color: #854D0E; color: #FDE047; }
    .pill-completed { background-color: #065F46; color: #6EE7B7; }
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

if "gemini_model" not in st.session_state:
    st.session_state.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


# ==========================================
# CASOS DE CORREO PREDEFINIDOS
# ==========================================
CORREOS_PREDEFINIDOS = {
    "⭐ Caso 1 (Oficial): Ana Torres (TechCorp — Módulo de Pagos)": {
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
    "💼 Caso 2: Carlos Vega (RetailPro — Migración Cloud & DB)": {
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
            "Carlos Vega — CTO RetailPro"
        )
    },
    "🚨 Caso 3: Lucía Morales (FintechBank — Incidencia Crítica Webhooks)": {
        "remitente": "lmorales@fintechbank.io",
        "asunto": "URGENTE: Incompatibilidad de Webhooks en Pasarela",
        "archivo": "error_logs_500.txt",
        "cuerpo": (
            "Estimado soporte de UTPConsult,\n\n"
            "Detectamos que los webhooks de confirmación están arrojando timeout en ambiente staging. "
            "Solicitamos abrir un ticket de máxima prioridad (Bug) para que el equipo dev lo revise "
            "y una sesión técnica de emergencia para revisar los logs adjuntos.\n\n"
            "Atentamente,\n"
            "Lucía Morales — Operaciones FintechBank"
        )
    }
}


# ==========================================
# BARRA LATERAL (DIAGNÓSTICO Y BASES DE DATOS)
# ==========================================
with st.sidebar:
    st.markdown("### 🔌 Estado de Conexiones")
    
    # Recargar .env en caliente si el usuario lo editó
    if st.button("🔄 Recargar Variables de .env", use_container_width=True, help="Vuelve a leer el archivo .env sin reiniciar el servidor"):
        load_dotenv(override=True)
        st.toast("Variables de entorno recargadas desde .env", icon="🔄")
        st.rerun()

    diag = obtener_diagnostico_conexiones()

    # 1. Gemini Card
    gemini_badge = "badge-active" if diag["gemini"]["activo"] else "badge-sim"
    gemini_icon = "🟢" if diag["gemini"]["activo"] else "🟡"
    st.markdown(f"""
    <div class="service-card">
        <div style="font-weight:700; font-size:0.95rem; margin-bottom:4px;">
            🤖 Google Gemini
            <span class="badge-status {gemini_badge}" style="float:right;">{gemini_icon} {diag['gemini']['tipo']}</span>
        </div>
        <div style="font-size:0.8rem; color:#94A3B8;">{diag['gemini']['detalle']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Selector de modelo de Gemini
    modelo_elegido = st.selectbox(
        "Modelo de Gemini en uso:",
        options=["gemini-3.6-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        index=0,
        help="El modelo se ejecutará usando la clave GEMINI_API_KEY configurada en tu .env"
    )
    st.session_state.gemini_model = modelo_elegido

    # 2. Jira Card
    jira_badge = "badge-active" if diag["jira"]["activo"] else "badge-sim"
    jira_icon = "🟢" if diag["jira"]["activo"] else "🟡"
    st.markdown(f"""
    <div class="service-card">
        <div style="font-weight:700; font-size:0.95rem; margin-bottom:4px;">
            🎫 Atlassian Jira
            <span class="badge-status {jira_badge}" style="float:right;">{jira_icon} {diag['jira']['tipo']}</span>
        </div>
        <div style="font-size:0.8rem; color:#94A3B8;">{diag['jira']['detalle']}</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. Calendar Card
    cal_badge = "badge-active" if diag["calendar"]["activo"] else "badge-sim"
    cal_icon = "🟢" if diag["calendar"]["activo"] else "🟡"
    st.markdown(f"""
    <div class="service-card">
        <div style="font-weight:700; font-size:0.95rem; margin-bottom:4px;">
            📅 Google Calendar
            <span class="badge-status {cal_badge}" style="float:right;">{cal_icon} {diag['calendar']['tipo']}</span>
        </div>
        <div style="font-size:0.8rem; color:#94A3B8;">{diag['calendar']['detalle']}</div>
    </div>
    """, unsafe_allow_html=True)

    # 4. CRM Card
    st.markdown(f"""
    <div class="service-card">
        <div style="font-weight:700; font-size:0.95rem; margin-bottom:4px;">
            👥 CRM Corporativo
            <span class="badge-status badge-info" style="float:right;">🔵 {diag['crm']['tipo']}</span>
        </div>
        <div style="font-size:0.8rem; color:#94A3B8;">{diag['crm']['detalle']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🗄️ Monitor de Registros en Vivo")
    
    estado_bd = obtener_estado_bd()
    m1, m2, m3 = st.columns(3)
    m1.metric("Jira", estado_bd["total_tickets_jira"])
    m2.metric("Calendar", estado_bd["total_eventos_calendar"])
    m3.metric("CRM", estado_bd["total_contactos_crm"])

    if st.button("🗑️ Reiniciar Almacén de Datos", use_container_width=True, help="Limpia los registros simulados en memoria"):
        reiniciar_bd()
        st.session_state.ultimo_resultado = None
        st.session_state.pm_aprobado_calendar = False
        st.session_state.pm_aprobado_jira = False
        st.toast("Base de datos en memoria reiniciada", icon="🧹")
        st.rerun()


# ==========================================
# ENCABEZADO PRINCIPAL
# ==========================================
st.markdown("""
<div class="main-header">
    <div class="main-title">🤖 UTP Assistant — PM & Sales Ops Hub</div>
    <p class="subtitle">
        Copiloto inteligente para automatizar requerimientos de correo corporativo mediante 
        <strong>Google Gemini API (gemini-2.0-flash)</strong>, <strong>Function Calling</strong> y 
        aprobación humana <strong>Human-in-the-Loop (HITL)</strong>.
    </p>
</div>
""", unsafe_allow_html=True)

# Alerta informativa si no hay GEMINI_API_KEY en .env
if not diag["gemini"]["activo"]:
    st.warning(
        "ℹ️ **Modo Simulación Inteligente Activo:** No se detectó una clave `GEMINI_API_KEY` válida en tu archivo `.env`. "
        "El asistente ejecutará el orquestador con respuestas simuladas estructuradas. "
        "Para usar el modelo real de Gemini, coloca tu clave en el archivo `.env` (consulta la pestaña **📖 Guía de Credenciales**)."
    )

# ==========================================
# PESTAÑAS PRINCIPALES DE LA APLICACIÓN
# ==========================================
tab_operaciones, tab_monitor, tab_guia = st.tabs([
    "🚀 Procesar Solicitud PM (HITL)",
    "📊 Monitor de Bases de Datos",
    "📖 Guía de Credenciales y APIs"
])


# ==========================================
# PESTAÑA 1: PROCESAMIENTO Y HITL
# ==========================================
with tab_operaciones:
    col_izq, col_der = st.columns([1, 1], gap="large")

    # --- BANDEJA DE CORREOS ---
    with col_izq:
        st.markdown("#### 📥 Bandeja de Entrada Corporativa")
        st.caption("Selecciona un correo empresarial de prueba o redacta una solicitud técnica libre.")

        opcion_correo = st.selectbox(
            "Cargar plantilla de correo:",
            options=list(CORREOS_PREDEFINIDOS.keys()),
            index=0
        )
        datos_correo = CORREOS_PREDEFINIDOS[opcion_correo]

        with st.form("form_procesamiento"):
            remitente_input = st.text_input("📧 Remitente (Email):", value=datos_correo["remitente"])
            asunto_input = st.text_input("📌 Asunto:", value=datos_correo["asunto"])
            archivo_input = st.text_input("📎 Archivo Adjunto Técnico:", value=datos_correo["archivo"])
            cuerpo_input = st.text_area("📝 Contenido del Correo:", value=datos_correo["cuerpo"], height=190)

            boton_procesar = st.form_submit_button(
                "⚡ Procesar con UTP Assistant",
                use_container_width=True,
                type="primary"
            )

        if boton_procesar:
            with st.spinner("🤖 UTP Assistant orquestando ciclo del Run y Function Calling..."):
                manager = UTPAssistantManager(model_name=st.session_state.gemini_model)
                resultado = manager.procesar_correo(
                    remitente=remitente_input,
                    asunto=asunto_input,
                    cuerpo=cuerpo_input,
                    archivo_nombre=archivo_input
                )
                st.session_state.ultimo_resultado = resultado
                st.session_state.pm_aprobado_calendar = False
                st.session_state.pm_aprobado_jira = False
                st.toast("¡Correo procesado con éxito por el Asistente!", icon="✅")
                st.rerun()

    # --- CONTROL HITL Y RUN ---
    with col_der:
        st.markdown("#### ⚙️ Orquestación del Run & Control Human-in-the-Loop")
        resultado = st.session_state.ultimo_resultado

        if resultado is None:
            st.info(
                "👈 Selecciona un caso de correo en la bandeja izquierda y haz clic en "
                "**'⚡ Procesar con UTP Assistant'** para visualizar el ciclo de vida del Run, "
                "las llamadas a herramientas y el panel HITL."
            )
        else:
            # 1. Ciclo de Vida del Run
            st.markdown("##### 1. Ciclo de Vida del Run")
            estados_cols = st.columns(4)
            nombres_estados = ["queued", "in_progress", "requires_action", "completed"]
            
            for idx, est_nombre in enumerate(nombres_estados):
                activo = est_nombre in resultado.get("lifecycle_states", [])
                with estados_cols[idx]:
                    if activo:
                        st.markdown(f'<span class="status-pill pill-{est_nombre}">● {est_nombre}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span class="status-pill pill-queued" style="opacity:0.35;">○ {est_nombre}</span>', unsafe_allow_html=True)

            st.caption(f"⏱️ **Timestamp:** {resultado.get('timestamp')} | **Modo de Ejecución:** `{resultado.get('mode')}`")

            # 2. Function Calling Detallado
            st.markdown("##### 2. Function Calling: Argumentos y Respuestas")
            tool_outputs = resultado.get("tool_outputs", [])

            if tool_outputs:
                for item in tool_outputs:
                    nombre = item["tool_name"]
                    args = item["arguments"]
                    output = item["output"]
                    modo_conn = output.get("conexion", "Ejecutado")

                    with st.expander(f"🔧 `{nombre}` — {output.get('status', 'ok').upper()} ({output.get('modo', 'ok')})", expanded=True):
                        st.caption(f"**Conexión utilizada:** `{modo_conn}`")
                        col_arg, col_out = st.columns(2)
                        with col_arg:
                            st.markdown("**Argumentos JSON generados:**")
                            st.json(args)
                        with col_out:
                            st.markdown("**Respuesta del Servicio:**")
                            st.json(output)
            else:
                st.warning("No se detectaron llamadas a herramientas en este ciclo.")

            # 3. Flujo Human-in-the-Loop (HITL)
            st.markdown("##### 3. Human-in-the-Loop (HITL) — Aprobación Requerida del PM")
            st.markdown("""
            <div class="hitl-alert">
                <strong>🛡️ Punto de Control Human-in-the-Loop:</strong><br>
                El Asistente ha extraído y preparado la reunión técnica y el ticket de desarrollo.
                Como <strong>Project Manager</strong>, debes validar y autorizar formalmente cada acción.
            </div>
            """, unsafe_allow_html=True)

            ticket_info = next((t["output"] for t in tool_outputs if t["tool_name"] == "crear_ticket_en_jira"), None)
            calendar_info = next((t["output"] for t in tool_outputs if t["tool_name"] == "agendar_reunion_en_google_calendar"), None)

            col_hitl_cal, col_hitl_jira = st.columns(2)

            with col_hitl_cal:
                if calendar_info:
                    st.markdown(f"**📅 Reunión:** `{calendar_info.get('event_id')}`")
                    st.caption(f"Horario: {calendar_info.get('start_time')} a {calendar_info.get('end_time')}")
                    if calendar_info.get("meet_url"):
                        st.markdown(f"[🔗 Abrir Google Meet]({calendar_info.get('meet_url')})")

                    if st.session_state.pm_aprobado_calendar:
                        st.success("✅ Reunión Confirmada por el PM")
                    else:
                        if st.button("🤝 Confirmar Reunión en Calendar", key="btn_confirm_cal", use_container_width=True):
                            confirmar_reunion_calendar(calendar_info.get("event_id"))
                            st.session_state.pm_aprobado_calendar = True
                            st.toast("Reunión autorizada y confirmada en Calendar", icon="📅")
                            st.rerun()

            with col_hitl_jira:
                if ticket_info:
                    st.markdown(f"**🎫 Ticket:** `{ticket_info.get('ticket_id')}`")
                    st.caption(f"Tipo: {ticket_info.get('issue_type')} | Prioridad: {ticket_info.get('priority')}")
                    if ticket_info.get("issue_url"):
                        st.markdown(f"[🔗 Ver Ticket en Jira]({ticket_info.get('issue_url')})")

                    if st.session_state.pm_aprobado_jira:
                        st.success("✅ Ticket Aprobado para Sprint Activo")
                    else:
                        if st.button("🚀 Aprobar Ticket para Sprint", key="btn_approve_jira", use_container_width=True):
                            aprobar_ticket_jira(ticket_info.get("ticket_id"))
                            st.session_state.pm_aprobado_jira = True
                            st.toast("Ticket aprobado y pasado al sprint activo", icon="🎫")
                            st.rerun()

            # 4. Resumen Ejecutivo Final
            st.markdown("##### 4. Notificación Ejecutiva Interna (Generada por Gemini)")
            mensaje_final = resultado.get("assistant_message", "")
            st.info(mensaje_final)


# ==========================================
# PESTAÑA 2: MONITOR DE BASES DE DATOS
# ==========================================
with tab_monitor:
    st.markdown("### 📊 Estado y Contenido de los Servicios")
    st.caption("Inspecciona los tickets creados en Jira, reuniones en Calendar y prospectos en CRM.")

    col_t1, col_t2, col_t3 = st.tabs(["🎫 Tickets en Jira", "📅 Eventos en Calendar", "👥 Contactos en CRM"])

    with col_t1:
        if estado_bd["tickets"]:
            for t in estado_bd["tickets"]:
                es_real = t.get("is_real", False)
                badge_real = "🟢 Jira Cloud Real" if es_real else "🟡 Simulación Fallback"
                badge_pm = "🟢 Aprobado PM" if t.get("aprobado_pm") else "🟡 Pendiente PM"
                
                with st.expander(f"[{t['id']}] {t['summary']} — {badge_pm}", expanded=True):
                    st.markdown(f"**Origen:** `{badge_real}` | **Tipo:** `{t['issue_type']}` | **Prioridad:** `{t['priority']}`")
                    st.markdown(f"**Descripción:**\n{t['description']}")
                    st.markdown(f"**Enlace oficial:** [{t['url']}]({t['url']})")
                    if not es_real and t.get("motivo_simulacion"):
                        st.caption(f"Motivo simulación: {t['motivo_simulacion']}")
        else:
            st.info("Aún no se han registrado tickets de Jira.")

    with col_t2:
        if estado_bd["eventos"]:
            for ev in estado_bd["eventos"]:
                es_real = ev.get("is_real", False)
                status_icon = "🟢 Confirmada" if ev["status"] == "confirmed" else "🟠 Tentativa (HITL)"
                badge_real = "🟢 Google Calendar API Real" if es_real else "🟡 Simulación Fallback"
                
                with st.expander(f"{ev['summary']} — {status_icon}", expanded=True):
                    st.markdown(f"**Origen:** `{badge_real}`")
                    st.markdown(f"**Inicio:** `{ev['start_time']}` | **Fin:** `{ev['end_time']}`")
                    st.markdown(f"**Participantes:** {', '.join(ev.get('attendees', []))}")
                    st.markdown(f"**Agenda:**\n{ev.get('agenda')}")
                    st.markdown(f"**Google Meet:** [{ev['meet_url']}]({ev['meet_url']})")
                    if ev.get("calendar_url"):
                        st.markdown(f"**Ver en Calendar:** [Abrir Evento]({ev['calendar_url']})")
                    if not es_real and ev.get("motivo_simulacion"):
                        st.caption(f"Motivo simulación: {ev['motivo_simulacion']}")
        else:
            st.info("Aún no se han programado reuniones en Google Calendar.")

    with col_t3:
        if estado_bd["contactos"]:
            for c in estado_bd["contactos"]:
                with st.expander(f"👤 {c['full_name']} — {c['company_name']} ({c['pipeline_stage']})", expanded=True):
                    st.markdown(f"**ID:** `{c['id']}` | **Email:** `{c['email']}`")
                    st.markdown(f"**Etapa Comercial:** `{c['pipeline_stage']}`")
                    st.markdown(f"**Interés Técnico:** {c['project_interest']}")
                    st.caption("Modo: Simulado en Memoria (Por diseño)")
        else:
            st.info("Aún no se han registrado contactos en el CRM.")


# ==========================================
# PESTAÑA 3: GUÍA DE CREDENCIALES Y APIS
# ==========================================
with tab_guia:
    st.markdown("### 📖 Guía Paso a Paso para Obtención de Credenciales y APIs")
    st.markdown(
        "UTP Assistant implementa una arquitectura híbrida resiliente: si configuras las claves en `.env`, "
        "se conectará a las APIs oficiales; si alguna falta, operará automáticamente en modo simulación estructurada."
    )

    with st.expander("1. 🤖 Google Gemini API (Obligatorio en .env para llamadas reales de IA)", expanded=True):
        st.markdown("""
        **Pasos para obtener tu clave gratuita:**
        1. Ingresa a **[Google AI Studio](https://aistudio.google.com/app/apikey)** con tu cuenta Google.
        2. Haz clic en el botón azul **"Create API key"** (o "Crear clave de API").
        3. Selecciona o crea un proyecto de Google Cloud rápido.
        4. Copia la clave generada (empieza habitualmente con `AIzaSy...`).
        5. Abre el archivo `.env` en la raíz del proyecto y reemplaza:
           ```ini
           GEMINI_API_KEY=AIzaSyTuClaveRealAqui
           GEMINI_MODEL=gemini-2.0-flash
           ```
        6. En la barra lateral de esta aplicación, pulsa **"🔄 Recargar Variables de .env"**.
        """)

    with st.expander("2. 🎫 Atlassian Jira Cloud API (Para creación real de tickets)", expanded=True):
        st.markdown("""
        **Pasos para conectar Jira Cloud:**
        1. **Cuenta e Instancia Jira:** Si no tienes una, crea una cuenta gratuita en [Atlassian Jira](https://www.atlassian.com/software/jira).
        2. **URL de tu Instancia:** Identifica la URL de tu espacio, por ejemplo `https://tu-organizacion.atlassian.net`.
        3. **Crear Proyecto:** En Jira, crea un proyecto Scrum o Kanban con la clave `PAYMOD` (o la que elijas, ej. `UTP`).
        4. **Generar API Token de Atlassian:**
           - Entra a **[Atlassian Security API Tokens](https://id.atlassian.com/manage-profile/security/api-tokens)**.
           - Haz clic en **"Crear token de API"** (Create API token).
           - Ponle una etiqueta (ej. `UTP-Assistant-Token`) y copia el token generado.
        5. **Configurar en `.env`:**
           ```ini
           JIRA_URL=https://tu-organizacion.atlassian.net
           JIRA_EMAIL=tu_correo_de_atlassian@ejemplo.com
           JIRA_API_TOKEN=tu_api_token_de_atlassian_aqui
           JIRA_PROJECT_KEY=PAYMOD
           ```
        6. Pulsa **"🔄 Recargar Variables de .env"** en la barra lateral.
        """)

    with st.expander("3. 📅 Google Calendar API v3 (Para agendar reuniones reales)", expanded=True):
        st.markdown("""
        **Pasos para obtener la Cuenta de Servicio (Service Account):**
        1. Entra a **[Google Cloud Console](https://console.cloud.google.com/)**.
        2. Ve a **"APIs y Servicios"** ➔ **"Biblioteca"**, busca **"Google Calendar API"** y haz clic en **"Habilitar"**.
        3. Ve a **"Credenciales"** ➔ **"Crear credenciales"** ➔ **"Cuenta de servicio"** (dale nombre `calendar-bot`).
        4. Haz clic en la cuenta creada ➔ pestaña **"Claves"** ➔ **"Agregar clave"** ➔ **"Crear clave nueva"** (JSON).
        5. **Paso crítico:** Copia el correo de la cuenta (`calendar-bot@tu-proyecto.iam.gserviceaccount.com`), abre **[Google Calendar](https://calendar.google.com/)**, en tu calendario ve a **"Configuración y uso compartido"** ➔ **"Compartir con personas específicas"**, agrega ese correo y dale permiso **"Realizar cambios en eventos"**.

        ---

        #### 🚀 Opción 2: Base64 en `.env` (Recomendado):
        Convierte tu archivo descargado a Base64 y pégalo en una sola línea en `.env`:
        - **En Windows (PowerShell):**
          ```powershell
          [Convert]::ToBase64String([IO.File]::ReadAllBytes("service_account.json")) | Set-Clipboard
          ```
        - **En tu `.env`:**
          ```ini
          GOOGLE_CALENDAR_ID=primary
          GOOGLE_SERVICE_ACCOUNT_B64="eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIs..."
          ```

        #### 📁 Opción 1: Ruta de archivo (Alternativa):
        ```ini
        GOOGLE_CALENDAR_ID=primary
        GOOGLE_APPLICATION_CREDENTIALS=service_account.json
        ```
        """)

    with st.expander("4. 👥 CRM Corporativo (Simulación en Memoria)", expanded=False):
        st.markdown("""
        Por requerimiento explícito del proyecto, el CRM opera **exclusivamente de manera simulada en memoria**:
        - Registra el prospecto comercial con nombre, empresa, correo, etapa del pipeline (*'Reunión Técnica'*) e interés del proyecto.
        - Se almacena en la estructura en memoria singleton `db.crm_contacts` para consulta inmediata en el panel.
        - No requiere credenciales externas ni configuraciones de red.
        """)
