#pip install streamlit pandas pdfplumber plotly
# se ejecuta python -m streamlit run dashBoardDiario.py


import os
import re
import pdfplumber
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import glob
import unicodedata


# ============================================================
# CONFIGURACIÓN
# ============================================================

# ============================================================
# REPORTES DIARIOS POR COORDINADOR
# ============================================================

#CARPETA_REPORTES = r"C:\Users\Lenovo\Downloads\reporteD\dashboardGit\reportesDiariosVL"
#CARPETA_REPORTES = r"C:\Users\Lenovo\Downloads\reporteD\dashboardGit\reportesDiarios/VLResumen_*.pdf"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARPETA_REPORTES = os.path.join(
    BASE_DIR,
    "reportesDiariosVL"
)

# Vacío = administrador (puede elegir cualquier coordinador).
# Con valor = portal exclusivo que solo enumera ese coordinador.
# Los archivos app_<coordinador>.py establecen esta variable antes de importar
# el dashboard, por lo que el filtro no depende de parámetros modificables.
DASHBOARD_COORDINADOR = os.environ.get("DASHBOARD_COORDINADOR", "").strip()

PDFS = glob.glob(
    os.path.join(
        CARPETA_REPORTES,
        "Resumen_*.pdf"
    )
)


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


def obtener_coordinador_archivo(nombre_archivo):
    """Obtiene el coordinador desde Resumen_<Coordinador>_<AAAAMMDD>.pdf."""
    nombre = os.path.basename(str(nombre_archivo))
    encontrado = re.match(
        r"^Resumen_(.+)_(\d{8})\.pdf$",
        nombre,
        flags=re.IGNORECASE,
    )
    if not encontrado:
        # Resumen_20260820.pdf y nombres que no cumplen el patrón son generales.
        return "General"
    coordinador = encontrado.group(1).strip("_ ")
    return coordinador.replace("_", " ") if coordinador else "General"


def obtener_fecha_archivo(nombre_archivo):
    encontrado = re.search(r"_(\d{8})\.pdf$", str(nombre_archivo), re.IGNORECASE)
    if not encontrado:
        return "Sin fecha"
    fecha = encontrado.group(1)
    return f"{fecha[6:8]}/{fecha[4:6]}/{fecha[0:4]}"


def seleccionar_reporte():
    reportes = obtener_reportes_pdf()

    if not reportes:
        st.error(f"No existen reportes PDF en: {CARPETA_REPORTES}")
        return None

    reportes_por_coordinador = {}
    for reporte in reportes:
        coordinador = obtener_coordinador_archivo(reporte)
        reportes_por_coordinador.setdefault(coordinador, []).append(reporte)

    coordinadores = sorted(
        reportes_por_coordinador,
        key=lambda valor: (valor.lower() == "general", valor.lower()),
    )

    if DASHBOARD_COORDINADOR:
        coincidencia = next(
            (c for c in coordinadores if c.casefold() == DASHBOARD_COORDINADOR.casefold()),
            None,
        )
        if coincidencia is None:
            st.error(
                f"No existen reportes para el coordinador configurado: "
                f"{DASHBOARD_COORDINADOR}"
            )
            return None
        coordinador_seleccionado = coincidencia
        st.sidebar.markdown(f"### Coordinador: {coordinador_seleccionado}")
    else:
        coordinador_seleccionado = st.sidebar.selectbox(
            "Seleccionar coordinador",
            coordinadores,
        )
    reportes_filtrados = sorted(
        reportes_por_coordinador[coordinador_seleccionado],
        reverse=True,
    )
    seleccionado = st.sidebar.selectbox(
        "Seleccionar reporte del coordinador",
        reportes_filtrados,
        format_func=lambda nombre: f"{obtener_fecha_archivo(nombre)} — {nombre}",
    )
    st.sidebar.caption(
        f"{len(reportes_filtrados)} reporte(s) disponible(s) para {coordinador_seleccionado}."
    )
    st.session_state["coordinador_seleccionado"] = coordinador_seleccionado
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

def extraer_secciones_pdf(pdf_path):
    """Separa el concentrado y cada campaña usando los encabezados del PDF."""

    if not os.path.exists(pdf_path):
        st.error(
            f"No se encontró el archivo PDF:\n\n{pdf_path}"
        )
        return {}

    secciones = {}
    seccion_actual = "Concentrado general"

    try:

        with pdfplumber.open(pdf_path) as pdf:

            for numero_pagina, pagina in enumerate(pdf.pages):

                contenido = pagina.extract_text() or ""

                encabezado_campania = re.search(
                    r"CAMPA.A\s*/\s*ARCHIVO:\s*([^\r\n]+)",
                    contenido,
                    flags=re.IGNORECASE,
                )
                if encabezado_campania:
                    seccion_actual = encabezado_campania.group(1).strip()

                if contenido:
                    seccion = secciones.setdefault(
                        seccion_actual,
                        {"texto": "", "paginas": []},
                    )
                    seccion["texto"] += "\n" + contenido
                    seccion["paginas"].append(numero_pagina)

    except Exception as e:

        st.error(f"Error leyendo el PDF: {e}")
        return {}

    return secciones


def extraer_texto_pdf(pdf_path):
    """Compatibilidad: devuelve todo el texto del PDF."""
    return "\n".join(
        seccion["texto"]
        for seccion in extraer_secciones_pdf(pdf_path).values()
    )


# ============================================================
# EXTRAER RESUMEN OPERATIVO
# ============================================================

def extraer_resumen(texto):
    campos = [
        "Intentos", "Conectada", "No conectada", "Abandonada", "Atendida",
        "Tipificada", "No tipificada", "Titular", "No titular", "Buzón",
        "Indefinida", "Negativa", "Efectiva", "Interesado", "Seguimiento",
        "Amarillo",
    ]
    globales = {campo: 0 for campo in campos}

    def normalizar_linea(valor):
        valor = str(valor).replace("�", "o")
        valor = unicodedata.normalize("NFKD", valor)
        return "".join(c for c in valor if not unicodedata.combining(c)).strip().lower()

    lineas_originales = [x.strip() for x in texto.splitlines() if x.strip()]
    lineas = [normalizar_linea(x) for x in lineas_originales]
    filas = [
        (["intentos"], ["Intentos"]),
        (["conectada", "no conectada"], ["Conectada", "No conectada"]),
        (["abandonada", "atendida"], ["Abandonada", "Atendida"]),
        (["tipificada", "no tipificada"], ["Tipificada", "No tipificada"]),
        (["titular", "no titular", "buzon", "indefinida"], ["Titular", "No titular", "Buzón", "Indefinida"]),
        (["negativa", "efectiva"], ["Negativa", "Efectiva"]),
        (["interesado", "seguimiento"], ["Interesado", "Seguimiento"]),
        (["amarillo"], ["Amarillo"]),
    ]

    usados = set()
    for etiquetas_busqueda, claves in filas:
        for i, linea in enumerate(lineas[:-1]):
            if i in usados or not all(etiqueta in linea for etiqueta in etiquetas_busqueda):
                continue
            valores = re.findall(r"\d[\d,]*", lineas_originales[i + 1])
            if len(valores) >= len(claves):
                for clave, valor in zip(claves, valores):
                    globales[clave] = int(numero(valor))
                usados.add(i)
                break

    # Compatibilidad con los títulos de la versión anterior del PDF.
    compatibilidad = {
        "Intentos": r"Intentos\s+de\s+Llamadas\s+([\d,]+)",
        "Conectada": r"Llamadas\s+Conectadas\s+([\d,]+)",
        "Abandonada": r"Abandonadas\s+([\d,]+)",
        "Tipificada": r"Llamadas\s+Tipificadas\s+([\d,]+)",
        "No tipificada": r"Sin\s+Tipificar\s+([\d,]+)",
        "Efectiva": r"Contacto\s+Efectivo\s+([\d,]+)",
        "Negativa": r"Contacto\s+Negativo\s+([\d,]+)",
    }
    for clave, patron in compatibilidad.items():
        if globales[clave] == 0:
            encontrado = re.search(patron, texto, re.IGNORECASE)
            if encontrado:
                globales[clave] = int(numero(encontrado.group(1)))

    if globales["Atendida"] == 0:
        globales["Atendida"] = max(0, globales["Conectada"] - globales["Abandonada"])
    if globales["No conectada"] == 0:
        globales["No conectada"] = max(0, globales["Intentos"] - globales["Conectada"])
    return globales


def extraer_agentes(texto, pdf_path=None, paginas_pdf=None):
    """Extrae la tabla por agente, incluso si sesión/nombre vienen vacíos o desbordados."""
    columnas = [
        "Agente", "Nombre", "Hora inicio", "Total sesión", "Titular",
        "No titular", "Buzón", "Indefinida", "Negativa", "Efectiva",
        "Interesado", "Seguimiento", "Sin tipificar", "Mal tipificadas", "Total",
    ]
    filas = []

    def celda(valor):
        return re.sub(r"\s+", " ", str(valor or "").replace("\n", " ")).strip()

    def agregar_fila(agente, nombre, hora_inicio, total_sesion, metricas):
        if not re.fullmatch(r"\d{3,6}", agente or "") or len(metricas) != 11:
            return
        filas.append([
            agente, nombre, hora_inicio, total_sesion,
            *[int(numero(valor)) for valor in metricas],
        ])

    patron_texto = re.compile(
        r"^(\d{3,6})(?:\s+(.*?))?\s+((?:[\d,]+\s+){10}[\d,]+)$"
    )
    nombres_texto = {}
    for linea in texto.splitlines():
        coincidencia = patron_texto.match(linea.strip())
        if coincidencia:
            nombres_texto[coincidencia.group(1)] = celda(coincidencia.group(2))

    # Método principal: pdfplumber conserva las 15 celdas aunque el texto
    # extraído de la página omita Hora inicio y Total sesión.
    if pdf_path and os.path.exists(pdf_path):
        try:
            with pdfplumber.open(pdf_path) as pdf:
                paginas_permitidas = (
                    set(paginas_pdf) if paginas_pdf is not None else None
                )
                for numero_pagina, pagina in enumerate(pdf.pages):
                    if (
                        paginas_permitidas is not None
                        and numero_pagina not in paginas_permitidas
                    ):
                        continue
                    for tabla in pagina.extract_tables() or []:
                        if not tabla or len(tabla[0]) < 15:
                            continue
                        encabezado = [celda(x).lower() for x in tabla[0]]
                        if not encabezado or encabezado[0] != "agente":
                            continue
                        for registro in tabla[1:]:
                            if not registro or len(registro) < 15:
                                continue
                            valores = [celda(x) for x in registro[:15]]
                            agente = valores[0]
                            nombre_partes = [valores[1]] if valores[1] else []
                            hora_inicio = valores[2] if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", valores[2]) else ""
                            total_sesion = valores[3] if re.fullmatch(r"\d{1,3}:\d{2}", valores[3]) else ""
                            # Los nombres largos pueden invadir visualmente las
                            # dos celdas vacías de sesión; se reconstruyen aquí.
                            if valores[2] and not hora_inicio:
                                nombre_partes.append(valores[2])
                            if valores[3] and not total_sesion:
                                nombre_partes.append(valores[3])
                            agregar_fila(
                                agente,
                                " ".join(x for x in nombre_partes if x).strip(),
                                hora_inicio,
                                total_sesion,
                                valores[-11:],
                            )
        except Exception as error:
            print(f"No se pudo extraer la tabla estructurada de agentes: {error}")

    if filas:
        for fila in filas:
            if fila[0] in nombres_texto:
                fila[1] = nombres_texto[fila[0]]
        return pd.DataFrame(filas, columns=columnas).drop_duplicates(
            subset=["Agente"], keep="first"
        )

    # Respaldo para PDF antiguos: toma los 11 KPI desde el final de cada fila
    # sin exigir que las columnas de sesión estén informadas.
    for linea in texto.splitlines():
        encontrado = patron_texto.match(linea.strip())
        if not encontrado:
            continue
        prefijo = celda(encontrado.group(2))
        hora_inicio = ""
        total_sesion = ""
        tokens = prefijo.split()
        if tokens and re.fullmatch(r"\d{1,3}:\d{2}", tokens[-1]):
            total_sesion = tokens.pop()
        if tokens and re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", tokens[-1]):
            hora_inicio = tokens.pop()
        agregar_fila(
            encontrado.group(1), " ".join(tokens), hora_inicio,
            total_sesion, encontrado.group(3).split(),
        )
    return pd.DataFrame(filas, columns=columnas)


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


def generar_dashboard_nuevos_kpi():
    """Dashboard operativo basado en el embudo oficial de nuevos KPI."""
    st.set_page_config(
        page_title="Dashboard Call Center - Nuevos KPI",
        page_icon="📊",
        layout="wide",
    )
    pdf_path = seleccionar_reporte()
    if not pdf_path:
        return

    secciones_pdf = extraer_secciones_pdf(pdf_path)
    if not secciones_pdf:
        return

    nombres_secciones = list(secciones_pdf)
    if len(nombres_secciones) > 1:
        seccion_seleccionada = st.sidebar.selectbox(
            "Seleccionar concentrado o campaña",
            nombres_secciones,
            format_func=lambda nombre: (
                nombre if nombre == "Concentrado general"
                else f"Campaña: {nombre}"
            ),
        )
        st.sidebar.caption(
            f"{len(nombres_secciones) - 1} campaña(s) disponible(s) "
            "en este reporte."
        )
    else:
        seccion_seleccionada = nombres_secciones[0]

    seccion_pdf = secciones_pdf[seccion_seleccionada]
    texto_pdf = seccion_pdf["texto"]

    kpi = extraer_resumen(texto_pdf)
    agentes = extraer_agentes(
        texto_pdf,
        pdf_path,
        paginas_pdf=seccion_pdf["paginas"],
    )

    st.markdown("""
    <style>
      .titulo-kpi {text-align:center; color:#17365d; font-size:2.1rem; font-weight:750;}
      .subtitulo-kpi {text-align:center; color:#64748b; margin-bottom:1.4rem;}
      div[data-testid="stMetric"] {background:#f5f9fc; border:1px solid #cbd9e6;
        border-radius:10px; padding:14px 16px; min-height:112px;}
      div[data-testid="stMetricLabel"] {
        font-weight:800;
        color:#17365d;
        font-size:1rem;
        letter-spacing:.02em;
      }
    </style>
    """, unsafe_allow_html=True)

    coordinador = st.session_state.get(
        "coordinador_seleccionado",
        obtener_coordinador_archivo(pdf_path),
    )
    nombre_reporte = os.path.basename(pdf_path).replace(".pdf", "").replace("_", " ")
    st.markdown('<div class="titulo-kpi">TABLERO OPERATIVO OUTBOUND</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="subtitulo-kpi">Coordinador: <b>{coordinador}</b><br>'
        f'{nombre_reporte}<br>Vista: <b>{seccion_seleccionada}</b></div>',
        unsafe_allow_html=True,
    )

    filas_tarjetas = [
        [("INTENTOS", "Intentos"), ("CONECTADA", "Conectada"), ("NO CONECTADA", "No conectada")],
        [("ABANDONADA", "Abandonada"), ("ATENDIDA", "Atendida"), ("TIPIFICADA", "Tipificada"), ("NO TIPIFICADA", "No tipificada")],
        [("TITULAR", "Titular"), ("NO TITULAR", "No titular"), ("BUZÓN", "Buzón"), ("INDEFINIDA", "Indefinida")],
        [("NEGATIVA", "Negativa"), ("EFECTIVA", "Efectiva"), ("INTERESADO", "Interesado"), ("SEGUIMIENTO", "Seguimiento"), ("AMARILLO", "Amarillo")],
    ]
    for fila in filas_tarjetas:
        columnas = st.columns(len(fila))
        for columna, (titulo, clave) in zip(columnas, fila):
            with columna:
                st.metric(titulo, f"{kpi[clave]:,}")
        st.write("")

    st.markdown("---")
    st.header("Embudo de llamadas")

    nodos = [
        "Intentos", "Conectada", "No conectada", "Abandonada", "Atendida",
        "Tipificada", "No tipificada", "Titular", "No titular", "Buzón",
        "Indefinida", "Negativa", "Efectiva", "Interesado", "Seguimiento", "Amarillo",
    ]
    indice = {nombre: i for i, nombre in enumerate(nodos)}
    relaciones = [
        ("Intentos", "Conectada"), ("Intentos", "No conectada"),
        ("Conectada", "Abandonada"), ("Conectada", "Atendida"),
        ("Atendida", "Tipificada"), ("Atendida", "No tipificada"),
        ("Tipificada", "Titular"), ("Tipificada", "No titular"),
        ("Tipificada", "Buzón"), ("Tipificada", "Indefinida"),
        ("Titular", "Negativa"), ("Titular", "Efectiva"),
        ("Efectiva", "Interesado"), ("Efectiva", "Seguimiento"),
        ("Interesado", "Amarillo"),
    ]
    fuente, destino, valores = [], [], []
    for padre, hijo in relaciones:
        valor = int(kpi[hijo])
        if valor > 0:
            fuente.append(indice[padre])
            destino.append(indice[hijo])
            valores.append(valor)

    fig_embudo = go.Figure(go.Sankey(
        arrangement="snap",
        textfont=dict(
            family="Arial Black, Arial, sans-serif",
            size=16,
            color="#111827",
        ),
        node=dict(
            pad=24,
            thickness=26,
            label=[f"{n}<br>{kpi[n]:,}" for n in nodos],
            color=["#17365d", "#3b82f6", "#94a3b8", "#f59e0b", "#22c55e",
                   "#2563eb", "#94a3b8", "#0f766e", "#64748b", "#64748b",
                   "#64748b", "#dc2626", "#16a34a", "#059669", "#0ea5e9", "#eab308"],
            line=dict(color="#334155", width=1.2),
            hovertemplate="<b>%{label}</b><extra></extra>",
        ),
        link=dict(
            source=fuente,
            target=destino,
            value=valores,
            color="rgba(147,197,253,.20)",
            hovertemplate="%{source.label} → %{target.label}<br>%{value:,}<extra></extra>",
        ),
    ))
    fig_embudo.update_layout(
        height=780,
        margin=dict(l=35, r=35, t=30, b=20),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(
            family="Arial Black, Arial, sans-serif",
            size=16,
            color="#111827",
        ),
    )
    st.plotly_chart(fig_embudo, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Clasificación de tipificadas")
        clasificacion = pd.DataFrame({
            "Clasificación": ["Titular", "No titular", "Buzón", "Indefinida"],
            "Valor": [kpi["Titular"], kpi["No titular"], kpi["Buzón"], kpi["Indefinida"]],
        })
        fig = px.pie(clasificacion, names="Clasificación", values="Valor", hole=.45)
        fig.update_layout(height=390, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Resultado del contacto titular")
        resultado = pd.DataFrame({
            "Resultado": ["Negativa", "Efectiva"],
            "Valor": [kpi["Negativa"], kpi["Efectiva"]],
        })
        fig = px.bar(resultado, x="Resultado", y="Valor", color="Resultado", text="Valor")
        fig.update_traces(textposition="outside")
        fig.update_layout(height=390, showlegend=False, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.header("Resumen por Agente / Extensión")
    if agentes.empty:
        st.info("El PDF seleccionado no contiene una tabla de agentes legible.")
    else:
        st.dataframe(agentes, use_container_width=True, hide_index=True)
        grafica = agentes.copy()
        grafica["Total"] = pd.to_numeric(grafica["Total"], errors="coerce").fillna(0)
        fig = px.bar(
            grafica.sort_values("Total", ascending=False),
            x="Agente", y="Total", text="Total", color="Mal tipificadas",
            title="Gestiones totales y concentración de malas tipificaciones",
            color_continuous_scale="Reds",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=460)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Validación de reconciliación de KPI"):
        validaciones = pd.DataFrame([
            ["Intentos", kpi["Intentos"], kpi["Conectada"] + kpi["No conectada"]],
            ["Conectada", kpi["Conectada"], kpi["Abandonada"] + kpi["Atendida"]],
            ["Atendida", kpi["Atendida"], kpi["Tipificada"] + kpi["No tipificada"]],
            ["Tipificada", kpi["Tipificada"], kpi["Titular"] + kpi["No titular"] + kpi["Buzón"] + kpi["Indefinida"]],
            ["Titular", kpi["Titular"], kpi["Negativa"] + kpi["Efectiva"]],
            ["Efectiva", kpi["Efectiva"], kpi["Interesado"] + kpi["Seguimiento"]],
        ], columns=["Nivel", "KPI padre", "Suma de ramas"])
        validaciones["Diferencia"] = validaciones["KPI padre"] - validaciones["Suma de ramas"]
        st.dataframe(validaciones, use_container_width=True, hide_index=True)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    generar_dashboard_nuevos_kpi()
