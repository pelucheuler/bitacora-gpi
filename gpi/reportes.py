"""Tablas para el tablero y para descargar a Excel / Power BI."""
import io

import pandas as pd

from .catalogo import OBJ, RUBRICA, nota

CRIT = [c["nombre"] for c in RUBRICA]


def _niveles_final(r):
    """[(obj, niveles)] de una revisión final: los validados si existen, si no los propuestos."""
    if r["estado"] == "validada" and (r.get("resultado") or {}).get("objetivos"):
        return [(x["obj"], x["niveles"]) for x in r["resultado"]["objetivos"]]
    return [(x["obj"], x.get("niveles")) for x in (r.get("prop_objetivos") or []) if isinstance(x.get("niveles"), list)]


def _niveles_avance(r):
    if r["estado"] == "validada" and (r.get("resultado") or {}).get("niveles"):
        return r["resultado"]["niveles"]
    return r.get("prop_niveles") if isinstance(r.get("prop_niveles"), list) else None


def ultima_final(revs, gid):
    """Última PPT final del grupo: la validada más reciente; si no hay, la propuesta más reciente."""
    fin = [r for r in revs if r["grupo_id"] == gid and r["tipo"] == "final"]
    val = [r for r in fin if r["estado"] == "validada"]
    return (val or fin or [None])[0]


def notas_largo(grupos, revs):
    """Una fila por grupo × revisión × objetivo, con los 5 criterios (formato largo para Power BI)."""
    g_by = {g["id"]: g for g in grupos}
    filas = []
    for r in revs:
        g = g_by.get(r["grupo_id"])
        if not g:
            continue
        pares = _niveles_final(r) if r["tipo"] == "final" else ([(r["obj"], _niveles_avance(r))] if _niveles_avance(r) else [])
        for obj, nv in pares:
            if not nv or not obj:
                continue
            filas.append({
                "ficha": g.get("ficha") or "", "grupo": g["nombre"], "empresa": g["empresa"],
                "revision_id": r["id"], "tipo_revision": r["tipo"], "fecha_revision": str(r["creado_en"])[:10],
                "estado": "Validada" if r["estado"] == "validada" else "Propuesta IA",
                "objetivo_n": int(obj), "objetivo": OBJ[int(obj)]["corto"], "competencia": OBJ[int(obj)]["competencia"],
                **{CRIT[i]: nv[i] for i in range(len(CRIT))},
                "nota_objetivo": nota(nv),
            })
    return pd.DataFrame(filas)


def revisiones_tabla(grupos, revs):
    g_by = {g["id"]: g for g in grupos}
    filas = []
    for r in revs:
        g = g_by.get(r["grupo_id"])
        if not g:
            continue
        filas.append({
            "ficha": g.get("ficha") or "", "grupo": g["nombre"], "empresa": g["empresa"], "revision_id": r["id"],
            "tipo_revision": r["tipo"], "objetivo_n": r.get("obj"), "archivo": r.get("archivo_nombre") or "",
            "diapositivas": r.get("diapositivas"), "fecha_revision": str(r["creado_en"])[:10],
            "estado": "Validada" if r["estado"] == "validada" else "Propuesta IA",
            "nota_propuesta_ia": r.get("prop_nota"), "nota_validada": r.get("nota") if r["estado"] == "validada" else None,
            "aprueba": r.get("aprueba") if r["estado"] == "validada" else None,
            "fecha_validacion": str(r.get("validado_en") or "")[:10],
        })
    return pd.DataFrame(filas)


def excel(hojas: dict) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        for nombre, df in hojas.items():
            (df if len(df.columns) else pd.DataFrame({"sin datos": []})).to_excel(w, sheet_name=nombre[:31], index=False)
            ws = w.sheets[nombre[:31]]
            for col in ws.columns:
                ancho = max(len(str(c.value or "")) for c in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(45, max(10, ancho + 2))
    return out.getvalue()
