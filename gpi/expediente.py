"""Expediente descargable del grupo (HTML imprimible a PDF desde el navegador)."""
import base64
import html
from datetime import datetime

from . import marca
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
body{{font-family:Work Sans,Segoe UI,Calibri,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1d2a1d;line-height:1.45}}
h1{{color:#00304D;margin-bottom:0}} h2{{color:#00304D;border-bottom:3px solid #39a900;padding-bottom:4px;margin-top:32px}}
h3{{margin-bottom:4px}} .muted{{color:#5c6b5c}} table{{border-collapse:collapse;width:100%;font-size:.9rem}}
td,th{{border:1px solid #cdd8cd;padding:4px 6px;text-align:left;vertical-align:top}} th{{background:#eef7e6;color:#00304D}}
.ok{{color:#1f7a00;font-weight:600}} .warn{{color:#a35b00;font-weight:600}}
.thumbs img{{height:110px;margin:2px;border:1px solid #ccc}} .box{{background:#f6faf3;border-left:4px solid #39a900;padding:8px 12px;margin:8px 0}}
@media print{{h2{{break-before:auto}} .obj{{break-inside:avoid-page}}}}
{marca.css_informe()}</style></head><body>
{marca.encabezado_informe()}
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


def informe_revision(grupo, integrantes, r, nombres, mostrar_nota=True):
    """Informe de una revisión de presentación (HTML; se abre en Word o se imprime a PDF)."""
    p = r.get("propuesta") or {}
    final = r["tipo"] == "final"
    validada = r["estado"] == "validada"
    res = r.get("resultado") or {}
    titulo = "Presentación final" if final else f"Avance · {etiqueta(r['obj'])}"
    h = [f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Informe de revisión {e(grupo['nombre'])}</title>
<style>
body{{font-family:Work Sans,Calibri,Segoe UI,Arial,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#1d2a1d;line-height:1.4}}
h1{{color:#00304D;margin-bottom:0}} h2{{color:#00304D;border-bottom:2px solid #39a900;padding-bottom:3px;margin-top:24px}}
table{{border-collapse:collapse;width:100%;font-size:10pt}} td,th{{border:1px solid #9fb59f;padding:4px 6px;text-align:left;vertical-align:top}}
th{{background:#eef7e6;color:#00304D}} .muted{{color:#5c6b5c}} .nota{{font-size:16pt;font-weight:bold}}
{marca.css_informe()}</style></head><body>
{marca.encabezado_informe()}
<h1>Informe de revisión del proyecto productivo</h1>
<p class="muted">Tecnología en Gestión de la Producción Industrial · {e(titulo)}</p>
<table><tr><th>Grupo</th><td>{e(grupo['nombre'])}</td><th>Ficha</th><td>{e(grupo.get('ficha'))}</td></tr>
<tr><th>Empresa proyecto</th><td>{e(grupo['empresa'])}</td><th>Fecha de revisión</th><td>{fecha(r['creado_en'])}</td></tr>
<tr><th>Integrantes</th><td colspan="3">{e(', '.join(m['nombre'] or m['correo'] for m in integrantes))}</td></tr>
<tr><th>Archivo</th><td>{e(r.get('archivo_nombre'))} ({r.get('diapositivas') or '?'} diapositivas)</td><th>Estado</th>
<td>{'Validada por ' + e(nombres.get(r.get('validado_por'), 'el instructor')) + ' el ' + fecha(r.get('validado_en')) if validada else 'Pendiente de validación por el instructor'}</td></tr></table>"""]
    if validada:
        h.append(f"<p class='nota'>Nota: {e(r['nota'])} · {'Aprueba' if r['aprueba'] else 'No aprueba'}</p>")
    elif mostrar_nota:
        h.append(f"<p class='nota'>Nota propuesta por la IA: {e(p.get('nota_propuesta'))} (sin validar)</p>")
    if mostrar_nota or validada:
        h.append("<h2>Rúbrica</h2><table><tr><th>Objetivo</th>" + "".join(f"<th>{e(c['nombre'])} ({round(c['peso'] * 100)}%)</th>" for c in RUBRICA)
                 + "<th>Nota</th>" + ("<th>Justificación</th>" if final else "") + "</tr>")
        if final:
            prop = {x["obj"]: x for x in p.get("objetivos") or []}
            filas = res.get("objetivos") if validada and res.get("objetivos") else p.get("objetivos") or []
            for x in filas:
                pr = prop.get(x["obj"], {})
                h.append(f"<tr><td>{e(etiqueta(x['obj']))}<br><span class='muted'>diap. {e(pr.get('diapositivas'))}</span></td>"
                         + "".join(f"<td>{v}</td>" for v in x["niveles"]) + f"<td><b>{nota(x['niveles'])}</b></td><td>{e(pr.get('justificacion'))}</td></tr>")
        else:
            nv = res.get("niveles") if validada and res.get("niveles") else p.get("niveles") or []
            h.append(f"<tr><td>{e(etiqueta(r['obj']))}</td>" + "".join(f"<td>{v}</td>" for v in nv) + f"<td><b>{nota(nv) if nv else ''}</b></td></tr>")
        h.append("</table><p class='muted'>Niveles de 1 a 4. Nota = 1 + 4/3 × (Σ peso × nivel − 1).</p>")
    recs = r.get("recomendaciones") if validada else "\n".join((p.get("recomendaciones_generales") if final else p.get("recomendaciones")) or [])
    opo = r.get("oportunidades") if validada else "\n".join(p.get("oportunidades_mejora") or [])
    for etq, txt in (("Recomendaciones", recs), ("Oportunidades de mejora", opo), ("Observaciones del instructor", r.get("observaciones") if validada else "")):
        if txt:
            h.append(f"<h2>{etq}</h2>" + lista(txt.split("\n")))
    if final:
        det = [x for x in p.get("objetivos") or [] if x.get("faltantes") or x.get("recomendaciones")]
        if det:
            h.append("<h2>Detalle por objetivo</h2>")
            for x in det:
                h.append(f"<p><b>{e(etiqueta(x['obj']))}</b></p>" + (f"<p>Falta: {e('; '.join(x['faltantes']))}</p>" if x.get("faltantes") else "") + lista(x.get("recomendaciones")))
    ext = p.get("extension")
    if ext:
        s = p.get("stats") or {}
        h.append(f"<h2>Extensión para la exposición ({s.get('minutos', 15)} min)</h2><p>{s.get('diapositivas', '?')} diapositivas. "
                 + ("Adecuada." if ext.get("adecuada") else f"Conviene condensar a unas {e(ext.get('diapositivas_recomendadas'))}.") + f" {e(ext.get('comentario'))}</p>"
                 + lista([f"Diap. {c.get('diapositivas', '')}: {c.get('sugerencia', '')}" for c in ext.get("condensar") or []])
                 + (f"<p>Mover a anexos: {e('; '.join(ext['anexos']))}</p>" if ext.get("anexos") else ""))
    sug = p.get("problematicas_sugeridas") or []
    if sug:
        h.append("<h2>Problemáticas sugeridas para objetivos sin cubrir</h2>" + lista(
            [f"Objetivo {x.get('obj')}: {x.get('situacion', '')}" + (f" Integrar en: {x['encaje']}." if x.get("encaje") else "")
             + (f" Indicador: {x['indicador']}." if x.get("indicador") else "") for x in sug]))
    if p.get("alertas"):
        h.append("<h2>Alertas</h2>" + lista(p["alertas"]))
    h.append("<p class='muted'>Informe generado por la Bitácora del Proyecto Productivo GPI. La nota la valida el instructor.</p></body></html>")
    return "".join(h)
