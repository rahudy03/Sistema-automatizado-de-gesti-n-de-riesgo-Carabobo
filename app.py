import json
import os
import streamlit as st
from datetime import datetime
import requests
from openai import OpenAI

# =========================================================
# CONFIGURACIÓN DE API KEYS DESDE secrets.toml
# =========================================================
WINDY_API_KEY = st.secrets["WINDY_API_KEY"]
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]

# =========================================================
# FUNCIÓN DE IA PARA MEJORAR REDACCIÓN
# =========================================================

def mejorar_redaccion_ia(texto, tipo_texto="general"):
    """Mejora la redacción usando DeepSeek con prompts optimizados por tipo."""
    if not texto.strip():
        return "Sin información adicional registrada."

    client = OpenAI(
        base_url="https://api.deepseek.com",
        api_key=DEEPSEEK_API_KEY,
    )

    base = "Corrige y redacta de forma muy técnica bomberil. Mantén esencia y estructura original. corrige rangos: 1er Gral, Gral, Tcnl, My, Cap, 1er Tte, Tte, S/M, S/1, S/2, C/1, C/2, Dtgdo (todos con (B)), Bbra, Bbro, Pste. Mantén unidades tal cual: UM-41, 4.4, 4.2, etc."

    instrucciones = {
                "reseña": 'Reseña: pasado, tercera persona, un párrafo fluido.',
        "reseña de incendio": 'Reseña: pasado, tercera persona, un párrafo fluido.',
        "acciones realizadas": 'Acciones: formato "HH:MM Hrs descripción de la acción", 24 horas. Agregar al comienzo "Reporta vía WhatsApp el Jefe de Comisión" excepto en la primera hora y donde se especifica quién reporta. Si ya se menciona otro medio (radio, teléfono), no agregar WhatsApp.',
        "observación": 'Observación: breve, directo, tono formal, solo hechos concretos.',
        "actividad": 'Actividad: pasado, tercera persona. Describe la actividad realizada.',
        "nota informativa": 'Nota informativa: tono institucional formal.',
        "condiciones meteorológicas": 'Condiciones: describe clima de forma técnica.',
        "motivo de unidad": 'Motivo: se breve.',"ejecutivo": 'Redacta un resumen ejecutivo de los hechos sin horas ni quién reporta. Formato: un párrafo fluido en pasado, tercera persona sin titulos.',
        "general": 'Corrige y redacta de forma muy técnica bomberil. Mantén esencia y estructura original. Rangos: 1er Gral, Gral, Tcnl, My, Cap, 1er Tte, Tte, S/M, S/1, S/2, C/1, C/2, Dtgdo (todos con (B)), Bbra, Bbro, Pste. Mantén unidades tal cual: UM-41, 4.4, 4.2, etc.'
    }

    instruccion = instrucciones.get(tipo_texto, "")

    prompt = f"""{base} {instruccion}

Devuelve SOLO el texto mejorado, sin frases adicionales.

TEXTO:
{texto}

MEJORADO:"""

    modelos = [
        "deepseek-chat"
    ]
    
    if "modelo_actual" not in st.session_state:
        st.session_state["modelo_actual"] = 0
    
    for intento in range(len(modelos)):
        indice_modelo = (st.session_state["modelo_actual"] + intento) % len(modelos)
        modelo_elegido = modelos[indice_modelo]
        
        try:
            response = client.chat.completions.create(
                model=modelo_elegido,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            st.session_state["modelo_actual"] = (indice_modelo + 1) % len(modelos)
            return response.choices[0].message.content.strip()
        except:
            continue
    
    st.warning("⚠️ Se excedió el límite de solicitudes. Intenta más tarde.")
    texto_limpio = texto.strip().capitalize()
    if not texto_limpio.endswith('.'):
        texto_limpio += '.'
    return texto_limpio

# =========================================================
# CONFIGURACIÓN GENERAL Y CONSTANTES
# =========================================================
ARCHIVO_SERVICIOS = "servicios_disponibles.json"
ARCHIVO_ORGANISMOS = "organismos_disponibles.json"
ARCHIVO_CAUSAS = "causas_disponibles.json"
ARCHIVO_ACUMULADOS_DIA = "servicios_acumulados.json"
ARCHIVO_PRELIMINARES = "incendios_preliminares.json"
ARCHIVO_UBICACIONES = "ubicaciones_carabobo.json"
ARCHIVO_MEMORIA = "ultimo_reporte.json"

def guardar_memoria(clave, valor):
    """Guarda un valor en la memoria persistente."""
    memoria = {}
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
                memoria = json.load(f)
        except:
            pass
    memoria[clave] = valor
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)

def cargar_memoria(clave, default=""):
    """Carga un valor de la memoria persistente."""
    if os.path.exists(ARCHIVO_MEMORIA):
        try:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
                memoria = json.load(f)
            return memoria.get(clave, default)
        except:
            pass
    return default

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
        return "00"
    
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

def guardar_incendio_preliminar(datos_incendio):
    """Guarda o actualiza un incendio en proceso."""
    lista = []
    if os.path.exists(ARCHIVO_PRELIMINARES):
        try:
            with open(ARCHIVO_PRELIMINARES, "r", encoding="utf-8") as f:
                lista = json.load(f)
        except:
            lista = []
    
    datos_incendio["fecha_modificacion"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    num_servicio = datos_incendio.get("num_servicio", "")
    encontrado = False
    for i, item in enumerate(lista):
        if item.get("num_servicio") == num_servicio and num_servicio:
            lista[i] = datos_incendio
            encontrado = True
            break
    
    if not encontrado:
        lista.append(datos_incendio)
    
    with open(ARCHIVO_PRELIMINARES, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)

def cargar_incendios_preliminares():
    """Carga los incendios en proceso guardados."""
    if not os.path.exists(ARCHIVO_PRELIMINARES):
        return []
    try:
        with open(ARCHIVO_PRELIMINARES, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def eliminar_incendio_preliminar(indice_o_num_servicio):
    """Elimina un incendio en proceso por índice o número de servicio."""
    lista = cargar_incendios_preliminares()
    
    if isinstance(indice_o_num_servicio, int):
        if 0 <= indice_o_num_servicio < len(lista):
            lista.pop(indice_o_num_servicio)
    else:
        lista = [item for item in lista if item.get("num_servicio") != indice_o_num_servicio]
    
    with open(ARCHIVO_PRELIMINARES, "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=4)
    return True

def obtener_numero_progresivo(num_servicio):
    """Obtiene el siguiente número progresivo para un incendio."""
    preliminares = cargar_incendios_preliminares()
    
    for preliminar in preliminares:
        if preliminar.get("num_servicio") == num_servicio:
            progresivos = preliminar.get("progresivos", [])
            if progresivos:
                return progresivos[-1] + 1
            else:
                return 1
    
    return 1

def guardar_progresivo(num_servicio, numero_progresivo, datos_actualizados):
    """Guarda o actualiza un progresivo específico."""
    preliminares = cargar_incendios_preliminares()
    
    for i, preliminar in enumerate(preliminares):
        if preliminar.get("num_servicio") == num_servicio:
            if "progresivos" not in preliminar:
                preliminar["progresivos"] = []
                preliminar["historial_progresivos"] = []
            
            if numero_progresivo not in preliminar["progresivos"]:
                preliminar["progresivos"].append(numero_progresivo)
            
            preliminar["historial_progresivos"].append({
                "numero": numero_progresivo,
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "datos": datos_actualizados
            })
            
            preliminares[i] = preliminar
            break
    
    with open(ARCHIVO_PRELIMINARES, "w", encoding="utf-8") as f:
        json.dump(preliminares, f, ensure_ascii=False, indent=4)

def cargar_ubicaciones():
    """Carga la estructura de estados, municipios, parroquias, sectores y sub-sectores."""
    default_ubicaciones = {
        "Carabobo": {
            "municipios": {
                "Bejuma": {
                    "parroquias": ["Bejuma", "Chirgua", "Simón Bolívar"],
                    "sectores": {
                        "Bejuma": [],
                        "Chirgua": [],
                        "Simón Bolívar": []
                    }
                },
                "Carlos Arvelo": {
                    "parroquias": ["Güigüe", "Tacarigua", "Belén"],
                    "sectores": {
                        "Güigüe": [],
                        "Tacarigua": [],
                        "Belén": []
                    }
                },
                "Diego Ibarra": {
                    "parroquias": ["Mariara", "Aguas Calientes"],
                    "sectores": {
                        "Mariara": [],
                        "Aguas Calientes": []
                    }
                },
                "Guacara": {
                    "parroquias": ["Guacara", "Ciudad Alianza", "Yagua"],
                    "sectores": {
                        "Guacara": [],
                        "Ciudad Alianza": [],
                        "Yagua": []
                    }
                },
                "Juan José Mora": {
                    "parroquias": ["Morón", "Urama"],
                    "sectores": {
                        "Morón": [],
                        "Urama": []
                    }
                },
                "Libertador": {
                    "parroquias": ["Tocuyito", "Independencia"],
                    "sectores": {
                        "Tocuyito": [],
                        "Independencia": []
                    }
                },
                "Los Guayos": {
                    "parroquias": ["Los Guayos"],
                    "sectores": {
                        "Los Guayos": []
                    }
                },
                "Miranda": {
                    "parroquias": ["Miranda"],
                    "sectores": {
                        "Miranda": []
                    }
                },
                "Montalbán": {
                    "parroquias": ["Montalbán"],
                    "sectores": {
                        "Montalbán": []
                    }
                },
                "Naguanagua": {
                    "parroquias": ["Naguanagua"],
                    "sectores": {
                        "Naguanagua": []
                    }
                },
                "Puerto Cabello": {
                    "parroquias": ["Puerto Cabello", "Democracia", "Fraternidad", "Goaigoaza", "Juan José Flores", "Patanemo", "Borburata"],
                    "sectores": {
                        "Puerto Cabello": [],
                        "Democracia": [],
                        "Fraternidad": [],
                        "Goaigoaza": [],
                        "Juan José Flores": [],
                        "Patanemo": [],
                        "Borburata": ["Isla Larga"]
                    }
                },
                "San Diego": {
                    "parroquias": ["San Diego"],
                    "sectores": {
                        "San Diego": ["La Cumaca", "Hacienda La Cumaca"]
                    }
                },
                "San Joaquín": {
                    "parroquias": ["San Joaquín"],
                    "sectores": {
                        "San Joaquín": []
                    }
                }
            }
        },
        "Amazonas": {},
        "Anzoátegui": {},
        "Apure": {},
        "Aragua": {},
        "Barinas": {},
        "Bolívar": {},
        "Cojedes": {},
        "Delta Amacuro": {},
        "Distrito Capital": {},
        "Falcón": {},
        "Guárico": {},
        "La Guaira": {},
        "Lara": {},
        "Mérida": {},
        "Miranda": {},
        "Monagas": {},
        "Nueva Esparta": {},
        "Portuguesa": {},
        "Sucre": {},
        "Táchira": {},
        "Trujillo": {},
        "Yaracuy": {},
        "Zulia": {}
    }
    
    if os.path.exists(ARCHIVO_UBICACIONES):
        try:
            with open(ARCHIVO_UBICACIONES, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default_ubicaciones

def guardar_ubicaciones(ubicaciones):
    """Guarda la estructura de ubicaciones."""
    try:
        with open(ARCHIVO_UBICACIONES, "w", encoding="utf-8") as f:
            json.dump(ubicaciones, f, ensure_ascii=False, indent=4)
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
st.sidebar.title("Sistema Autónomo de Redacción Operativa (SARO)-BOMBEROS FORESTALES INPARQUES")
st.sidebar.markdown("---")

opcion_modulo = st.sidebar.radio(
    "Seleccione el Módulo:",
    [
        "PARTE MATUTINO",
        "PARTE VESPERTINO",
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
if opcion_modulo == "PARTE MATUTINO":
    st.header("🌅 Parte Matutino")

    st.subheader("📌 Datos del Encabezado")
    col1, col2 = st.columns(2)
    with col1:
        coord_estadal = st.text_input("Coordinador Forestal Estadal", cargar_memoria("mat_coord_estadal", "My (B) Mendoza Luis"))
        jefe_estacion = st.text_input("Jefe de Estación", cargar_memoria("mat_jefe_estacion", "S/2 (B) Meléndez Alberlen"))
        jefe_seccion = st.text_input("Jefe de Sección / Auxiliar", cargar_memoria("mat_jefe_seccion", "C/2 (B) Berroteran Luis"))
        fecha_mat = st.date_input("Fecha", datetime.now(), key="f_mat")
    with col2:
        parte_num = st.text_input("Parte N°", cargar_memoria("mat_parte_num", "240-2026"))
        seccion_guardia = st.text_input("Sección de Guardia", cargar_memoria("mat_seccion_guardia", "C"))
        pie_fuerza = st.number_input("Pie de Fuerza Total", min_value=1, value=int(cargar_memoria("mat_pie_fuerza", 49)), step=1)
        analista_mat = st.text_input("Analista de Guardia", cargar_memoria("mat_analista", ""))

    st.subheader("👥 Desglose de Personal")
    c_p1, c_p2, c_p3 = st.columns(3)
    with c_p1:
        p_guardia = st.number_input("Personal de Guardia", min_value=0, value=int(cargar_memoria("mat_p_guardia", 6)))
        p_retardado = st.number_input("Personal Retardado", min_value=0, value=int(cargar_memoria("mat_p_retardado", 0)))
        p_libre = st.number_input("Personal Libre", min_value=0, value=int(cargar_memoria("mat_p_libre", 26)))
    with c_p2:
        p_permiso = st.number_input("Personal Permiso", min_value=0, value=int(cargar_memoria("mat_p_permiso", 0)))
        p_reposo = st.number_input("Personal de Reposo", min_value=0, value=int(cargar_memoria("mat_p_reposo", 4)))
        p_ausente = st.number_input("Personal Ausente", min_value=0, value=int(cargar_memoria("mat_p_ausente", 0)))
    with c_p3:
        p_vacaciones = st.number_input("Personal de Vacaciones", min_value=0, value=int(cargar_memoria("mat_p_vacaciones", 2)))
        p_comision = st.number_input("Personal de Comisión", min_value=0, value=int(cargar_memoria("mat_p_comision", 5)))
        p_pasantes = st.number_input("Personal Pasante", min_value=0, value=int(cargar_memoria("mat_p_pasantes", 6)))

    st.subheader("🚒 Estado de Unidades y Actividades")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        serv_nocturnos = st.number_input("Servicios Nocturnos", min_value=0, value=int(cargar_memoria("mat_serv_nocturnos", 0)))
    with col_u2:
        actividades_mat = st.number_input("Actividades", min_value=0, value=int(cargar_memoria("mat_actividades", 0)))

    st.subheader("📝 Detalle de Actividades")
    
    if "mat_texto_actividad" not in st.session_state:
        st.session_state["mat_texto_actividad"] = cargar_memoria("mat_texto_actividad", "")

    texto_actividad_mat = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder="Ejemplo:\nEl día de hoy en horas matutinas se da una sesión educativa...",
        height=120,
        key="mat_texto_actividad"
    )
    
    col_act_btn1, col_act_btn2 = st.columns([3, 1])
    with col_act_btn2:
        if st.button("✨ IA Actividad", key="btn_ia_act_mat"):
            if texto_actividad_mat.strip():
                with st.spinner("🤖 Mejorando..."):
                    act_mejorada = mejorar_redaccion_ia(texto_actividad_mat, "actividad")
                    st.session_state["act_mejorada_mostrar_mat"] = act_mejorada
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "act_mejorada_mostrar_mat" in st.session_state:
        st.text_area(
            "Actividad mejorada:",
            value=st.session_state["act_mejorada_mostrar_mat"],
            key="act_mejorada_display_mat",
            height=120,
            disabled=True
        )
        
        col_conf1_act, col_conf2_act = st.columns(2)
        with col_conf1_act:
            if st.button("✅ Usar mejorado", key="btn_usar_act_mat"):
                guardar_memoria("mat_texto_actividad", st.session_state["act_mejorada_mostrar_mat"])
                del st.session_state["mat_texto_actividad"]
                del st.session_state["act_mejorada_mostrar_mat"]
                st.rerun()
        with col_conf2_act:
            if st.button("❌ Mantener original", key="btn_mantener_act_mat"):
                del st.session_state["act_mejorada_mostrar_mat"]
                st.rerun()

    st.subheader("📝 Observaciones")
    
    cant_obs_mat = st.number_input("Cantidad de Observaciones", min_value=0, value=int(cargar_memoria("mat_cant_obs", 0)), step=1)
    
    if "mat_texto_obs" not in st.session_state:
        st.session_state["mat_texto_obs"] = cargar_memoria("mat_texto_obs", "")

    texto_observaciones_mat = st.text_area(
        "Redacte las observaciones (una por línea):",
        placeholder="Ejemplo:\n- Primera observación\n- Segunda observación\n- Tercera observación",
        height=150,
        key="mat_texto_obs"
    )
    
    col_obs_btn1, col_obs_btn2 = st.columns([3, 1])
    with col_obs_btn2:
        if st.button("✨ IA Obs", key="btn_ia_obs_mat"):
            if texto_observaciones_mat.strip():
                with st.spinner("🤖 Mejorando..."):
                    obs_mejorada = mejorar_redaccion_ia(texto_observaciones_mat, "observación")
                    st.session_state["obs_mejorada_mostrar_mat"] = obs_mejorada
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "obs_mejorada_mostrar_mat" in st.session_state:
        st.text_area(
            "Observaciones mejoradas:",
            value=st.session_state["obs_mejorada_mostrar_mat"],
            key="obs_mejorada_display_mat",
            height=150,
            disabled=True
        )
        
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ Usar mejorado", key="btn_usar_obs_mat"):
                guardar_memoria("mat_texto_obs", st.session_state["obs_mejorada_mostrar_mat"])
                del st.session_state["mat_texto_obs"]
                del st.session_state["obs_mejorada_mostrar_mat"]
                st.rerun()
        with col_confirm2:
            if st.button("❌ Mantener original", key="btn_mantener_obs_mat"):
                del st.session_state["obs_mejorada_mostrar_mat"]
                st.rerun()

    unidades_op = st.text_area(
        "Unidades Operativas",
        cargar_memoria("mat_unidades_op", ". Unidad 4.4 Transporte de Personal Matrícula AD050WM\n. Unidad UM-45 Tipo Moto"),
        height=80
    )

    unidades_inop = st.text_area(
        "Unidades Inoperativas",
        cargar_memoria("mat_unidades_inop", ". Unidad Cisterna 4.2 (Falla de Almacenador de energía)\n. Unidad UM-41 Tipo Moto (Por falla del Sistema eléctrico del Arranque)\n. Unidad UM-42 Tipo Moto (Motor)\n. Unidad UM-43 Tipo Moto (Motor)\n. Unidad UM-44 Tipo Moto (Motor)"),
        height=120
    )

    cond_meteo = st.text_input("Condiciones Meteorológicas", cargar_memoria("mat_cond_meteo", "Cielo despejado en el sector la Cumaca, sub-sector fila Las Josefinas municipio San Diego estado Carabobo."))

    if 'parte_matutino_generado' not in st.session_state:
        st.session_state.parte_matutino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE MATUTINO", use_container_width=True):
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        nombre_dia = dias[fecha_mat.weekday()]
        fecha_str = f"{nombre_dia} {fecha_mat.strftime('%d/%m/%Y')}"

        guardar_memoria("mat_coord_estadal", coord_estadal)
        guardar_memoria("mat_jefe_estacion", jefe_estacion)
        guardar_memoria("mat_jefe_seccion", jefe_seccion)
        guardar_memoria("mat_parte_num", parte_num)
        guardar_memoria("mat_seccion_guardia", seccion_guardia)
        guardar_memoria("mat_pie_fuerza", pie_fuerza)
        guardar_memoria("mat_analista", analista_mat)
        guardar_memoria("mat_p_guardia", p_guardia)
        guardar_memoria("mat_p_retardado", p_retardado)
        guardar_memoria("mat_p_libre", p_libre)
        guardar_memoria("mat_p_permiso", p_permiso)
        guardar_memoria("mat_p_reposo", p_reposo)
        guardar_memoria("mat_p_ausente", p_ausente)
        guardar_memoria("mat_p_vacaciones", p_vacaciones)
        guardar_memoria("mat_p_comision", p_comision)
        guardar_memoria("mat_p_pasantes", p_pasantes)
        guardar_memoria("mat_serv_nocturnos", serv_nocturnos)
        guardar_memoria("mat_actividades", actividades_mat)
        guardar_memoria("mat_texto_actividad", texto_actividad_mat)
        guardar_memoria("mat_cant_obs", cant_obs_mat)
        guardar_memoria("mat_texto_obs", texto_observaciones_mat)
        guardar_memoria("mat_unidades_op", unidades_op)
        guardar_memoria("mat_unidades_inop", unidades_inop)
        guardar_memoria("mat_cond_meteo", cond_meteo)

        if cant_obs_mat == 0 or not texto_observaciones_mat.strip():
            texto_observaciones_ws = "00"
        else:
            lineas_obs = [l.strip() for l in texto_observaciones_mat.splitlines() if l.strip()]
            texto_observaciones_ws = f"{len(lineas_obs):02d}\n"
            for i, linea in enumerate(lineas_obs, 1):
                texto_observaciones_ws += f"{i}. {linea}\n"

        if actividades_mat == 0 or not texto_actividad_mat.strip():
            texto_actividad_ws = "00"
        else:
            lineas_act = [l.strip() for l in texto_actividad_mat.splitlines() if l.strip()]
            texto_actividad_ws = f"{len(lineas_act):02d}\n"
            for i, linea in enumerate(lineas_act, 1):
                texto_actividad_ws += f"{i}. {linea}\n"
                
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

{servicios_del_dia}

*ACTIVIDAD:* {texto_actividad_ws}

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
elif opcion_modulo == "PARTE VESPERTINO":
    st.header("🌆 Parte Vespertino")

    st.subheader("📌 Datos Principales")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        estacion_vesp = st.text_input("Estación", cargar_memoria("vesp_estacion", "EBF LAS JOSEFINAS"))
        fecha_vesp = st.date_input("Fecha", datetime.now(), key="f_vesp")
    with col_v2:
        serv_realizados = st.number_input("Servicios Realizados", min_value=0, value=int(cargar_memoria("vesp_serv_realizados", 0)))
        actividades_vesp = st.number_input("Actividades", min_value=0, value=int(cargar_memoria("vesp_actividades", 1)))

    st.subheader("📝 Actividad Realizada")
    
    if "vesp_texto_actividad" not in st.session_state:
        st.session_state["vesp_texto_actividad"] = cargar_memoria("vesp_texto_actividad", "")

    texto_actividad = st.text_area(
        "Detalle de la actividad realizada:",
        placeholder="Ejemplo:\nEl día de hoy en horas matutinas se da una sesión educativa al personal pasante...",
        height=120,
        key="vesp_texto_actividad"
    )
    
    col_act_btn1_v, col_act_btn2_v = st.columns([3, 1])
    with col_act_btn2_v:
        if st.button("✨ IA Actividad", key="btn_ia_act_vesp"):
            if texto_actividad.strip():
                with st.spinner("🤖 Mejorando..."):
                    act_mejorada_v = mejorar_redaccion_ia(texto_actividad, "actividad")
                    st.session_state["act_mejorada_mostrar_vesp"] = act_mejorada_v
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "act_mejorada_mostrar_vesp" in st.session_state:
        st.text_area(
            "Actividad mejorada:",
            value=st.session_state["act_mejorada_mostrar_vesp"],
            key="act_mejorada_display_vesp",
            height=120,
            disabled=True
        )
        
        col_conf1_act_v, col_conf2_act_v = st.columns(2)
        with col_conf1_act_v:
            if st.button("✅ Usar mejorado", key="btn_usar_act_vesp"):
                guardar_memoria("vesp_texto_actividad", st.session_state["act_mejorada_mostrar_vesp"])
                del st.session_state["vesp_texto_actividad"]
                del st.session_state["act_mejorada_mostrar_vesp"]
                st.rerun()
        with col_conf2_act_v:
            if st.button("❌ Mantener original", key="btn_mantener_act_vesp"):
                del st.session_state["act_mejorada_mostrar_vesp"]
                st.rerun()

    st.subheader("📋 Observaciones")
    
    cant_obs_vesp = st.number_input("Cantidad de Observaciones", min_value=0, value=int(cargar_memoria("vesp_cant_obs", 0)), step=1)
    
    if "vesp_texto_obs" not in st.session_state:
        st.session_state["vesp_texto_obs"] = cargar_memoria("vesp_texto_obs", "")

    texto_observaciones_vesp = st.text_area(
        "Redacte las observaciones (una por línea):",
        placeholder="Ejemplo:\n- Primera observación\n- Segunda observación\n- Tercera observación",
        height=150,
        key="vesp_texto_obs"
    )
    
    col_obs_btn1_v, col_obs_btn2_v = st.columns([3, 1])
    with col_obs_btn2_v:
        if st.button("✨ IA Obs", key="btn_ia_obs_vesp"):
            if texto_observaciones_vesp.strip():
                with st.spinner("🤖 Mejorando..."):
                    obs_mejorada_v = mejorar_redaccion_ia(texto_observaciones_vesp, "observación")
                    st.session_state["obs_mejorada_mostrar_vesp"] = obs_mejorada_v
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "obs_mejorada_mostrar_vesp" in st.session_state:
        st.text_area(
            "Observaciones mejoradas:",
            value=st.session_state["obs_mejorada_mostrar_vesp"],
            key="obs_mejorada_display_vesp",
            height=150,
            disabled=True
        )
        
        col_confirm1_v, col_confirm2_v = st.columns(2)
        with col_confirm1_v:
            if st.button("✅ Usar mejorado", key="btn_usar_obs_vesp"):
                guardar_memoria("vesp_texto_obs", st.session_state["obs_mejorada_mostrar_vesp"])
                del st.session_state["vesp_texto_obs"]
                del st.session_state["obs_mejorada_mostrar_vesp"]
                st.rerun()
        with col_confirm2_v:
            if st.button("❌ Mantener original", key="btn_mantener_obs_vesp"):
                del st.session_state["obs_mejorada_mostrar_vesp"]
                st.rerun()

    st.subheader("🌤️ Clima y Analista")
    cond_meteo_vesp = st.text_input(
        "Condiciones Meteorológicas",
        cargar_memoria("vesp_cond_meteo", "Cielo Despejado en el sector La Cumaca, parroquia San Diego, municipio San Diego, estado Carabobo.")
    )
    analista_vesp = st.text_input("Analista que Registra", cargar_memoria("vesp_analista", ""))

    if 'parte_vespertino_generado' not in st.session_state:
        st.session_state.parte_vespertino_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("📝 REDACTAR PARTE VESPERTINO", use_container_width=True):
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        nombre_dia = dias[fecha_vesp.weekday()]
        fecha_str = f"{nombre_dia} {fecha_vesp.strftime('%d/%m/%Y')}"

        guardar_memoria("vesp_estacion", estacion_vesp)
        guardar_memoria("vesp_serv_realizados", serv_realizados)
        guardar_memoria("vesp_actividades", actividades_vesp)
        guardar_memoria("vesp_texto_actividad", texto_actividad)
        guardar_memoria("vesp_cant_obs", cant_obs_vesp)
        guardar_memoria("vesp_texto_obs", texto_observaciones_vesp)
        guardar_memoria("vesp_cond_meteo", cond_meteo_vesp)
        guardar_memoria("vesp_analista", analista_vesp)

        if cant_obs_vesp == 0 or not texto_observaciones_vesp.strip():
            texto_observaciones_ws_v = "00"
        else:
            lineas_obs_v = [l.strip() for l in texto_observaciones_vesp.splitlines() if l.strip()]
            texto_observaciones_ws_v = f"{len(lineas_obs_v):02d}\n"
            for i, linea in enumerate(lineas_obs_v, 1):
                texto_observaciones_ws_v += f"{i}. {linea}\n"

        if actividades_vesp == 0 or not texto_actividad.strip():
            texto_actividad_ws_v = "00"
        else:
            lineas_act_v = [l.strip() for l in texto_actividad.splitlines() if l.strip()]
            texto_actividad_ws_v = f"{len(lineas_act_v):02d}\n"
            for i, linea in enumerate(lineas_act_v, 1):
                texto_actividad_ws_v += f"{i}. {linea}\n"

        servicios_del_dia_vesp = consumir_y_limpiar_servicios()

        st.session_state.parte_vespertino_generado = f"""*SISTEMA NACIONAL DE GESTIÓN DE RIESGO*

*CUERPO DE BOMBEROS FORESTALES INPARQUES*

*COORDINACIÓN FORESTAL CARABOBO*

*{estacion_vesp}*

*FECHA:* {fecha_str}

*SERVICIOS REALIZADOS:* {serv_realizados:02d}

{servicios_del_dia_vesp}

*ACTIVIDAD:* {texto_actividad_ws_v}

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

    ubicaciones = cargar_ubicaciones()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        tipo_servicio = st.selectbox(
            "Tipo de Servicio",
            st.session_state.lista_servicios,
            index=st.session_state.lista_servicios.index(cargar_memoria("srv_tipo_servicio", st.session_state.lista_servicios[0]))
        )
        
        with st.expander("➕ / 🗑️ Agregar o Borrar Tipo de Servicio"):
            nuevo_servicio = st.text_input("Escriba un nuevo tipo de servicio:")
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("Guardar nuevo", use_container_width=True):
                    if nuevo_servicio and nuevo_servicio.upper() not in st.session_state.lista_servicios:
                        st.session_state.lista_servicios.append(nuevo_servicio)
                        guardar_servicios_persistencia(st.session_state.lista_servicios)
                        st.success("¡Servicio agregado!")
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
        num_servicio = st.text_input("Número de Servicio", cargar_memoria("srv_num_servicio", ""), placeholder="Ej: 04-0267-2026")
        
        st.markdown("📍 **Ubicación Geográfica**")
        
        estados_venezuela = list(ubicaciones.keys())
        srv_estado = st.selectbox(
            "Estado",
            estados_venezuela,
            index=estados_venezuela.index(cargar_memoria("srv_estado", "Carabobo"))
        )
        
        if srv_estado == "Carabobo":
            municipios_carabobo = ubicaciones["Carabobo"]["municipios"]
            srv_municipio = st.selectbox(
                "Municipio",
                list(municipios_carabobo.keys()),
                index=list(municipios_carabobo.keys()).index(cargar_memoria("srv_municipio", "San Diego"))
            )
            
            parroquias_disponibles = municipios_carabobo[srv_municipio]["parroquias"]
            srv_parroquia = st.selectbox(
                "Parroquia",
                parroquias_disponibles,
                index=parroquias_disponibles.index(cargar_memoria("srv_parroquia", parroquias_disponibles[0]))
            )
            
            with st.expander("➕ / 🗑️ Gestionar Sectores y Sub-sectores"):
                sectores_de_parroquia = municipios_carabobo[srv_municipio]["sectores"].get(srv_parroquia, [])
                
                if sectores_de_parroquia:
                    st.write("**Sectores existentes:**")
                    for sector_nombre in sectores_de_parroquia:
                        st.write(f"- {sector_nombre}")
                
                st.markdown("---")
                st.write("**Agregar Sector:**")
                nuevo_sector = st.text_input("Nombre del nuevo sector:")
                if st.button("➕ Agregar Sector", key="btn_agregar_sector_srv"):
                    if nuevo_sector.strip():
                        if srv_parroquia not in municipios_carabobo[srv_municipio]["sectores"]:
                            municipios_carabobo[srv_municipio]["sectores"][srv_parroquia] = []
                        if nuevo_sector.strip() not in municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]:
                            municipios_carabobo[srv_municipio]["sectores"][srv_parroquia].append(nuevo_sector.strip())
                            guardar_ubicaciones(ubicaciones)
                            st.success(f"✅ Sector '{nuevo_sector}' agregado a {srv_parroquia}")
                            st.rerun()
                        else:
                            st.warning("Ese sector ya existe.")
                    else:
                        st.warning("Escribe el nombre del sector.")
                
                if sectores_de_parroquia:
                    sector_a_eliminar = st.selectbox("Seleccione sector a eliminar:", sectores_de_parroquia, key="sec_eliminar_srv")
                    if st.button("🗑️ Eliminar Sector", key="btn_eliminar_sector_srv"):
                        if sector_a_eliminar in municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]:
                            municipios_carabobo[srv_municipio]["sectores"][srv_parroquia].remove(sector_a_eliminar)
                            guardar_ubicaciones(ubicaciones)
                            st.success(f"✅ Sector '{sector_a_eliminar}' eliminado")
                            st.rerun()
                
                st.markdown("---")
                st.write("**Agregar Sub-sector a Sector existente:**")
                if sectores_de_parroquia:
                    sector_para_sub = st.selectbox("Seleccione sector:", sectores_de_parroquia, key="sec_para_sub_srv")
                    nuevo_sub_sector = st.text_input("Nombre del nuevo sub-sector:")
                    if st.button("➕ Agregar Sub-sector", key="btn_agregar_sub_srv"):
                        if nuevo_sub_sector.strip():
                            if nuevo_sub_sector.strip() not in municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]:
                                municipios_carabobo[srv_municipio]["sectores"][srv_parroquia].append(nuevo_sub_sector.strip())
                                guardar_ubicaciones(ubicaciones)
                                st.success(f"✅ Sub-sector '{nuevo_sub_sector}' agregado a {sector_para_sub}")
                                st.rerun()
                            else:
                                st.warning("Ese sub-sector ya existe.")
                        else:
                            st.warning("Escribe el nombre del sub-sector.")
                    
                    sub_sectores_de_sector = municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]
                    if sub_sectores_de_sector:
                        sub_a_eliminar = st.selectbox("Seleccione sub-sector a eliminar:", sub_sectores_de_sector, key="sub_eliminar_srv")
                        if st.button("🗑️ Eliminar Sub-sector", key="btn_eliminar_sub_srv"):
                            if sub_a_eliminar in municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]:
                                municipios_carabobo[srv_municipio]["sectores"][srv_parroquia].remove(sub_a_eliminar)
                                guardar_ubicaciones(ubicaciones)
                                st.success(f"✅ Sub-sector '{sub_a_eliminar}' eliminado")
                                st.rerun()
                else:
                    st.info("No hay sectores. Agrega un sector primero.")
            
            sectores_de_parroquia = municipios_carabobo[srv_municipio]["sectores"].get(srv_parroquia, [])
            
            if sectores_de_parroquia:
                srv_sector = st.selectbox(
                    "Sector",
                    sectores_de_parroquia,
                    index=sectores_de_parroquia.index(cargar_memoria("srv_sector", sectores_de_parroquia[0]))
                )
                
                sub_sectores_del_sector = municipios_carabobo[srv_municipio]["sectores"][srv_parroquia]
                if sub_sectores_del_sector:
                    srv_sub_sector = st.selectbox(
                        "Sub-sector",
                        sub_sectores_del_sector,
                        index=sub_sectores_del_sector.index(cargar_memoria("srv_sub_sector", sub_sectores_del_sector[0]))
                    )
                else:
                    srv_sub_sector = st.text_input("Sub-sector (no hay registrados)", "", key="s_sub_sec")
            else:
                srv_sector = st.text_input("Sector (no hay registrados)", cargar_memoria("srv_sector", ""), key="s_sec")
                srv_sub_sector = st.text_input("Sub-sector", cargar_memoria("srv_sub_sector", ""), key="s_sub_sec")
        else:
            srv_municipio = st.text_input("Municipio", cargar_memoria("srv_municipio", ""), key="s_mun")
            srv_parroquia = st.text_input("Parroquia", cargar_memoria("srv_parroquia", ""), key="s_par")
            srv_sector = st.text_input("Sector", cargar_memoria("srv_sector", ""), key="s_sec")
            srv_sub_sector = st.text_input("Sub-sector", cargar_memoria("srv_sub_sector", ""), key="s_sub_sec")
        
        ubicacion_srv = f"{srv_sub_sector}, {srv_sector}, parroquia {srv_parroquia}, municipio {srv_municipio}, estado {srv_estado}"

        jefe_comision = st.text_input("Jefe de Comisión", cargar_memoria("srv_jefe_comision", ""), placeholder="Indique el rango y nombre")

    with col_s2:
        estatus_srv = st.selectbox(
            "Estatus",
            ["en proceso", "Finalizado"],
            index=["en proceso", "Finalizado"].index(cargar_memoria("srv_estatus", "en proceso"))
        )
        hora_fin = st.time_input("Hora de Finalizado", datetime.now().time(), key="h_fin")
        efectivos_srv = st.number_input("Número de Efectivos", min_value=1, value=int(cargar_memoria("srv_efectivos", 3)), step=1)
        latitud_srv = st.number_input("Latitud", value=float(cargar_memoria("srv_latitud", 10.3047984)), format="%.7f", key="lat_srv")
        longitud_srv = st.number_input("Longitud", value=float(cargar_memoria("srv_longitud", -67.9307846)), format="%.7f", key="lon_srv")

    st.subheader("📌 Observaciones")
    num_observaciones = st.number_input("Cantidad de Observaciones", min_value=0, value=int(cargar_memoria("srv_num_obs", 0)), step=1)
    
    if "srv_texto_obs" not in st.session_state:
        st.session_state["srv_texto_obs"] = cargar_memoria("srv_texto_obs", "")

    texto_observaciones_srv = st.text_area(
        "Redacte las observaciones (una por línea):",
        placeholder="Ejemplo:\n- Primera observación\n- Segunda observación\n- Tercera observación",
        height=150,
        key="srv_texto_obs"
    )
    
    col_obs_btn1_s, col_obs_btn2_s = st.columns([3, 1])
    with col_obs_btn2_s:
        if st.button("✨ IA Obs", key="btn_ia_obs_srv"):
            if texto_observaciones_srv.strip():
                with st.spinner("🤖 Mejorando..."):
                    obs_mejorada_s = mejorar_redaccion_ia(texto_observaciones_srv, "observación")
                    st.session_state["obs_mejorada_mostrar_srv"] = obs_mejorada_s
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "obs_mejorada_mostrar_srv" in st.session_state:
        st.text_area(
            "Observaciones mejoradas:",
            value=st.session_state["obs_mejorada_mostrar_srv"],
            key="obs_mejorada_display_srv",
            height=150,
            disabled=True
        )
        
        col_conf1_s, col_conf2_s = st.columns(2)
        with col_conf1_s:
            if st.button("✅ Usar mejorado", key="btn_usar_obs_srv"):
                guardar_memoria("srv_texto_obs", st.session_state["obs_mejorada_mostrar_srv"])
                del st.session_state["srv_texto_obs"]
                del st.session_state["obs_mejorada_mostrar_srv"]
                st.rerun()
        with col_conf2_s:
            if st.button("❌ Mantener original", key="btn_mantener_obs_srv"):
                del st.session_state["obs_mejorada_mostrar_srv"]
                st.rerun()

    st.subheader("🚓 Organismos Presentes")
    
    if 'lista_org_oficiales' not in st.session_state:
        st.session_state.lista_org_oficiales = cargar_organismos_persistencia()

    org_seleccionados = st.multiselect(
        "Seleccione los organismos:",
        st.session_state.lista_org_oficiales,
        default=cargar_memoria("srv_org_seleccionados", [])
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
                st.success("¡Organismo agregado!")
                st.rerun()
    
    cantidades_org = {}
    if org_seleccionados:
        cols_org = st.columns(4)
        for idx, org in enumerate(org_seleccionados):
            with cols_org[idx % 4]:
                sigla_mostrar = org.split(" (")[0]
                cantidades_org[org] = st.number_input(
                    sigla_mostrar,
                    min_value=1,
                    value=int(cargar_memoria(f"srv_cant_{org}", 1)),
                    step=1,
                    key=f"cant_{org}"
                )

    st.subheader("📝 Reseña y Acciones Operativas")
    
    if "srv_resena" not in st.session_state:
        st.session_state["srv_resena"] = cargar_memoria("srv_resena", "")

    resena_borrador = st.text_area(
        "Reseña:",
        placeholder="Ejemplo: Por instrucciones del jefe...",
        height=100,
        key="srv_resena"
    )
    
    col_res_btn1, col_res_btn2 = st.columns([3, 1])
    with col_res_btn2:
        if st.button("✨ IA Reseña", key="btn_ia_resena_srv"):
            if resena_borrador.strip():
                with st.spinner("🤖 Mejorando..."):
                    resena_mejorada_ia = mejorar_redaccion_ia(resena_borrador, "reseña")
                    st.session_state["resena_mejorada_mostrar_srv"] = resena_mejorada_ia
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "resena_mejorada_mostrar_srv" in st.session_state:
        st.text_area(
            "Reseña mejorada:",
            value=st.session_state["resena_mejorada_mostrar_srv"],
            key="resena_mejorada_display_srv",
            height=100,
            disabled=True
        )
        
        col_res_conf1, col_res_conf2 = st.columns(2)
        with col_res_conf1:
            if st.button("✅ Usar mejorado", key="btn_usar_resena_srv"):
                guardar_memoria("srv_resena", st.session_state["resena_mejorada_mostrar_srv"])
                del st.session_state["srv_resena"]
                del st.session_state["resena_mejorada_mostrar_srv"]
                st.rerun()
        with col_res_conf2:
            if st.button("❌ Mantener original", key="btn_mantener_resena_srv"):
                del st.session_state["resena_mejorada_mostrar_srv"]
                st.rerun()
    
    if "srv_acciones" not in st.session_state:
        st.session_state["srv_acciones"] = cargar_memoria("srv_acciones", "")

    acciones_borrador = st.text_area(
        "Acciones Realizadas:",
        placeholder="Ejemplo: 07:29 Hrs Se destaca comisión...",
        height=150,
        key="srv_acciones"
    )
    
    col_acc_btn1, col_acc_btn2 = st.columns([3, 1])
    with col_acc_btn2:
        if st.button("✨ IA Acciones", key="btn_ia_acciones_srv"):
            if acciones_borrador.strip():
                with st.spinner("🤖 Mejorando..."):
                    acciones_mejoradas_ia = mejorar_redaccion_ia(acciones_borrador, "acciones realizadas")
                    st.session_state["acciones_mejoradas_mostrar_srv"] = acciones_mejoradas_ia
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "acciones_mejoradas_mostrar_srv" in st.session_state:
        st.text_area(
            "Acciones mejoradas:",
            value=st.session_state["acciones_mejoradas_mostrar_srv"],
            key="acciones_mejoradas_display_srv",
            height=150,
            disabled=True
        )
        
        col_acc_conf1, col_acc_conf2 = st.columns(2)
        with col_acc_conf1:
            if st.button("✅ Usar mejorado", key="btn_usar_acciones_srv"):
                texto_final = st.session_state["acciones_mejoradas_mostrar_srv"]
                if jefe_comision:
                    texto_final = texto_final.replace("Jefe de Comisión", jefe_comision)
                guardar_memoria("srv_acciones", texto_final)
                del st.session_state["srv_acciones"]
                del st.session_state["acciones_mejoradas_mostrar_srv"]
                st.rerun()
        with col_acc_conf2:
            if st.button("❌ Mantener original", key="btn_mantener_acciones_srv"):
                del st.session_state["acciones_mejoradas_mostrar_srv"]
                st.rerun()
    
    analista_srv = st.text_input("Analista que Registra", cargar_memoria("srv_analista", ""))

    if 'reporte_generado' not in st.session_state:
        st.session_state.reporte_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("✨ GENERAR REPORTE PARA WHATSAPP", use_container_width=True):
        if not resena_borrador.strip() or not acciones_borrador.strip():
            st.warning("⚠️ Por favor complete tanto la reseña como las acciones realizadas.")
        else:
            with st.spinner("🤖 Formateando el reporte..."):
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dia_str = dias_semana[fecha_srv.weekday()]
                
                guardar_memoria("srv_tipo_servicio", tipo_servicio)
                guardar_memoria("srv_num_servicio", num_servicio)
                guardar_memoria("srv_estado", srv_estado)
                guardar_memoria("srv_municipio", srv_municipio)
                guardar_memoria("srv_parroquia", srv_parroquia)
                guardar_memoria("srv_sector", srv_sector)
                guardar_memoria("srv_sub_sector", srv_sub_sector)
                guardar_memoria("srv_jefe_comision", jefe_comision)
                guardar_memoria("srv_estatus", estatus_srv)
                guardar_memoria("srv_efectivos", efectivos_srv)
                guardar_memoria("srv_latitud", latitud_srv)
                guardar_memoria("srv_longitud", longitud_srv)
                guardar_memoria("srv_num_obs", num_observaciones)
                guardar_memoria("srv_texto_obs", texto_observaciones_srv)
                guardar_memoria("srv_org_seleccionados", org_seleccionados)
                guardar_memoria("srv_resena", resena_borrador)
                guardar_memoria("srv_acciones", acciones_borrador)
                guardar_memoria("srv_analista", analista_srv)
                
                for org, cant in cantidades_org.items():
                    guardar_memoria(f"srv_cant_{org}", cant)
                
                texto_organismos_ws = ""
                if cantidades_org:
                    for org, cant in cantidades_org.items():
                        sigla_final = org.split(" (")[0]
                        texto_organismos_ws += f"{sigla_final}: {cant:02d}\n"
                else:
                    texto_organismos_ws = "00\n"
                
                if num_observaciones == 0 or not texto_observaciones_srv.strip():
                    texto_observaciones_ws = "00"
                else:
                    lineas_obs_srv = [l.strip() for l in texto_observaciones_srv.splitlines() if l.strip()]
                    texto_observaciones_ws = f"{len(lineas_obs_srv):02d}\n"
                    for i, linea in enumerate(lineas_obs_srv, 1):
                        texto_observaciones_ws += f"{i}. {linea}\n"
                
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

                datos_servicio = {
                    "tipo_servicio": tipo_servicio,
                    "num_servicio": num_servicio,
                    "ubicacion": ubicacion_srv,
                    "resena": resena_borrador,
                    "coordenadas": f"{latitud_srv}, {longitud_srv}",
                    "estatus": estatus_srv
                }
                registrar_servicio_dia(datos_servicio)
                st.success("✅ Servicio registrado para los partes")

    if st.session_state.reporte_generado:
        st.subheader("📋 Reporte Formateado (Listo para copiar a WhatsApp)")
        st.code(st.session_state.reporte_generado, language=None)

    st.markdown("---")
    
    if st.button("📋 GENERAR REPORTE EJECUTIVO", use_container_width=True, key="btn_ejecutivo_srv"):
        if not resena_borrador.strip() or not acciones_borrador.strip():
            st.warning("⚠️ Necesitas reseña y acciones para generar el ejecutivo.")
        else:
            with st.spinner("🤖 Generando reporte ejecutivo..."):
                texto_combinado = f"RESEÑA: {resena_borrador}\n\nACCIONES: {acciones_borrador}"
                resumen_ejecutivo = mejorar_redaccion_ia(texto_combinado, "ejecutivo")
                
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dia_str = dias_semana[fecha_srv.weekday()]
                
                st.session_state.reporte_ejecutivo_srv = f"""*SISTEMA NACIONAL PARA LA GESTIÓN DEL RIESGO*

*CUERPO DE BOMBEROS FORESTALES DE INPARQUES*

*REPORTE EJECUTIVO*

*FECHA:* {fecha_srv.strftime('%d/%m/%Y')}

*ESTADO:* {srv_estado}

*HORA DE INICIO:* {hora_inicio.strftime('%H:%M')} hrs

*HORA DE FIN:* {hora_fin.strftime('%H:%M')} hrs

*DIRECCIÓN:* {ubicacion_srv}

*EVENTO:* {tipo_servicio}

*DESCRIPCIÓN:*

{resumen_ejecutivo}

*COORDENADAS:*

{latitud_srv},{longitud_srv}

*ESTATUS:* {estatus_srv}"""

    if "reporte_ejecutivo_srv" in st.session_state:
        st.subheader("📋 Reporte Ejecutivo Formateado")
        st.code(st.session_state.reporte_ejecutivo_srv, language=None)
        
# =========================================================
# MÓDULO 4: REPORTES DE INCENDIOS
# =========================================================
elif opcion_modulo == "REPORTES DE INCENDIOS":
    st.header("🔥 Reportes de Incendios")

    # =========================================================
    # SECCIÓN: INCENDIOS PRELIMINARES GUARDADOS
    # =========================================================
    st.subheader("📂 Incendios en Proceso Guardados")
    
    preliminares = cargar_incendios_preliminares()
    
    if preliminares:
        st.info(f"Hay {len(preliminares)} incendio(s) guardado(s) para edición")
        
        with st.expander("Ver / Editar Progresivos"):
            for idx, preliminar in enumerate(preliminares):
                st.write(f"**{idx+1}. {preliminar.get('tipo_incendio', 'Incendio')} - {preliminar.get('num_servicio', 'Sin número')}**")
                st.write(f"   Estatus: {preliminar.get('estatus', 'N/A')}")
                st.write(f"   Última modificación: {preliminar.get('fecha_modificacion', 'N/A')}")
                
                col_pre1, col_pre2 = st.columns(2)
                with col_pre1:
                    if st.button(f"📝 Cargar", key=f"cargar_pre_{idx}"):
                        st.session_state["preliminar_cargado"] = preliminar
                        st.session_state["mostrar_preliminar"] = True
                        guardar_memoria("inc_resena", preliminar.get("resena", ""))
                        guardar_memoria("inc_acciones", preliminar.get("acciones", ""))
                        st.rerun()
                with col_pre2:
                    if st.button(f"🗑️ Eliminar", key=f"eliminar_pre_{idx}"):
                        eliminar_incendio_preliminar(idx)
                        st.success("¡Preliminar eliminado!")
                        st.rerun()
                st.markdown("---")
    else:
        st.info("No hay incendios en proceso guardados.")
    
    st.markdown("---")

    # =========================================================
    # FORMULARIO DE INCENDIO
    # =========================================================
    
    if "preliminar_cargado" in st.session_state:
        pre = st.session_state["preliminar_cargado"]
        default_tipo_reporte = pre.get("tipo_reporte", "Preliminar")
        default_tipo_incendio = pre.get("tipo_incendio", "Incendio de Vegetacion")
        default_num_servicio = pre.get("num_servicio", "")
        default_comandante = pre.get("comandante", "")
        default_estacion = pre.get("estacion", "EBF Las Josefinas")
        default_sub_sector = pre.get("sub_sector", "")
        default_sector = pre.get("sector", "")
        default_municipio = pre.get("municipio", "San Diego")
        default_parroquia = pre.get("parroquia", "San Diego")
        default_estado = pre.get("estado", "Carabobo")
        default_abrae = pre.get("abrae", "P/N San Esteban")
        default_efectivos = pre.get("efectivos", 10)
        default_recursos = pre.get("recursos", "Batidor Forestal")
        default_unidades = pre.get("unidades", "Unidad Tipo Moto 41")
        default_resena = pre.get("resena", "")
        default_acciones = pre.get("acciones", "")
        default_estatus = pre.get("estatus", "en proceso")
        default_delegado = pre.get("delegado", "C/2 (B) Reyes Edwin")
    else:
        default_tipo_reporte = cargar_memoria("inc_tipo_reporte", "Preliminar")
        default_tipo_incendio = cargar_memoria("inc_tipo_incendio", "Incendio de Vegetacion")
        default_num_servicio = cargar_memoria("inc_num_servicio", "")
        default_comandante = cargar_memoria("inc_comandante", "")
        default_estacion = cargar_memoria("inc_estacion", "EBF Las Josefinas")
        default_sub_sector = cargar_memoria("inc_sub_sector", "")
        default_sector = cargar_memoria("inc_sector", "")
        default_municipio = cargar_memoria("inc_municipio", "San Diego")
        default_parroquia = cargar_memoria("inc_parroquia", "San Diego")
        default_estado = cargar_memoria("inc_estado", "Carabobo")
        default_abrae = cargar_memoria("inc_abrae", "P/N San Esteban")
        default_efectivos = int(cargar_memoria("inc_efectivos", 10))
        default_recursos = cargar_memoria("inc_recursos", "Batidor Forestal")
        default_unidades = cargar_memoria("inc_unidades", "Unidad Tipo Moto 41")
        default_resena = cargar_memoria("inc_resena", "")
        default_acciones = cargar_memoria("inc_acciones", "")
        default_estatus = cargar_memoria("inc_estatus", "en proceso")
        default_delegado = cargar_memoria("inc_delegado", "C/2 (B) Reyes Edwin")

    col_i1, col_i2 = st.columns(2)
    with col_i1:
        tipo_reporte_opcion = st.selectbox(
            "Tipo de Reporte", 
            ["Final", "Preliminar", "Progresivo"],
            index=["Final", "Preliminar", "Progresivo"].index(default_tipo_reporte) if default_tipo_reporte in ["Final", "Preliminar", "Progresivo"] else 1
        )
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
            ],
            index=["Incendio de Vegetacion", "Incendio Forestal", "Conato de Incendio"].index(default_tipo_incendio) if default_tipo_incendio in ["Incendio de Vegetacion", "Incendio Forestal", "Conato de Incendio"] else 0
        )
        num_servicio_inc = st.text_input("Número de Servicio", default_num_servicio, placeholder="Ej: 04-0028-2026")
        fecha_inc = st.date_input("Fecha del Evento", datetime.now(), key="f_inc")
        hora_inc = st.time_input("Hora del Reporte", datetime.now().time(), key="h_inc")
        comandante_escena = st.text_input("Comandante en Escena", default_comandante, placeholder="Ej: C/1 (B) Gutiérrez Orlando")
        estacion_ebf = st.text_input("Estación / Base", default_estacion)

    with col_i2:
        ubicaciones = cargar_ubicaciones()
        estados_venezuela = list(ubicaciones.keys())
        estado_inc = st.selectbox(
            "Estado",
            estados_venezuela,
            index=estados_venezuela.index(default_estado) if default_estado in estados_venezuela else 0,
            key="estado_inc"
        )
        
        if estado_inc == "Carabobo":
            municipios_carabobo = ubicaciones["Carabobo"]["municipios"]
            municipio = st.selectbox(
                "Municipio",
                list(municipios_carabobo.keys()),
                index=list(municipios_carabobo.keys()).index(default_municipio) if default_municipio in municipios_carabobo else 0,
                key="municipio_inc"
            )
            
            parroquias_disponibles_inc = municipios_carabobo[municipio]["parroquias"]
            parroquia = st.selectbox(
                "Parroquia",
                parroquias_disponibles_inc,
                index=parroquias_disponibles_inc.index(default_parroquia) if default_parroquia in parroquias_disponibles_inc else 0,
                key="parroquia_inc"
            )
            
            sectores_de_parroquia_inc = municipios_carabobo[municipio]["sectores"].get(parroquia, [])
        else:
            municipio = st.text_input("Municipio", default_municipio, key="municipio_inc")
            parroquia = st.text_input("Parroquia", default_parroquia, key="parroquia_inc")
            sectores_de_parroquia_inc = []
        
        if estado_inc == "Carabobo":
            with st.expander("➕ / 🗑️ Gestionar Sectores y Sub-sectores"):
                if sectores_de_parroquia_inc:
                    st.write("**Sectores existentes:**")
                    for sector_nombre in sectores_de_parroquia_inc:
                        st.write(f"- {sector_nombre}")
                else:
                    st.info("No hay sectores registrados para esta parroquia.")
        
        if estado_inc == "Carabobo" and sectores_de_parroquia_inc:
            sector = st.selectbox(
                "Sector",
                sectores_de_parroquia_inc,
                index=sectores_de_parroquia_inc.index(default_sector) if default_sector in sectores_de_parroquia_inc else 0,
                key="sector_inc"
            )
            sub_sector = st.text_input("Sub-sector", default_sub_sector, key="sub_sector_inc")
        else:
            sector = st.text_input("Sector", default_sector, key="sector_inc")
            sub_sector = st.text_input("Sub-sector", default_sub_sector, key="sub_sector_inc")
        
        lista_abrae = ["P/N San Esteban",
            "Fuera de ABRAE",
            "Parque Nacional",
            "Monumento Natural",
            "Refugio de Fauna Silvestre",
            "Santuario de Fauna Silvestre",
            "Reserva de Biosfera",
            "Reserva Forestal",
            "Lote Boscoso",
            "Área Vital de Obtención de Recursos Minerales",
            "Área Rural de Desarrollo Integrado (ARDI)",
            "Zona de Aprovechamiento Agrícola",
            "Área de Protección y Recuperación Ambiental",
            "Zona Protectora",
            "Reserva Hidráulica",
            "Cuenca Hidrográfica en Ordenación",
            "Área de Mitigación de Riesgos",
            "Área de Control del Manejo de Aguas",
            "Parque Recreacional",
            "Zona de Interés Turístico",
            "Sitio de Patrimonio Histórico, Artístico y Arqueológico",
            "Área Fronteriza",
            "Zona de Seguridad",
            "Área de Manejo de Instalaciones Militares y Estratégicas"
        ]
        
        abrae_inc = st.selectbox("Abrae", lista_abrae, index=lista_abrae.index(default_abrae) if default_abrae in lista_abrae else 0)

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
        efectivos_inc = st.number_input("Cantidad de Efectivos (BFI)", min_value=1, value=default_efectivos, step=1, key="ef_inc")
        recursos_disp = st.text_input("Recursos Disponibles", default_recursos)
        unidades_disp = st.text_input("Unidades", default_unidades)

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
    
    cant_obs_inc = st.number_input("Cantidad de Observaciones", min_value=0, value=int(cargar_memoria("inc_cant_obs", 0)), step=1)
    
    if "inc_texto_obs" not in st.session_state:
        st.session_state["inc_texto_obs"] = cargar_memoria("inc_texto_obs", "")

    texto_observaciones_inc = st.text_area(
        "Redacte las observaciones (una por línea):",
        placeholder="Ejemplo:\n- Primera observación\n- Segunda observación\n- Tercera observación",
        height=150,
        key="inc_texto_obs"
    )
    
    col_obs_btn1_i, col_obs_btn2_i = st.columns([3, 1])
    with col_obs_btn2_i:
        if st.button("✨ IA Obs", key="btn_ia_obs_inc"):
            if texto_observaciones_inc.strip():
                with st.spinner("🤖 Mejorando..."):
                    obs_mejorada_i = mejorar_redaccion_ia(texto_observaciones_inc, "observación")
                    st.session_state["obs_mejorada_mostrar_inc"] = obs_mejorada_i
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "obs_mejorada_mostrar_inc" in st.session_state:
        st.text_area(
            "Observaciones mejoradas:",
            value=st.session_state["obs_mejorada_mostrar_inc"],
            key="obs_mejorada_display_inc",
            height=150,
            disabled=True
        )
        
        col_conf1_i, col_conf2_i = st.columns(2)
        with col_conf1_i:
            if st.button("✅ Usar mejorado", key="btn_usar_obs_inc"):
                guardar_memoria("inc_texto_obs", st.session_state["obs_mejorada_mostrar_inc"])
                del st.session_state["inc_texto_obs"]
                del st.session_state["obs_mejorada_mostrar_inc"]
                st.rerun()
        with col_conf2_i:
            if st.button("❌ Mantener original", key="btn_mantener_obs_inc"):
                del st.session_state["obs_mejorada_mostrar_inc"]
                st.rerun()

    if "inc_resena" not in st.session_state:
        st.session_state["inc_resena"] = cargar_memoria("inc_resena", default_resena)

    resena_inc = st.text_area(
        "RESEÑA:",
        placeholder="Ejemplo: Durante recorrido...",
        height=100,
        key="inc_resena"
    )
    
    col_res_btn1_i, col_res_btn2_i = st.columns([3, 1])
    with col_res_btn2_i:
        if st.button("✨ IA Reseña", key="btn_ia_resena_inc"):
            if resena_inc.strip():
                with st.spinner("🤖 Mejorando..."):
                    resena_mejorada_inc_ia = mejorar_redaccion_ia(resena_inc, "reseña de incendio")
                    st.session_state["resena_mejorada_mostrar_inc"] = resena_mejorada_inc_ia
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "resena_mejorada_mostrar_inc" in st.session_state:
        st.text_area(
            "Reseña mejorada:",
            value=st.session_state["resena_mejorada_mostrar_inc"],
            key="resena_mejorada_display_inc",
            height=100,
            disabled=True
        )
        
        col_res_conf1_i, col_res_conf2_i = st.columns(2)
        with col_res_conf1_i:
            if st.button("✅ Usar mejorado", key="btn_usar_resena_inc"):
                guardar_memoria("inc_resena", st.session_state["resena_mejorada_mostrar_inc"])
                del st.session_state["inc_resena"]
                del st.session_state["resena_mejorada_mostrar_inc"]
                st.rerun()
        with col_res_conf2_i:
            if st.button("❌ Mantener original", key="btn_mantener_resena_inc"):
                del st.session_state["resena_mejorada_mostrar_inc"]
                st.rerun()

    if "inc_acciones" not in st.session_state:
        st.session_state["inc_acciones"] = cargar_memoria("inc_acciones", default_acciones)

    acciones_inc = st.text_area(
        "ACCIÓN REALIZADA (Bitácora de Eventos):",
        placeholder="Ejemplo:\n15:10 Hrs Se destaca...",
        height=200,
        key="inc_acciones"
    )
    
    col_acc_btn1_i, col_acc_btn2_i = st.columns([3, 1])
    with col_acc_btn2_i:
        if st.button("✨ IA Acciones", key="btn_ia_acciones_inc"):
            if acciones_inc.strip():
                with st.spinner("🤖 Mejorando..."):
                    acciones_mejoradas_inc_ia = mejorar_redaccion_ia(acciones_inc, "acciones realizadas")
                    st.session_state["acciones_mejoradas_mostrar_inc"] = acciones_mejoradas_inc_ia
                    st.rerun()
            else:
                st.warning("Escribe algo primero")
    
    if "acciones_mejoradas_mostrar_inc" in st.session_state:
        st.text_area(
            "Acciones mejoradas:",
            value=st.session_state["acciones_mejoradas_mostrar_inc"],
            key="acciones_mejoradas_display_inc",
            height=200,
            disabled=True
        )
        
        col_acc_conf1_i, col_acc_conf2_i = st.columns(2)
        with col_acc_conf1_i:
            if st.button("✅ Usar mejorado", key="btn_usar_acciones_inc"):
                texto_final_acc = st.session_state["acciones_mejoradas_mostrar_inc"]
                if comandante_escena:
                    texto_final_acc = texto_final_acc.replace("Jefe de Comisión", comandante_escena)
                guardar_memoria("inc_acciones", texto_final_acc)
                del st.session_state["inc_acciones"]
                del st.session_state["acciones_mejoradas_mostrar_inc"]
                st.rerun()
        with col_acc_conf2_i:
            if st.button("❌ Mantener original", key="btn_mantener_acciones_inc"):
                del st.session_state["acciones_mejoradas_mostrar_inc"]
                st.rerun()

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        estatus_inc = st.selectbox("Estatus del Incendio", ["Finalizado-combatido", "En proceso", "Finalizado no combatido"], index=["Finalizado-combatido", "En proceso", "Finalizado no combatido"].index(default_estatus) if default_estatus in ["Finalizado-combatido", "En proceso", "Finalizado no combatido"] else 1)
    with col_e2:
        hora_envio_inc = st.time_input("Hora de Envío del Reporte", datetime.now().time(), key="h_envio_inc")
    with col_e3:
        delegado_ame = st.text_input("Delegado Estadal AME", default_delegado)

    if 'incendio_generado' not in st.session_state:
        st.session_state.incendio_generado = ""

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔥 GENERAR REPORTE DE INCENDIO", use_container_width=True):
        if not resena_inc.strip() or not acciones_inc.strip():
            st.warning("⚠️ Por favor complete la reseña y las acciones realizadas.")
        else:
            if comandante_escena and acciones_inc:
                acciones_inc = acciones_inc.replace("Jefe de Comisión", comandante_escena)
            
            with st.spinner("🤖 Formateando el reporte de incendio..."):
                
                guardar_memoria("inc_tipo_reporte", tipo_reporte)
                guardar_memoria("inc_tipo_incendio", tipo_incendio)
                guardar_memoria("inc_num_servicio", num_servicio_inc)
                guardar_memoria("inc_comandante", comandante_escena)
                guardar_memoria("inc_estacion", estacion_ebf)
                guardar_memoria("inc_estado", estado_inc)
                guardar_memoria("inc_municipio", municipio)
                guardar_memoria("inc_parroquia", parroquia)
                guardar_memoria("inc_sector", sector)
                guardar_memoria("inc_sub_sector", sub_sector)
                guardar_memoria("inc_abrae", abrae_inc)
                guardar_memoria("inc_efectivos", efectivos_inc)
                guardar_memoria("inc_recursos", recursos_disp)
                guardar_memoria("inc_unidades", unidades_disp)
                guardar_memoria("inc_estatus", estatus_inc)
                guardar_memoria("inc_delegado", delegado_ame)
                guardar_memoria("inc_cant_obs", cant_obs_inc)
                guardar_memoria("inc_texto_obs", texto_observaciones_inc)
                guardar_memoria("inc_resena", resena_inc)
                guardar_memoria("inc_acciones", acciones_inc)
                
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

                if cant_obs_inc == 0 or not texto_observaciones_inc.strip():
                    texto_observaciones_ws_i = "00"
                else:
                    lineas_obs_inc = [l.strip() for l in texto_observaciones_inc.splitlines() if l.strip()]
                    texto_observaciones_ws_i = f"{len(lineas_obs_inc):02d}\n"
                    for i, linea in enumerate(lineas_obs_inc, 1):
                        texto_observaciones_ws_i += f"{i}. {linea}\n"

                datos_incendio = {
                    "tipo_servicio": tipo_incendio,
                    "num_servicio": num_servicio_inc,
                    "ubicacion": f"{sector}, {municipio}",
                    "resena": resena_inc,
                    "coordenadas": f"{lat_inc}, {lon_inc}",
                    "estatus": estatus_inc
                }
                registrar_servicio_dia(datos_incendio)
                
                if estatus_inc not in ["Finalizado", "Finalizado-combatido"]:
                    datos_preliminar = {
                        "tipo_reporte": tipo_reporte,
                        "tipo_incendio": tipo_incendio,
                        "num_servicio": num_servicio_inc,
                        "fecha": fecha_inc.strftime("%d/%m/%Y"),
                        "hora": hora_inc.strftime("%H:%M"),
                        "comandante": comandante_escena,
                        "estacion": estacion_ebf,
                        "sector": sector,
                        "sub_sector": sub_sector,
                        "parroquia": parroquia,
                        "municipio": municipio,
                        "estado": estado_inc,
                        "abrae": abrae_inc,
                        "resena": resena_inc,
                        "acciones": acciones_inc,
                        "efectivos": efectivos_inc,
                        "recursos": recursos_disp,
                        "unidades": unidades_disp,
                        "estatus": estatus_inc,
                        "coordenadas": f"{lat_inc}, {lon_inc}",
                        "delegado": delegado_ame
                    }
                    guardar_incendio_preliminar(datos_preliminar)
                    st.success(f"✅ Incendio guardado como {tipo_reporte}")
                else:
                    eliminar_incendio_preliminar(num_servicio_inc)
                    st.success("✅ Incendio finalizado y cerrado")

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

    st.markdown("---")
    
    if st.button("📋 GENERAR REPORTE EJECUTIVO", use_container_width=True, key="btn_ejecutivo_inc"):
        if not resena_inc.strip() or not acciones_inc.strip():
            st.warning("⚠️ Necesitas reseña y acciones para generar el ejecutivo.")
        else:
            with st.spinner("🤖 Generando reporte ejecutivo..."):
                texto_combinado = f"RESEÑA: {resena_inc}\n\nACCIONES: {acciones_inc}"
                resumen_ejecutivo_inc = mejorar_redaccion_ia(texto_combinado, "ejecutivo")
                
                st.session_state.reporte_ejecutivo_inc = f"""*SISTEMA NACIONAL PARA LA GESTIÓN DEL RIESGO*

*CUERPO DE BOMBEROS FORESTALES DE INPARQUES*

*REPORTE EJECUTIVO*

*FECHA:* {fecha_inc.strftime('%d/%m/%Y')}

*ESTADO:* {estado_inc}

*HORA DE INICIO:* {hora_inc.strftime('%H:%M')} hrs

*DIRECCIÓN:* {sector} sub-sector {sub_sector}, Parroquia {parroquia}, Municipio {municipio}, Estado {estado_inc}

*EVENTO:* {tipo_incendio}

*ABRAE:* {abrae_inc}

*DESCRIPCIÓN:*

{resumen_ejecutivo_inc}

*COORDENADAS:*

{lat_inc},{lon_inc}

*ESTATUS:* {estatus_inc}"""

    if "reporte_ejecutivo_inc" in st.session_state:
        st.subheader("📋 Reporte Ejecutivo Formateado")
        st.code(st.session_state.reporte_ejecutivo_inc, language=None)
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
        
        if "ni_texto" not in st.session_state:
            st.session_state["ni_texto"] = cargar_memoria("ni_texto", ". El día hoy en horas matutinas se da continuidad a la Formación en servicio impartida por el coordinador Forestal (B) Mayor Mendoza Luis al personal perteneciente al estado Portuguesa y personal de planta con el tema: introducción del sistema S.A.R")

        texto_ni = st.text_area(
            "Contenido de la Nota Informativa",
            height=130,
            key="ni_texto"
        )
        
        col_ni_btn1, col_ni_btn2 = st.columns([3, 1])
        with col_ni_btn2:
            if st.button("✨ IA Nota", key="btn_ia_nota_ni"):
                if texto_ni.strip():
                    with st.spinner("🤖 Mejorando..."):
                        nota_mejorada_ni = mejorar_redaccion_ia(texto_ni, "nota informativa")
                        st.session_state["nota_mejorada_mostrar_ni"] = nota_mejorada_ni
                        st.rerun()
                else:
                    st.warning("Escribe algo primero")
        
        if "nota_mejorada_mostrar_ni" in st.session_state:
            st.text_area(
                "Nota mejorada:",
                value=st.session_state["nota_mejorada_mostrar_ni"],
                key="nota_mejorada_display_ni",
                height=130,
                disabled=True
            )
            
            col_ni_conf1, col_ni_conf2 = st.columns(2)
            with col_ni_conf1:
                if st.button("✅ Usar mejorado", key="btn_usar_nota_ni"):
                    guardar_memoria("ni_texto", st.session_state["nota_mejorada_mostrar_ni"])
                    del st.session_state["ni_texto"]
                    del st.session_state["nota_mejorada_mostrar_ni"]
                    st.rerun()
            with col_ni_conf2:
                if st.button("❌ Mantener original", key="btn_mantener_nota_ni"):
                    del st.session_state["nota_mejorada_mostrar_ni"]
                    st.rerun()
        
        coord_ni = st.text_input("Coordinador Forestal", cargar_memoria("ni_coord", "My (B) Mendoza Luis"))

        if 'nota_informativa_generada' not in st.session_state:
            st.session_state.nota_informativa_generada = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("📝 GENERAR NOTA INFORMATIVA", use_container_width=True, key="btn_ni"):
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            nombre_dia = dias[fecha_ni.weekday()].capitalize()
            fecha_str_ni = f"{nombre_dia} {fecha_ni.strftime('%d/%m/%Y')}"

            guardar_memoria("ni_texto", texto_ni)
            guardar_memoria("ni_coord", coord_ni)

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
            estado_met = st.text_input("estado", cargar_memoria("met_estado", "Carabobo"))
            estacion_met = st.text_input("Estación", cargar_memoria("met_estacion", "EBF Las Josefinas"))
            fecha_met = st.date_input("Fecha", datetime.now(), key="f_met_rep")
        with col_m2:
            hora_met = st.text_input("Hora", cargar_memoria("met_hora", "07:26 Hrs"))
            capacidad_op = st.number_input("Capacidad Operativa", min_value=0, value=int(cargar_memoria("met_capacidad", 20)), step=1)

        if "met_condiciones" not in st.session_state:
            st.session_state["met_condiciones"] = cargar_memoria("met_condiciones", "Precipitaciones leves en el sector La Cumaca, parroquia San Diego, municipio San Diego, estado Carabobo")

        condiciones_met = st.text_area(
            "Condiciones Atmosféricas",
            height=80,
            key="met_condiciones"
        )
        
        col_met_btn1, col_met_btn2 = st.columns([3, 1])
        with col_met_btn2:
            if st.button("✨ IA Condiciones", key="btn_ia_cond_met"):
                if condiciones_met.strip():
                    with st.spinner("🤖 Mejorando..."):
                        cond_mejorada_met = mejorar_redaccion_ia(condiciones_met, "condiciones meteorológicas")
                        st.session_state["cond_mejorada_mostrar_met"] = cond_mejorada_met
                        st.rerun()
                else:
                    st.warning("Escribe algo primero")
        
        if "cond_mejorada_mostrar_met" in st.session_state:
            st.text_area(
                "Condiciones mejoradas:",
                value=st.session_state["cond_mejorada_mostrar_met"],
                key="cond_mejorada_display_met",
                height=80,
                disabled=True
            )
            
            col_met_conf1, col_met_conf2 = st.columns(2)
            with col_met_conf1:
                if st.button("✅ Usar mejorado", key="btn_usar_cond_met"):
                    guardar_memoria("met_condiciones", st.session_state["cond_mejorada_mostrar_met"])
                    del st.session_state["met_condiciones"]
                    del st.session_state["cond_mejorada_mostrar_met"]
                    st.rerun()
            with col_met_conf2:
                if st.button("❌ Mantener original", key="btn_mantener_cond_met"):
                    del st.session_state["cond_mejorada_mostrar_met"]
                    st.rerun()
        
        if "met_acciones" not in st.session_state:
            st.session_state["met_acciones"] = cargar_memoria("met_acciones", "El personal se encuentra de manera preventiva para atender cualquier eventualidad que se pueda suscitar en la zona.")

        acciones_met = st.text_area(
            "Acciones Realizadas",
            height=80,
            key="met_acciones"
        )
        
        col_acc_met_btn1, col_acc_met_btn2 = st.columns([3, 1])
        with col_acc_met_btn2:
            if st.button("✨ IA Acciones", key="btn_ia_acc_met"):
                if acciones_met.strip():
                    with st.spinner("🤖 Mejorando..."):
                        acc_mejorada_met = mejorar_redaccion_ia(acciones_met, "acciones realizadas")
                        st.session_state["acc_mejorada_mostrar_met"] = acc_mejorada_met
                        st.rerun()
                else:
                    st.warning("Escribe algo primero")
        
        if "acc_mejorada_mostrar_met" in st.session_state:
            st.text_area(
                "Acciones mejoradas:",
                value=st.session_state["acc_mejorada_mostrar_met"],
                key="acc_mejorada_display_met",
                height=80,
                disabled=True
            )
            
            col_acc_met_conf1, col_acc_met_conf2 = st.columns(2)
            with col_acc_met_conf1:
                if st.button("✅ Usar mejorado", key="btn_usar_acc_met"):
                    guardar_memoria("met_acciones", st.session_state["acc_mejorada_mostrar_met"])
                    del st.session_state["met_acciones"]
                    del st.session_state["acc_mejorada_mostrar_met"]
                    st.rerun()
            with col_acc_met_conf2:
                if st.button("❌ Mantener original", key="btn_mantener_acc_met"):
                    del st.session_state["acc_mejorada_mostrar_met"]
                    st.rerun()

        if 'reporte_met_generado' not in st.session_state:
            st.session_state.reporte_met_generado = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🌤️ GENERAR REPORTE METEOROLÓGICO", use_container_width=True, key="btn_rm"):
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            nombre_dia = dias[fecha_met.weekday()].capitalize()
            fecha_str_met = f"{nombre_dia} {fecha_met.strftime('%d/%m/%Y')}"

            guardar_memoria("met_estado", estado_met)
            guardar_memoria("met_estacion", estacion_met)
            guardar_memoria("met_hora", hora_met)
            guardar_memoria("met_capacidad", capacidad_op)
            guardar_memoria("met_condiciones", condiciones_met)
            guardar_memoria("met_acciones", acciones_met)

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
            tipo_unidad = st.selectbox(
                "Tipo de Unidad",
                [
                    "UNIDAD PARTICULAR",
                    "UNIDAD TIPO MOTO",
                    "UNIDAD 4.4 (Transporte de Personal)",
                    "UNIDAD 4.2 (Cisterna)"
                ],
                index=["UNIDAD PARTICULAR", "UNIDAD TIPO MOTO", "UNIDAD 4.4 (Transporte de Personal)", "UNIDAD 4.2 (Cisterna)"].index(cargar_memoria("unidad_tipo", "UNIDAD TIPO MOTO")),
                key="tipo_unidad"
            )
            
            if tipo_unidad == "UNIDAD TIPO MOTO":
                num_unidad = st.number_input("Número de Unidad", min_value=1, max_value=99, value=int(cargar_memoria("unidad_num", 41)))
                unidad_completa = f"{tipo_unidad} {num_unidad:02d}"
            else:
                unidad_completa = tipo_unidad

        st.subheader("👥 Personal")
        col_ru3, col_ru4 = st.columns(2)
        with col_ru3:
            comandante_comision = st.text_input(
                "Comandante de Comisión",
                cargar_memoria("unidad_comandante", ""),
                placeholder="Ej: C/1(B) Brito Pedro"
            )
        with col_ru4:
            operador_conductor = st.text_input(
                "Operador/Conductor",
                cargar_memoria("unidad_operador", ""),
                placeholder="Ej: S/1 (B) Díaz Jorge"
            )

        st.subheader("📍 Ubicación")
        ubicaciones_unidad = cargar_ubicaciones()
        estados_unidad = list(ubicaciones_unidad.keys())
        
        estado_unidad = st.selectbox(
            "Estado",
            estados_unidad,
            index=estados_unidad.index(cargar_memoria("unidad_estado", "Carabobo")),
            key="estado_unidad"
        )
        
        if estado_unidad == "Carabobo":
            municipios_carabobo_unidad = ubicaciones_unidad["Carabobo"]["municipios"]
            col_ru5, col_ru6 = st.columns(2)
            with col_ru5:
                municipio_unidad = st.selectbox(
                    "Municipio",
                    list(municipios_carabobo_unidad.keys()),
                    index=list(municipios_carabobo_unidad.keys()).index(cargar_memoria("unidad_municipio", "San Diego")),
                    key="municipio_unidad"
                )
            with col_ru6:
                parroquia_unidad = st.selectbox(
                    "Parroquia",
                    municipios_carabobo_unidad[municipio_unidad]["parroquias"],
                    index=municipios_carabobo_unidad[municipio_unidad]["parroquias"].index(cargar_memoria("unidad_parroquia", municipios_carabobo_unidad[municipio_unidad]["parroquias"][0])),
                    key="parroquia_unidad"
                )
            sector_unidad = st.text_input("Sector", cargar_memoria("unidad_sector", ""), key="sector_unidad")
        else:
            municipio_unidad = st.text_input("Municipio", cargar_memoria("unidad_municipio", ""), key="municipio_unidad")
            parroquia_unidad = st.text_input("Parroquia", cargar_memoria("unidad_parroquia", ""), key="parroquia_unidad")
            sector_unidad = st.text_input("Sector", cargar_memoria("unidad_sector", ""), key="sector_unidad")

        ubicacion_unidad = f"parroquia {parroquia_unidad}, municipio {municipio_unidad}, {sector_unidad}, estado {estado_unidad}"

        st.subheader("👥 Efectivos y Motivo")
        cantidad_efectivos_unidad = st.number_input(
            "Cantidad de Efectivos",
            min_value=1,
            value=int(cargar_memoria("unidad_efectivos", 4)),
            step=1
        )

        if "unidad_motivo" not in st.session_state:
            st.session_state["unidad_motivo"] = cargar_memoria("unidad_motivo", "")

        motivo_unidad = st.text_area(
            "Motivo:",
            placeholder="Ejemplo: Reporta C/1 (B) Brito Pedro que se encuentran en el lugar antes mencionado...",
            height=120,
            key="unidad_motivo"
        )

        col_mot_btn1, col_mot_btn2 = st.columns([3, 1])
        with col_mot_btn2:
            if st.button("✨ IA Motivo", key="btn_ia_motivo_unidad"):
                if motivo_unidad.strip():
                    with st.spinner("🤖 Mejorando..."):
                        motivo_mejorado = mejorar_redaccion_ia(motivo_unidad, "motivo de unidad")
                        st.session_state["motivo_mejorado_mostrar_unidad"] = motivo_mejorado
                        st.rerun()
                else:
                    st.warning("Escribe algo primero")

        if "motivo_mejorado_mostrar_unidad" in st.session_state:
            st.text_area(
                "Motivo mejorado:",
                value=st.session_state["motivo_mejorado_mostrar_unidad"],
                key="motivo_mejorado_display_unidad",
                height=120,
                disabled=True
            )
            
            col_mot_conf1, col_mot_conf2 = st.columns(2)
            with col_mot_conf1:
                if st.button("✅ Usar mejorado", key="btn_usar_motivo_unidad"):
                    guardar_memoria("unidad_motivo", st.session_state["motivo_mejorado_mostrar_unidad"])
                    del st.session_state["unidad_motivo"]
                    del st.session_state["motivo_mejorado_mostrar_unidad"]
                    st.rerun()
            with col_mot_conf2:
                if st.button("❌ Mantener original", key="btn_mantener_motivo_unidad"):
                    del st.session_state["motivo_mejorado_mostrar_unidad"]
                    st.rerun()

        if 'reporte_unidad_generado' not in st.session_state:
            st.session_state.reporte_unidad_generado = ""

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚒 GENERAR REPORTE DE UNIDAD", use_container_width=True, key="btn_generar_unidad"):
            if not motivo_unidad.strip():
                st.warning("⚠️ Por favor complete el motivo.")
            else:
                guardar_memoria("unidad_tipo", tipo_unidad)
                guardar_memoria("unidad_num", num_unidad if tipo_unidad == "UNIDAD TIPO MOTO" else 41)
                guardar_memoria("unidad_comandante", comandante_comision)
                guardar_memoria("unidad_operador", operador_conductor)
                guardar_memoria("unidad_estado", estado_unidad)
                guardar_memoria("unidad_municipio", municipio_unidad)
                guardar_memoria("unidad_parroquia", parroquia_unidad)
                guardar_memoria("unidad_sector", sector_unidad)
                guardar_memoria("unidad_efectivos", cantidad_efectivos_unidad)
                guardar_memoria("unidad_motivo", motivo_unidad)
                
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
{motivo_unidad}"""

        if st.session_state.reporte_unidad_generado:
            st.subheader("📋 Reporte de Unidad Formateado (Listo para copiar a WhatsApp)")
            st.code(st.session_state.reporte_unidad_generado, language=None)
