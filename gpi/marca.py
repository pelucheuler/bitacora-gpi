"""Identidad visual institucional del SENA (colores, tipografía y logo opcional).

El logo NO viene incluido: descargue el logo oficial del SENA y guárdelo como
assets/logo_sena.png (ver assets/LEEME.txt). Si el archivo no existe, la app funciona igual sin logo.
"""
import base64
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Paleta institucional SENA
VERDE = "#39A900"         # verde SENA (color principal)
AZUL = "#00304D"          # azul oscuro institucional
VERDE_OSCURO = "#007832"  # verde oscuro de apoyo
GRIS = "#F6F6F6"          # gris claro de fondos
AMARILLO = "#FDC300"      # acento / alertas
VERDE_CLARO = "#EEF7E6"   # fondo suave derivado del verde SENA
FUENTE = "'Work Sans', 'Segoe UI', Calibri, Arial, sans-serif"


def logo_ruta():
    for nombre in ("logo_sena.png", "logo_sena.jpg", "logo_sena.jpeg", "logo_sena.svg", "logo.png"):
        p = RAIZ / "assets" / nombre
        if p.exists():
            return p
    return None


def logo_html(alto=56):
    """<img> con el logo incrustado (para los informes descargables), o cadena vacía si no hay logo."""
    p = logo_ruta()
    if not p:
        return ""
    tipo = {"svg": "svg+xml", "jpg": "jpeg"}.get(p.suffix[1:].lower(), p.suffix[1:].lower())
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/{tipo};base64,{b64}" alt="SENA" style="height:{alto}px">'


def css_informe():
    """Estilos comunes de los informes (expediente e informe de revisión)."""
    return f"""
.marca{{display:flex;align-items:center;gap:16px;border-bottom:6px solid {VERDE};padding-bottom:10px;margin-bottom:12px}}
.marca .txt{{color:{AZUL};font-size:10pt;line-height:1.3}} .marca .txt b{{font-size:11pt}}
"""


def encabezado_informe():
    return (f'<div class="marca">{logo_html()}<div class="txt"><b>Servicio Nacional de Aprendizaje SENA</b><br>'
            'Tecnología en Gestión de la Producción Industrial · Proyecto productivo</div></div>')


CSS_APP = f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, select {{font-family: {FUENTE};}}
h1, h2, h3 {{color: {AZUL}; font-family: {FUENTE}; font-weight: 700;}}
h1 {{border-bottom: 4px solid {VERDE}; padding-bottom: .3rem;}}
[data-testid="stMetricValue"] {{font-size: 1.1rem; color: {AZUL};}}
.estado {{font-size: .85rem; padding: 2px 8px; border-radius: 10px; background: {VERDE_CLARO};}}
.celda {{font-size: .82rem; line-height: 1.3; background: {VERDE_CLARO}; border-left: 4px solid {VERDE};
         border-radius: 6px; padding: 6px 8px; min-height: 3.4rem; color: {AZUL};}}
.franja {{background: {AZUL}; color: #fff; border-bottom: 5px solid {VERDE}; border-radius: 8px;
          padding: 10px 16px; margin-bottom: 1rem; display: flex; align-items: center; gap: 14px;}}
.franja b {{font-size: 1.05rem;}} .franja span {{opacity: .85; font-size: .85rem;}}
[data-testid="stSidebar"] {{border-right: 4px solid {VERDE};}}
.stTabs [aria-selected="true"] {{color: {VERDE_OSCURO};}}
</style>"""
