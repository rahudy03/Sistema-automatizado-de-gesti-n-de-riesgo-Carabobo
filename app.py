import os
import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WINDY_API_KEY = os.getenv("WINDY_API_KEY")

client_ai = genai.Client(api_key=GEMINI_API_KEY)
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
    
    # Vaciar el archivo para el siguiente ciclo
    with open(ARCHIVO_ACUMULADOS_DIA, "w", encoding="utf-8") as f:
        json.dump([], f)
        
    if not lista:
        return "00 (Sin servicios registrados en este periodo)"
    
    # Formatear la salida exactamente al formato personalizado
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
st.sidebar.title("Sistema de Gestion de Riesgo del Estado Carabobo, Bomberos Forestales INPARQUES")
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
        coord_estadal = st.text_input(
            "Coordinador Forestal Estadal", "My (B) Mendoza Luis"
        )
        jefe_estacion = st.text_input(
            "Jefe de Estación", "S/2 (B) Meléndez Alberlen"
        )
        jefe_seccion = st.text_input(
            "Jefe de Sección / Auxiliar", "C/2 (B) Berroteran Luis"
        )
        fecha_mat = st.date_input("Fecha", datetime.now(), key="f_mat")
    with col2:
        parte_num = st.text_input("Parte N°", "240-2026")
        seccion_guardia = st.text_input("Sección de Guardia", "C")
        pie_fuerza = st.number_input(
            "Pie de Fuerza Total", min_value=1, value=49, step=1
        )
        analista_mat = st.text_input("Analista de Guardia", "", key="a_mat")

    st.subheader("👥 Desglose de Personal")
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        p_guardia = st.number_input(
            "Personal de Guardia", min_value=0, value=6
        )
        p_retardado = st.number_input(
            "Personal Retardado", min_value=0, value=0
        )
        p_libre = st.number_input("Personal Libre", min_value=0, value=26)
    with c_p2:
        p_permiso = st.number_input("Personal Permiso", min_value=0, value=0)
        p_reposo = st.number_input("Personal de Reposo", min_value=0, value=4)
        p_ausente = st.number_input("Personal Ausente", min_value=0, value=0)
    with c_p3:
        p_vacaciones = st.number_input(
            "Personal de Vacaciones", min_value=0, value=2
        )
        p_comision = st.number_input(
            "Personal de Comisión", min_value=0, value=5
        )
        p_pasantes = st.number_input(
            "Personal Pasante", min_value=0, value=6
        )

    st.subheader("📝 Observaciones")
    cant_obs_mat = st.number_input(
        "Cantidad de Observaciones",
        min_value=0,
        value=0,
        step=1,
        key="num_obs_mat",
    )

    # UN SOLO CUADRO DE TEXTO PARA TODAS LAS OBSERVACIONES
    texto_observaciones_input = st.text_area(
        "Redacte las Observaciones del Parte",
        placeholder="Escriba aquí las observaciones...",
        height=100,
        key="obs_general_mat",
    )

    st.subheader("🚒 Estado de Unidades y Actividades")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        serv_nocturnos = st.number_input(
            "Servicios Nocturnos", min_value=0, value=0, key="srv_noct_mat"
        )
    with col_u2:
        actividades_mat = st.number_input(
            "Actividades", min_value=0, value=0, key="act_mat"
        )

    st.subheader("📝 Detalle de Actividades")
    texto_actividad_mat = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder=(
            "Ejemplo:\nEl día de hoy en horas matutinas se da una sesión"
            " educativa..."
        ),
        height=120,
        key="act_txt_mat",
    )

    unidades_op = st.text_area(
        "Unidades Operativas",
        ". Unidad 4.4 Transporte de Personal Matrícula AD050WM\n. Unidad UM-45"
        " Tipo Moto",
        height=80,
    )

    unidades_inop = st.text_area(
        "Unidades Inoperativas",
        ". Unidad Cisterna 4.2 (Falla de Almacenador de energía)\n. Unidad UM-41"
        " Tipo Moto (Por falla del Sistema eléctrico del Arranque)\n. Unidad"
        " UM-42 Tipo Moto (Motor)\n. Unidad UM-43 Tipo Moto (Motor)\n. Unidad"
        " UM-44 Tipo Moto (Motor)",
        height=120,
    )

    cond_meteo = st.text_input(
        "Condiciones Meteorológicas",
        "Cielo despejado en el Sector la Cumaca, Sub-Sector Fila Las Josefinas"
        " Municipio San Diego Estado Carabobo.",
    )

    if "parte_matutino_generado" not in st.session_state:
        st.session_state.parte_matutino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE MATUTINO", use_container_width=True):
        dias = [
            "lunes",
            "martes",
            "miércoles",
            "jueves",
            "viernes",
            "sábado",
            "domingo",
        ]
        nombre_dia = dias[fecha_mat.weekday()]
        fecha_str = f"{nombre_dia} {fecha_mat.strftime('%d/%m/%Y')}"

        # LÓGICA DE FORMATEO PARA LAS OBSERVACIONES
        if cant_obs_mat == 0 or not texto_observaciones_input.strip():
            texto_observaciones_ws = "00"
        else:
            texto_observaciones_ws = f"{int(cant_obs_mat):02d}\n"
            # Si el usuario metió varias líneas, les agrega viñeta a cada una
            lineas_obs = texto_observaciones_input.strip().splitlines()
            for obs in lineas_obs:
                if obs.strip():
                    # Si la línea ya empieza con guión no duplica la viñeta
                    if obs.strip().startswith("-"):
                        texto_observaciones_ws += f"{obs.strip()}\n"
                    else:
                        texto_observaciones_ws += f"- {obs.strip()}\n"

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
        st.subheader(
            "📋 Parte Matutino Formateado (Listo para copiar a WhatsApp)"
        )
        st.code(st.session_state.parte_matutino_generado, language=None)
# =========================================================
# MÓDULO 2: PARTE VESPERTINO
# =========================================================
elif opcion_modulo == "RESUMEN VESPERTINO":
    st.header("🌆 Parte Vespertino")

    st.subheader("📌 Datos Principales")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        estacion_vesp = st.text_input(
            "Estación", "EBF LAS JOSEFINAS", key="est_vesp"
        )
        fecha_vesp = st.date_input("Fecha", datetime.now(), key="f_vesp")
    with col_v2:
        serv_realizados = st.number_input(
            "Servicios Realizados", min_value=0, value=0, key="sr_vesp"
        )
        actividades_vesp = st.number_input(
            "Actividades", min_value=0, value=1, key="act_vesp"
        )

    st.subheader("📝 Actividad Realizada")
    texto_actividad = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder=(
            "Ejemplo:\nEl día de hoy en horas matutinas se da una sesión"
            " educativa al personal pasante..."
        ),
        height=120,
        key="act_txt_vesp",
    )

    st.subheader("📋 Observaciones")
    cant_obs_vesp = st.number_input(
        "Cantidad de Observaciones",
        min_value=0,
        value=0,
        step=1,
        key="c_obs_vesp",
    )

    # UN SOLO CUADRO DE TEXTO PARA TODAS LAS OBSERVACIONES
    texto_obs_input_vesp = st.text_area(
        "Redacte las Observaciones del Parte",
        placeholder="Escriba las observaciones aquí...",
        height=100,
        key="obs_general_vesp",
    )

    st.subheader("🌤️ Clima y Analista")
    cond_meteo_vesp = st.text_input(
        "Condiciones Meteorológicas",
        "Cielo Despejado en el Sector La Cumaca, parroquia San Diego,"
        " Municipio San Diego, Estado Carabobo.",
        key="meteo_vesp",
    )
    analista_vesp = st.text_input(
        "Analista que Registra", "Pasante Escalona M", key="a_vesp"
    )

    if "parte_vespertino_generado" not in st.session_state:
        st.session_state.parte_vespertino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE VESPERTINO", use_container_width=True):
        dias = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]
        nombre_dia = dias[fecha_vesp.weekday()]
        fecha_str = f"{nombre_dia} {fecha_vesp.strftime('%d/%m/%Y')}"

        # LÓGICA DE FORMATEO DE OBSERVACIONES
        if cant_obs_vesp == 0 or not texto_obs_input_vesp.strip():
            texto_observaciones_ws_v = "00"
        else:
            texto_observaciones_ws_v = f"{int(cant_obs_vesp):02d}\n"
            lineas_obs = texto_obs_input_vesp.strip().splitlines()
            for obs in lineas_obs:
                if obs.strip():
                    if obs.strip().startswith("-"):
                        texto_observaciones_ws_v += f"{obs.strip()}\n"
                    else:
                        texto_observaciones_ws_v += f"- {obs.strip()}\n"

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
        st.subheader(
            "📋 Parte Vespertino Formateado (Listo para copiar a WhatsApp)"
        )
        st.code(st.session_state.parte_vespertino_generado, language=None)

# =========================================================
# MÓDULO 3: REPORTES DE SERVICIOS
# =========================================================
elif opcion_modulo == "REPORTES DE SERVICIOS":
    st.header("🚨 Reportes de Servicios")

    # FUNCIÓN DE IA CORREGIDA Y SEGURA CON ESPACIO DE INSTRUCCIONES
    def redactar_con_ia(texto_borrador, tipo_campo="reseña"):
        if not client_ai:
            st.error(
                "⚠️ No se ha configurado la GEMINI_API_KEY o el cliente 'client_ai' es None."
            )
            return texto_borrador, True  # Retorna (texto, hubo_error=True)

        if tipo_campo == "reseña":
            instrucciones = """
            INSTRUCCIONES:
            - Eres un redactor experto en reportes operacionales para Bomberos Forestales / INPARQUES.
            - Transforma las notas o borrador en una reseña técnica, formal e institucional en tercera persona.
            - Si el texto ingresado es un saludo casual o informal (ejemplo: 'hola amor', 'probando'), no respondas como chat. Devuelve únicamente: "S/I - El texto ingresado no contiene detalles operacionales válidos para la reseña."
            - Devuelve ÚNICAMENTE el texto redactado final sin introducciones ni comentarios adicionales.
            """
        elif tipo_campo == "acciones":
            instrucciones = """
            INSTRUCCIONES:
            - Eres un especialista en redactar cronologías operacionales para Bomberos Forestales / INPARQUES.
            - Formatea la lista de acciones cronológicamente indicando horas (ej. '08:00 Hrs Se destaca comisión...').
            - Si el texto ingresado es informal o no contiene acciones reales, devuelve únicamente: "00:00 Hrs Sin acciones operativas registradas."
            - Devuelve ÚNICAMENTE las acciones estructuradas sin comentarios adicionales.
            """
        else:  # tipo_campo == "observaciones"
            instrucciones = """
            INSTRUCCIONES:
            - Eres un redactor técnico institucional para Bomberos Forestales / INPARQUES.
            - Redacta y mejora las observaciones proporcionadas garantizando ortografía, coherencia y lenguaje técnico institucional.
            - Mantén la estructura de lista o puntos si hay varias observaciones.
            - Si el texto ingresado no aporta datos técnicos relevantes o es informal, devuelve el texto de manera corregida y formal sin inventar información.
            - Devuelve ÚNICAMENTE las observaciones redactadas finales sin introducciones ni comentarios adicionales.
            """

        prompt = (
            f"{instrucciones}\n\nEntrada del usuario:\n\"{texto_borrador}\"\n\nSalida redactada:"
        )

        try:
            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip(), False  # Éxito
            else:
                st.error("⚠️ La IA no devolvió ninguna respuesta (respuesta vacía).")
                return texto_borrador, True
        except Exception as e:
            st.error(f"❌ Error al conectar con la IA de Gemini: {e}")
            return texto_borrador, True

    if "lista_servicios" not in st.session_state:
        st.session_state.lista_servicios = cargar_servicios_persistencia()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        tipo_servicio = st.selectbox(
            "Tipo de Servicio", st.session_state.lista_servicios
        )

        with st.expander("➕ / 🗑️ Agregar o Borrar Tipo de Servicio"):
            nuevo_servicio = st.text_input("Escriba un nuevo tipo de servicio:")
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Guardar nuevo", use_container_width=True):
                    if (
                        nuevo_servicio
                        and nuevo_servicio.upper()
                        not in st.session_state.lista_servicios
                    ):
                        st.session_state.lista_servicios.append(
                            nuevo_servicio.upper()
                        )
                        guardar_servicios_persistencia(
                            st.session_state.lista_servicios
                        )
                        st.success("¡Servicio agregado y guardado!")
                        st.rerun()
            with c_btn2:
                if st.button("Borrar actual", use_container_width=True):
                    if len(st.session_state.lista_servicios) > 1:
                        st.session_state.lista_servicios.remove(tipo_servicio)
                        guardar_servicios_persistencia(
                            st.session_state.lista_servicios
                        )
                        st.success("¡Servicio eliminado!")
                        st.rerun()
                    else:
                        st.error("No puedes borrar todos los servicios.")

        fecha_srv = st.date_input(
            "Fecha del Servicio", datetime.now(), key="f_srv"
        )
        hora_inicio = st.time_input(
            "Hora de Inicio", datetime.now().time(), key="h_ini"
        )
        num_servicio = st.text_input(
            "Número de Servicio", "", placeholder="Ej: 04-0267-2026"
        )

        st.markdown("📍 **Ubicación Geográfica**")
        
        # Diccionario estructurado idéntico al módulo de incendios
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

        # Desplegables igualados al módulo de incendios
        srv_municipio = st.selectbox("Municipio", list(municipios_carabobo.keys()), index=list(municipios_carabobo.keys()).index("Puerto Cabello"), key="s_mun")
        srv_parroquia = st.selectbox("Parroquia", municipios_carabobo[srv_municipio], key="s_par")
        srv_estado = st.text_input("Estado", "Carabobo", key="s_est")

        srv_sector = st.text_input(
            "Sub-sector / Sector",
            "Sector isla larga, Sub-sector insular",
            key="s_sec",
        )
        ubicacion_srv = (
            f"{srv_sector}, Parroquia {srv_parroquia}, Municipio"
            f" {srv_municipio}, Estado {srv_estado}"
        )

        jefe_comision = st.text_input(
            "Jefe de Comisión", "", placeholder="Indique el rango y nombre"
        )

    with col_s2:
        estatus_srv = st.selectbox("Estatus", ["en proceso", "Finalizado"])
        hora_fin = st.time_input(
            "Hora de Finalizado", datetime.now().time(), key="h_fin"
        )
        efectivos_srv = st.number_input(
            "Número de Efectivos", min_value=1, value=3, step=1
        )
        latitud_srv = st.number_input(
            "Latitud", value=10.3047984, format="%.7f", key="lat_srv"
        )
        longitud_srv = st.number_input(
            "Longitud", value=-67.9307846, format="%.7f", key="lon_srv"
        )

    # --- SECCIÓN OBSERVACIONES CON IA (ÚNICO CUADRO DE TEXTO) ---
    st.subheader("📌 Observaciones")
    num_observaciones = st.number_input(
        "Cantidad de Observaciones",
        min_value=0,
        value=0,
        step=1,
        key="num_obs",
    )

    obs_texto_srv = st.text_area(
        "Redacte las Observaciones",
        placeholder="Escriba las observaciones del servicio aquí...",
        height=100,
        key="obs_general_srv",
    )

    if st.button("✨ Mejorar observaciones con IA", key="btn_ia_obs_srv"):
        if obs_texto_srv.strip():
            with st.spinner("Mejorando observaciones con IA..."):
                obs_formateada, hubo_error = redactar_con_ia(
                    obs_texto_srv, tipo_campo="observaciones"
                )
                if not hubo_error:
                    st.session_state["obs_general_srv"] = obs_formateada
                    st.rerun()
        else:
            st.warning(
                "⚠️ Ingrese un texto en las observaciones antes de solicitar la mejora con IA."
            )

    st.subheader("🚓 Organismos Presentes")

    if "lista_org_oficiales" not in st.session_state:
        st.session_state.lista_org_oficiales = (
            cargar_organismos_persistencia()
        )

    org_seleccionados = st.multiselect(
        "Seleccione los organismos que asistieron (Opcional)",
        st.session_state.lista_org_oficiales,
        default=[],
    )

    with st.expander("➕ Agregar organismo de seguridad"):
        nuevo_org = st.text_input("Escriba el nombre del organismo:")
        if st.button("Añadir Organismo"):
            if nuevo_org and nuevo_org.upper() not in [
                o.upper() for o in st.session_state.lista_org_oficiales
            ]:
                if "OTRO" in st.session_state.lista_org_oficiales:
                    st.session_state.lista_org_oficiales.insert(
                        -1, nuevo_org.upper()
                    )
                else:
                    st.session_state.lista_org_oficiales.append(
                        nuevo_org.upper()
                    )
                guardar_organismos_persistencia(
                    st.session_state.lista_org_oficiales
                )
                st.success("¡Organismo agregado y guardado!")
                st.rerun()

    cantidades_org = {}
    if org_seleccionados:
        cols_org = st.columns(4)
        for idx, org in enumerate(org_seleccionados):
            with cols_org[idx % 4]:
                sigla_mostrar = org.split(" (")[0]
                cantidades_org[org] = st.number_input(
                    sigla_mostrar, min_value=1, value=1, step=1, key=f"cant_{org}"
                )

    st.subheader("📝 Reseña y Acciones Operativas")

    # --- CAMPO RESEÑA CON IA ---
    st.markdown("**Reseña:**")
    resena_borrador = st.text_area(
        "Reseña:",
        placeholder=(
            "Ejemplo: por instrucciones del jefe de Estacion S/2 (B) Meléndez Alberlen..."
        ),
        height=100,
        key="resena_borrador_key",
        label_visibility="collapsed",
    )
    if st.button("✨ Mejorar redacción con IA", key="btn_ia_resena_srv"):
        borrador_resena = st.session_state.get("resena_borrador_key", "")
        if borrador_resena.strip():
            with st.spinner("Procesando redacción técnica con IA..."):
                resena_formateada, hubo_error = redactar_con_ia(
                    borrador_resena, tipo_campo="reseña"
                )
                if not hubo_error:
                    st.session_state["resena_borrador_key"] = resena_formateada
                    st.rerun()
        else:
            st.warning(
                "⚠️ Ingrese un borrador o notas en el campo de reseña primero."
            )

    # --- CAMPO ACCIONES CON IA ---
    st.markdown("<br>**Acciones Realizadas:**", unsafe_allow_html=True)
    acciones_borrador = st.text_area(
        "Acciones Realizadas:",
        placeholder="Ejemplo: 07:29 Hrs Se destaca comisión bomberil...",
        height=150,
        key="acciones_borrador_key",
        label_visibility="collapsed",
    )
    if st.button("✨ Mejorar redacción con IA", key="btn_ia_acciones_srv"):
        borrador_acc = st.session_state.get("acciones_borrador_key", "")
        if borrador_acc.strip():
            with st.spinner("Organizando acciones con IA..."):
                acciones_formateadas, hubo_error = redactar_con_ia(
                    borrador_acc, tipo_campo="acciones"
                )
                if not hubo_error:
                    st.session_state["acciones_borrador_key"] = (
                        acciones_formateadas
                    )
                    st.rerun()
        else:
            st.warning(
                "⚠️ Ingrese las acciones realizadas en el campo primero."
            )

    analista_srv = st.text_input(
        "Analista que Registra",
        "",
        key="a_srv",
        placeholder="Indique el rango y nombre",
    )

    if "reporte_generado" not in st.session_state:
        st.session_state.reporte_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("✨ GENERAR REPORTE PARA WHATSAPP", use_container_width=True):
        if not resena_borrador.strip() or not acciones_borrador.strip():
            st.warning(
                "⚠️ Por favor complete tanto la reseña como las acciones realizadas."
            )
        else:
            with st.spinner("🤖 Formateando el reporte..."):
                dias_semana = [
                    "Lunes",
                    "Martes",
                    "Miércoles",
                    "Jueves",
                    "Viernes",
                    "Sábado",
                    "Domingo",
                ]
                dia_str = dias_semana[fecha_srv.weekday()]

                texto_organismos_ws = ""
                if cantidades_org:
                    for org, cant in cantidades_org.items():
                        sigla_final = org.split(" (")[0]
                        texto_organismos_ws += f"{sigla_final}: {cant:02d}\n"
                else:
                    texto_organismos_ws = "00\n"

                # LÓGICA DE FORMATEO DE OBSERVACIONES
                texto_obs_usuario = st.session_state.get(
                    "obs_general_srv", ""
                ).strip()
                if num_observaciones == 0 or not texto_obs_usuario:
                    texto_observaciones_ws = "00"
                else:
                    texto_observaciones_ws = f"{int(num_observaciones):02d}\n"
                    lineas_obs = texto_obs_usuario.splitlines()
                    for obs in lineas_obs:
                        if obs.strip():
                            if obs.strip().startswith("-"):
                                texto_observaciones_ws += f"{obs.strip()}\n"
                            else:
                                texto_observaciones_ws += f"- {obs.strip()}\n"

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
{resena_borrador}

*ACCION REALIZADA*
{acciones_borrador}

*OBSERVACIONES:* {texto_observaciones_ws}
*ORGANISMOS PRESENTES* 

{texto_organismos_ws}
*CANTIDAD DE EFECTIVOS:*  {efectivos_srv:02d}

*ESTATUS:* {estatus_srv} 

*COORDENADAS:*
{latitud_srv}, {longitud_srv}

*ANALISTA:* 
{analista_srv}"""

                # Enlazar servicio para los partes
                datos_servicio = {
                    "tipo_servicio": tipo_servicio,
                    "num_servicio": num_servicio,
                    "ubicacion": ubicacion_srv,
                    "resena": resena_borrador,
                    "coordenadas": f"{latitud_srv}, {longitud_srv}",
                    "estatus": estatus_srv,
                }
                registrar_servicio_dia(datos_servicio)

    if st.session_state.reporte_generado:
        st.subheader("📋 Reporte Formateado (Listo para copiar a WhatsApp)")
        st.code(st.session_state.reporte_generado, language=None)
# =========================================================
# MÓDULO 4: REPORTES DE INCENDIOS
# =========================================================
elif opcion_modulo == "REPORTES DE INCENDIOS":
    st.header("🔥 Reportes de Incendios")

    ARCHIVO_INCENDIOS_JSON = "incendios_activos.json"

    def cargar_incendios_disco():
        if os.path.exists(ARCHIVO_INCENDIOS_JSON):
            try:
                with open(ARCHIVO_INCENDIOS_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def guardar_incendios_disco(datos):
        with open(ARCHIVO_INCENDIOS_JSON, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

    # Listas estáticas requeridas para índices
    lista_causas = [
        "Quemas de Basura", "Quemas de Pastos", "Quemas en Áreas Forestales", "Quemas Agricolas",
        "Explotaciones Forestales", "Fuegos Artificiales", "Hogueras o Fogatas", "Apicultores",
        "Pescadores", "Cazadores", "Caminantes Nocturnos", "Tendidos Eléctricos",
        "Motores y Maquinas", "Maniobras Militares", "Venganzas y Recillas", "Piromaníacos",
        "Incendiarios", "Ritos Mágicos Religiosos", "Quemas de Cables", "Desconocida", "Por Determinar"
    ]

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

    lista_abrae = [
        "P/N San Esteban", "Parque Nacional", "Zona Protectora", "Reserva Forestal",
        "Área Especial de Seguridad y Defensa", "Reserva de Fauna Silvestre",
        "Refugio de Fauna Silvestre", "Santuario de Fauna Silvestre", "Monumento Natural",
        "Zona de Interés Turístico", "Área consagrada en Tratados Internacionales", "No aplica"
    ]

    # Cargar siempre la información desde el disco
    st.session_state.incendios_activos = cargar_incendios_disco()

    # Función Callback para forzar la actualización de inputs al cambiar la selección
    def al_cambiar_incendio():
        sel = st.session_state.selector_incendio_activo
        d = st.session_state.incendios_activos.get(sel, {}) if sel != "Nuevo Incendio" else {}

        st.session_state["res_inc"] = d.get("resena", "")
        st.session_state["acc_inc"] = d.get("acciones", "")
        st.session_state["obs_texto_unico_inc"] = d.get("observaciones_texto", "")
        st.session_state["v_viento"] = d.get("viento", "")
        st.session_state["v_temp"] = d.get("temp", "")
        st.session_state["v_precip"] = d.get("precip", "0%")
        st.session_state["v_hum"] = d.get("humedad", "")
        st.session_state["v_pres"] = d.get("presion", "")
        st.session_state["select_causa_prob"] = d.get("causas_prob", lista_causas[0])

    st.subheader("📌 Cargar o Modificar un Incendio Activo")

    opciones_incendios = ["Nuevo Incendio"] + [
        k for k, v in st.session_state.incendios_activos.items() 
        if "Finalizado" not in v.get("estatus", "")
    ]

    incendio_sel = st.selectbox(
        "Seleccione un incendio en proceso para editar o cree uno nuevo:", 
        opciones_incendios,
        key="selector_incendio_activo",
        on_change=al_cambiar_incendio
    )

    datos_cargados = st.session_state.incendios_activos.get(incendio_sel, {}) if incendio_sel != "Nuevo Incendio" else {}
    if incendio_sel != "Nuevo Incendio":
        st.info(f"✏️ Editando el informe activo del Servicio Nº: **{incendio_sel}**")

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        opts_tipo_rep = ["Final", "Preliminar", "Progresivo"]
        idx_tr = opts_tipo_rep.index(datos_cargados.get("tipo_reporte", "Final")) if datos_cargados.get("tipo_reporte") in opts_tipo_rep else 0
        tipo_reporte_opcion = st.selectbox("Tipo de Reporte", opts_tipo_rep, index=idx_tr)

        if tipo_reporte_opcion == "Progresivo":
            num_prog = st.number_input("Número Progresivo", min_value=1, value=int(datos_cargados.get("num_prog", 1)), step=1, key="n_prog")
            tipo_reporte = f"Progresivo {num_prog:03d}"
        else:
            tipo_reporte = tipo_reporte_opcion

        opts_evento = ["Incendio de Vegetacion", "Incendio Forestal", "Conato de Incendio"]
        idx_ev = opts_evento.index(datos_cargados.get("tipo_incendio")) if datos_cargados.get("tipo_incendio") in opts_evento else 0
        tipo_incendio = st.selectbox("Tipo de Evento", opts_evento, index=idx_ev)

        num_servicio_inc = st.text_input("Número de Servicio", value=datos_cargados.get("num_servicio", ""), placeholder="Ej: 04-0028-2026")
        fecha_inc = st.date_input("Fecha del Evento", datetime.now(), key="f_inc")
        hora_inc = st.time_input("Hora del Reporte", datetime.now().time(), key="h_inc")
        comandante_escena = st.text_input("Comandante en Escena", value=datos_cargados.get("comandante", ""), placeholder="Ej: C/1 (B) Gutiérrez Orlando")
        estacion_ebf = st.text_input("Estación / Base", value=datos_cargados.get("estacion", "EBF Las Josefinas"))

    with col_i2:
        sub_sector = st.text_input("Sub-Sector", value=datos_cargados.get("sub_sector", "Hacienda la Cumaca"))
        sector = st.text_input("Sector", value=datos_cargados.get("sector", "La Cumaca"))

        keys_mun = list(municipios_carabobo.keys())
        idx_mun = keys_mun.index(datos_cargados.get("municipio", "San Diego")) if datos_cargados.get("municipio") in keys_mun else keys_mun.index("San Diego")
        municipio = st.selectbox("Municipio", keys_mun, index=idx_mun)

        parroquia_opts = municipios_carabobo[municipio]
        idx_parr = parroquia_opts.index(datos_cargados.get("parroquia")) if datos_cargados.get("parroquia") in parroquia_opts else 0
        parroquia = st.selectbox("Parroquia", parroquia_opts, index=idx_parr)

        estado_inc = st.text_input("Estado", value=datos_cargados.get("estado", "Carabobo"))

        idx_abrae = lista_abrae.index(datos_cargados.get("abrae")) if datos_cargados.get("abrae") in lista_abrae else 0
        abrae_inc = st.selectbox("Abrae", lista_abrae, index=idx_abrae)

    st.subheader("📍 Coordenadas y Ubicación")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        lat_inc = st.number_input("Latitud", value=float(datos_cargados.get("lat", 10.290985)), format="%.6f", key="lat_inc")
    with col_c2:
        lon_inc = st.number_input("Longitud", value=float(datos_cargados.get("lon", -67.959402)), format="%.6f", key="lon_inc")

    st.subheader("📊 Afectación y Recursos")
    causas_prob = st.selectbox("Causas Probables", lista_causas, key="select_causa_prob")

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        efectivos_inc = st.number_input("Cantidad de Efectivos (BFI)", min_value=1, value=int(datos_cargados.get("efectivos", 10)), step=1, key="ef_inc")
        recursos_disp_text = st.text_area("Recursos Disponibles (Uno por línea)", value=datos_cargados.get("recursos", "Batidor Forestal"), height=100)
        unidades_disp_text = st.text_area("Unidades (Una por línea)", value=datos_cargados.get("unidades", "Unidad Tipo Moto 41"), height=100)

    with col_r2:
        area_herbacea = st.number_input("Área Herbacea (Baja) en ha", min_value=0.0, value=float(datos_cargados.get("area_herba", 13.7)), step=0.1)
        area_arbustiva = st.number_input("Área Arbustiva (Media) en ha", min_value=0.0, value=float(datos_cargados.get("area_arbus", 3.0)), step=0.1)
        area_arboria = st.number_input("Área Arbórea (Alta) en ha", min_value=0.0, value=float(datos_cargados.get("area_arbor", 0.0)), step=0.1)

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
        precip_val = st.text_input("Precipitaciones (%)", key="v_precip")
    with col_at4:
        humedad_val = st.text_input("Humedad Relativa", key="v_hum")
    with col_at5:
        presion_val = st.text_input("Presión Atmosférica", key="v_pres")

    st.subheader("📝 Bitácora, Estatus y Autoridades")

    cant_obs_inc = st.number_input("Cantidad de Observaciones (Opcional)", min_value=0, value=int(datos_cargados.get("cant_obs", 0)), step=1, key="num_obs_inc")
    obs_texto_unico = st.text_area(
        "Observaciones (Una por línea):",
        placeholder="Ejemplo:\nSe requiere apoyo logístico\nCondición de terreno difícil",
        height=120,
        key="obs_texto_unico_inc"
    )

    resena_inc = st.text_area(
        "RESEÑA:",
        placeholder="Ejemplo: Durante recorrido por el sector la cumaca se visualiza una columna de humo...",
        height=100,
        key="res_inc"
    )

    acciones_inc = st.text_area(
        "ACCIÓN REALIZADA (Bitácora de Eventos):",
        placeholder="Ejemplo:\n15:10 Hrs Se destaca el Bombero Peralta Javier...\n15:15 Hrs Reporta el Bombero...",
        height=200,
        key="acc_inc"
    )

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        opts_estatus = ["en proceso", "Finalizado-combatido", "Finalizado-No combatido"]
        idx_est = opts_estatus.index(datos_cargados.get("estatus")) if datos_cargados.get("estatus") in opts_estatus else 0
        estatus_inc = st.selectbox("Estatus del Incendio", opts_estatus, index=idx_est)
    with col_e2:
        hora_envio_inc = st.time_input("Hora de Envío del Reporte", datetime.now().time(), key="h_envio_inc")
    with col_e3:
        delegado_ame = st.text_input("Delegado Estadal AME", value=datos_cargados.get("delegado", "C/2 (B) Reyes Edwin"))

    if 'incendio_generado' not in st.session_state:
        st.session_state.incendio_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔥 GENERAR REPORTE DE INCENDIO", use_container_width=True):
        if not num_servicio_inc.strip():
            st.warning("⚠️ Por favor ingrese un Número de Servicio para identificar el incendio.")
        elif not resena_inc.strip() or not acciones_inc.strip():
            st.warning("⚠️ Por favor complete la reseña y las acciones realizadas.")
        else:
            with st.spinner("🤖 Formateando el reporte de incendio..."):

                lineas_recursos = [r.strip() for r in recursos_disp_text.split("\n") if r.strip()]
                texto_recursos_disp = "\n".join([f"-{r}" if not r.startswith("-") else r for r in lineas_recursos]) if lineas_recursos else "Ninguno"

                lineas_unidades = [u.strip() for u in unidades_disp_text.split("\n") if u.strip()]
                texto_unidades_disp = "\n".join([f"-{u}" if not u.startswith("-") else u for u in lineas_unidades]) if lineas_unidades else "Ninguno"

                area_total_ha = round(area_herbacea + area_arbustiva + area_arboria, 2)

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

                lineas_obs = [linea.strip() for linea in obs_texto_unico.split("\n") if linea.strip()]
                if cant_obs_inc == 0 or not lineas_obs:
                    texto_observaciones_ws_i = "00"
                else:
                    texto_observaciones_ws_i = f"{int(cant_obs_inc):02d}\n"
                    for txt in lineas_obs:
                        texto_observaciones_ws_i += f"- {txt}\n"

                ubicacion_completa = f"{sector}, sub-sector {sub_sector}, Parroquia {parroquia}, Municipio {municipio}, Estado {estado_inc}"

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
{texto_recursos_disp}

*UNIDADES:*
{texto_unidades_disp} 

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

                datos_incendio_dia = {
                    "tipo_servicio": tipo_incendio,
                    "num_servicio": num_servicio_inc,
                    "ubicacion": ubicacion_completa,
                    "resena": resena_inc,
                    "coordenadas": f"{lat_inc}, {lon_inc}",
                    "estatus": estatus_inc,
                    "area_afectada": area_total_ha
                }

                if "registrar_servicio_dia" in globals():
                    registrar_servicio_dia(datos_incendio_dia)

                # Persistencia completa en el diccionario de datos
                dict_guardar = {
                    "tipo_reporte": tipo_reporte_opcion,
                    "num_prog": num_prog if tipo_reporte_opcion == "Progresivo" else 1,
                    "tipo_incendio": tipo_incendio,
                    "num_servicio": num_servicio_inc,
                    "comandante": comandante_escena,
                    "estacion": estacion_ebf,
                    "sector": sector,
                    "sub_sector": sub_sector,
                    "municipio": municipio,
                    "parroquia": parroquia,
                    "estado": estado_inc,
                    "abrae": abrae_inc,
                    "lat": lat_inc,
                    "lon": lon_inc,
                    "causas_prob": causas_prob,
                    "efectivos": efectivos_inc,
                    "recursos": recursos_disp_text,
                    "unidades": unidades_disp_text,
                    "area_herba": area_herbacea,
                    "area_arbus": area_arbustiva,
                    "area_arbor": area_arboria,
                    "viento": viento_vel,
                    "temp": temp_val,
                    "precip": precip_val,
                    "humedad": humedad_val,
                    "presion": presion_val,
                    "cant_obs": cant_obs_inc,
                    "observaciones_texto": obs_texto_unico,
                    "resena": resena_inc,
                    "acciones": acciones_inc,
                    "estatus": estatus_inc,
                    "delegado": delegado_ame
                }

                if "Finalizado" in estatus_inc:
                    if num_servicio_inc in st.session_state.incendios_activos:
                        del st.session_state.incendios_activos[num_servicio_inc]
                        guardar_incendios_disco(st.session_state.incendios_activos)
                else:
                    st.session_state.incendios_activos[num_servicio_inc] = dict_guardar
                    guardar_incendios_disco(st.session_state.incendios_activos)

                st.success("¡Reporte generado y sincronizado con el registro diario!")

    if st.session_state.incendio_generado:
        st.subheader("📋 Reporte de Incendio Formateado")
        st.code(st.session_state.incendio_generado, language=None)
# =========================================================
# MÓDULO 5: REPORTES MIXTOS
# =========================================================
elif opcion_modulo == "REPORTES MIXTOS":
    st.header("📄 Reportes Mixtos")

    tab_ni, tab_rm, tab_ru = st.tabs(["📌 Nota Informativa", "🌤️ Reporte Meteorológico", "🚛 Reporte de Unidades"])

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
        
        acciones_met = st.text_area(
            "Acciones Realizadas",
            value="El personal se encuentra de manera preventiva para atender cualquier eventualidad que se pueda suscitar en la zona.",
            height=80,
            key="acc_met"
        )

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
    # SUBMÓDULO: REPORTE DE UNIDAD
    # ---------------------------------------------------------
    with tab_ru:
        st.subheader("🚛 Generar Reporte de Unidad")

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            tipo_unidad_sel = st.selectbox(
                "Tipo de Unidad",
                [
                    "UNIDAD PARTICULAR",
                    "UNIDAD 4.2 CISTERNA",
                    "UNIDAD 4.4 TRANSPORTE DE PERSONAL",
                    "UNIDAD UM-"
                ],
                key="sel_tipo_u"
            )

            if tipo_unidad_sel == "UNIDAD UM-":
                num_um = st.text_input("Número de dos dígitos para UM-", "01", max_chars=2, key="num_um_input")
                nombre_unidad_header = f"REPORTE DE UNIDAD UM-{num_um}"
            else:
                nombre_unidad_header = f"REPORTE DE {tipo_unidad_sel}"

            hora_unid = st.text_input("Hora", "12:52 HRS", key="h_unid")
            detalle_unidad = st.text_input(
                "Detalles de la Unidad",
                "Tipo Moto Particular Modelo Caracal Murasaki Placa AM9H06G",
                key="det_unid"
            )
            comision_unid = st.text_input("Comandante de Comisión", "C/1 (B) Orlando Gutiérrez", key="com_unid")
            operador_unid = st.text_input("Operador / Conductor", "Bombero Peralta Javier", key="op_unid")
            efectivos_unid = st.number_input("Cantidad de Efectivos", min_value=1, value=2, step=1, key="ef_unid")

        with col_u2:
            st.markdown("**📍 Ubicación del Evento**")
            sub_sector_u = st.text_input("Sub-Sector", "pueblo de San Diego", key="sub_sec_u")
            sector_u = st.text_input("Sector", "San Diego", key="sec_u")

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

            municipio_u = st.selectbox(
                "Municipio",
                list(municipios_carabobo.keys()),
                index=list(municipios_carabobo.keys()).index("San Diego"),
                key="muni_u"
            )
            parroquia_u = st.selectbox("Parroquia", municipios_carabobo[municipio_u], key="parr_u")
            estado_u = st.text_input("Estado", "Carabobo", key="est_u")

            motivo_unid = st.text_area("Motivo", "A realizar diligencias varias", height=80, key="mot_unid")

        if 'reporte_unidad_generado' not in st.session_state:
            st.session_state.reporte_unidad_generado = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚛 GENERAR REPORTE DE UNIDAD", use_container_width=True, key="btn_ru"):
            
            # Construcción estructurada de la ubicación como en los demás servicios
            texto_ubicacion = f"{sub_sector_u}, sector {sector_u}, parroquia {parroquia_u}, municipio {municipio_u}, Estado {estado_u}"

            st.session_state.reporte_unidad_generado = f"""*{nombre_unidad_header}*

*HORA:* {hora_unid}

*UNIDAD:* {detalle_unidad}

*COMANDANTE DE COMISIÓN:*
{comision_unid}

*OPERADOR/ CONDUCTOR:*
{operador_unid}

*CANTIDAD DE EFECTIVOS:* {efectivos_unid:02d}

*UBICACIÓN:* {texto_ubicacion}

*MOTIVO:* {motivo_unid}"""

        if st.session_state.reporte_unidad_generado:
            st.subheader("📋 Reporte de Unidad Formateado (Listo para WhatsApp)")
            st.code(st.session_state.reporte_unidad_generado, language=None)