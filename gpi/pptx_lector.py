"""Lectura de presentaciones .pptx sin dependencias externas (zip + XML).

Devuelve el texto de cada diapositiva (incluidas tablas como | col | col |), las notas
del orador y la lista de imágenes por diapositiva para poder transcribirlas con IA.
"""
import io
import posixpath
import re
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PN = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _xml(z, path):
    try:
        return ET.fromstring(z.read(path))
    except (KeyError, ET.ParseError):
        return None


def _rels(z, path):
    d = _xml(z, path)
    out = {}
    if d is not None:
        for r in d.iter(f"{REL}Relationship"):
            out[r.get("Id")] = {"t": r.get("Target", ""), "type": r.get("Type", ""), "mode": r.get("TargetMode")}
    return out


def _resolver(base_dir, target):
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, target))


def _texto(root):
    out = []

    def walk(el):
        for c in el:
            if c.tag == f"{A}tbl":
                for tr in c.iter(f"{A}tr"):
                    celdas = [" ".join(t.text or "" for t in tc.iter(f"{A}t")).strip() for tc in tr.iter(f"{A}tc")]
                    out.append("| " + " | ".join(celdas) + " |")
            elif c.tag == f"{A}p":
                t = "".join(t.text or "" for t in c.iter(f"{A}t")).strip()
                if t:
                    out.append(t)
            else:
                walk(c)

    walk(root)
    return "\n".join(out)


def leer_pptx(data: bytes) -> dict:
    z = zipfile.ZipFile(io.BytesIO(data))
    pres = _xml(z, "ppt/presentation.xml")
    prel = _rels(z, "ppt/_rels/presentation.xml.rels")
    orden = []
    if pres is not None:
        for s in pres.iter(f"{PN}sldId"):
            r = prel.get(s.get(f"{R}id"))
            if r:
                orden.append(_resolver("ppt", r["t"]))
    if not orden:
        orden = sorted(
            (n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
            key=lambda n: int(re.search(r"(\d+)", n.rsplit("/", 1)[1]).group(1)),
        )
    slides, media = [], []
    for i, path in enumerate(orden, start=1):
        d = _xml(z, path)
        if d is None:
            continue
        base = posixpath.dirname(path)
        rl = _rels(z, f"{base}/_rels/{posixpath.basename(path)}.rels")
        notas = ""
        for r in rl.values():
            if r["type"].endswith("/notesSlide"):
                nd = _xml(z, _resolver(base, r["t"]))
                if nd is not None:
                    notas = re.sub(r"^\d+$", "", _texto(nd), flags=re.M).strip()
        pics = 0
        recortes = {}  # rId de la imagen -> recorte (izq, arriba, der, abajo) en fracción, como se ve en la diapositiva
        for pic in d.iter(f"{PN}pic"):
            pics += 1
            blip = pic.find(f".//{A}blip")
            rid = blip.get(f"{R}embed") if blip is not None else None
            src = pic.find(f".//{A}srcRect")
            if rid and src is not None and rid not in recortes:
                try:
                    c = tuple(int(src.get(k) or 0) / 100000 for k in ("l", "t", "r", "b"))
                except ValueError:
                    c = (0, 0, 0, 0)
                if any(c):
                    recortes[rid] = c
        charts = sum(1 for r in rl.values() if r["type"].endswith("/chart"))
        for rid, r in rl.items():
            if r["type"].endswith("/image") and r["mode"] != "External":
                mp = _resolver(base, r["t"])
                if re.search(r"\.(png|jpe?g|gif|webp|bmp)$", mp, re.I):
                    media.append({"path": mp, "slide": i, "crop": recortes.get(rid)})
        slides.append({"n": i, "text": _texto(d), "notes": notas, "pics": pics, "charts": charts})
    return {"slides": slides, "media": media, "zip": z}


def imagenes_relevantes(px: dict) -> list:
    """Imágenes con contenido: descarta fondos/logos repetidos en 3+ diapositivas e íconos < 12 KB."""
    z = px["zip"]
    usos = {}
    for m in px["media"]:
        usos.setdefault(m["path"], set()).add(m["slide"])
    vistos, items = set(), []
    for m in px["media"]:
        k = (m["slide"], m["path"])
        if k in vistos:
            continue
        vistos.add(k)
        if len(usos[m["path"]]) >= 3:
            continue
        try:
            size = z.getinfo(m["path"]).file_size
        except KeyError:
            continue
        if size < 12000:
            continue
        items.append(m)
    return items


def a_jpeg(data: bytes, lado_max: int = 1600, calidad: int = 85, crop=None) -> bytes:
    """Reduce una imagen y la convierte a JPEG (fondo blanco para transparencias).
    crop = (izq, arriba, der, abajo) en fracción: se recorta igual que en la diapositiva,
    para que la IA no lea partes que el grupo ocultó."""
    im = Image.open(io.BytesIO(data))
    im.load()
    if crop and any(crop):
        w, h = im.size
        l, t, r, b = (max(0.0, min(0.95, float(x or 0))) for x in crop)
        caja = (int(l * w), int(t * h), int(w - r * w), int(h - b * h))
        if caja[2] - caja[0] > 10 and caja[3] - caja[1] > 10:
            im = im.crop(caja)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fondo = Image.new("RGB", im.size, (255, 255, 255))
        fondo.paste(im, mask=im.split()[-1])
        im = fondo
    elif im.mode != "RGB":
        im = im.convert("RGB")
    im.thumbnail((lado_max, lado_max))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=calidad, optimize=True)
    return out.getvalue()


def palabras(s: str) -> int:
    return len((s or "").split())


def estadisticas(px: dict, transcripciones: dict, minutos: int) -> dict:
    por = [(s["n"], palabras(s["text"]) + palabras(transcripciones.get(s["n"], ""))) for s in px["slides"]]
    return {
        "diapositivas": len(px["slides"]),
        "minutos": minutos,
        "densas": [n for n, w in por if w > 120],
        "palabras": sum(w for _, w in por),
    }


def texto_diapositivas(px: dict, transcripciones: dict, limite: int) -> str:
    partes = []
    for s in px["slides"]:
        cab = f"--- Diapositiva {s['n']}"
        if s["pics"]:
            cab += f" [{s['pics']} imagen(es)]"
        if s["charts"]:
            cab += f" [{s['charts']} gráfico(s)]"
        cuerpo = s["text"] or "(sin texto)"
        if transcripciones.get(s["n"]):
            cuerpo += f"\n[Contenido leído de las imágenes de esta diapositiva]\n{transcripciones[s['n']]}"
        if s["notes"]:
            cuerpo += f"\nNotas: {s['notes']}"
        partes.append(cab + "\n" + cuerpo)
    return "\n".join(partes)[:limite]
