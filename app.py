import json
import os
import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import google.generativeai as genai

# =========================================================
# CONFIGURACIÓN DE API KEYS DESDE secrets.toml
# =========================================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
WINDY_API_KEY = st.secrets["WINDY_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
# =========================================================
# FUNCIÓN DE IA PARA MEJORAR REDACCIÓN
# =========================================================
def mejorar_redaccion_ia(texto, tipo_texto="general"):
    """Mejora la redacción usando Gemini con instrucciones específicas para cada tipo de texto."""
    if not texto.strip():
        return "Sin información adicional registrada."

    instrucciones_base = """Eres un asistente de redacción para reportes oficiales del Cuerpo de Bomberos Forestales INPARQUES.

INSTRUCCIONES GENERALES:
- Corrige todos los errores ortográficos y gramaticales.
- Si el texto está escrito de forma informal, desordenada o "a los golpes", redáctalo de manera técnica y profesional.
- Mantén el significado original, NO agregues información que no esté en el texto original.
- El resultado debe estar en español.
- Usa terminología apropiada para reportes de emergencias y bomberiles.
- NO uses emojis en el texto mejorado.
- Respeta los rangos militares tal como aparecen (Ej: S/2 (B), C/1 (B), My (B), etc.)"""

    instrucciones_por_tipo = {
        "reseña": """
INSTRUCCIONES ESPECÍFICAS PARA RESEÑA:
- Redacta en pasado y en tercera persona.
- Estructura en un solo párrafo fluido.
- Incluye quién ordenó, qué se hizo y por qué.
- Ejemplo de tono: "Por instrucciones del Jefe de Estación, se procedió a..." """,

        "reseña de incendio": """
INSTRUCCIONES ESPECÍFICAS PARA RESEÑA DE INCENDIO:
- Redacta en pasado y en tercera persona.
- Describe cómo se detectó el incendio, quién lo reportó y qué se visualizó.
- Usa términos como "columna de humo", "foco de incendio", "propagación".
- Ejemplo de tono: "Durante recorrido por el sector se visualiza una columna de humo..." """,

        "acciones realizadas": """
INSTRUCCIONES ESPECÍFICAS PARA ACCIONES REALIZADAS:
- Mantén el formato de bitácora si tiene horas (Ej: "07:29 Hrs Se destaca comisión...").
- Usa verbos en pasado (destacó, reportó, procedió, controló).
- Cada acción debe ir en línea separada si hay múltiples eventos.
- NO combines todas las acciones en un solo párrafo.""",

        "bitácora de eventos": """
INSTRUCCIONES ESPECÍFICAS PARA BITÁCORA DE EVENTOS:
- Mantén el formato cronológico con horas si existen.
- Cada evento debe ir en línea separada.
- Usa verbos en pasado (destacó, reportó, procedió, controló).
- No elimines horas ni detalles técnicos.
- Formato: "HH:MM Hrs - Descripción de la acción" """,

        "observación": """
INSTRUCCIONES ESPECÍFICAS PARA OBSERVACIONES:
- Sé breve y directo, máximo 2-3 líneas.
- Redacta en tono formal y objetivo.
- No uses juicios de valor ni opiniones personales.
- Solo hechos concretos.""",

        "actividad": """
INSTRUCCIONES ESPECÍFICAS PARA ACTIVIDAD:
- Redacta en pasado y en tercera persona.
- Describe la actividad realizada, quién la impartió y a quién.
- Incluye el tema tratado si se menciona.
- Ejemplo: "El día de hoy se realizó sesión educativa sobre..." """,

        "nota informativa": """
INSTRUCCIONES ESPECÍFICAS PARA NOTA INFORMATIVA:
- Redacta en tono formal e institucional.
- Estructura en párrafos claros y concisos.
- Usa frases como "Se informa que...", "Se hace de conocimiento...".
- No uses lenguaje coloquial.""",

        "condiciones meteorológicas": """
INSTRUCCIONES ESPECÍFICAS PARA CONDICIONES METEOROLÓGICAS:
- Describe el clima de forma técnica y precisa.
- Usa términos como "precipitaciones", "nubosidad", "vientos".
- Incluye ubicación geográfica si se menciona.
- Formato: "Cielo despejado en el Sector..., Parroquia..., Municipio..., Estado..." """,

        "motivo de unidad": """
INSTRUCCIONES ESPECÍFICAS PARA MOTIVO DE UNIDAD:
- Redacta en pasado y en tercera persona.
- Incluye quién reporta, qué reporta y desde dónde.
- Usa formato: "Reporta [rango y nombre] que se encuentran en el lugar antes mencionado..."
- Sé breve y directo.""",

        "general": """
INSTRUCCIONES ESPECÍFICAS:
- Redacta de manera profesional y clara.
- Corrige errores manteniendo el significado original."""
    }

    instrucciones_especificas = instrucciones_por_tipo.get(tipo_texto, instrucciones_por_tipo["general"])

    prompt = f"""{instrucciones_base}

{instrucciones_especificas}

TIPO DE TEXTO: {tipo_texto}

TEXTO ORIGINAL:
{texto}

TEXTO MEJORADO:"""

    try:
        model = genai.GenerativeModel("gemini-3.6-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.warning(f"⚠️ No se pudo usar IA: {e}")
        texto_limpio = texto.strip().capitalize()
        if not texto_limpio.endswith('.'):
            texto_limpio += '.'
        return texto_limpio

# =========================================================
# CONFIGURACIÓN GENERAL Y CONSTANTES
# =========================================================
EXCEL_SERVICIOS = "servicios.xlsx"
EXCEL_INCENDIOS = "incendios.xlsx"
ARCHIVO_SERVICIOS = "servicios_disponibles.json"
ARCHIVO_ORGANISMOS = "organismos_disponibles.json"
ARCHIVO_CAUSAS = "causas_disponibles.json"
ARCHIVO_ACUMULADOS_DIA = "servicios_acumulados.json"

def registrar_servicio_dia(objeto_servicio):
    """Guarda una estructura completa del servicio para los partes matutino/vespertino."""
    lista = []
    if os.path.exists(ARCHIVO_ACUMULADOS_DIA):
        try:
            with open(ARCHIVO_ACUMULADOS_DIA, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except:
            lista = []
    lista.append(objeto_servicio)
    with open(ARCHIVO_ACUMULADOS_DIA, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

def consumir_y_limpiar_servicios():
    """Extrae los servicios formateados con la estructura exacta solicitada y vacía el registro."""
    if not os.path.exists(ARCHIVO_ACUMULADOS_DIA):
        return "00 (Sin servicios registrados en este periodo)"
    try:
        with open(ARCHIVO_ACUMULADOS_DIA, "r", encoding="utf-8") as f:
            lista = json.load(f)
    except:
        lista = []
    
    with open(ARCHIVO_ACUMULADOS_DIA, "w", encoding="utf-8") as f:
        json.dump([], f)
        
    if not lista:
        return "00 (Sin servicios registrados en este periodo)"
    
    bloques_resumen = []
    for idx, srv in enumerate(lista, 1):
        texto = (
            f"Servicio {idx:02d}\n\n"
            f" *TIPO DE SERVICIO:* \n"
            f"{srv.get('tipo_servicio', 'N/A')}\n\n"
            f"*NÚMERO DE SERVICIO:*\n"
            f"{srv.get('num_servicio', 'N/A')}\n\n"
            f"*UBICACIÓN:*\n"
            f"{srv.get('ubicacion', 'N/A')}\n\n"
            f"*RESEÑA:* {srv.get('resena', 'Sin reseña')}\n\n"
            f"*COORDENADAS:*\n"
            f"{srv.get('coordenadas', 'N/A')}\n\n"
            f"*ESTATUS:*  {srv.get('estatus', 'N/A')}"
        )
        bloques_resumen.append(texto)
        
    return "\n\n".join(bloques_resumen)

def cargar_servicios_persistencia():
    default_servicios = [
        "INSPECCIÓN / EVALUACIÓN DE RIESGO",
        "ATENCIÓN PREHOSPITALARIA",
        "APOYO INSTITUCIONAL",
        "RESCATE",
        "GUARDIA DE PREVENCIÓN"
    ]
    if os.path.exists(ARCHIVO_SERVICIOS):
        try:
            with open(ARCHIVO_SERVICIOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_servicios

def guardar_servicios_persistencia(lista):
    try:
        with open(ARCHIVO_SERVICIOS, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)
    except:
        pass

def cargar_organismos_persistencia():
    default_orgs = [
        "BFI", "CCGP", "PC (Protección Civil)", "GNB", 
        "CPNB", "POLICARABOBO", "CPE (Cuerpos de Policías Estadales)", 
        "CPM (Cuerpos de Policías Municipales)", 
        "CICPC", "BOMBEROS", "BOMBEROS UC (Cuerpo de Bomberos Universidad de Carabobo)",
        "SEBIN", "DGCIM", "FANB", "Milicia Bolivariana", "INTT", "CRUZ ROJA", "OTRO"
    ]
    if os.path.exists(ARCHIVO_ORGANISMOS):
        try:
            with open(ARCHIVO_ORGANISMOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_orgs

def guardar_organismos_persistencia(lista):
    try:
        with open(ARCHIVO_ORGANISMOS, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)
    except:
        pass

def cargar_causas_persistencia():
    default_causas = ["Vandalismo", "Quema de desechos", "Quema agrícola", "Accidental", "Indeterminada", "Otro"]
    if os.path.exists(ARCHIVO_CAUSAS):
        try:
            with open(ARCHIVO_CAUSAS, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_causas

def guardar_causas_persistencia(lista):
    try:
        with open(ARCHIVO_CAUSAS, "w", encoding="utf-8") as f:
            json.dump(lista, f, ensure_ascii=False, indent=4)
    except:
        pass

# =========================================================
# ESTILO CSS MEJORADO PARA LOS BOTONES
# =========================================================
st.markdown("""
<style>
    div.stButton > button {
        background: linear-gradient(135deg, #1e7e34, #28a745) !important;
        color: #ffffff !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        letter-spacing: 1px !important;
        padding: 16px 30px !important;
        border-radius: 12px !important;
        border: 2px solid #28a745 !important;
        box-shadow: 0 0 15px rgba(40, 167, 69, 0.4) !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.3s ease-in-out !important;
    }

    div.stButton > button:hover {
        background: linear-gradient(135deg, #155724, #1e7e34) !important;
        box-shadow: 0 0 25px rgba(40, 167, 69, 0.8) !important;
        border-color: #ffffff !important;
        transform: scale(1.01) !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# MENÚ LATERAL (NAVEGACIÓN)
# =========================================================
st.sidebar.title("🚒 Bomberos Forestales")
st.sidebar.markdown("---")

opcion_modulo = st.sidebar.radio(
    "Seleccione el Módulo:",
    [
        "RESUMEN MATUTINO",
        "RESUMEN VESPERTINO",
        "REPORTES DE SERVICIOS",
        "REPORTES DE INCENDIOS", 
        "REPORTES MIXTOS"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info("Sistema de Gestión e Informes Operativos")

# =========================================================
# MÓDULO 1: RESUMEN MATUTINO (PARTE GENERAL)
# =========================================================
if opcion_modulo == "RESUMEN MATUTINO":
    st.header("🌅 Resumen Matutino (Parte General)")

    st.subheader("📌 Datos del Encabezado")
    col1, col2 = st.columns(2)
    with col1:
        coord_estadal = st.text_input("Coordinador Forestal Estadal", "My (B) Mendoza Luis")
        jefe_estacion = st.text_input("Jefe de Estación", "S/2 (B) Meléndez Alberlen")
        jefe_seccion = st.text_input("Jefe de Sección / Auxiliar", "C/2 (B) Berroteran Luis")
        fecha_mat = st.date_input("Fecha", datetime.now(), key="f_mat")
    with col2:
        parte_num = st.text_input("Parte N°", "240-2026")
        seccion_guardia = st.text_input("Sección de Guardia", 'C')
        pie_fuerza = st.number_input("Pie de Fuerza Total", min_value=1, value=49, step=1)
        analista_mat = st.text_input("Analista de Guardia", "", key="a_mat")

    st.subheader("👥 Desglose de Personal")
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        p_guardia = st.number_input("Personal de Guardia", min_value=0, value=6)
        p_retardado = st.number_input("Personal Retardado", min_value=0, value=0)
        p_libre = st.number_input("Personal Libre", min_value=0, value=26)
    with c_p2:
        p_permiso = st.number_input("Personal Permiso", min_value=0, value=0)
        p_reposo = st.number_input("Personal de Reposo", min_value=0, value=4)
        p_ausente = st.number_input("Personal Ausente", min_value=0, value=0)
    with c_p3:
        p_vacaciones = st.number_input("Personal de Vacaciones", min_value=0, value=2)
        p_comision = st.number_input("Personal de Comisión", min_value=0, value=5)
        p_pasantes = st.number_input("Personal Pasante", min_value=0, value=6)

    st.subheader("📝 Observaciones")
    cant_obs_mat = st.number_input("Cantidad de Observaciones", min_value=0, value=0, step=1, key="num_obs_mat")
    
    lista_textos_observaciones_mat = []
    if cant_obs_mat > 0:
        for i in range(int(cant_obs_mat)):
            obs_texto = st.text_area(f"Redacte la Observación {i+1}", key=f"obs_input_mat_{i}", height=70)
            
            # === IA === Botón para mejorar cada observación
            col_obs_btn1, col_obs_btn2 = st.columns([3, 1])
            with col_obs_btn2:
                if st.button(f"✨ IA Obs {i+1}", key=f"btn_ia_obs_mat_{i}"):
                    if obs_texto.strip():
                        with st.spinner("🤖 Mejorando..."):
                            obs_mejorada = mejorar_redaccion_ia(obs_texto, "observación")
                            st.session_state[f"obs_mejorada_mat_{i}"] = obs_mejorada
                    else:
                        st.warning("Escribe algo primero")
            
            if f"obs_mejorada_mat_{i}" in st.session_state:
                obs_texto = st.text_area(f"Observación {i+1} mejorada (copia este texto)", 
                                         value=st.session_state[f"obs_mejorada_mat_{i}"], 
                                         key=f"obs_mejorada_display_mat_{i}", 
                                         height=70)
            
            if obs_texto.strip():
                lista_textos_observaciones_mat.append(obs_texto.strip())

    st.subheader("🚒 Estado de Unidades y Actividades")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        serv_nocturnos = st.number_input("Servicios Nocturnos", min_value=0, value=0, key="srv_noct_mat")
    with col_u2:
        actividades_mat = st.number_input("Actividades", min_value=0, value=0, key="act_mat")

    st.subheader("📝 Detalle de Actividades")
    texto_actividad_mat = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder="Ejemplo:\nEl día de hoy en horas matutinas se da una sesión educativa...",
        height=120,
        key="act_txt_mat"
    )
    
    # === IA === Botón para mejorar actividad matutina
    col_act_btn1, col_act_btn2 = st.columns([3, 1])
    with col_act_btn2:
        if st.button("✨ IA Actividad", key="btn_ia_act_mat"):
            if texto_actividad_mat.strip():
                with st.spinner("🤖 Mejorando..."):
                    act_mejorada = mejorar_redaccion_ia(texto_actividad_mat, "actividad")
                    st.session_state["act_mejorada_mat"] = act_mejorada
            else:
                st.warning("Escribe algo primero")
    
    if "act_mejorada_mat" in st.session_state:
        texto_actividad_mat = st.text_area("Actividad mejorada (copia este texto)", 
                                           value=st.session_state["act_mejorada_mat"], 
                                           key="act_mejorada_display_mat", 
                                           height=120)

    unidades_op = st.text_area(
        "Unidades Operativas", 
        ". Unidad 4.4 Transporte de Personal Matrícula AD050WM\n. Unidad UM-45 Tipo Moto", 
        height=80
    )

    unidades_inop = st.text_area(
        "Unidades Inoperativas", 
        ". Unidad Cisterna 4.2 (Falla de Almacenador de energía)\n. Unidad UM-41 Tipo Moto (Por falla del Sistema eléctrico del Arranque)\n. Unidad UM-42 Tipo Moto (Motor)\n. Unidad UM-43 Tipo Moto (Motor)\n. Unidad UM-44 Tipo Moto (Motor)", 
        height=120
    )

    cond_meteo = st.text_input("Condiciones Meteorológicas", "Cielo despejado en el Sector la Cumaca, Sub-Sector Fila Las Josefinas Municipio San Diego Estado Carabobo.")

    if 'parte_matutino_generado' not in st.session_state:
        st.session_state.parte_matutino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE MATUTINO", use_container_width=True):
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        nombre_dia = dias[fecha_mat.weekday()]
        fecha_str = f"{nombre_dia} {fecha_mat.strftime('%d/%m/%Y')}"

        if cant_obs_mat == 0 or not lista_textos_observaciones_mat:
            texto_observaciones_ws = "00"
        else:
            texto_observaciones_ws = f"{int(cant_obs_mat):02d}\n"
            for idx, txt in enumerate(lista_textos_observaciones_mat, 1):
                texto_observaciones_ws += f"- {txt}\n"

        servicios_del_dia = consumir_y_limpiar_servicios()

        st.session_state.parte_matutino_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGO*

*CUERPO DE BOMBEROS FORESTALES INPARQUES*

*COORDINACIÓN FORESTAL CARABOBO*

*PARTE GENERAL*

*COORDINADOR FORESTAL ESTADAL:* 
{coord_estadal}

*EBF LAS JOSEFINAS*

*JEFE DE ESTACIÓN:* 
{jefe_estacion}    

*JEFE DE SECCIÓN:* (Auxiliar) {jefe_seccion} 

*PIE DE FUERZA:* {pie_fuerza:02d}

*FECHA:* {fecha_str}

*PARTE N°:* {parte_num}

*SECCIÓN DE GUARDIA:* "{seccion_guardia}"

- Personal de Guardia: {p_guardia:02d}
- Personal Retardado: {p_retardado:02d}
- Personal Libre: {p_libre:02d}
- Personal Permiso: {p_permiso:02d}
- Personal de Reposo: {p_reposo:02d}
- Personal Ausente: {p_ausente:02d}
- Personal de Vacaciones: {p_vacaciones:02d}
- Personal de Comisión: {p_comision:02d}
- Personal Pasante de guardia: {p_pasantes:02d}

*OBSERVACIONES:* {texto_observaciones_ws}

*SERVICIOS NOCTURNOS:* {serv_nocturnos:02d}

*SERVICIOS Y ACCIONES DEL DÍA:*
{servicios_del_dia}

*ACTIVIDAD:* {actividades_mat:02d}
{texto_actividad_mat}

*UNIDADES OPERATIVAS:* {len(unidades_op.strip().splitlines()) if unidades_op.strip() else 0:02d}
{unidades_op}

*UNIDADES INOPERATIVAS:* {len(unidades_inop.strip().splitlines()) if unidades_inop.strip() else 0:02d}
{unidades_inop}

*CONDICIONES METEOROLÓGICA:* {cond_meteo}

*ANALISTA:* {analista_mat}"""

    if st.session_state.parte_matutino_generado:
        st.subheader("📋 Parte Matutino Formateado (Listo para copiar a WhatsApp)")
        st.code(st.session_state.parte_matutino_generado, language=None)

# =========================================================
# MÓDULO 2: PARTE VESPERTINO
# =========================================================
elif opcion_modulo == "RESUMEN VESPERTINO":
    st.header("🌆 Parte Vespertino")

    st.subheader("📌 Datos Principales")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        estacion_vesp = st.text_input("Estación", "EBF LAS JOSEFINAS", key="est_vesp")
        fecha_vesp = st.date_input("Fecha", datetime.now(), key="f_vesp")
    with col_v2:
        serv_realizados = st.number_input("Servicios Realizados", min_value=0, value=0, key="sr_vesp")
        actividades_vesp = st.number_input("Actividades", min_value=0, value=1, key="act_vesp")

    st.subheader("📝 Actividad Realizada")
    texto_actividad = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder="Ejemplo:\nEl día de hoy en horas matutinas se da una sesión educativa al personal pasante...",
        height=120,
        key="act_txt_vesp"
    )
    
    # === IA === Botón para mejorar actividad vespertina
    col_act_btn1_v, col_act_btn2_v = st.columns([3, 1])
    with col_act_btn2_v:
        if st.button("✨ IA Actividad", key="btn_ia_act_vesp"):
            if texto_actividad.strip():
                with st.spinner("🤖 Mejorando..."):
                    act_mejorada_v = mejorar_redaccion_ia(texto_actividad, "actividad")
                    st.session_state["act_mejorada_vesp"] = act_mejorada_v
            else:
                st.warning("Escribe algo primero")
    
    if "act_mejorada_vesp" in st.session_state:
        texto_actividad = st.text_area("Actividad mejorada (copia este texto)", 
                                       value=st.session_state["act_mejorada_vesp"], 
                                       key="act_mejorada_display_vesp", 
                                       height=120)

    st.subheader("📋 Observaciones")
    cant_obs_vesp = st.number_input("Cantidad de Observaciones", min_value=0, value=0, step=1, key="c_obs_vesp")
    
    lista_textos_observaciones_vesp = []
    if cant_obs_vesp > 0:
        for i in range(int(cant_obs_vesp)):
            obs_texto_v = st.text_area(f"Redacte la Observación {i+1}", key=f"obs_input_vesp_{i}", height=70)
            
            # === IA === Botón para mejorar cada observación vespertina
            col_obs_btn1_v, col_obs_btn2_v = st.columns([3, 1])
            with col_obs_btn2_v:
                if st.button(f"✨ IA Obs {i+1}", key=f"btn_ia_obs_vesp_{i}"):
                    if obs_texto_v.strip():
                        with st.spinner("🤖 Mejorando..."):
                            obs_mejorada_v = mejorar_redaccion_ia(obs_texto_v, "observación")
                            st.session_state[f"obs_mejorada_vesp_{i}"] = obs_mejorada_v
                    else:
                        st.warning("Escribe algo primero")
            
            if f"obs_mejorada_vesp_{i}" in st.session_state:
                obs_texto_v = st.text_area(f"Observación {i+1} mejorada (copia este texto)", 
                                           value=st.session_state[f"obs_mejorada_vesp_{i}"], 
                                           key=f"obs_mejorada_display_vesp_{i}", 
                                           height=70)
            
            if obs_texto_v.strip():
                lista_textos_observaciones_vesp.append(obs_texto_v.strip())

    st.subheader("🌤️ Clima y Analista")
    cond_meteo_vesp = st.text_input(
        "Condiciones Meteorológicas",
        "Cielo Despejado en el Sector La Cumaca, parroquia San Diego, Municipio San Diego, Estado Carabobo.",
        key="meteo_vesp"
    )
    analista_vesp = st.text_input("Analista que Registra", "Pasante Escalona M", key="a_vesp")

    if 'parte_vespertino_generado' not in st.session_state:
        st.session_state.parte_vespertino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE VESPERTINO", use_container_width=True):
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        nombre_dia = dias[fecha_vesp.weekday()]
        fecha_str = f"{nombre_dia} {fecha_vesp.strftime('%d/%m/%Y')}"

        if cant_obs_vesp == 0 or not lista_textos_observaciones_vesp:
            texto_observaciones_ws_v = "00"
        else:
            texto_observaciones_ws_v = f"{int(cant_obs_vesp):02d}\n"
            for idx, txt in enumerate(lista_textos_observaciones_vesp, 1):
                texto_observaciones_ws_v += f"- {txt}\n"

        servicios_del_dia_vesp = consumir_y_limpiar_servicios()

        st.session_state.parte_vespertino_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGO*

*CUERPO DE BOMBEROS FORESTALES INPARQUES*

*COORDINACIÓN FORESTAL CARABOBO*

*{estacion_vesp}*

*FECHA:* {fecha_str}

*SERVICIOS REALIZADOS:* {serv_realizados:02d}

{servicios_del_dia_vesp}

*ACTIVIDAD:* {actividades_vesp:02d}

{texto_actividad}

*OBSERVACIONES:* {texto_observaciones_ws_v}

*CONDICIONES METEOROLÓGICAS:* {cond_meteo_vesp}

*ANALISTA:* {analista_vesp}"""

    if st.session_state.parte_vespertino_generado:
        st.subheader("📋 Parte Vespertino Formateado (Listo para copiar a WhatsApp)")
        st.code(st.session_state.parte_vespertino_generado, language=None)

# =========================================================
# MÓDULO 3: REPORTES DE SERVICIOS 
# =========================================================
elif opcion_modulo == "REPORTES DE SERVICIOS":
    st.header("🚨 Reportes de Servicios")

    if 'lista_servicios' not in st.session_state:
        st.session_state.lista_servicios = cargar_servicios_persistencia()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        tipo_servicio = st.selectbox(
            "Tipo de Servicio",
            st.session_state.lista_servicios
        )
        
        with st.expander("➕ / 🗑️ Agregar o Borrar Tipo de Servicio"):
            nuevo_servicio = st.text_input("Escriba un nuevo tipo de servicio:")
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Guardar nuevo", use_container_width=True):
                    if nuevo_servicio and nuevo_servicio.upper() not in st.session_state.lista_servicios:
                        st.session_state.lista_servicios.append(nuevo_servicio.upper())
                        guardar_servicios_persistencia(st.session_state.lista_servicios)
                        st.success("¡Servicio agregado y guardado!")
                        st.rerun()
            with c_btn2:
                if st.button("Borrar actual", use_container_width=True):
                    if len(st.session_state.lista_servicios) > 1:
                        st.session_state.lista_servicios.remove(tipo_servicio)
                        guardar_servicios_persistencia(st.session_state.lista_servicios)
                        st.success("¡Servicio eliminado!")
                        st.rerun()
                    else:
                        st.error("No puedes borrar todos los servicios.")

        fecha_srv = st.date_input("Fecha del Servicio", datetime.now(), key="f_srv")
        hora_inicio = st.time_input("Hora de Inicio", datetime.now().time(), key="h_ini")
        num_servicio = st.text_input("Número de Servicio", "", placeholder="Ej: 04-0267-2026")
        
        st.markdown("📍 **Ubicación Geográfica**")
        srv_estado = st.text_input("Estado", "Carabobo", key="s_est")
        srv_municipio = st.text_input("Municipio", "Puerto Cabello", key="s_mun")
        srv_parroquia = st.text_input("Parroquia", "Borburata", key="s_par")
        srv_sector = st.text_input("Sub-sector / Sector", "Sector isla larga, Sub-sector insular", key="s_sec")
        ubicacion_srv = f"{srv_sector}, Parroquia {srv_parroquia}, Municipio {srv_municipio}, Estado {srv_estado}"

        jefe_comision = st.text_input("Jefe de Comisión", "", placeholder="Indique el rango y nombre")

    with col_s2:
        estatus_srv = st.selectbox("Estatus", ["en proceso", "Finalizado"])
        hora_fin = st.time_input("Hora de Finalizado", datetime.now().time(), key="h_fin")
        efectivos_srv = st.number_input("Número de Efectivos", min_value=1, value=3, step=1)
        latitud_srv = st.number_input("Latitud", value=10.3047984, format="%.7f", key="lat_srv")
        longitud_srv = st.number_input("Longitud", value=-67.9307846, format="%.7f", key="lon_srv")

    st.subheader("📌 Observaciones")
    num_observaciones = st.number_input("Cantidad de Observaciones", min_value=0, value=0, step=1, key="num_obs")
    
    lista_textos_observaciones = []
    if num_observaciones > 0:
        for i in range(int(num_observaciones)):
            obs_texto = st.text_area(f"Redacte la Observación {i+1}", key=f"obs_input_{i}", height=70)
            
            # === IA === Botón para mejorar cada observación de servicios
            col_obs_btn1_s, col_obs_btn2_s = st.columns([3, 1])
            with col_obs_btn2_s:
                if st.button(f"✨ IA Obs {i+1}", key=f"btn_ia_obs_srv_{i}"):
                    if obs_texto.strip():
                        with st.spinner("🤖 Mejorando..."):
                            obs_mejorada_s = mejorar_redaccion_ia(obs_texto, "observación")
                            st.session_state[f"obs_mejorada_srv_{i}"] = obs_mejorada_s
                    else:
                        st.warning("Escribe algo primero")
            
            if f"obs_mejorada_srv_{i}" in st.session_state:
                obs_texto = st.text_area(f"Observación {i+1} mejorada (copia este texto)", 
                                         value=st.session_state[f"obs_mejorada_srv_{i}"], 
                                         key=f"obs_mejorada_display_srv_{i}", 
                                         height=70)
            
            if obs_texto.strip():
                lista_textos_observaciones.append(obs_texto.strip())

    st.subheader("🚓 Organismos Presentes")
    
    if 'lista_org_oficiales' not in st.session_state:
        st.session_state.lista_org_oficiales = cargar_organismos_persistencia()

    org_seleccionados = st.multiselect(
        "Seleccione los organismos que asistieron (Opcional)", 
        st.session_state.lista_org_oficiales, 
        default=[]
    )
    
    with st.expander("➕ Agregar organismo de seguridad"):
        nuevo_org = st.text_input("Escriba el nombre del organismo:")
        if st.button("Añadir Organismo"):
            if nuevo_org and nuevo_org.upper() not in [o.upper() for o in st.session_state.lista_org_oficiales]:
                if "OTRO" in st.session_state.lista_org_oficiales:
                    st.session_state.lista_org_oficiales.insert(-1, nuevo_org.upper())
                else:
                    st.session_state.lista_org_oficiales.append(nuevo_org.upper())
                guardar_organismos_persistencia(st.session_state.lista_org_oficiales)
                st.success("¡Organismo agregado y guardado!")
                st.rerun()
    
    cantidades_org = {}
    if org_seleccionados:
        cols_org = st.columns(4)
        for idx, org in enumerate(org_seleccionados):
            with cols_org[idx % 4]:
                sigla_mostrar = org.split(" (")[0]
                cantidades_org[org] = st.number_input(sigla_mostrar, min_value=1, value=1, step=1, key=f"cant_{org}")

    st.subheader("📝 Reseña y Acciones Operativas")
    resena_borrador = st.text_area(
        "Reseña:",
        placeholder="Ejemplo: por instrucciones del jefe de Estacion S/2 (B) Meléndez Alberlen...",
        height=100
    )
    
    # === IA === Botón para mejorar reseña
    col_res_btn1, col_res_btn2 = st.columns([3, 1])
    with col_res_btn2:
        if st.button("✨ IA Reseña", key="btn_ia_resena_srv"):
            if resena_borrador.strip():
                with st.spinner("🤖 Mejorando..."):
                    resena_mejorada_ia = mejorar_redaccion_ia(resena_borrador, "reseña")
                    st.session_state["resena_mejorada_srv"] = resena_mejorada_ia
            else:
                st.warning("Escribe algo primero")
    
    if "resena_mejorada_srv" in st.session_state:
        resena_borrador = st.text_area("Reseña mejorada (copia este texto)", 
                                       value=st.session_state["resena_mejorada_srv"], 
                                       key="resena_mejorada_display_srv", 
                                       height=100)
    
    acciones_borrador = st.text_area(
        "Acciones Realizadas:",
        placeholder="Ejemplo: 07:29 Hrs Se destaca comisión bomberil...",
        height=150
    )
    
    # === IA === Botón para mejorar acciones
    col_acc_btn1, col_acc_btn2 = st.columns([3, 1])
    with col_acc_btn2:
        if st.button("✨ IA Acciones", key="btn_ia_acciones_srv"):
            if acciones_borrador.strip():
                with st.spinner("🤖 Mejorando..."):
                    acciones_mejoradas_ia = mejorar_redaccion_ia(acciones_borrador, "acciones realizadas")
                    st.session_state["acciones_mejoradas_srv"] = acciones_mejoradas_ia
            else:
                st.warning("Escribe algo primero")
    
    if "acciones_mejoradas_srv" in st.session_state:
        acciones_borrador = st.text_area("Acciones mejoradas (copia este texto)", 
                                         value=st.session_state["acciones_mejoradas_srv"], 
                                         key="acciones_mejoradas_display_srv", 
                                         height=150)
    
    analista_srv = st.text_input("Analista que Registra", "", key="a_srv", placeholder="Indique el rango y nombre")

    if 'reporte_generado' not in st.session_state:
        st.session_state.reporte_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("✨ GENERAR REPORTE PARA WHATSAPP", use_container_width=True):
        if not resena_borrador.strip() or not acciones_borrador.strip():
            st.warning("⚠️ Por favor complete tanto la reseña como las acciones realizadas.")
        else:
            with st.spinner("🤖 Formateando el reporte..."):
                resena_optimizada = resena_borrador
                acciones_optimizadas = acciones_borrador
                
                st.session_state.resena_mejorada = resena_optimizada
                st.session_state.acciones_mejoradas = acciones_optimizadas
                
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dia_str = dias_semana[fecha_srv.weekday()]
                
                texto_organismos_ws = ""
                if cantidades_org:
                    for org, cant in cantidades_org.items():
                        sigla_final = org.split(" (")[0]
                        texto_organismos_ws += f"{sigla_final}: {cant:02d}\n"
                else:
                    texto_organismos_ws = "00\n"
                
                if num_observaciones == 0 or not lista_textos_observaciones:
                    texto_observaciones_ws = "00"
                else:
                    texto_observaciones_ws = f"{int(num_observaciones):02d}\n"
                    for idx, txt in enumerate(lista_textos_observaciones, 1):
                        texto_observaciones_ws += f"- {txt}\n"
                
                st.session_state.reporte_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGOS*

*BOMBEROS FORESTALES INPARQUES*

*COORDINACIÓN FORESTAL CARABOBO*

*EBF LAS JOSEFINAS* 

*FECHA:* {dia_str} 
{fecha_srv.strftime('%d/%m/%Y')}
 
*REPORTE DE SERVICIO*

*TIPO DE SERVICIO:* 
{tipo_servicio}

*HORA DE INICIO:* {hora_inicio.strftime('%H:%M')} Hrs

*HORA DE FINALIZADO:* {hora_fin.strftime('%H:%M')} Hrs

*NÚMERO DE SERVICIO:* 
{num_servicio}

*UBICACIÓN:* {ubicacion_srv} 

*JEFE DE COMISIÓN:*  
{jefe_comision} 

*RESEÑA:*
{resena_optimizada}

*ACCION REALIZADA*
{acciones_optimizadas}

*OBSERVACIONES:* {texto_observaciones_ws}
*ORGANISMOS PRESENTES* 

{texto_organismos_ws}
*CANTIDAD DE EFECTIVOS:*  {efectivos_srv:02d}

*ESTATUS:* {estatus_srv} 

*COORDENADAS:*
{latitud_srv}, {longitud_srv}

*ANALISTA:* 
{analista_srv}"""

    if st.session_state.reporte_generado:
        st.subheader("📋 Reporte Formateado (Listo para copiar a WhatsApp)")
        st.code(st.session_state.reporte_generado, language=None)

        if st.button("💾 GUARDAR SERVICIO EN EXCEL", use_container_width=True):
            org_excel = ", ".join([f"{org.split(' (')[0]}: {cant}" for org, cant in cantidades_org.items()]) if cantidades_org else "Ninguno"
            obs_excel = f"{num_observaciones} observaciones registradas" if num_observaciones > 0 else "00"
            
            nuevo_srv = pd.DataFrame([{
                "Fecha": fecha_srv.strftime('%Y-%m-%d'),
                "Hora Inicio": hora_inicio.strftime('%H:%M'),
                "Hora Fin": hora_fin.strftime('%H:%M'),
                "Tipo Servicio": tipo_servicio,
                "Número Servicio": num_servicio,
                "Jefe Comisión": jefe_comision,
                "Ubicación": ubicacion_srv,
                "Reseña Original": resena_borrador,
                "Acciones Realizadas": acciones_borrador,
                "Observaciones": obs_excel,
                "Organismos Presentes": org_excel,
                "Efectivos": efectivos_srv,
                "Estatus": estatus_srv,
                "Coordenadas": f"{latitud_srv}, {longitud_srv}",
                "Analista": analista_srv
            }])

            if os.path.exists(EXCEL_SERVICIOS):
                df_existente = pd.read_excel(EXCEL_SERVICIOS)
                df_final = pd.concat([df_existente, nuevo_srv], ignore_index=True)
            else:
                df_final = nuevo_srv

            df_final.to_excel(EXCEL_SERVICIOS, index=False)
            
            datos_servicio = {
                "tipo_servicio": tipo_servicio,
                "num_servicio": num_servicio,
                "ubicacion": ubicacion_srv,
                "resena": resena_borrador,
                "coordenadas": f"{latitud_srv}, {longitud_srv}",
                "estatus": estatus_srv
            }
            registrar_servicio_dia(datos_servicio)
            st.success(f"✅ ¡Servicio '{tipo_servicio}' guardado en Excel y enlazado para los partes!")

# =========================================================
# MÓDULO 4: REPORTES DE INCENDIOS
# =========================================================
elif opcion_modulo == "REPORTES DE INCENDIOS":
    st.header("🔥 Reportes de Incendios")

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        tipo_reporte_opcion = st.selectbox("Tipo de Reporte", ["Final", "Preliminar", "Progresivo"])
        if tipo_reporte_opcion == "Progresivo":
            num_prog = st.number_input("Número Progresivo", min_value=1, value=1, step=1, key="n_prog")
            tipo_reporte = f"Progresivo {num_prog:03d}"
        else:
            tipo_reporte = tipo_reporte_opcion

        tipo_incendio = st.selectbox(
            "Tipo de Evento",
            [
                "Incendio de Vegetacion",
                "Incendio Forestal",
                "Conato de Incendio"
            ]
        )
        num_servicio_inc = st.text_input("Número de Servicio", "", placeholder="Ej: 04-0028-2026")
        fecha_inc = st.date_input("Fecha del Evento", datetime.now(), key="f_inc")
        hora_inc = st.time_input("Hora del Reporte", datetime.now().time(), key="h_inc")
        comandante_escena = st.text_input("Comandante en Escena", "", placeholder="Ej: C/1 (B) Gutiérrez Orlando")
        estacion_ebf = st.text_input("Estación / Base", "EBF Las Josefinas")

    with col_i2:
        sub_sector = st.text_input("Sub-Sector", "Hacienda la Cumaca")
        sector = st.text_input("Sector", "La Cumaca")
        
        municipios_carabobo = {
            "Bejuma": ["Bejuma", "Chirgua", "Simón Bolívar"],
            "Carlos Arvelo": ["Güigüe", "Tacarigua", "Belén"],
            "Diego Ibarra": ["Mariara", "Aguas Calientes"],
            "Guacara": ["Guacara", "Ciudad Alianza", "Yagua"],
            "Juan José Mora": ["Morón", "Urama"],
            "Libertador": ["Tocuyito", "Independencia"],
            "Los Guayos": ["Los Guayos"],
            "Miranda": ["Miranda"],
            "Montalbán": ["Montalbán"],
            "Naguanagua": ["Naguanagua"],
            "Puerto Cabello": ["Puerto Cabello", "Democracia", "Fraternidad", "Goaigoaza", "Juan José Flores", "Patanemo", "Borburata"],
            "San Diego": ["San Diego"],
            "San Joaquín": ["San Joaquín"]
        }

        municipio = st.selectbox("Municipio", list(municipios_carabobo.keys()), index=list(municipios_carabobo.keys()).index("San Diego"))
        parroquia = st.selectbox("Parroquia", municipios_carabobo[municipio])
        
        estado_inc = st.text_input("Estado", "Carabobo")
        abrae_inc = st.selectbox("Abrae", ["P/N San Esteban", "No aplica"])

    st.subheader("📍 Coordenadas y Ubicación")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        lat_inc = st.number_input("Latitud", value=10.290985, format="%.6f", key="lat_inc")
    with col_c2:
        lon_inc = st.number_input("Longitud", value=-67.959402, format="%.6f", key="lon_inc")

    st.subheader("📊 Afectación y Recursos")
    
    if "lista_causas_disponibles" not in st.session_state:
        st.session_state.lista_causas_disponibles = cargar_causas_persistencia()

    col_cau1, col_cau2 = st.columns([2, 1])
    with col_cau1:
        causas_prob = st.selectbox("Causas Probables", st.session_state.lista_causas_disponibles, key="select_causa_prob")
    with col_cau2:
        nueva_causa = st.text_input("Añadir Causa", placeholder="Nueva causa...", key="input_nueva_causa", label_visibility="collapsed")
        if st.button("➕ Agregar Causa", use_container_width=True):
            if nueva_causa.strip() and nueva_causa.strip() not in st.session_state.lista_causas_disponibles:
                st.session_state.lista_causas_disponibles.append(nueva_causa.strip())
                guardar_causas_persistencia(st.session_state.lista_causas_disponibles)
                st.success("¡Causa agregada y guardada!")
                st.rerun()

    if st.button("🗑️ Eliminar Causa Seleccionada", use_container_width=True):
        if len(st.session_state.lista_causas_disponibles) > 1:
            st.session_state.lista_causas_disponibles.remove(causas_prob)
            guardar_causas_persistencia(st.session_state.lista_causas_disponibles)
            st.success("¡Causa eliminada!")
            st.rerun()
        else:
            st.warning("Debe quedar al menos una causa en la lista.")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        efectivos_inc = st.number_input("Cantidad de Efectivos (BFI)", min_value=1, value=10, step=1, key="ef_inc")
        recursos_disp = st.text_input("Recursos Disponibles", "Batidor Forestal")
        unidades_disp = st.text_input("Unidades", "Unidad Tipo Moto 41")

    with col_r2:
        area_herbacea = st.number_input("Área Herbacea (Baja) en ha", min_value=0.0, value=13.7, step=0.1)
        area_arbustiva = st.number_input("Área Arbustiva (Media) en ha", min_value=0.0, value=3.0, step=0.1)
        area_arboria = st.number_input("Área Arbórea (Alta) en ha", min_value=0.0, value=0.0, step=0.1)

    st.subheader("🌤️ Condiciones Atmosféricas")
    
    if st.button("📥 Consultar Clima Automático desde Windy", use_container_width=True):
        with st.spinner("Conectando con la API de Windy..."):
            url_windy = "https://api.windy.com/api/point-forecast/v2"
            payload_windy = {
                "lat": lat_inc,
                "lon": lon_inc,
                "model": "gfs",
                "parameters": ["wind", "temp", "rh", "pressure", "precip"],
                "levels": ["surface"],
                "key": WINDY_API_KEY,
            }
            try:
                resp_windy = requests.post(url_windy, json=payload_windy, timeout=10)
                if resp_windy.status_code == 200:
                    data_w = resp_windy.json()
                    
                    def safe_get(key, default=0):
                        val = data_w.get(key)
                        if val and isinstance(val, list) and len(val) > 0 and val[0] is not None:
                            return val[0]
                        return default

                    temp_k = safe_get("temp-surface", 298.15)
                    temp_c = round(temp_k - 273.15)
                    humedad_w = safe_get("rh-surface", 0)
                    presion_pa = safe_get("pressure-surface", 101325)
                    presion_hpa = round(presion_pa / 100, 4)
                    precip_mm = safe_get("precip-surface", 0)
                    
                    wind_surface = safe_get("wind-surface", None)
                    if wind_surface is not None and wind_surface > 0:
                        viento_ms = wind_surface
                    else:
                        u = safe_get("wind_u-surface", 0)
                        v = safe_get("wind_v-surface", 0)
                        viento_ms = (u**2 + v**2)**0.5
                    
                    viento_kmh = round(float(viento_ms) * 3.6)

                    st.session_state["v_viento"] = f"{viento_kmh:02d} Km/h"
                    st.session_state["v_temp"] = f"{temp_c}°C"
                    st.session_state["v_hum"] = f"{round(humedad_w)}%"
                    st.session_state["v_pres"] = f"{presion_hpa:,.4f} hPa".replace(",", ".")
                    st.session_state["v_precip"] = f"{int(precip_mm * 10)}%" if precip_mm > 0 else "0%"
                    
                    st.success("¡Datos atmosféricos sincronizados desde Windy!")
                    st.rerun()
                else:
                    st.error(f"Error en Windy: Código {resp_windy.status_code} - {resp_windy.text}")
            except Exception as e:
                st.error(f"No se pudo conectar con Windy: {e}")

    col_at1, col_at2, col_at3, col_at4, col_at5 = st.columns(5)
    with col_at1:
        viento_vel = st.text_input("Viento (Km/h)", key="v_viento")
    with col_at2:
        temp_val = st.text_input("Temperatura", key="v_temp")
    with col_at3:
        precip_val = st.text_input("Precipitaciones (%)", "0%", key="v_precip")
    with col_at4:
        humedad_val = st.text_input("Humedad Relativa", key="v_hum")
    with col_at5:
        presion_val = st.text_input("Presión Atmosférica", key="v_pres")

    st.subheader("📝 Bitácora, Estatus y Autoridades")
    
    cant_obs_inc = st.number_input("Cantidad de Observaciones (Opcional)", min_value=0, value=0, step=1, key="num_obs_inc")
    lista_textos_observaciones_inc = []
    if cant_obs_inc > 0:
        for i in range(int(cant_obs_inc)):
            obs_texto_i = st.text_area(f"Redacte la Observación {i+1}", key=f"obs_input_inc_{i}", height=70)
            
            # === IA === Botón para mejorar cada observación de incendios
            col_obs_btn1_i, col_obs_btn2_i = st.columns([3, 1])
            with col_obs_btn2_i:
                if st.button(f"✨ IA Obs {i+1}", key=f"btn_ia_obs_inc_{i}"):
                    if obs_texto_i.strip():
                        with st.spinner("🤖 Mejorando..."):
                            obs_mejorada_i = mejorar_redaccion_ia(obs_texto_i, "observación")
                            st.session_state[f"obs_mejorada_inc_{i}"] = obs_mejorada_i
                    else:
                        st.warning("Escribe algo primero")
            
            if f"obs_mejorada_inc_{i}" in st.session_state:
                obs_texto_i = st.text_area(f"Observación {i+1} mejorada (copia este texto)", 
                                           value=st.session_state[f"obs_mejorada_inc_{i}"], 
                                           key=f"obs_mejorada_display_inc_{i}", 
                                           height=70)
            
            if obs_texto_i.strip():
                lista_textos_observaciones_inc.append(obs_texto_i.strip())

    resena_inc = st.text_area(
        "RESEÑA:",
        placeholder="Ejemplo: Durante recorrido por el sector la cumaca se visualiza una columna de humo...",
        height=100,
        key="res_inc"
    )
    
    # === IA === Botón para mejorar reseña de incendio
    col_res_btn1_i, col_res_btn2_i = st.columns([3, 1])
    with col_res_btn2_i:
        if st.button("✨ IA Reseña", key="btn_ia_resena_inc"):
            if resena_inc.strip():
                with st.spinner("🤖 Mejorando..."):
                    resena_mejorada_inc_ia = mejorar_redaccion_ia(resena_inc, "reseña de incendio")
                    st.session_state["resena_mejorada_inc"] = resena_mejorada_inc_ia
            else:
                st.warning("Escribe algo primero")
    
    if "resena_mejorada_inc" in st.session_state:
        resena_inc = st.text_area("Reseña mejorada (copia este texto)", 
                                  value=st.session_state["resena_mejorada_inc"], 
                                  key="resena_mejorada_display_inc", 
                                  height=100)
    
    acciones_inc = st.text_area(
        "ACCIÓN REALIZADA (Bitácora de Eventos):",
        placeholder="Ejemplo:\n15:10 Hrs Se destaca el Bombero Peralta Javier...\n15:15 Hrs Reporta el Bombero...",
        height=200,
        key="acc_inc"
    )
    
    # === IA === Botón para mejorar acciones de incendio
    col_acc_btn1_i, col_acc_btn2_i = st.columns([3, 1])
    with col_acc_btn2_i:
        if st.button("✨ IA Acciones", key="btn_ia_acciones_inc"):
            if acciones_inc.strip():
                with st.spinner("🤖 Mejorando..."):
                    acciones_mejoradas_inc_ia = mejorar_redaccion_ia(acciones_inc, "bitácora de eventos")
                    st.session_state["acciones_mejoradas_inc"] = acciones_mejoradas_inc_ia
            else:
                st.warning("Escribe algo primero")
    
    if "acciones_mejoradas_inc" in st.session_state:
        acciones_inc = st.text_area("Acciones mejoradas (copia este texto)", 
                                    value=st.session_state["acciones_mejoradas_inc"], 
                                    key="acciones_mejoradas_display_inc", 
                                    height=200)

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        estatus_inc = st.selectbox("Estatus del Incendio", ["Finalizado-combatido", "en proceso", "Finalizado"])
    with col_e2:
        hora_envio_inc = st.time_input("Hora de Envío del Reporte", datetime.now().time(), key="h_envio_inc")
    with col_e3:
        delegado_ame = st.text_input("Delegado Estadal AME", "C/2 (B) Reyes Edwin")

    if 'incendio_generado' not in st.session_state:
        st.session_state.incendio_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔥 GENERAR REPORTE DE INCENDIO", use_container_width=True):
        if not resena_inc.strip() or not acciones_inc.strip():
            st.warning("⚠️ Por favor complete la reseña y las acciones realizadas.")
        else:
            with st.spinner("🤖 Formateando el reporte de incendio..."):
                
                area_total_ha = area_herbacea + area_arbustiva + area_arboria
                
                texto_vegetacion = ""
                if area_herbacea > 0:
                    texto_vegetacion += f"- Herbácea (Baja)\n"
                if area_arbustiva > 0:
                    texto_vegetacion += f"- Arbustiva (Media)\n"
                if area_arboria > 0:
                    texto_vegetacion += f"- Arbórea (Alta)\n"

                texto_area_afectada = ""
                if area_herbacea > 0:
                    texto_area_afectada += f"- Herbácea (Baja): {area_herbacea} ha\n"
                if area_arbustiva > 0:
                    texto_area_afectada += f"- Arbustiva (Media): {area_arbustiva} ha\n"
                if area_arboria > 0:
                    texto_area_afectada += f"- Arbórea (Alta): {area_arboria} ha\n"
                texto_area_afectada += f"Área Afectada Total: {area_total_ha} ha"

                if cant_obs_inc == 0 or not lista_textos_observaciones_inc:
                    texto_observaciones_ws_i = "00"
                else:
                    texto_observaciones_ws_i = f"{int(cant_obs_inc):02d}\n"
                    for idx, txt in enumerate(lista_textos_observaciones_inc, 1):
                        texto_observaciones_ws_i += f"- {txt}\n"

                st.session_state.incendio_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGOS*

*CUERPO DE BOMBEROS FORESTALES  INPARQUES*

*REPORTE {tipo_reporte}*

*TIPO DE EVENTO:* {tipo_incendio}

*NÚMERO DE SERVICIO:* {num_servicio_inc}

*FECHA:* {fecha_inc.strftime('%d/%m/%Y')}

*HORA:* {hora_inc.strftime('%H:%M')} HLV 

*COMANDANTE EN ESCENA:* {comandante_escena} 

{estacion_ebf}

*SECTOR:* {sector} sub-sector {sub_sector}

*PARROQUIA:* {parroquia}

*MUNICIPIO:* {municipio}

*ESTADO:* {estado_inc} 

*ABRAE:* {abrae_inc} 

*RESEÑA:*
{resena_inc}

*ACCIÓN REALIZADA:*
{acciones_inc}

*OBSERVACIONES:* {texto_observaciones_ws_i}

*ORGANISMOS PRESENTES:*
BFI: {efectivos_inc:02d}

*RECURSOS DISPONIBLES:*
{recursos_disp}

*UNIDADES:*
-{unidades_disp} 

*ÁREA AFECTADA:*
{texto_area_afectada.strip()}

*VEGETACIÓN:*
{texto_vegetacion.strip()}

*COORDENADAS:*
{lat_inc} {lon_inc}

*CAUSAS PROBABLES:*
{causas_prob} 

*CONDICIONES ATMOSFÉRICAS:*
✅ Viento: {viento_vel}
✅ Temperatura: {temp_val}
✅ Precipitaciones: {precip_val}
✅ Humedad relativa: {humedad_val}
✅ Presión atmosférica: {presion_val}

*HORA DE ENVÍO:* {hora_envio_inc.strftime('%H:%M')} HLV

*ESTATUS:*
{estatus_inc}

*DELEGADO ESTADAL AME:*
{delegado_ame}"""

    if st.session_state.incendio_generado:
        st.subheader("📋 Reporte de Incendio Formateado")
        st.code(st.session_state.incendio_generado, language=None)

        if st.button("💾 GUARDAR INCENDIO EN EXCEL", use_container_width=True):
            nuevo_inc = pd.DataFrame([{
                "Fecha": fecha_inc.strftime('%Y-%m-%d'),
                "Hora": hora_inc.strftime('%H:%M'),
                "Tipo Servicio": tipo_incendio,
                "Número Servicio": num_servicio_inc,
                "Ubicación": f"{sector}, {municipio}",
                "Comandante": comandante_escena,
                "Área Afectada": f"{area_total_ha} ha",
                "Efectivos": efectivos_inc,
                "Estatus": estatus_inc,
                "Coordenadas": f"{lat_inc}, {lon_inc}",
                "Analista / Delegado": delegado_ame
            }])

            if os.path.exists(EXCEL_SERVICIOS):
                df_existente = pd.read_excel(EXCEL_SERVICIOS)
                df_final = pd.concat([df_existente, nuevo_inc], ignore_index=True)
            else:
                df_final = nuevo_inc

            df_final.to_excel(EXCEL_SERVICIOS, index=False)
            
            datos_incendio = {
                "tipo_servicio": tipo_incendio,
                "num_servicio": num_servicio_inc,
                "ubicacion": f"{sector}, {municipio}",
                "resena": resena_inc,
                "coordenadas": f"{lat_inc}, {lon_inc}",
                "estatus": estatus_inc
            }
            registrar_servicio_dia(datos_incendio)
            st.success(f"✅ ¡Incendio guardado exitosamente en `{EXCEL_SERVICIOS}` y enlazado para los partes!")

# =========================================================
# MÓDULO 5: REPORTES MIXTOS
# =========================================================
elif opcion_modulo == "REPORTES MIXTOS":
    st.header("📄 Reportes Mixtos")

    tab_ni, tab_rm, tab_ru = st.tabs(["📌 Nota Informativa", "🌤️ Reporte Meteorológico", "🚒 Reporte de Unidades"])

    # ---------------------------------------------------------
    # SUBMÓDULO: NOTA INFORMATIVA
    # ---------------------------------------------------------
    with tab_ni:
        st.subheader("📝 Generar Nota Informativa")
        fecha_ni = st.date_input("Fecha de la Nota", datetime.now(), key="f_nota")
        
        texto_ni = st.text_area(
            "Contenido de la Nota Informativa",
            value=". El día hoy en horas matutinas se da continuidad a la  Formación en servicio impartida por el coordinador Forestal (B) Mayor Mendoza Luis al personal perteneciente al Estado Portuguesa y personal de planta con el tema: introducción del sistema S.A.R",
            height=130,
            key="txt_ni"
        )
        
        # === IA === Botón para mejorar nota informativa
        col_ni_btn1, col_ni_btn2 = st.columns([3, 1])
        with col_ni_btn2:
            if st.button("✨ IA Nota", key="btn_ia_nota_ni"):
                if texto_ni.strip():
                    with st.spinner("🤖 Mejorando..."):
                        nota_mejorada_ni = mejorar_redaccion_ia(texto_ni, "nota informativa")
                        st.session_state["nota_mejorada_ni"] = nota_mejorada_ni
                else:
                    st.warning("Escribe algo primero")
        
        if "nota_mejorada_ni" in st.session_state:
            texto_ni = st.text_area("Nota mejorada (copia este texto)", 
                                    value=st.session_state["nota_mejorada_ni"], 
                                    key="nota_mejorada_display_ni", 
                                    height=130)
        
        coord_ni = st.text_input("Coordinador Forestal", "My (B) Mendoza Luis", key="c_ni")

        if 'nota_informativa_generada' not in st.session_state:
            st.session_state.nota_informativa_generada = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("📝 GENERAR NOTA INFORMATIVA", use_container_width=True, key="btn_ni"):
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            nombre_dia = dias[fecha_ni.weekday()].capitalize()
            fecha_str_ni = f"{nombre_dia} {fecha_ni.strftime('%d/%m/%Y')}"

            st.session_state.nota_informativa_generada = f"""*SISTEMA NACIONAL DE GESTION DE RIESGOS*

*COORDINACION ESTADAL FORESTAL CARABOBO*

*FECHA:* 
{fecha_str_ni}

*NOTA INFORMATIVA:*

{texto_ni}

*COORDINADOR FORESTAL:* {coord_ni}

*ABNEGACION NATURALEZA PATRIA*"""

        if st.session_state.nota_informativa_generada:
            st.subheader("📋 Nota Informativa Formateada (Lista para WhatsApp)")
            st.code(st.session_state.nota_informativa_generada, language=None)

    # ---------------------------------------------------------
    # SUBMÓDULO: REPORTE METEOROLÓGICO
    # ---------------------------------------------------------
    with tab_rm:
        st.subheader("🌤️ Generar Reporte Meteorológico")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            estado_met = st.text_input("Estado", "Carabobo", key="est_met")
            estacion_met = st.text_input("Estación", "EBF Las Josefinas", key="estc_met")
            fecha_met = st.date_input("Fecha", datetime.now(), key="f_met_rep")
        with col_m2:
            hora_met = st.text_input("Hora", "07:26 Hrs", key="h_met")
            capacidad_op = st.number_input("Capacidad Operativa", min_value=0, value=20, step=1, key="cap_op_met")

        condiciones_met = st.text_area(
            "Condiciones Atmosféricas",
            value="Precipitaciones Leves  en el Sector La Cumaca, Parroquia San Diego, Municipio San Diego, Estado Carabobo",
            height=80,
            key="cond_met"
        )
        
        # === IA === Botón para mejorar condiciones meteorológicas
        col_met_btn1, col_met_btn2 = st.columns([3, 1])
        with col_met_btn2:
            if st.button("✨ IA Condiciones", key="btn_ia_cond_met"):
                if condiciones_met.strip():
                    with st.spinner("🤖 Mejorando..."):
                        cond_mejorada_met = mejorar_redaccion_ia(condiciones_met, "condiciones meteorológicas")
                        st.session_state["cond_mejorada_met"] = cond_mejorada_met
                else:
                    st.warning("Escribe algo primero")
        
        if "cond_mejorada_met" in st.session_state:
            condiciones_met = st.text_area("Condiciones mejoradas (copia este texto)", 
                                           value=st.session_state["cond_mejorada_met"], 
                                           key="cond_mejorada_display_met", 
                                           height=80)
        
        acciones_met = st.text_area(
            "Acciones Realizadas",
            value="El personal se encuentra de manera preventiva para atender cualquier eventualidad que se pueda suscitar en la zona.",
            height=80,
            key="acc_met"
        )
        
        # === IA === Botón para mejorar acciones meteorológicas
        col_acc_met_btn1, col_acc_met_btn2 = st.columns([3, 1])
        with col_acc_met_btn2:
            if st.button("✨ IA Acciones", key="btn_ia_acc_met"):
                if acciones_met.strip():
                    with st.spinner("🤖 Mejorando..."):
                        acc_mejorada_met = mejorar_redaccion_ia(acciones_met, "acciones realizadas")
                        st.session_state["acc_mejorada_met"] = acc_mejorada_met
                else:
                    st.warning("Escribe algo primero")
        
        if "acc_mejorada_met" in st.session_state:
            acciones_met = st.text_area("Acciones mejoradas (copia este texto)", 
                                        value=st.session_state["acc_mejorada_met"], 
                                        key="acc_mejorada_display_met", 
                                        height=80)

        if 'reporte_met_generado' not in st.session_state:
            st.session_state.reporte_met_generado = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🌤️ GENERAR REPORTE METEOROLÓGICO", use_container_width=True, key="btn_rm"):
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            nombre_dia = dias[fecha_met.weekday()].capitalize()
            fecha_str_met = f"{nombre_dia} {fecha_met.strftime('%d/%m/%Y')}"

            st.session_state.reporte_met_generado = f"""*REPORTE METEOROLOGICO*

*ESTADO:* {estado_met}
*ESTACION:* {estacion_met}
*FECHA:* {fecha_str_met}
*HORA:* {hora_met}

*CAPACIDAD OPERATIVA:* {capacidad_op}

*CONDICIONES ATMOSFÉRICAS:* {condiciones_met}

*ACCIONES REALIZADAS:*
{acciones_met}"""

        if st.session_state.reporte_met_generado:
            st.subheader("📋 Reporte Meteorológico Formateado (Listo para WhatsApp)")
            st.code(st.session_state.reporte_met_generado, language=None)
    # ---------------------------------------------------------
    # SUBMÓDULO: REPORTE DE UNIDADES
    # ---------------------------------------------------------
    with tab_ru:
        st.subheader("🚒 Reporte de Unidades")

        col_ru1, col_ru2 = st.columns(2)
        with col_ru1:
            hora_unidad = st.time_input("Hora", datetime.now().time(), key="hora_unidad")
            fecha_unidad = st.date_input("Fecha", datetime.now(), key="fecha_unidad")

        with col_ru2:
            # Selector de tipo de unidad
            tipo_unidad = st.selectbox(
                "Tipo de Unidad",
                [
                    "UNIDAD PARTICULAR",
                    "UNIDAD TIPO MOTO",
                    "UNIDAD 4.4 (Transporte de Personal)",
                    "UNIDAD 4.2 (Cisterna)"
                ],
                key="tipo_unidad"
            )

            # Si es tipo moto o particular, pedir número de dos dígitos
            if tipo_unidad == "UNIDAD PARTICULAR" or tipo_unidad == "UNIDAD TIPO MOTO":
                num_unidad = st.number_input(
                    "Número de Unidad (dos dígitos)",
                    min_value=1,
                    max_value=99,
                    value=41,
                    step=1,
                    key="num_unidad"
                )
                unidad_completa = f"{tipo_unidad} {num_unidad:02d}"
            else:
                unidad_completa = tipo_unidad

        st.subheader("👥 Personal")
        col_ru3, col_ru4 = st.columns(2)
        with col_ru3:
            comandante_comision = st.text_input(
                "Comandante de Comisión",
                "",
                placeholder="Ej: C/1(B) Brito Pedro",
                key="comandante_comision"
            )
        with col_ru4:
            operador_conductor = st.text_input(
                "Operador/Conductor",
                "",
                placeholder="Ej: S/1 (B) Díaz Jorge",
                key="operador_conductor"
            )

        st.subheader("📍 Ubicación")
        col_ru5, col_ru6 = st.columns(2)
        with col_ru5:
            municipios_carabobo_unidad = {
                "Bejuma": ["Bejuma", "Chirgua", "Simón Bolívar"],
                "Carlos Arvelo": ["Güigüe", "Tacarigua", "Belén"],
                "Diego Ibarra": ["Mariara", "Aguas Calientes"],
                "Guacara": ["Guacara", "Ciudad Alianza", "Yagua"],
                "Juan José Mora": ["Morón", "Urama"],
                "Libertador": ["Tocuyito", "Independencia"],
                "Los Guayos": ["Los Guayos"],
                "Miranda": ["Miranda"],
                "Montalbán": ["Montalbán"],
                "Naguanagua": ["Naguanagua"],
                "Puerto Cabello": ["Puerto Cabello", "Democracia", "Fraternidad", "Goaigoaza", "Juan José Flores", "Patanemo", "Borburata"],
                "San Diego": ["San Diego"],
                "San Joaquín": ["San Joaquín"]
            }
            municipio_unidad = st.selectbox(
                "Municipio",
                list(municipios_carabobo_unidad.keys()),
                index=list(municipios_carabobo_unidad.keys()).index("San Diego"),
                key="municipio_unidad"
            )
        with col_ru6:
            parroquia_unidad = st.selectbox(
                "Parroquia",
                municipios_carabobo_unidad[municipio_unidad],
                key="parroquia_unidad"
            )

        estado_unidad = st.text_input("Estado", "Carabobo", key="estado_unidad")
        sector_unidad = st.text_input(
            "Sector / Lugar de referencia",
            "",
            placeholder="Ej: Terminal de pasajeros Big Low Center, zona industrial Castillo",
            key="sector_unidad"
        )

        ubicacion_unidad = f"Parroquia {parroquia_unidad}, Municipio {municipio_unidad}, {sector_unidad}, Estado {estado_unidad}"

        st.subheader("👥 Efectivos y Motivo")
        cantidad_efectivos_unidad = st.number_input(
            "Cantidad de Efectivos",
            min_value=1,
            value=4,
            step=1,
            key="cantidad_efectivos_unidad"
        )

        motivo_unidad = st.text_area(
            "Motivo:",
            placeholder="Ejemplo: Reporta C/1 (B) Brito Pedro que se encuentran en el lugar antes mencionado...",
            height=120,
            key="motivo_unidad"
        )

        # === IA === Botón para mejorar motivo
        col_mot_btn1, col_mot_btn2 = st.columns([3, 1])
        with col_mot_btn2:
            if st.button("✨ IA Motivo", key="btn_ia_motivo_unidad"):
                if motivo_unidad.strip():
                    with st.spinner("🤖 Mejorando..."):
                        motivo_mejorado = mejorar_redaccion_ia(motivo_unidad, "motivo de unidad")
                        st.session_state["motivo_mejorado_unidad"] = motivo_mejorado
                else:
                    st.warning("Escribe algo primero")

        if "motivo_mejorado_unidad" in st.session_state:
            motivo_unidad = st.text_area(
                "Motivo mejorado (copia este texto):",
                value=st.session_state["motivo_mejorado_unidad"],
                key="motivo_mejorado_display_unidad",
                height=120
            )

        analista_unidad = st.text_input(
            "Analista que Registra",
            "",
            placeholder="Indique el rango y nombre",
            key="analista_unidad"
        )

        if 'reporte_unidad_generado' not in st.session_state:
            st.session_state.reporte_unidad_generado = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚒 GENERAR REPORTE DE UNIDAD", use_container_width=True, key="btn_generar_unidad"):
            if not motivo_unidad.strip():
                st.warning("⚠️ Por favor complete el motivo.")
            else:
                dias_semana_unidad = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dia_str_unidad = dias_semana_unidad[fecha_unidad.weekday()]
                fecha_str_unidad = f"{dia_str_unidad} {fecha_unidad.strftime('%d/%m/%Y')}"

                st.session_state.reporte_unidad_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGOS*

*CUERPO DE BOMBEROS FORESTALES INPARQUES*

*COORDINACIÓN FORESTAL CARABOBO*

*EBF LAS JOSEFINAS*

*REPORTE DE {unidad_completa}*

*FECHA:* {fecha_str_unidad}

*HORA:* {hora_unidad.strftime('%H:%M')} HRS

*UNIDAD:* {unidad_completa}

*COMANDANTE DE COMISIÓN:* {comandante_comision}

*OPERADOR/CONDUCTOR:* {operador_conductor}

*UBICACIÓN:* {ubicacion_unidad}

*CANTIDAD DE EFECTIVOS:* {cantidad_efectivos_unidad:02d}

*MOTIVO:* 
{motivo_unidad}

*ANALISTA:* {analista_unidad}"""

        if st.session_state.reporte_unidad_generado:
            st.subheader("📋 Reporte de Unidad Formateado (Listo para copiar a WhatsApp)")
            st.code(st.session_state.reporte_unidad_generado, language=None)
