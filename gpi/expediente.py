"""Expediente descargable del grupo (HTML imprimible a PDF desde el navegador)."""
import base64
import html
from datetime import datetime

from .catalogo import OBJ, OBJ8, RUBRICA, etiqueta, nota

e = lambda s: html.escape(str(s or ""))


def fecha(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return str(s or "")[:10]


def lista(items):
    items = [x for x in (items or []) if x]
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>" if items else ""


def construir(grupo, integrantes, nombres, asign, evid, anal, vistos, revs, fotos=None):
    """fotos: {ruta: bytes JPEG pequeños} para incrustar miniaturas (opcional)."""
    fotos = fotos or {}
    asig = {a["obj"]: a["instructor_id"] for a in asign}
    an = {a["obj"]: a for a in anal}
    partes = [f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Expediente {e(grupo['nombre'])}</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1d2a1d;line-height:1.45}}
h1{{color:#2d7d00;margin-bottom:0}} h2{{border-bottom:3px solid #39a900;padding-bottom:4px;margin-top:32px}}
h3{{margin-bottom:4px}} .muted{{color:#5c6b5c}} table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border:1px solid #cdd8cd;padding:4px 6px;text-align:left;vertical-align:top}} th{{background:#eef6e8}}
.ok{{color:#1f7a00;font-weight:600}} .warn{{color:#a35b00;font-weight:600}}
.thumbs img{{height:110px;margin:2px;border:1px solid #ccc}} .box{{background:#f6faf3;border-left:4px solid #39a900;padding:8px 12px;margin:8px 0}}
@media print{{h2{{break-before:auto}} .obj{{break-inside:avoid-page}}}}
</style></head><body>
<h1>Expediente del proyecto productivo</h1>
<p class="muted">Tecnología en Gestión de la Producción Industrial · Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
<table><tr><th>Grupo</th><td>{e(grupo['nombre'])}</td><th>Ficha</th><td>{e(grupo.get('ficha'))}</td></tr>
<tr><th>Empresa proyecto</th><td>{e(grupo['empresa'])}</td><th>Sector</th><td>{e(grupo.get('sector'))}</td></tr>
<tr><th>Integrantes</th><td colspan="3">{e(', '.join(m['nombre'] or m['correo'] for m in integrantes))}</td></tr></table>
<h2>Resumen por competencia</h2><table><tr><th>Objetivo / competencia</th><th>Instructor técnico</th><th>Evidencias</th><th>Estado</th></tr>"""]
    for o in OBJ8:
        vb = next((v for v in vistos if v["obj"] == o["n"]), None)
        est = ("<span class='ok'>Visto bueno</span>" if vb and vb["estado"] == "aprobado"
               else "<span class='warn'>Ajustes solicitados</span>" if vb else "Sin visto bueno")
        n_ev = sum(1 for x in evid if x["obj"] == o["n"])
        partes.append(f"<tr><td>{e(etiqueta(o['n']))}</td><td>{e(nombres.get(asig.get(o['n']), '—'))}</td><td>{n_ev}</td><td>{est}{' · ' + fecha(vb['creado_en']) if vb else ''}</td></tr>")
    partes.append("</table>")

    for n in range(0, 9):
        o = OBJ[n]
        evs = [x for x in evid if x["obj"] == n]
        a = an.get(n)
        vbs = [v for v in vistos if v["obj"] == n]
        if not (evs or a or vbs):
            continue
        partes.append(f"<div class='obj'><h2>{e(etiqueta(n))}</h2>")
        if n:
            partes.append(f"<p class='muted'>{e(o['objetivo'])}</p>")
        if evs:
            partes.append("<h3>Evidencias</h3>")
            for x in sorted(evs, key=lambda z: z["creado_en"]):
                partes.append(f"<p><b>{e(x['titulo'])}</b> <span class='muted'>({e(x['tipo'])}, {fecha(x['creado_en'])}, {e(nombres.get(x.get('autor'), ''))})</span>"
                              + (f"<br><span class='muted'>Fuente: {e(x['fuente'])}</span>" if x.get("fuente") else "") + "</p>")
                imgs = [f"<img alt='' src='data:image/jpeg;base64,{base64.b64encode(fotos[r]).decode()}'>" for r in (x.get("archivos") or []) if r in fotos]
                if imgs:
                    partes.append("<div class='thumbs'>" + "".join(imgs) + "</div>")
                otros = [r.split("/")[-1].split("-", 2)[-1] for r in (x.get("archivos") or []) if r not in fotos]
                if otros:
                    partes.append(f"<p class='muted'>Archivos: {e(', '.join(otros))}</p>")
                if x.get("descripcion"):
                    partes.append(f"<div class='box'>{e(x['descripcion']).replace(chr(10), '<br>')}</div>")
        if a and a.get("elegida") is not None and a.get("alternativas"):
            alts = a["alternativas"].get("alternativas") or []
            alt = alts[a["elegida"]] if 0 <= a["elegida"] < len(alts) else {}
            partes.append(f"<h3>Situación problémica trabajada ({'enviada' if a['estado'] == 'enviado' else 'borrador'})</h3>"
                          f"<p><b>{e(alt.get('titulo'))}</b></p>")
            for etq, k in (("Planteamiento", "planteamiento"), ("Causas a verificar", "causas"), ("Indicador y medición", "indicador"), ("Datos a recolectar", "datos")):
                if a.get(k):
                    partes.append(f"<p><b>{etq}:</b> {e(a[k])}</p>")
        if vbs:
            partes.append("<h3>Vistos buenos y observaciones del instructor técnico</h3><table><tr><th>Fecha</th><th>Instructor</th><th>Estado</th><th>Observaciones</th><th>Nota</th></tr>")
            for v in vbs:
                partes.append(f"<tr><td>{fecha(v['creado_en'])}</td><td>{e(nombres.get(v['instructor_id'], ''))}</td><td>{'Visto bueno' if v['estado'] == 'aprobado' else 'Ajustes'}</td><td>{e(v['observaciones'])}</td><td>{e(v.get('nota') or '')}</td></tr>")
            partes.append("</table>")
        partes.append("</div>")

    finales = [r for r in revs if r["tipo"] == "final" and r["estado"] == "validada"]
    if finales:
        r = finales[0]
        res = r.get("resultado") or {}
        partes.append(f"<h2>Presentación final</h2><p>Archivo: {e(r['archivo_nombre'])} · {r.get('diapositivas') or ''} diapositivas · validada el {fecha(r.get('validado_en'))} por {e(nombres.get(r.get('validado_por'), ''))}</p>"
                      f"<p style='font-size:1.3rem'><b>Nota: {e(r['nota'])}</b> · {'<span class=ok>Aprueba</span>' if r['aprueba'] else '<span class=warn>No aprueba</span>'}</p>")
        objs = res.get("objetivos") or []
        if objs:
            partes.append("<table><tr><th>Objetivo</th>" + "".join(f"<th>{e(c['nombre'])}</th>" for c in RUBRICA) + "<th>Nota</th></tr>")
            for x in objs:
                partes.append(f"<tr><td>{e(etiqueta(x['obj']))}</td>" + "".join(f"<td>{v}</td>" for v in x["niveles"]) + f"<td>{nota(x['niveles'])}</td></tr>")
            partes.append("</table>")
        for etq, k in (("Recomendaciones", "recomendaciones"), ("Oportunidades de mejora", "oportunidades"), ("Observaciones del instructor", "observaciones")):
            if r.get(k):
                partes.append(f"<h3>{etq}</h3>" + lista(r[k].split("\n")))
    partes.append("</body></html>")
    return "".join(partes)
