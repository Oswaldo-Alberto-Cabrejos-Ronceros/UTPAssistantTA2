"""
app.py
======
Interfaz interactiva y amigable en Streamlit para UTP Assistant.
Asistente inteligente de correos.
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
    aprobar_ticket_jira
)

# ==========================================
# CONFIGURACIÓN DE PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="UTP Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# ESTILOS CSS MODERNOS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(124, 58, 237, 0.06) 100%);
        border: 1px solid rgba(124, 58, 237, 0.2);
        border-radius: 14px;
        padding: 1.2rem 1.8rem;
        margin-bottom: 1.5rem;
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
        color: #94A3B8;
        font-size: 1rem;
        margin: 0;
    }
    
    .hitl-alert {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(217, 119, 6, 0.08) 100%);
        border-left: 5px solid #F59E0B;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def formatear_rango_fechas(inicio_iso: str, fin_iso: str) -> str:
    """Convierte cadenas ISO-8601 a un formato en español amigable y legible."""
    try:
        dt_ini = datetime.fromisoformat(inicio_iso.replace("Z", "+00:00"))
        dt_fin = datetime.fromisoformat(fin_iso.replace("Z", "+00:00"))
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        
        dia_nom = dias[dt_ini.weekday()]
        mes_nom = meses[dt_ini.month - 1]
        
        hora_ini = dt_ini.strftime("%H:%M")
        hora_fin = dt_fin.strftime("%H:%M")
        
        return f"{dia_nom} {dt_ini.day} de {mes_nom}, {dt_ini.year} de {hora_ini} a {hora_fin} UTC"
    except Exception:
        return f"{inicio_iso} a {fin_iso}"


# ==========================================
# INICIALIZACIÓN DE ESTADO DE SESIÓN
# ==========================================
if "ultimo_resultado" not in st.session_state:
    st.session_state.ultimo_resultado = None

if "pm_aprobado_calendar" not in st.session_state:
    st.session_state.pm_aprobado_calendar = False

if "pm_aprobado_jira" not in st.session_state:
    st.session_state.pm_aprobado_jira = False


# ==========================================
# CASOS DE CORREO PREDEFINIDOS
# ==========================================
CORREOS_PREDEFINIDOS = {
    "⭐ Caso 1: Ana Torres (TechCorp — Módulo de Pagos)": {
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
# ENCABEZADO PRINCIPAL
# ==========================================
st.markdown("""
<div class="main-header">
    <div class="main-title">🤖 UTP Assistant</div>
    <p class="subtitle">Asistente inteligente de correos</p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# CUERPO PRINCIPAL: PROCESAMIENTO DIRECTO
# ==========================================
col_izq, col_der = st.columns([1, 1], gap="large")

# --- BANDEJA DE CORREOS ---
with col_izq:
    st.markdown("#### 📥 Bandeja de Entrada Corporativa")
    st.caption("Selecciona un correo empresarial de prueba o redacta una solicitud técnica.")

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
        with st.spinner("🤖 UTP Assistant procesando correo y ejecutando herramientas..."):
            manager = UTPAssistantManager()
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

# --- RESULTADOS Y APROBACIÓN ---
with col_der:
    st.markdown("#### ⚙️ Resultado del Procesamiento")
    resultado = st.session_state.ultimo_resultado

    if resultado is None:
        st.info(
            "👈 Selecciona un caso de correo en la bandeja izquierda y haz clic en "
            "**'⚡ Procesar con UTP Assistant'** para procesar la solicitud."
        )
    else:
        # 1. Herramientas Invocadas (Function Calling)
        st.markdown("##### Herramientas Detectadas y Argumentos JSON")
        tool_outputs = resultado.get("tool_outputs", [])

        if tool_outputs:
            for item in tool_outputs:
                nombre = item["tool_name"]
                args = item["arguments"]
                output = item["output"]

                with st.expander(f"🔧 `{nombre}` — {output.get('status', 'ok').upper()}", expanded=True):
                    col_arg, col_out = st.columns(2)
                    with col_arg:
                        st.markdown("**Argumentos JSON generados:**")
                        st.json(args)
                    with col_out:
                        st.markdown("**Respuesta del Servicio:**")
                        st.json(output)
        else:
            st.warning("No se detectaron llamadas a herramientas en este ciclo.")

        # 2. Aprobación
        st.markdown("##### Aprobación")
        st.markdown("""
        <div class="hitl-alert">
            <strong>🛡️ Punto de Control:</strong><br>
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
                
                # Parsear fecha de forma amigable
                fecha_amigable = formatear_rango_fechas(
                    calendar_info.get("start_time", ""),
                    calendar_info.get("end_time", "")
                )
                st.caption(f"Horario: {fecha_amigable}")

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

                if st.session_state.pm_aprobado_jira:
                    st.success("✅ Ticket Aprobado para Sprint Activo")
                else:
                    if st.button("🚀 Aprobar Ticket para Sprint", key="btn_approve_jira", use_container_width=True):
                        aprobar_ticket_jira(ticket_info.get("ticket_id"))
                        st.session_state.pm_aprobado_jira = True
                        st.toast("Ticket aprobado y pasado al sprint activo", icon="🎫")
                        st.rerun()

        # 3. Notificación Ejecutiva Interna
        st.markdown("##### Notificación Ejecutiva Interna")
        mensaje_final = resultado.get("assistant_message", "")
        # Limpiar cualquier mención residual de "HITL" si aparece en el texto generado
        mensaje_limpio = mensaje_final.replace("HITL", "Aprobación del PM").replace("panel HITL", "panel de aprobación")
        st.info(mensaje_limpio)
