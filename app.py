"""Bitácora del Proyecto Productivo GPI · Streamlit + Supabase + Claude."""
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from gpi import datos as db
from gpi import ia
from gpi import marca
from gpi.catalogo import OBJ, OBJ8, RUBRICA, aprueba, aprueba_final, etiqueta, nota, nota_final
from gpi.pptx_lector import a_jpeg, estadisticas, imagenes_relevantes, leer_pptx

st.set_page_config(page_title="Bitácora Proyecto Productivo GPI", page_icon=str(marca.logo_ruta()) if marca.logo_ruta() else "📒", layout="wide")
st.markdown(marca.CSS_APP, unsafe_allow_html=True)
if marca.logo_ruta():
    st.logo(str(marca.logo_ruta()), size="large")

IMG_TIPOS = ["jpg", "jpeg", "png", "webp"]
DOC_TIPOS = ["xlsx", "xls", "csv", "pdf", "docx", "doc", "pptx", "txt"]
MAX_PPT_GUARDAR = 45 * 1024 * 1024   # Supabase gratis: 50 MB por archivo
ICONO = {"aprobado": "✅", "ajustes": "🔁", "enviado": "📨", "proceso": "✏️", "vacio": "—"}
TEXTO_ESTADO = {"aprobado": "Visto bueno", "ajustes": "Ajustes solicitados", "enviado": "Enviado al instructor",
                "proceso": "En proceso", "vacio": "Sin iniciar"}


def fecha(s, hora=False):
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone()
        return d.strftime("%d/%m/%Y %H:%M" if hora else "%d/%m/%Y")
    except ValueError:
        return str(s or "")[:10]


def falla(e):
    msg = getattr(e, "message", None) or str(e)
    if "row-level security" in msg or "permission denied" in msg:
        msg = "No tiene permiso para esta acción."
    st.error(msg)


# ======================================================================= acceso
def configurada():
    falt = [k for k in ("SUPABASE_URL", "SUPABASE_ANON_KEY") if not st.secrets.get(k)]
    if falt:
        st.title("Bitácora del Proyecto Productivo GPI")
        st.error("Falta configurar la app: agregue " + ", ".join(falt) + " en los secretos (ver la guía de instalación).")
        return False
    return True


def pantalla_acceso():
    if marca.logo_ruta():
        st.image(str(marca.logo_ruta()), width=110)
    st.title("Bitácora del Proyecto Productivo")
    st.caption("SENA · Tecnología en Gestión de la Producción Industrial")
    t1, t2, t3, t4 = st.tabs(["Ingresar", "Crear cuenta", "Olvidé mi contraseña", "❓ ¿Cómo funciona?"])
    with t4:
        st.write("Descargue el instructivo según su rol. Dentro de la app también está en el menú «Ayuda».")
        botones_instructivo(["aprendices", "instructores"], "acc")
    with t1, st.form("login"):
        correo = st.text_input("Correo")
        clave = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar", type="primary"):
            try:
                db.iniciar_sesion(correo, clave)
                st.rerun()
            except Exception as e:
                st.error("No se pudo ingresar. Revise el correo y la contraseña" +
                         (" o confirme su correo con el enlace que le llegó." if "confirm" in str(e).lower() else "."))
    with t2, st.form("registro"):
        st.write("Los aprendices crean su cuenta y luego se unen a su grupo con el código que les da el instructor.")
        nombre = st.text_input("Nombre completo")
        correo = st.text_input("Correo ", key="reg_correo")
        clave = st.text_input("Contraseña (mínimo 6 caracteres)", type="password", key="reg_clave")
        if st.form_submit_button("Crear cuenta", type="primary"):
            if not nombre.strip() or len(clave) < 6:
                st.error("Escriba su nombre y una contraseña de al menos 6 caracteres.")
            else:
                try:
                    r = db.registrarse(nombre, correo, clave)
                    if r.session:
                        st.rerun()
                    st.success("Cuenta creada. Revise su correo para confirmarla y luego ingrese.")
                except Exception as e:
                    st.error(f"No se pudo crear la cuenta: {e}")
    with t3:
        st.info("Pida al instructor líder una **contraseña temporal** (él la asigna desde Administración → Usuarios y roles). "
                "Ingrese con ella y cámbiela en «Mi cuenta».")


# ======================================================================= estados
def estado_objetivo(obj, evid, anal, vistos):
    vb = next((v for v in vistos if v["obj"] == obj), None)
    an = next((a for a in anal if a["obj"] == obj), None)
    if vb and vb["estado"] == "aprobado":
        return "aprobado"
    if an and an["estado"] == "enviado" and (not vb or str(an.get("actualizado_en", "")) > str(vb["creado_en"])):
        return "enviado"
    if vb:
        return "ajustes"
    if an or any(e["obj"] == obj for e in evid):
        return "proceso"
    return "vacio"


def corto(n):
    return f"{n}. {OBJ[n]['corto']}"


def nombres_de(perfiles):
    return {p["id"]: (p.get("nombre") or p.get("correo") or "—") for p in perfiles}


# ======================================================================= bitácora
def pagina_bitacora(grupo, perfil):
    gid = grupo["id"]
    staff = perfil["rol"] in ("instructor", "lider")
    try:
        evid = db.evidencias(gid)
        anal = db.analisis(gid)
        vistos = db.vistos_buenos(gid)
        asign = db.asignaciones(gid)
        integrantes = db.miembros(gid)
        nombres = nombres_de(db.perfiles() if staff else integrantes + db.perfiles(["instructor", "lider"]))
    except Exception as e:
        falla(e)
        return
    st.title(f"📒 {grupo['nombre']}")
    st.caption(f"Empresa proyecto: **{grupo['empresa']}**" + (f" · {grupo['sector']}" if grupo.get("sector") else "")
               + (f" · Ficha {grupo['ficha']}" if grupo.get("ficha") else "")
               + f" · Código para unirse: `{grupo['codigo']}`")
    if integrantes:
        st.caption("Integrantes: " + ", ".join(m["nombre"] or m["correo"] for m in integrantes))

    cols = st.columns(8)
    for c, o in zip(cols, OBJ8):
        est = estado_objetivo(o["n"], evid, anal, vistos)
        c.markdown(f"<div class='celda'><b>{o['n']}. {o['corto']}</b><br>{ICONO[est]} {TEXTO_ESTADO[est]}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    obj = c1.selectbox("Competencia / objetivo", list(range(0, 9)), format_func=etiqueta, key=f"obj_{gid}")
    with c2:
        st.write("")
        boton_expediente(grupo, integrantes, nombres, asign, evid, anal, vistos)
    o = OBJ[obj]
    asig = next((a for a in asign if a["obj"] == obj), None)
    with st.expander("¿Qué se espera en esta competencia?"):
        if obj:
            st.markdown(f"**Objetivo:** {o['objetivo']}  \n**Competencia:** {o['competencia']} ({o['codigo']}, {o['horas']} h)  \n"
                        f"**Instructor técnico:** {nombres.get(asig['instructor_id'], '—') if asig else 'sin asignar'}")
            if o["raps"]:
                st.markdown("**Resultados de aprendizaje:**\n" + "\n".join(f"- {r}" for r in o["raps"]))
        st.markdown("**Evidencias esperadas:**\n" + "\n".join(f"- {r}" for r in o["evid"]))

    if obj == 0:
        seccion_evidencias(grupo, 0, evid, perfil, nombres)
        return
    t1, t2, t3 = st.tabs(["📎 Evidencias", "🔎 Situación problémica", "✅ Visto bueno del instructor"])
    with t1:
        seccion_evidencias(grupo, obj, evid, perfil, nombres)
    with t2:
        seccion_analisis(grupo, obj, evid, next((a for a in anal if a["obj"] == obj), None), perfil)
    with t3:
        seccion_visto_bueno(grupo, obj, vistos, asig, perfil, nombres, next((a for a in anal if a["obj"] == obj), None))


def seccion_evidencias(grupo, obj, evid, perfil, nombres):
    gid = grupo["id"]
    lst = [e for e in evid if e["obj"] == obj]
    n = st.session_state.setdefault("ev_reset", 0)
    k = f"{gid}_{obj}_{n}"
    with st.expander("➕ Agregar evidencia", expanded=not lst):
        tipo = st.radio("Tipo", ["foto", "datos", "nota", "documento"], horizontal=True, key=f"evtipo_{k}",
                        format_func={"foto": "Fotos de la visita", "datos": "Datos de la empresa", "nota": "Nota de visita", "documento": "Documento / Excel"}.get)
        titulo = st.text_input("Título", key=f"evtit_{k}", placeholder="Ej.: Visita a la línea de ensamble, 12 de marzo")
        fuente = st.text_input("Fuente (quién entregó el dato, área, fecha)", key=f"evfue_{k}")
        archivos = st.file_uploader("Archivos", accept_multiple_files=True, key=f"evarch_{k}",
                                    type=IMG_TIPOS if tipo == "foto" else IMG_TIPOS + DOC_TIPOS)
        fotos = [a for a in (archivos or []) if a.name.lower().rsplit(".", 1)[-1] in IMG_TIPOS]
        if tipo == "foto" and fotos:
            st.image([a for a in fotos[:8]], width=140)
            ctx = st.text_input("Contexto para la IA (qué área es, qué estaban haciendo)", key=f"evctx_{k}")
            if ia.disponible():
                if st.button("🤖 Describir fotos con IA", key=f"evdesc_{k}"):
                    with st.spinner("Describiendo las fotos…"):
                        try:
                            st.session_state[f"evtxt_{k}"] = ia.describir_fotos([a_jpeg(a.getvalue()) for a in fotos[:10]], grupo, obj, ctx)
                        except ia.IAError as e:
                            st.error(str(e))
            else:
                with st.expander("🤖 Describir las fotos con Claude (opcional)"):
                    bloque_claude(f"evcl_{k}", ia.prompt_fotos(len(fotos), grupo, obj, ctx), json_resp=False,
                                  adjuntar=f"las mismas {len(fotos)} fotos", destino="en el campo «Descripción» de abajo y corríjanla")
        st.text_area("Descripción, datos o notas (revisen y corrijan lo que escriba la IA)", key=f"evtxt_{k}", height=180)
        if st.button("Guardar evidencia", type="primary", key=f"evsave_{k}"):
            texto = st.session_state.get(f"evtxt_{k}", "").strip()
            if not titulo.strip():
                st.error("Escriba un título.")
            elif not texto and not archivos:
                st.error("Agregue una descripción o archivos.")
            else:
                try:
                    with st.spinner("Guardando…"):
                        rutas = []
                        for a in archivos or []:
                            ext = a.name.lower().rsplit(".", 1)[-1]
                            if ext in IMG_TIPOS:
                                rutas.append(db.subir_archivo(gid, a.name.rsplit(".", 1)[0] + ".jpg", a_jpeg(a.getvalue()), "image/jpeg"))
                            else:
                                if a.size > MAX_PPT_GUARDAR:
                                    st.warning(f"{a.name} pesa más de 45 MB y no se guardó.")
                                    continue
                                rutas.append(db.subir_archivo(gid, a.name, a.getvalue(), a.type))
                        db.crear_evidencia({"grupo_id": gid, "obj": obj, "tipo": tipo, "titulo": titulo.strip(),
                                            "descripcion": texto, "fuente": fuente.strip(), "archivos": rutas, "autor": perfil["id"]})
                    st.session_state.ev_reset = n + 1
                    st.toast("Evidencia guardada")
                    st.rerun()
                except Exception as e:
                    falla(e)

    st.subheader(f"Evidencias ({len(lst)})")
    if not lst:
        st.info("Aún no hay evidencias para esta competencia." + ("" if obj == 0 else " Las de «General» también se usan al analizar."))
        return
    urls = db.urls_firmadas({r for e in lst for r in (e.get("archivos") or [])})
    for e in lst:
        with st.container(border=True):
            a, b = st.columns([5, 1])
            a.markdown(f"**{e['titulo']}**  \n<span class='estado'>{e['tipo']}</span> · {fecha(e['creado_en'], True)} · {nombres.get(e.get('autor'), '')}"
                       + (f"  \nFuente: {e['fuente']}" if e.get("fuente") else ""), unsafe_allow_html=True)
            if e.get("autor") == perfil["id"] or perfil["rol"] != "aprendiz":
                with b.popover("Eliminar"):
                    st.write("¿Eliminar esta evidencia y sus archivos?")
                    if st.button("Sí, eliminar", key=f"del_{e['id']}"):
                        try:
                            db.borrar_evidencia(e)
                            st.rerun()
                        except Exception as ex:
                            falla(ex)
            imgs = [urls[r] for r in (e.get("archivos") or []) if r.endswith(".jpg") and urls.get(r)]
            if imgs:
                st.image(imgs, width=180)
            docs = [r for r in (e.get("archivos") or []) if not r.endswith(".jpg")]
            for r in docs:
                if urls.get(r):
                    st.link_button("⬇ " + r.split("/")[-1].split("-", 2)[-1], urls[r])
            if e.get("descripcion"):
                with st.expander("Ver descripción"):
                    st.write(e["descripcion"])


def _init(key, valor):
    if key not in st.session_state:
        st.session_state[key] = valor


def bloque_claude(clave, prompt, adjuntar=None, json_resp=True, destino=None):
    """Modo sin clave de API: instrucciones para pegar en claude.ai con la cuenta de cada quien.

    Devuelve la respuesta pegada cuando se pulsa «Procesar respuesta» (o None)."""
    texto = ia.para_claude_ai(prompt) if json_resp else prompt
    pasos = ["Abra [claude.ai](https://claude.ai/new) con su cuenta e inicie una **conversación nueva**."]
    if adjuntar:
        pasos.append(f"Adjunte {adjuntar}.")
    pasos.append("Copie las instrucciones (botón 📋 en la esquina del recuadro) y péguelas en el mensaje, "
                 "o descargue el archivo .txt y adjúntelo. Envíe.")
    pasos.append(f"Cuando Claude termine, copie **toda** su respuesta y péguela {destino or 'abajo'}.")
    st.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(pasos, start=1)))
    with st.expander("📋 Instrucciones para Claude", expanded=len(texto) < 5000):
        st.code(texto, language=None, wrap_lines=True)
    st.download_button("⬇ Descargar instrucciones (.txt)", texto.encode("utf-8"), file_name="instrucciones-claude.txt",
                       mime="text/plain", key=clave + "_dl")
    if not json_resp:
        return None
    pegado = st.text_area("Respuesta de Claude (pegue aquí)", key=clave + "_resp", height=160)
    if st.button("✔ Procesar respuesta", type="primary", key=clave + "_ok"):
        if not pegado.strip():
            st.error("Pegue primero la respuesta de Claude.")
            return None
        return pegado
    return None


def seccion_analisis(grupo, obj, evid, an, perfil):
    gid = grupo["id"]
    puede = perfil["rol"] == "aprendiz" or perfil["rol"] == "lider"
    an = an or {}
    alts = (an.get("alternativas") or {})
    ev_obj = [e for e in evid if e["obj"] in (obj, 0)]
    st.write("La IA propone **posibles** situaciones problémicas a partir de sus evidencias. Ustedes eligen una, responden las preguntas guía y hacen su propio análisis.")
    if puede:
        def guardar_alts(r):
            if not isinstance(r.get("alternativas"), list) or not r["alternativas"]:
                raise ia.IAError("La respuesta no trae alternativas. Copie de nuevo la respuesta completa de Claude.")
            db.guardar_analisis(gid, obj, {"alternativas": r, "elegida": None, "respuestas": [], "estado": "borrador"}, perfil["id"])
            for kk in [x for x in st.session_state if str(x).startswith(f"an_{gid}_{obj}_") or str(x).startswith(f"alcl_{gid}_{obj}")]:
                del st.session_state[kk]
            st.rerun()

        etq = "🤖 Proponer alternativas con IA" if not alts else "🔄 Proponer otras alternativas (reemplaza las actuales)"
        if ia.disponible():
            if st.button(etq, disabled=not ev_obj, key=f"alt_{gid}_{obj}"):
                with st.spinner("Analizando las evidencias… (puede tardar un minuto)"):
                    try:
                        guardar_alts(ia.proponer_alternativas(grupo, obj, evid))
                    except (ia.IAError, Exception) as e:
                        falla(e)
        elif ev_obj:
            with st.expander(etq.replace("con IA", "con Claude"), expanded=not alts):
                pegado = bloque_claude(f"alcl_{gid}_{obj}", ia.prompt_alternativas(grupo, obj, evid))
                if pegado:
                    try:
                        guardar_alts(ia.extraer_json(pegado))
                    except (ia.IAError, Exception) as e:
                        falla(e)
        if not ev_obj:
            st.caption("Primero carguen evidencias de esta competencia o generales.")
    if not alts:
        return
    if alts.get("lectura_general"):
        st.info(alts["lectura_general"])
    for w in alts.get("advertencias") or []:
        st.warning(w)
    lista = alts.get("alternativas") or []
    for i, x in enumerate(lista):
        with st.expander(f"Alternativa {i + 1}: {x.get('titulo', '')}"):
            st.markdown("**Evidencias:** " + "; ".join(x.get("evidencias") or []))
            st.markdown(f"**Por qué podría ser un problema:** {x.get('por_que_podria_ser_problema', '')}")
            ind = x.get("indicador") or {}
            if ind.get("nombre"):
                st.markdown(f"**Indicador:** {ind.get('nombre')} = {ind.get('formula', '')} ({ind.get('unidad', '')})")
            if x.get("datos_que_faltan"):
                st.markdown("**Datos que faltan:**\n" + "\n".join(f"- {d}" for d in x["datos_que_faltan"]))
            if x.get("tecnicas"):
                st.markdown("**Técnicas de la competencia:** " + "; ".join(x["tecnicas"]))
    pre = f"an_{gid}_{obj}_"
    opciones = list(range(len(lista)))
    eleg = st.radio("¿Cuál alternativa van a trabajar?", opciones, key=pre + "eleg", horizontal=True,
                    index=an.get("elegida") if an.get("elegida") in opciones else None,
                    format_func=lambda i: f"Alternativa {i + 1}", disabled=not puede)
    if eleg is None:
        return
    alt = lista[eleg]
    st.markdown(f"#### {alt.get('titulo', '')}")
    resp = an.get("respuestas") or []
    for i, q in enumerate(alt.get("preguntas_guia") or []):
        _init(f"{pre}r{eleg}_{i}", resp[i] if i < len(resp) and an.get("elegida") == eleg else "")
        st.text_area(q, key=f"{pre}r{eleg}_{i}", disabled=not puede, height=90)
    campos = [("planteamiento", "Planteamiento del problema (con datos de la empresa)"),
              ("causas", "Causas que van a verificar"),
              ("indicador", "Indicador y cómo lo van a medir"),
              ("datos", "Datos que van a recolectar y a quién pedirlos")]
    for c, etq in campos:
        _init(pre + c, an.get(c) or "")
        st.text_area(etq, key=pre + c, disabled=not puede, height=110)

    def datos_form():
        n = len(alt.get("preguntas_guia") or [])
        return {"elegida": eleg, "respuestas": [st.session_state.get(f"{pre}r{eleg}_{i}", "") for i in range(n)],
                **{c: st.session_state.get(pre + c, "") for c, _ in campos}}

    if an.get("retro_ia"):
        r = an["retro_ia"]
        with st.container(border=True):
            st.markdown(f"**Retroalimentación de la IA** (nivel estimado en «Contexto y problema»: {r.get('nivel', '?')} de 4)")
            for t, k in (("Fortalezas", "fortalezas"), ("Para mejorar", "a_mejorar"), ("Preguntas", "preguntas")):
                if r.get(k):
                    st.markdown(f"*{t}:*\n" + "\n".join(f"- {x}" for x in r[k]))
    if an.get("estado") == "enviado":
        st.success(f"Enviado al instructor técnico el {fecha(an.get('actualizado_en'), True)}.")
    if not puede:
        return
    b1, b2, b3 = st.columns(3)
    if b1.button("💾 Guardar borrador", key=pre + "g"):
        try:
            db.guardar_analisis(gid, obj, {**datos_form(), "estado": "borrador"}, perfil["id"])
            st.toast("Guardado")
            st.rerun()
        except Exception as e:
            falla(e)
    if ia.disponible() and b2.button("🤖 Pedir retroalimentación", key=pre + "f"):
        with st.spinner("Revisando su planteamiento…"):
            try:
                d = datos_form()
                r = ia.retroalimentar(obj, alt, d, evid)
                db.guardar_analisis(gid, obj, {**d, "retro_ia": r, "estado": "borrador"}, perfil["id"])
                st.rerun()
            except (ia.IAError, Exception) as e:
                falla(e)
    if b3.button("📨 Enviar al instructor", type="primary", key=pre + "e"):
        d = datos_form()
        if not d["planteamiento"].strip():
            st.error("Escriban el planteamiento antes de enviar.")
        else:
            try:
                db.guardar_analisis(gid, obj, {**d, "estado": "enviado"}, perfil["id"])
                st.rerun()
            except Exception as e:
                falla(e)
    if not ia.disponible():
        with st.expander("🤖 Pedir retroalimentación a Claude (opcional)"):
            pegado = bloque_claude(f"{pre}retcl", ia.prompt_retro(obj, alt, datos_form(), evid))
            if pegado:
                try:
                    db.guardar_analisis(gid, obj, {**datos_form(), "retro_ia": ia.extraer_json(pegado), "estado": "borrador"}, perfil["id"])
                    st.rerun()
                except (ia.IAError, Exception) as e:
                    falla(e)


def seccion_visto_bueno(grupo, obj, vistos, asig, perfil, nombres, an):
    gid = grupo["id"]
    lst = [v for v in vistos if v["obj"] == obj]
    st.markdown(f"**Instructor técnico asignado:** {nombres.get(asig['instructor_id'], '—') if asig else 'sin asignar (el líder lo asigna en Administración)'}")
    puede = perfil["rol"] == "lider" or (asig and asig["instructor_id"] == perfil["id"])
    if puede:
        if an and an.get("estado") == "enviado":
            st.info("El grupo envió su análisis. Revíselo en la pestaña «Situación problémica» y las evidencias antes de dar el visto bueno.")
        with st.form(f"vb_{gid}_{obj}"):
            estado = st.radio("Decisión", ["aprobado", "ajustes"], horizontal=True,
                              format_func={"aprobado": "✅ Visto bueno", "ajustes": "🔁 Requiere ajustes"}.get)
            obs = st.text_area("Observaciones para el grupo", height=140)
            calif = st.checkbox("Calificar también con la rúbrica (opcional)")
            cols = st.columns(5)
            niveles = [c.selectbox(r["nombre"], [4, 3, 2, 1], index=1, key=f"vbn_{gid}_{obj}_{i}") for i, (c, r) in enumerate(zip(cols, RUBRICA))]
            if st.form_submit_button("Guardar", type="primary"):
                if estado == "ajustes" and not obs.strip():
                    st.error("Escriba qué deben ajustar.")
                else:
                    try:
                        db.dar_visto_bueno({"grupo_id": gid, "obj": obj, "instructor_id": perfil["id"], "estado": estado,
                                            "observaciones": obs.strip(), "niveles": niveles if calif else None,
                                            "nota": nota(niveles) if calif else None})
                        st.rerun()
                    except Exception as e:
                        falla(e)
    st.subheader("Historial")
    if not lst:
        st.info("Aún no hay visto bueno para esta competencia.")
    for v in lst:
        with st.container(border=True):
            st.markdown(f"{'✅ **Visto bueno**' if v['estado'] == 'aprobado' else '🔁 **Ajustes solicitados**'} · {fecha(v['creado_en'], True)} · {nombres.get(v['instructor_id'], '')}"
                        + (f" · Nota {v['nota']}" if v.get("nota") else ""))
            if v.get("observaciones"):
                st.write(v["observaciones"])


def boton_expediente(grupo, integrantes, nombres, asign, evid, anal, vistos):
    from gpi import expediente

    with st.popover("📄 Expediente"):
        fotos_inc = st.checkbox("Incluir miniaturas de las fotos (tarda más)", value=True, key=f"exf_{grupo['id']}")
        if st.button("Preparar expediente", key=f"exb_{grupo['id']}"):
            with st.spinner("Preparando…"):
                fotos = {}
                if fotos_inc:
                    for r in [r for e in evid for r in (e.get("archivos") or []) if r.endswith(".jpg")][:80]:
                        try:
                            fotos[r] = a_jpeg(db.descargar(r), 360, 70)
                        except Exception:
                            pass
                try:
                    revs = db.revisiones(grupo["id"])
                except Exception:
                    revs = []
                st.session_state[f"exp_{grupo['id']}"] = expediente.construir(grupo, integrantes, nombres, asign, evid, anal, vistos, revs, fotos)
        h = st.session_state.get(f"exp_{grupo['id']}")
        if h:
            st.download_button("⬇ Descargar (HTML, se puede imprimir a PDF)", h.encode("utf-8"),
                               file_name=f"expediente-{grupo['nombre']}.html", mime="text/html")


# ======================================================================= presentación
def bitacora_para_ia(gid):
    vistos = db.vistos_buenos(gid)
    anal = {a["obj"]: a for a in db.analisis(gid)}
    out = {}
    for o in OBJ8:
        vb = next((v for v in vistos if v["obj"] == o["n"]), None)
        a = anal.get(o["n"]) or {}
        prob = ""
        if a.get("alternativas") and a.get("elegida") is not None:
            alts = a["alternativas"].get("alternativas") or []
            if 0 <= a["elegida"] < len(alts):
                prob = alts[a["elegida"]].get("titulo", "") + ". " + (a.get("planteamiento") or "")
        out[o["n"]] = {"visto_bueno": {"estado": vb["estado"], "observaciones": vb["observaciones"], "fecha": fecha(vb["creado_en"])} if vb else None,
                       "problema": prob}
    return out


def pagina_presentacion(grupo, perfil):
    gid = grupo["id"]
    staff = perfil["rol"] in ("instructor", "lider")
    st.title(f"🎯 Presentación · {grupo['nombre']}")
    st.caption("Suban la presentación (.pptx). La IA propone nota, recomendaciones y oportunidades de mejora; el instructor siempre valida la nota.")
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        tipo = c1.radio("Tipo de revisión", ["final", "avance"], horizontal=True,
                        format_func={"final": "PPT final (los 8 objetivos)", "avance": "Avance de un objetivo"}.get)
        obj = c2.selectbox("Objetivo", [o["n"] for o in OBJ8], format_func=etiqueta, disabled=tipo == "final")
        minutos = c3.number_input("Minutos de exposición", 5, 60, 15)
        if ia.disponible():
            leer = st.checkbox("Leer también las imágenes de las diapositivas (tablas, gráficas y diagramas pegados como imagen)", value=True)
        arch = st.file_uploader("Presentación .pptx", type=["pptx"], key=f"ppt_{gid}")
        if ia.disponible():
            if st.button("🤖 Evaluar con IA", type="primary", disabled=not arch):
                evaluar(grupo, perfil, arch, tipo, obj, minutos, leer)
        else:
            revisar_con_claude(grupo, perfil, arch, tipo, obj, minutos)

    try:
        revs = db.revisiones(gid)
    except Exception as e:
        falla(e)
        return
    st.subheader("Revisiones")
    if not revs:
        st.info("Aún no hay revisiones de presentación.")
        return
    etq = lambda r: (f"{fecha(r['creado_en'], True)} · {'Final' if r['tipo'] == 'final' else 'Avance obj. ' + str(r['obj'])} · "
                     f"{r['archivo_nombre']} · {'✅ validada' if r['estado'] == 'validada' else '⏳ pendiente de validación'}")
    por_id = {r["id"]: r for r in revs}
    if st.session_state.get(f"rsel_{gid}") not in por_id:
        st.session_state[f"rsel_{gid}"] = revs[0]["id"]
    rid = st.selectbox("Revisión", list(por_id), format_func=lambda i: etq(por_id[i]), key=f"rsel_{gid}")
    mostrar_revision(por_id[rid], perfil, staff, grupo)


def evaluar(grupo, perfil, arch, tipo, obj, minutos, leer):
    data = arch.getvalue()
    with st.status("Evaluando la presentación…", expanded=True) as stt:
        try:
            st.write("Leyendo el archivo…")
            px = leer_pptx(data)
            trans, fallidos, adj = {}, 0, None
            if leer and ia.proveedor() == "gemini":
                adj, total = ia.imagenes_para_gemini(px, imagenes_relevantes(px))
                adj = adj or None
                if total > len(adj or []):
                    st.write(f"La presentación tiene {total} imágenes con contenido; se envían las {len(adj or [])} más importantes, reducidas.")
                st.write(f"Enviando el texto y {len(adj or [])} imágenes en una sola solicitud…")
            elif leer:
                items = imagenes_relevantes(px)
                if items:
                    barra = st.progress(0.0, text=f"Leyendo {len(items)} imágenes…")
                    trans, fallidos = ia.transcribir_imagenes(px, items, lambda k, n: barra.progress(k / n, text=f"Leyendo imágenes: lote {k} de {n}"))
            stats = estadisticas(px, trans, int(minutos))
            st.write("Aplicando la rúbrica… (suele tardar de 1 a 3 minutos; si pasa de 5 la app se detiene sola y avisa)")

            def aplicar(imagenes):
                if tipo == "final":
                    return ia.evaluar_final(grupo, px, trans, fallidos, stats, bitacora_para_ia(grupo["id"]), imagenes=imagenes)
                return ia.evaluar_avance(grupo, obj, px, trans, fallidos, stats, imagenes=imagenes)

            solo_texto = False
            try:
                r = aplicar(adj)
            except ia.IATiempo:
                if not adj:
                    raise
                st.write("Gemini tardó demasiado con las imágenes. Reintentando solo con el texto…")
                adj, solo_texto = None, True
                r = aplicar(None)
            if solo_texto:
                r.setdefault("alertas", [])
                if isinstance(r["alertas"], list):
                    r["alertas"].insert(0, "Evaluación hecha SOLO con el texto: Gemini no alcanzó a leer las imágenes. "
                                           "Revise usted las tablas y gráficas pegadas como imagen antes de validar.")
            if tipo == "final":
                n_prop, ap = nota_final(r["objetivos"]), aprueba_final(r["objetivos"])
            else:
                n_prop, ap = nota(r["niveles"]), aprueba(r["niveles"])
            r.update({"nota_propuesta": n_prop, "aprueba_propuesta": ap, "stats": stats,
                      "imagenes_leidas": len(adj) if adj else len(trans), "lotes_fallidos": fallidos,
                      "via": ia.proveedor()})
            guardar_revision(grupo, perfil, arch.name, data, tipo, obj, px, r, trans)
            stt.update(label="Evaluación lista", state="complete")
        except ia.IATiempo as e:
            stt.update(label="Tiempo agotado", state="error")
            st.error(f"⏱️ {e} No es falta de cupo: Gemini está lento en este momento. Intente de nuevo en unos minutos.")
            return
        except ia.IAError as e:
            stt.update(label="No se pudo evaluar", state="error")
            txt = str(e)
            st.error(("🚫 " if "cupo" in txt.lower() or "límite" in txt.lower() else "⚠️ ") + txt)
            return
        except Exception as e:
            stt.update(label="No se pudo evaluar", state="error")
            falla(e)
            return
    st.rerun()


def guardar_revision(grupo, perfil, nombre, data, tipo, obj, px, r, trans):
    ruta = None
    if len(data) <= MAX_PPT_GUARDAR:
        try:
            ruta = db.subir_archivo(grupo["id"], nombre, data, "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        except Exception:
            ruta = None
    else:
        st.warning("El archivo pesa más de 45 MB y no se guardó; sí quedan guardados su contenido y la evaluación.")
    contenido = {"slides": [{k: s[k] for k in ("n", "text", "notes", "pics", "charts")} for s in px["slides"]],
                 "transcripciones": {str(k): v for k, v in trans.items()}}
    fila = db.crear_revision({"grupo_id": grupo["id"], "tipo": tipo, "obj": obj if tipo == "avance" else None,
                              "archivo_nombre": nombre, "archivo_ruta": ruta, "diapositivas": len(px["slides"]),
                              "contenido": contenido, "propuesta": r, "estado": "propuesta", "subido_por": perfil["id"]})
    st.session_state[f"rsel_{grupo['id']}"] = fila["id"]


def revisar_con_claude(grupo, perfil, arch, tipo, obj, minutos):
    """Revisión de la PPT sin clave de API: se hace en claude.ai y se pega aquí el resultado."""
    st.info("La revisión se hace en **claude.ai con su propia cuenta**: la app prepara las instrucciones con la rúbrica, "
            "usted las lleva a Claude junto con la presentación en PDF y pega aquí la respuesta.")
    if not arch:
        return
    clave = f"pptcl_{grupo['id']}_{arch.file_id}_{tipo}_{obj}_{int(minutos)}"
    if clave not in st.session_state:
        try:
            px = leer_pptx(arch.getvalue())
        except Exception:
            st.error("No se pudo leer el archivo. Verifique que sea .pptx (no .ppt ni PDF).")
            return
        stats = estadisticas(px, {}, int(minutos))
        if tipo == "final":
            prompt = ia.prompt_final(grupo, px, {}, 0, stats, bitacora_para_ia(grupo["id"]), manual=True)
        else:
            prompt = ia.prompt_avance(grupo, obj, px, {}, 0, stats, manual=True)
        st.session_state[clave] = {"px": px, "stats": stats, "prompt": prompt}
    prep = st.session_state[clave]
    st.caption(f"{len(prep['px']['slides'])} diapositivas leídas.")
    pegado = bloque_claude(clave, prep["prompt"],
                           adjuntar="la presentación guardada como **PDF** (en PowerPoint: Archivo → Exportar → PDF), "
                                    "para que Claude lea también las tablas y gráficas que están como imagen")
    if pegado:
        try:
            r = ia.extraer_json(pegado)
            if tipo == "final":
                if not r.get("objetivos"):
                    raise ia.IAError("La respuesta no trae la evaluación de los objetivos. Copie de nuevo la respuesta completa.")
                r = ia.procesar_final(r)
                n_prop, ap = nota_final(r["objetivos"]), aprueba_final(r["objetivos"])
            else:
                if not r.get("criterios"):
                    raise ia.IAError("La respuesta no trae los criterios de la rúbrica. Copie de nuevo la respuesta completa.")
                r = ia.procesar_avance(r)
                n_prop, ap = nota(r["niveles"]), aprueba(r["niveles"])
            r.update({"nota_propuesta": n_prop, "aprueba_propuesta": ap, "stats": prep["stats"],
                      "imagenes_leidas": 0, "lotes_fallidos": 0, "via": "claude.ai"})
            with st.spinner("Guardando…"):
                guardar_revision(grupo, perfil, arch.name, arch.getvalue(), tipo, obj, prep["px"], r, {})
            del st.session_state[clave]
            st.rerun()
        except (ia.IAError, Exception) as e:
            falla(e)


def _extras(p):
    ext = p.get("extension")
    if ext:
        s = p.get("stats") or {}
        with st.container(border=True):
            st.markdown(f"**Extensión para {s.get('minutos', 15)} minutos** · {s.get('diapositivas', '?')} diapositivas · "
                        + ("✅ adecuada" if ext.get("adecuada") else f"💡 conviene condensar (sugerido: unas {ext.get('diapositivas_recomendadas', '?')})"))
            if ext.get("comentario"):
                st.write(ext["comentario"])
            for c in ext.get("condensar") or []:
                st.markdown(f"- Diap. {c.get('diapositivas', '')}: {c.get('sugerencia', '')}")
            if ext.get("anexos"):
                st.markdown("**Mover a anexos:** " + "; ".join(ext["anexos"]))
    sug = p.get("problematicas_sugeridas") or []
    if sug:
        st.markdown("**Problemáticas sugeridas para objetivos sin cubrir** (hipótesis para verificar en la empresa, integradas sin agregar diapositivas)")
        for x in sug:
            st.markdown(f"- **Objetivo {x.get('obj')}:** {x.get('situacion', '')}"
                        + (f" *Integrar en:* {x['encaje']}." if x.get("encaje") else "")
                        + (f" *Indicador:* {x['indicador']}." if x.get("indicador") else "")
                        + (f" *Datos a pedir:* {'; '.join(x['datos_que_faltan'])}." if x.get("datos_que_faltan") else ""))
    for a in p.get("alertas") or []:
        st.warning(a)


def botones_informe(grupo, r, staff):
    from gpi import expediente

    try:
        integrantes = db.miembros(grupo["id"])
        nombres = nombres_de(db.perfiles() if staff else integrantes + db.perfiles(["instructor", "lider"]))
    except Exception:
        integrantes, nombres = [], {}
    html = expediente.informe_revision(grupo, integrantes, r, nombres, mostrar_nota=staff)
    base = f"informe-{grupo['nombre']}-{'final' if r['tipo'] == 'final' else 'obj' + str(r['obj'])}-{fecha(r['creado_en']).replace('/', '-')}"
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("⬇ Informe en Word", ("\ufeff" + html).encode("utf-8"), file_name=base + ".doc",
                       mime="application/msword", key=f"iw_{r['id']}")
    c2.download_button("⬇ Informe para PDF", html.encode("utf-8"), file_name=base + ".html", mime="text/html",
                       key=f"ih_{r['id']}", help="Ábralo y use Imprimir → Guardar como PDF")


def mostrar_revision(r, perfil, staff, grupo=None):
    p = r.get("propuesta") or {}
    final = r["tipo"] == "final"
    if grupo:
        botones_informe(grupo, r, staff)
    if r.get("archivo_ruta"):
        u = db.urls_firmadas([r["archivo_ruta"]]).get(r["archivo_ruta"])
        if u:
            st.link_button("⬇ Descargar la presentación", u)
    via = {"claude.ai": "revisada en claude.ai", "gemini": "revisada con Gemini", "claude": "revisada con Claude"}.get(p.get("via"), "")
    st.caption(f"{r.get('diapositivas') or '?'} diapositivas · " + (via + " · " if via else "")
               + (f"{p.get('imagenes_leidas', 0)} imágenes leídas" if p.get("via") != "claude.ai" else "imágenes leídas desde el PDF"))

    if r["estado"] == "validada":
        res = r.get("resultado") or {}
        st.success(f"**Nota validada: {r['nota']}** · {'Aprueba' if r['aprueba'] else 'No aprueba'} · {fecha(r.get('validado_en'), True)}")
        if final:
            df = pd.DataFrame([{"Objetivo": corto(x["obj"]), **{c["nombre"]: x["niveles"][i] for i, c in enumerate(RUBRICA)}, "Nota": nota(x["niveles"])}
                               for x in res.get("objetivos") or []])
            st.dataframe(df, hide_index=True)
        elif res.get("niveles"):
            st.dataframe(pd.DataFrame([{c["nombre"]: res["niveles"][i] for i, c in enumerate(RUBRICA)}]), hide_index=True)
        for t, k in (("Recomendaciones", "recomendaciones"), ("Oportunidades de mejora", "oportunidades"), ("Observaciones del instructor", "observaciones")):
            if r.get(k):
                st.markdown(f"**{t}**\n" + "\n".join(f"- {x}" for x in r[k].split("\n") if x.strip()))
        _extras(p)
        return

    if not staff:
        st.info("⏳ La nota está pendiente de validación por el instructor. Mientras tanto, estas son las recomendaciones de la revisión automática.")
        recs = p.get("recomendaciones_generales") if final else p.get("recomendaciones")
        if recs:
            st.markdown("**Recomendaciones**\n" + "\n".join(f"- {x}" for x in recs))
        if p.get("oportunidades_mejora"):
            st.markdown("**Oportunidades de mejora**\n" + "\n".join(f"- {x}" for x in p["oportunidades_mejora"]))
        if final:
            for x in p.get("objetivos") or []:
                if x.get("faltantes") or x.get("recomendaciones"):
                    with st.expander(etiqueta(x["obj"])):
                        if x.get("faltantes"):
                            st.markdown("*Falta:* " + "; ".join(x["faltantes"]))
                        for y in x.get("recomendaciones") or []:
                            st.markdown(f"- {y}")
        _extras(p)
        return

    # ---- validación por el instructor
    st.markdown(f"### Validar · nota propuesta por la IA: **{p.get('nota_propuesta', '?')}**")
    st.caption("Ajuste los niveles (1 a 4) donde no esté de acuerdo. La nota se recalcula con la fórmula unificada.")
    cols_cfg = {c["nombre"]: st.column_config.SelectboxColumn(c["nombre"] + f" ({round(c['peso'] * 100)}%)", options=[1, 2, 3, 4], required=True) for c in RUBRICA}
    if final:
        base = pd.DataFrame([{"obj": x["obj"], "Objetivo": corto(x["obj"]), "Diapositivas": x.get("diapositivas", ""),
                              **{c["nombre"]: x["niveles"][i] for i, c in enumerate(RUBRICA)}, "Justificación de la IA": x.get("justificacion", "")}
                             for x in p.get("objetivos") or []])
    else:
        base = pd.DataFrame([{"obj": r["obj"], "Objetivo": corto(r["obj"]), **{c["nombre"]: p["niveles"][i] for i, c in enumerate(RUBRICA)},
                              "Justificación de la IA": " | ".join(j for j in p.get("justificaciones") or [] if j)}])
    ed = st.data_editor(base, column_config={**cols_cfg, "obj": None}, disabled=["Objetivo", "Diapositivas", "Justificación de la IA"],
                        hide_index=True, key=f"ed_{r['id']}")
    objetivos = [{"obj": int(f["obj"]), "niveles": [int(f[c["nombre"]]) for c in RUBRICA]} for _, f in ed.iterrows()]
    if final:
        n, ap = nota_final(objetivos), aprueba_final(objetivos)
        st.markdown(f"**Nota: {n}** · {'✅ Aprueba' if ap else '❌ No aprueba'} (promedio de los 8 objetivos; aprueba con 3.5 o más y todos los objetivos aprobados)")
    else:
        n, ap = nota(objetivos[0]["niveles"]), aprueba(objetivos[0]["niveles"])
        st.markdown(f"**Nota: {n}** · {'✅ Aprueba' if ap else '❌ No aprueba'} (aprueba con 3.5 o más y ningún criterio en nivel 1)")
    if not final and (p.get("evidencias_encontradas") or p.get("evidencias_faltantes")):
        with st.expander("Evidencias encontradas y faltantes"):
            for x in p.get("evidencias_encontradas") or []:
                st.markdown(f"- {x.get('evidencia', '')} (diap. {x.get('diapositivas', '')}): {x.get('calidad', '')}")
            if p.get("evidencias_faltantes"):
                st.markdown("*Faltan:* " + "; ".join(p["evidencias_faltantes"]))
    _extras(p)
    recs = p.get("recomendaciones_generales") if final else p.get("recomendaciones")
    k = f"val_{r['id']}_"
    _init(k + "rec", "\n".join(recs or []))
    _init(k + "opo", "\n".join(p.get("oportunidades_mejora") or []))
    st.text_area("Recomendaciones (una por línea)", key=k + "rec", height=140)
    st.text_area("Oportunidades de mejora (una por línea)", key=k + "opo", height=110)
    st.text_area("Observaciones del instructor", key=k + "obs", height=90)
    if st.button("✅ Validar y publicar la nota", type="primary", key=k + "ok"):
        try:
            db.validar_revision(r["id"], {
                "resultado": {"objetivos": objetivos} if final else {"niveles": objetivos[0]["niveles"]},
                "nota": n, "aprueba": ap, "recomendaciones": st.session_state[k + "rec"].strip(),
                "oportunidades": st.session_state[k + "opo"].strip(), "observaciones": st.session_state.get(k + "obs", "").strip(),
                "estado": "validada", "validado_por": perfil["id"], "validado_en": datetime.now().astimezone().isoformat()})
            st.session_state.pop(f"rsel_{r['grupo_id']}", None)
            st.rerun()
        except Exception as e:
            falla(e)


# ======================================================================= tablero
def _abrir(gid, obj):
    st.session_state.gid = gid
    st.session_state[f"obj_{gid}"] = obj
    st.session_state.pagina = "Bitácora del grupo"


def filtrar_grupos(grupos, perfil):
    """Filtros del menú lateral para instructores: ficha y «mis grupos»."""
    fichas = sorted({(g.get("ficha") or "").strip() for g in grupos if (g.get("ficha") or "").strip()})
    ficha = st.selectbox("Ficha", ["Todas"] + fichas, key="f_ficha")
    mios = st.checkbox("Solo mis grupos", key="f_mios", help="Grupos que usted creó o donde es instructor técnico de alguna competencia")
    if ficha != "Todas":
        grupos = [g for g in grupos if (g.get("ficha") or "").strip() == ficha]
    if mios:
        try:
            asg = {a["grupo_id"] for a in db.asignaciones() if a["instructor_id"] == perfil["id"]}
        except Exception:
            asg = set()
        grupos = [g for g in grupos if g["id"] in asg or g.get("creado_por") == perfil["id"]]
    st.caption(f"{len(grupos)} grupo(s)")
    return grupos


def pagina_tablero(perfil, grupos):
    from gpi import reportes

    st.title("📊 Avance de los grupos")
    try:
        R = db.resumen_todos()
        revs = db.revisiones_resumen()
    except Exception as e:
        falla(e)
        return
    if not grupos:
        st.info("No hay grupos con este filtro. Cambie el filtro del menú lateral o cree grupos en Administración.")
        return
    t1, t2, t3 = st.tabs(["📈 Notas de las presentaciones", "📒 Bitácora y vistos buenos", "⬇ Descargar datos (Excel / Power BI)"])

    # ---------------- notas
    with t1:
        filas, finales = [], []
        for g in grupos:
            r = reportes.ultima_final(revs, g["id"])
            fila = {"Ficha": g.get("ficha") or "", "Grupo": g["nombre"], "Empresa": g["empresa"]}
            pares = dict(reportes._niveles_final(r)) if r else {}
            for o in OBJ8:
                nv = pares.get(o["n"])
                fila[corto(o["n"])] = nota(nv) if nv else None
            if r:
                validada = r["estado"] == "validada"
                fila["Nota final"] = r["nota"] if validada else r.get("prop_nota")
                fila["Estado"] = "✅ Validada" if validada else "⏳ Propuesta IA"
                finales.append((g, r, pares))
            else:
                fila["Nota final"] = None
                fila["Estado"] = "Sin PPT final"
            filas.append(fila)
        val = [r for _, r, _ in finales if r["estado"] == "validada"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Grupos", len(grupos))
        c2.metric("Con PPT final revisada", len(finales))
        c3.metric("Nota promedio (validadas)", f"{sum(float(r['nota']) for r in val) / len(val):.1f}" if val else "—")
        c4.metric("Aprueban (validadas)", f"{sum(1 for r in val if r['aprueba'])} de {len(val)}" if val else "—")
        st.caption("Nota de cada objetivo en la última PPT final del grupo (1.0 a 5.0). Si el instructor ya la validó se usa esa; "
                   "si no, la propuesta de la IA. Vacío = el grupo aún no tiene PPT final revisada.")
        cfg = {corto(o["n"]): st.column_config.NumberColumn(corto(o["n"]), format="%.1f") for o in OBJ8}
        cfg["Nota final"] = st.column_config.NumberColumn("Nota final", format="%.1f")
        st.dataframe(pd.DataFrame(filas), hide_index=True, column_config=cfg)
        if finales:
            prom = []
            for o in OBJ8:
                v = [nota(p[o["n"]]) for _, _, p in finales if p.get(o["n"])]
                if v:
                    prom.append({"Objetivo": corto(o["n"]), "Nota promedio": round(sum(v) / len(v), 2)})
            if prom:
                st.markdown("**Nota promedio por objetivo** (todos los grupos filtrados): muestra qué competencias necesitan más refuerzo.")
                st.bar_chart(pd.DataFrame(prom), x="Objetivo", y="Nota promedio", color="#39A900", horizontal=True, height=320)

    # ---------------- bitácora
    pendientes, filas_b = [], []
    for g in grupos:
        ev = [x for x in R["evidencias"] if x["grupo_id"] == g["id"]]
        an = [x for x in R["analisis"] if x["grupo_id"] == g["id"]]
        vb = [x for x in R["vistos"] if x["grupo_id"] == g["id"]]
        fila = {"Ficha": g.get("ficha") or "", "Grupo": g["nombre"], "Empresa": g["empresa"], "Evidencias": len(ev)}
        for o in OBJ8:
            est = estado_objetivo(o["n"], ev, an, vb)
            fila[corto(o["n"])] = f"{ICONO[est]} {TEXTO_ESTADO[est]}" if est != "vacio" else "—"
            asg = next((a for a in R["asignaciones"] if a["grupo_id"] == g["id"] and a["obj"] == o["n"]), None)
            if est == "enviado" and (perfil["rol"] == "lider" or (asg and asg["instructor_id"] == perfil["id"])):
                pendientes.append((g, o))
        fila["Vistos buenos"] = f"{sum(1 for o in OBJ8 if fila[corto(o['n'])].startswith('✅'))} de 8"
        filas_b.append(fila)
    with t2:
        st.caption("Avance de la bitácora durante el trimestre: evidencias que sube el grupo, análisis del problema y visto bueno del "
                   "instructor técnico de cada competencia. Aparece «—» mientras el grupo no haya cargado nada de esa competencia en la app; "
                   "no depende de la PPT.")
        st.caption(" · ".join(f"{ICONO[k]} {TEXTO_ESTADO[k]}" for k in ICONO))
        st.dataframe(pd.DataFrame(filas_b), hide_index=True)
        st.subheader("Pendientes de su visto bueno")
        if not pendientes:
            st.success("No tiene análisis pendientes por revisar.")
        for g, o in pendientes:
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{g['nombre']}** ({g['empresa']}) · {etiqueta(o['n'])}")
            c2.button("Abrir", key=f"open_{g['id']}_{o['n']}", on_click=_abrir, args=(g["id"], o["n"]))

    # ---------------- descargas
    with t3:
        largo = reportes.notas_largo(grupos, revs)
        tab_rev = reportes.revisiones_tabla(grupos, revs)
        bit = pd.DataFrame([{**{k: v for k, v in f.items()}} for f in filas_b])
        st.write("Descargue los datos de los grupos filtrados para analizarlos en Excel o alimentar un tablero en **Power BI**.")
        st.markdown(
            "- **Notas_por_objetivo**: una fila por grupo, revisión y objetivo, con los 5 criterios y la nota (formato ideal para Power BI).\n"
            "- **Revisiones**: una fila por PPT revisada, con nota propuesta, nota validada y si aprueba.\n"
            "- **Bitacora**: estado de cada competencia por grupo.")
        nombre = "bitacora-gpi-" + datetime.now().strftime("%Y%m%d")
        st.download_button("⬇ Descargar Excel (3 hojas)", reportes.excel({"Notas_por_objetivo": largo, "Revisiones": tab_rev, "Bitacora": bit}),
                           file_name=nombre + ".xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.download_button("⬇ Notas por objetivo (CSV)", largo.to_csv(index=False).encode("utf-8-sig"), file_name=nombre + "-notas.csv", mime="text/csv")
        with st.expander("Cómo usarlo en Power BI"):
            st.markdown(
                "1. Power BI Desktop → **Obtener datos → Libro de Excel** → elija el archivo y marque las 3 hojas.\n"
                "2. Con la hoja **Notas_por_objetivo** arme, por ejemplo: matriz *grupo × objetivo* con promedio de `nota_objetivo`, "
                "barras de promedio por `competencia`, y un segmentador por `ficha` y `estado`.\n"
                "3. Para actualizar, descargue de nuevo el Excel con el mismo nombre de archivo y pulse **Actualizar** en Power BI.")


# ======================================================================= administración
def pagina_admin(perfil):
    st.title("⚙️ Administración")
    lider = perfil["rol"] == "lider"
    tabs = st.tabs(["Grupos", "Instructores por competencia", "Integrantes"] + (["Usuarios y roles"] if lider else []))
    try:
        grupos = db.grupos_visibles()
    except Exception as e:
        falla(e)
        return
    with tabs[0]:
        with st.form("nuevo_grupo", clear_on_submit=True):
            st.markdown("**Nuevo grupo**")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre del grupo")
            ficha = c2.text_input("Ficha")
            empresa = c1.text_input("Empresa proyecto")
            sector = c2.text_input("Sector / actividad")
            if st.form_submit_button("Crear grupo", type="primary"):
                if not nombre.strip() or not empresa.strip():
                    st.error("Nombre y empresa son obligatorios.")
                else:
                    try:
                        g = db.crear_grupo({"nombre": nombre.strip(), "ficha": ficha.strip(), "empresa": empresa.strip(), "sector": sector.strip()}, perfil["id"])
                        st.success(f"Grupo creado. Código para que los aprendices se unan: **{g['codigo']}**")
                    except Exception as e:
                        falla(e)
        if grupos:
            df = pd.DataFrame([{"id": g["id"], "Nombre": g["nombre"], "Ficha": g.get("ficha") or "", "Empresa": g["empresa"],
                                "Sector": g.get("sector") or "", "Código": g["codigo"], "Activo": g["activo"]} for g in grupos])
            ed = st.data_editor(df, column_config={"id": None}, disabled=["Código"], hide_index=True, key="ed_grupos")
            if st.button("Guardar cambios de grupos"):
                try:
                    for (_, a), (_, b) in zip(df.iterrows(), ed.iterrows()):
                        if not a.equals(b):
                            db.actualizar_grupo(a["id"], {"nombre": b["Nombre"], "ficha": b["Ficha"], "empresa": b["Empresa"],
                                                          "sector": b["Sector"], "activo": bool(b["Activo"])})
                    st.success("Guardado.")
                except Exception as e:
                    falla(e)
    if not grupos:
        return
    with tabs[1]:
        g = st.selectbox("Grupo", grupos, format_func=lambda g: f"{g['nombre']} · {g['empresa']}", key="adm_g1")
        inst = db.perfiles(["instructor", "lider"])
        ops = [None] + [p["id"] for p in inst]
        nom = nombres_de(inst)
        actual = {a["obj"]: a["instructor_id"] for a in db.asignaciones(g["id"])}
        with st.form(f"asig_{g['id']}"):
            sel = {o["n"]: st.selectbox(etiqueta(o["n"]), ops, index=ops.index(actual.get(o["n"])) if actual.get(o["n"]) in ops else 0,
                                        format_func=lambda x: "— sin asignar —" if x is None else nom.get(x, x)) for o in OBJ8}
            aplicar_todos = st.checkbox("Aplicar esta misma asignación a todos los grupos activos")
            if st.form_submit_button("Guardar asignaciones", type="primary"):
                try:
                    destino = [x for x in grupos if x["activo"]] if aplicar_todos else [g]
                    for gg in destino:
                        for n, iid in sel.items():
                            db.guardar_asignacion(gg["id"], n, iid)
                    st.success("Asignaciones guardadas.")
                except Exception as e:
                    falla(e)
    with tabs[2]:
        g = st.selectbox("Grupo ", grupos, format_func=lambda g: f"{g['nombre']} · {g['empresa']}", key="adm_g2")
        st.caption(f"Los aprendices también pueden unirse solos con el código **{g['codigo']}** (menú «Mi cuenta»).")
        mm = db.miembros(g["id"])
        for m in mm:
            c1, c2 = st.columns([4, 1])
            c1.write(f"{m['nombre']} · {m['correo']}")
            if c2.button("Quitar", key=f"q_{g['id']}_{m['id']}"):
                db.quitar_miembro(g["id"], m["id"])
                st.rerun()
        apr = [p for p in db.perfiles("aprendiz") if p["id"] not in {m["id"] for m in mm}]
        if apr:
            nuevo = st.selectbox("Agregar aprendiz", [None] + apr, format_func=lambda p: "—" if p is None else f"{p['nombre']} · {p['correo']}")
            if nuevo and st.button("Agregar al grupo"):
                db.agregar_miembro(g["id"], nuevo["id"])
                st.rerun()
    if lider:
        with tabs[3]:
            st.caption("Toda cuenta nueva queda como aprendiz. Cambie aquí a instructor a sus compañeros.")
            pp = db.perfiles()
            df = pd.DataFrame([{"id": p["id"], "Nombre": p["nombre"], "Correo": p["correo"], "Rol": p["rol"]} for p in pp])
            ed = st.data_editor(df, column_config={"id": None, "Rol": st.column_config.SelectboxColumn("Rol", options=["aprendiz", "instructor", "lider"], required=True)},
                                disabled=["Nombre", "Correo"], hide_index=True, key="ed_roles")
            if st.button("Guardar roles", type="primary"):
                try:
                    for (_, a), (_, b) in zip(df.iterrows(), ed.iterrows()):
                        if a["Rol"] != b["Rol"]:
                            db.asignar_rol(a["id"], b["Rol"])
                    st.success("Roles actualizados.")
                except Exception as e:
                    falla(e)
            st.divider()
            st.markdown("**Contraseña temporal** (para quien olvidó la suya)")
            with st.form("clave_temporal", clear_on_submit=True):
                quien = st.selectbox("Usuario", pp, format_func=lambda p: f"{p['nombre']} · {p['correo']}")
                temp = st.text_input("Contraseña temporal (mínimo 6 caracteres)")
                if st.form_submit_button("Asignar contraseña temporal"):
                    if len(temp) < 6:
                        st.error("Mínimo 6 caracteres.")
                    else:
                        try:
                            db.clave_temporal(quien["id"], temp)
                            st.success(f"Listo. Entréguele la contraseña temporal a {quien['nombre']} y pídale que la cambie en «Mi cuenta».")
                        except Exception as e:
                            falla(e)


# ======================================================================= cuenta
def pagina_cuenta(perfil):
    st.title("👤 Mi cuenta")
    st.write(f"**Correo:** {perfil['correo']}  \n**Rol:** {perfil['rol']}")
    with st.form("nombre"):
        n = st.text_input("Nombre", value=perfil["nombre"])
        if st.form_submit_button("Guardar nombre"):
            db.cambiar_nombre(perfil["id"], n.strip())
            st.session_state.pop("perfil", None)
            st.rerun()
    with st.form("cambiar_clave", clear_on_submit=True):
        st.markdown("**Cambiar mi contraseña**")
        c1 = st.text_input("Contraseña nueva (mínimo 6 caracteres)", type="password")
        c2 = st.text_input("Repita la contraseña nueva", type="password")
        if st.form_submit_button("Cambiar contraseña"):
            if len(c1) < 6 or c1 != c2:
                st.error("Las contraseñas no coinciden o tienen menos de 6 caracteres.")
            else:
                try:
                    db.cambiar_mi_clave(c1)
                    st.success("Contraseña cambiada.")
                except Exception as e:
                    falla(e)
    if perfil["rol"] == "aprendiz":
        try:
            mios = db.mis_grupos(perfil["id"])
        except Exception:
            mios = []
        if mios:
            st.markdown("**Mis grupos** (compartan el código con sus compañeros para que se unan)\n" +
                        "\n".join(f"- {g['nombre']} · {g['empresa']} · ficha {g.get('ficha') or '—'} · código `{g['codigo']}`" for g in mios))
        st.markdown("**¿Ya tienen grupo?** Únase con el código que le dio su instructor o un compañero.")
        with st.form("unirse"):
            cod = st.text_input("Código de grupo")
            if st.form_submit_button("Unirme al grupo", type="primary"):
                try:
                    db.unirse_grupo(cod)
                    st.success("Listo, ya pertenece al grupo.")
                except Exception as e:
                    st.error("Código no válido." if "no válido" in str(e) else str(e))
        st.markdown("**¿Su grupo aún no existe?** Créelo (lo hace un solo integrante); los demás se unen con el código.")
        with st.form("crear_grupo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre del grupo (ej.: Grupo 1)")
            ficha = c2.text_input("Ficha")
            empresa = c1.text_input("Empresa proyecto")
            sector = c2.text_input("Sector / actividad")
            if st.form_submit_button("Crear grupo"):
                try:
                    r = db.crear_mi_grupo(nombre.strip(), ficha.strip(), empresa.strip(), sector.strip())
                    if r.get("existente"):
                        st.info(f"Ya existía un grupo de la ficha {ficha} con esa empresa («{r['nombre']}»): lo unimos a ese. Código: **{r['codigo']}**")
                    else:
                        st.success(f"Grupo creado. Compartan este código con sus compañeros: **{r['codigo']}**")
                except Exception as e:
                    st.error("Escriba nombre del grupo, ficha y empresa." if "obligatorios" in str(e) else str(e))


# ======================================================================= principal
# ======================================================================= ayuda
INSTRUCTIVOS = Path(__file__).resolve().parent / "instructivos"
NOMBRE_INSTR = {"aprendices": "Instructivo para aprendices", "instructores": "Instructivo para instructores"}


def botones_instructivo(roles, pre):
    cols = st.columns(len(roles) * 2)
    i = 0
    for rol in roles:
        for ext, mime in (("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"), ("pdf", "application/pdf")):
            f = INSTRUCTIVOS / f"instructivo_{rol}.{ext}"
            if f.exists():
                cols[i].download_button(f"⬇ {NOMBRE_INSTR[rol]} ({'Word' if ext == 'docx' else 'PDF'})", f.read_bytes(),
                                        file_name=f.name, mime=mime, key=f"{pre}_{rol}_{ext}")
            i += 1


def pagina_ayuda(staff):
    st.title("❓ Ayuda")
    roles = ["instructores", "aprendices"] if staff else ["aprendices"]
    botones_instructivo(roles, "ay")
    tabs = st.tabs([NOMBRE_INSTR[r] for r in roles])
    for t, rol in zip(tabs, roles):
        f = INSTRUCTIVOS / f"instructivo_{rol}.md"
        with t:
            texto = f.read_text(encoding="utf-8") if f.exists() else "El instructivo no está en la carpeta «instructivos»."
            st.markdown(texto.split("\n", 1)[1] if texto.startswith("# ") else texto)


def main():
    if not configurada():
        return
    user = db.usuario_actual()
    if not user:
        pantalla_acceso()
        return
    if "perfil" not in st.session_state or st.session_state.perfil["id"] != user.id:
        st.session_state.perfil = db.mi_perfil(user.id)
    perfil = st.session_state.perfil
    if not perfil:
        st.error("Su cuenta no tiene perfil. Pida al líder que revise la instalación (disparador al_crear_usuario).")
        if st.button("Salir"):
            db.cerrar_sesion()
            st.rerun()
        return
    staff = perfil["rol"] in ("instructor", "lider")
    paginas = (["Tablero", "Bitácora del grupo", "Presentación", "Administración", "Mi cuenta", "Ayuda"] if staff
               else ["Bitácora del grupo", "Presentación", "Mi cuenta", "Ayuda"])
    with st.sidebar:
        st.markdown(f"### Bitácora GPI\n{perfil['nombre'] or perfil['correo']}  \n*{perfil['rol']}*")
        if st.session_state.get("pagina") not in paginas:
            st.session_state.pagina = paginas[0]
        pagina = st.radio("Menú", paginas, key="pagina", label_visibility="collapsed")
        grupos = db.grupos_visibles() if staff else db.mis_grupos(perfil["id"])
        if staff:
            grupos = [g for g in grupos if g["activo"]]
            if pagina in ("Tablero", "Bitácora del grupo", "Presentación"):
                grupos = filtrar_grupos(grupos, perfil)
        grupo = None
        if grupos and pagina in ("Bitácora del grupo", "Presentación"):
            ids = [g["id"] for g in grupos]
            if st.session_state.get("gid") not in ids:
                st.session_state.gid = ids[0]
            gid = st.selectbox("Grupo (escriba para buscar)", ids, key="gid", format_func=lambda i: next(f"{g['nombre']} · {g['empresa']}" for g in grupos if g["id"] == i))
            grupo = next(g for g in grupos if g["id"] == gid)
        if ia.proveedor() == "gemini":
            st.caption("🤖 IA: Gemini (plan gratuito, con cupo diario limitado).")
        elif not ia.disponible():
            st.caption("🤖 IA: se usa con su propia cuenta de claude.ai (copiar y pegar).")
        st.divider()
        if st.button("Cerrar sesión"):
            db.cerrar_sesion()
            st.rerun()

    if pagina == "Tablero":
        pagina_tablero(perfil, grupos)
    elif pagina == "Administración":
        pagina_admin(perfil)
    elif pagina == "Mi cuenta":
        pagina_cuenta(perfil)
    elif pagina == "Ayuda":
        pagina_ayuda(staff)
    elif not grupo:
        st.title("📒 Bitácora")
        st.info("Aún no pertenece a ningún grupo. Vaya a «Mi cuenta» y escriba el código que le dio su instructor." if not staff
                else "No hay grupos activos. Créelos en Administración.")
    elif pagina == "Bitácora del grupo":
        pagina_bitacora(grupo, perfil)
    else:
        pagina_presentacion(grupo, perfil)


main()
