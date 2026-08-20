#pip install streamlit pandas pdfplumber plotly
# se ejecuta python -m streamlit run dashBoardDiario.py


import os
import re
import pdfplumber
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px


# ============================================================
# CONFIGURACIÓN
# ============================================================

# ============================================================
# REPORTES DIARIOS POR COORDINADOR
# ============================================================

#CARPETA_REPORTES = r"C:\Users\Lenovo\Downloads\reporteD\dashboardGit\reportesDiariosVL"
CARPETA_REPORTES = r"C:\Users\Lenovo\Downloads\reporteD\dashboardGit\reportesDiariosVLResumen_*.pdf"

def obtener_reportes_pdf():
    if not os.path.exists(CARPETA_REPORTES):
        return []
    return sorted(
        [
            f for f in os.listdir(CARPETA_REPORTES)
            if f.lower().endswith(".pdf") and f.startswith("Resumen_")
        ],
        reverse=True
    )

def seleccionar_reporte():
    reportes = obtener_reportes_pdf()

    if not reportes:
        st.error(f"No existen reportes PDF en: {CARPETA_REPORTES}")
        return None

    seleccionado = st.sidebar.selectbox(
        "Seleccionar reporte diario",
        reportes
    )

    return os.path.join(CARPETA_REPORTES, seleccionado)

PDF_PATH = None


# ============================================================
# FUNCIÓN AUXILIAR
# ============================================================

def numero(valor):
    """
    Convierte textos como:
    7,155
    7.81 %
    35,269.95
    en números.
    """

    if valor is None:
        return 0

    valor = str(valor).strip()
    valor = valor.replace(",", "")
    valor = valor.replace("%", "")
    valor = valor.strip()

    try:
        if "." in valor:
            return float(valor)
        return int(valor)
    except:
        return 0


# ============================================================
# EXTRAER TEXTO DEL PDF
# ============================================================

def extraer_texto_pdf(pdf_path):

    if not os.path.exists(pdf_path):
        st.error(
            f"No se encontró el archivo PDF:\n\n{pdf_path}"
        )
        return ""

    texto = ""

    try:

        with pdfplumber.open(pdf_path) as pdf:

            for pagina in pdf.pages:

                contenido = pagina.extract_text()

                if contenido:
                    texto += "\n" + contenido

    except Exception as e:

        st.error(f"Error leyendo el PDF: {e}")
        return ""

    return texto


# ============================================================
# EXTRAER RESUMEN OPERATIVO
# ============================================================

def extraer_resumen(texto):

    globales = {
        "Registros Cargados": 0,
        "Intentos de Llamadas": 0,
        "Llamadas Conectadas": 0,
        "Sin Tipificar": 0,
        "Llamadas Tipificadas": 0,
        "Abandonadas": 0,
        "Contacto Efectivo": 0,
        "Contacto Negativo": 0,
        "Tipificación Correcta": 0,
        "Tipificación Incorrecta": 0,
        "% Campaña": 0,
        "% Efectivo": 0,
        "% Negativo": 0
    }

    # --------------------------------------------------------
    # Buscar cada dato dentro del texto
    # --------------------------------------------------------

    patrones = {

        "Registros Cargados":
            r"Registros\s+Cargados\s+([\d,]+)",

        "Intentos de Llamadas":
            r"Intentos\s+de\s+Llamadas\s+([\d,]+)",

        "Llamadas Conectadas":
            r"Llamadas\s+Conectadas\s+([\d,]+)",

        "Sin Tipificar":
            r"Sin\s+Tipificar\s+([\d,]+)",

        "Llamadas Tipificadas":
            r"Llamadas\s+Tipificadas\s+([\d,]+)",

        "Abandonadas":
            r"Abandonadas\s+([\d,]+)",

        "% Efectivo":
            r"%\s*Efectivo\s+([\d.]+)\s*%",

        "Contacto Efectivo":
            r"Contacto\s+Efectivo\s+([\d,]+)",

        "% Negativo":
            r"%\s*Negativo\s+([\d.]+)\s*%",

        "Contacto Negativo":
            r"Contacto\s+Negativo\s+([\d,]+)",

        "Tipificación Correcta":
            r"Tipificacion\s+Correcta\s+([\d,]+)",

        "Tipificación Incorrecta":
            r"Tipificacion\s+Incorrecta\s+([\d,]+)",

        "% Campaña":
            r"%\s*Campaña\s+([\d.]+)\s*%"
    }

    for campo, patron in patrones.items():

        encontrado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if encontrado:

            valor = encontrado.group(1)

            if "%" in campo:
                globales[campo] = float(valor)
            else:
                globales[campo] = numero(valor)

    return globales


# ============================================================
# DATOS DE TIPIFICACIÓN EXITOSA
# ============================================================

def datos_exitosa():

    datos = [

        [
            "Interés Real",
            "ENVIARA DATOS PARA COTIZACION",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "Interés Real",
            "CLIENTE INTERESADO",
            5,
            35269.95,
            12311.39,
            3,
            2
        ],

        [
            "Seguimiento",
            "SE BRINDA INFORMACION GENERAL A CLIENTE",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "Seguimiento",
            "VOLVER A LLAMAR",
            2,
            17056.87,
            3499.04,
            2,
            0
        ],

        [
            "Seguimiento",
            "RECADO",
            2,
            55027.34,
            16508.20,
            2,
            0
        ],

        [
            "Cierre de Gestión Positivo",
            "YA RENOVO",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "Cierre de Gestión Positivo",
            "VENTA",
            0,
            0.00,
            0.00,
            0,
            0
        ]

    ]

    return pd.DataFrame(
        datos,
        columns=[
            "Grupo",
            "Concepto",
            "Valor",
            "Prom. Líquido",
            "Prom. Capacidad",
            "Tipificación Correcta",
            "Tipificación Incorrecta"
        ]
    )


# ============================================================
# DATOS DE TIPIFICACIÓN NEGATIVA
# ============================================================

def datos_negativa():

    datos = [

        [
            "Si Titular",
            "CLIENTE MOLESTO",
            12,
            33288.57,
            8681.89,
            12,
            0
        ],

        [
            "Si Titular",
            "NO LE INTERESA",
            38,
            38559.42,
            10908.66,
            38,
            0
        ],

        [
            "No Titular",
            "CONTESTADORA / FAX",
            14,
            43647.34,
            9836.52,
            6,
            8
        ],

        [
            "No Titular",
            "CLIENTE NO DISPONIBLE",
            1,
            49302.16,
            14790.65,
            0,
            1
        ],

        [
            "No Titular",
            "FUERA DE SERVICIO / SUSPENDIDO",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "No Titular",
            "NO CONTESTA / LINEA OCUPADA",
            60,
            40730.76,
            13228.29,
            40,
            20
        ],

        [
            "No Titular",
            "LLAMADA NO CALIFICADA",
            0,
            0.00,
            2.17,
            0,
            0
        ],

        [
            "No Titular",
            "LLAMADA DE PRUEBA",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "No Titular",
            "TELEFONO INEXISTENTE",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "No Titular",
            "TELEFONO EQUIVOCADO",
            7,
            34970.30,
            8332.11,
            0,
            7
        ],

        [
            "Cierre de Gestión Negativo",
            "FINADO",
            1,
            0.00,
            0.00,
            1,
            0
        ],

        [
            "Cierre de Gestión Negativo",
            "NO SUJETO A CREDITO",
            0,
            0.00,
            933.00,
            0,
            0
        ],

        [
            "Cierre de Gestión Negativo",
            "NO CUMPLE EL TIEMPO",
            0,
            0.00,
            0.00,
            0,
            0
        ],

        [
            "Cierre de Gestión Negativo",
            "SIN CAPACIDAD DE CREDITO",
            0,
            0.00,
            0.00,
            0,
            0
        ]

    ]

    return pd.DataFrame(
        datos,
        columns=[
            "Grupo",
            "Concepto",
            "Valor",
            "Prom. Líquido",
            "Prom. Capacidad",
            "Tipificación Correcta",
            "Tipificación Incorrecta"
        ]
    )


# ============================================================
# DATOS POR AGENTE
# ============================================================

def datos_agentes():

    datos = [

        [1006, "1", "2", 0, 10, 12, 0, 30, 55],
        [1007, "0", "0", 0, 0, 5, 0, 165, 170],
        [1013, "1", "2", 0, 6, 56, 1, 17, 83],
        [1031, "0", "0", 0, 0, 1, 0, 66, 67],
        [1033, "1", "0", 0, 0, 4, 0, 6, 11],
        [1051, "2", "0", 0, 34, 3, 0, 54, 93],
        [1063, "0", "0", 0, 0, 1, 0, 1, 2]

    ]

    return pd.DataFrame(
        datos,
        columns=[
            "Agente",
            "Interés Real",
            "Seguimiento",
            "Cierre Positivo",
            "Si Titular",
            "No Titular",
            "Cierre Negativo",
            "Sin Tipificar",
            "Total"
        ]
    )


# ============================================================
# REGISTROS CARGADOS
# ============================================================

def datos_cargados():

    return pd.DataFrame({

        "Concepto": [
            "Refinanciado",
            "Compra Cartera",
            "Nuevos",
            "General"
        ],

        "Valor": [
            0,
            3485,
            0,
            3670
        ]

    })


# ============================================================
# DASHBOARD
# ============================================================

def generar_dashboard():

    global PDF_PATH

    PDF_PATH = seleccionar_reporte()

    if not PDF_PATH:
        return


    st.set_page_config(
        page_title="Dashboard Dalila",
        page_icon="📊",
        layout="wide"
    )

    # --------------------------------------------------------
    # ESTILO
    # --------------------------------------------------------

    st.markdown("""
    <style>

    .titulo {
        color:#800020;
        text-align:center;
        font-size:32px;
        font-weight:bold;
        margin-bottom:5px;
    }

    .subtitulo {
        text-align:center;
        color:#666;
        font-size:18px;
        margin-bottom:25px;
    }

    </style>
    """, unsafe_allow_html=True)

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    texto_pdf = extraer_texto_pdf(PDF_PATH)

    if not texto_pdf:
        return

    globales = extraer_resumen(texto_pdf)

    df_exitosa = datos_exitosa()
    df_negativa = datos_negativa()
    df_agentes = datos_agentes()
    df_cargados = datos_cargados()

    # --------------------------------------------------------
    # ENCABEZADO
    # --------------------------------------------------------

    st.markdown(
        '<div class="titulo">'
        'TABLERO OPERATIVO OUTBOUND'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitulo">'
        'DALILA — AGOSTO 2026'
        '</div>',
        unsafe_allow_html=True
    )

    # ========================================================
    # KPI
    # ========================================================

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "REGISTROS CARGADOS",
            f"{globales['Registros Cargados']:,}"
        )

    with col2:
        st.metric(
            "INTENTOS DE LLAMADAS",
            f"{globales['Intentos de Llamadas']:,}"
        )

    with col3:
        st.metric(
            "LLAMADAS CONECTADAS",
            f"{globales['Llamadas Conectadas']:,}"
        )

    with col4:
        st.metric(
            "SIN TIPIFICAR",
            f"{globales['Sin Tipificar']:,}"
        )

    with col5:
        st.metric(
            "ABANDONADAS",
            f"{globales['Abandonadas']:,}"
        )

    st.markdown("---")

    # ========================================================
    # SEGUNDA FILA KPI
    # ========================================================

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "LLAMADAS TIPIFICADAS",
            f"{globales['Llamadas Tipificadas']:,}"
        )

    with col2:
        st.metric(
            "CONTACTO EFECTIVO",
            f"{globales['Contacto Efectivo']:,}",
            f"{globales['% Efectivo']:.2f}%"
        )

    with col3:
        st.metric(
            "CONTACTO NEGATIVO",
            f"{globales['Contacto Negativo']:,}",
            f"{globales['% Negativo']:.2f}%"
        )

    with col4:
        st.metric(
            "TIPIFICACIÓN CORRECTA",
            f"{globales['Tipificación Correcta']:,}"
        )

    with col5:
        st.metric(
            "TIPIFICACIÓN INCORRECTA",
            f"{globales['Tipificación Incorrecta']:,}"
        )

    st.markdown("---")

    # ========================================================
    # GRÁFICAS PRINCIPALES
    # ========================================================

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # CONTACTOS
    # --------------------------------------------------------

    with col1:

        st.subheader("Distribución de Contactos")

        labels = [
            "Contacto Efectivo",
            "Contacto Negativo",
            "Sin Tipificar"
        ]

        values = [
            globales["Contacto Efectivo"],
            globales["Contacto Negativo"],
            globales["Sin Tipificar"]
        ]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.45
                )
            ]
        )

        fig.update_layout(
            height=400,
            margin=dict(
                t=20,
                b=20,
                l=20,
                r=20
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # --------------------------------------------------------
    # CORRECTA / INCORRECTA
    # --------------------------------------------------------

    with col2:

        st.subheader("Calidad de Tipificación")

        labels = [
            "Correcta",
            "Incorrecta"
        ]

        values = [
            globales["Tipificación Correcta"],
            globales["Tipificación Incorrecta"]
        ]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.45
                )
            ]
        )

        fig.update_layout(
            height=400,
            margin=dict(
                t=20,
                b=20,
                l=20,
                r=20
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("---")

    # ========================================================
    # TIPIFICACIONES
    # ========================================================

    st.header("📋 Desglose de Tipificaciones")

    tab1, tab2 = st.tabs([
        "🟢 Tipificación Exitosa",
        "🔴 Tipificación Negativa"
    ])

    # --------------------------------------------------------
    # EXITOSA
    # --------------------------------------------------------

    with tab1:

        resumen_exitosa = (
            df_exitosa
            .groupby("Grupo")["Valor"]
            .sum()
            .reset_index()
        )

        col1, col2 = st.columns([1, 2])

        with col1:

            st.subheader("Resumen")

            fig = px.bar(
                resumen_exitosa,
                x="Grupo",
                y="Valor",
                text="Valor"
            )

            fig.update_layout(
                height=350
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col2:

            st.subheader("Detalle")

            st.dataframe(
                df_exitosa,
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------
    # NEGATIVA
    # --------------------------------------------------------

    with tab2:

        resumen_negativa = (
            df_negativa
            .groupby("Grupo")["Valor"]
            .sum()
            .reset_index()
        )

        col1, col2 = st.columns([1, 2])

        with col1:

            st.subheader("Resumen")

            fig = px.bar(
                resumen_negativa,
                x="Grupo",
                y="Valor",
                text="Valor"
            )

            fig.update_layout(
                height=350
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with col2:

            st.subheader("Detalle")

            st.dataframe(
                df_negativa,
                use_container_width=True,
                hide_index=True
            )

    st.markdown("---")

    # ========================================================
    # REGISTROS CARGADOS
    # ========================================================

    st.header("📦 Registros Cargados")

    col1, col2 = st.columns(2)

    with col1:

        fig = px.pie(
            df_cargados,
            names="Concepto",
            values="Valor",
            hole=0.45
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with col2:

        st.dataframe(
            df_cargados,
            use_container_width=True,
            hide_index=True
        )

        st.metric(
            "TOTAL REGISTROS",
            f"{df_cargados['Valor'].sum():,}"
        )

    st.markdown("---")

    # ========================================================
    # AGENTES
    # ========================================================

    st.header("👥 Resumen de Desempeño por Agente / Extensión")

    st.dataframe(
        df_agentes,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # GRÁFICA DE AGENTES
    # ========================================================

    st.subheader("Total de Gestiones por Agente")

    df_grafica = df_agentes.sort_values(
        "Total",
        ascending=False
    )

    fig = px.bar(
        df_grafica,
        x="Agente",
        y="Total",
        text="Total"
    )

    fig.update_layout(
        height=450,
        xaxis_title="Agente",
        yaxis_title="Total de gestiones"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.markdown("---")

    # ========================================================
    # RESUMEN FINAL
    # ========================================================

    st.header("📊 Resumen Ejecutivo")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "EFECTIVIDAD",
            f"{globales['% Efectivo']:.2f}%"
        )

    with col2:
        st.metric(
            "NEGATIVIDAD",
            f"{globales['% Negativo']:.2f}%"
        )

    with col3:
        st.metric(
            "TIPIFICADAS",
            f"{globales['Llamadas Tipificadas']:,}"
        )

    with col4:
        st.metric(
            "ABANDONADAS",
            f"{globales['Abandonadas']:,}"
        )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    generar_dashboard()





