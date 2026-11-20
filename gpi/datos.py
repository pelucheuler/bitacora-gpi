"""Acceso a Supabase. Cada sesión de Streamlit tiene su propio cliente (su propio inicio de sesión)."""
import time
import uuid

import streamlit as st
from supabase import Client, create_client

BUCKET = "evidencias"


def cliente() -> Client:
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return st.session_state.sb


def T(nombre):
    return cliente().table(nombre)


# ------------------------------------------------------------------ cuenta
def iniciar_sesion(correo, clave):
    r = cliente().auth.sign_in_with_password({"email": correo.strip(), "password": clave})
    return r.user


def registrarse(nombre, correo, clave):
    return cliente().auth.sign_up({"email": correo.strip(), "password": clave, "options": {"data": {"nombre": nombre.strip()}}})


def cambiar_mi_clave(clave):
    cliente().auth.update_user({"password": clave})


def clave_temporal(pid, clave):
    """Solo el líder: asigna una contraseña temporal (función restablecer_clave en la base de datos)."""
    cliente().rpc("restablecer_clave", {"usuario": pid, "nueva": clave}).execute()


def cerrar_sesion():
    try:
        cliente().auth.sign_out()
    finally:
        for k in list(st.session_state.keys()):
            del st.session_state[k]


def usuario_actual():
    try:
        s = cliente().auth.get_session()  # renueva el token si venció
        return s.user if s else None
    except Exception:
        return None


def mi_perfil(uid):
    r = T("perfiles").select("*").eq("id", uid).limit(1).execute().data
    return r[0] if r else None


def cambiar_nombre(uid, nombre):
    T("perfiles").update({"nombre": nombre}).eq("id", uid).execute()


# ------------------------------------------------------------------ grupos
def grupos_visibles():
    return T("grupos").select("*").order("nombre").execute().data


def mis_grupos(uid):
    ids = [m["grupo_id"] for m in T("miembros").select("grupo_id").eq("perfil_id", uid).execute().data]
    if not ids:
        return []
    return T("grupos").select("*").in_("id", ids).order("nombre").execute().data


def crear_grupo(datos, uid):
    return T("grupos").insert({**datos, "creado_por": uid}).execute().data[0]


def actualizar_grupo(gid, datos):
    T("grupos").update(datos).eq("id", gid).execute()


def unirse_grupo(codigo):
    return cliente().rpc("unirse_grupo", {"cod": codigo}).execute().data


def miembros(gid):
    filas = T("miembros").select("perfil_id, unido_en").eq("grupo_id", gid).execute().data
    ids = [f["perfil_id"] for f in filas]
    if not ids:
        return []
    return T("perfiles").select("id, nombre, correo").in_("id", ids).order("nombre").execute().data


def quitar_miembro(gid, pid):
    T("miembros").delete().eq("grupo_id", gid).eq("perfil_id", pid).execute()


def agregar_miembro(gid, pid):
    T("miembros").upsert({"grupo_id": gid, "perfil_id": pid}).execute()


def perfiles(rol=None):
    q = T("perfiles").select("id, nombre, correo, rol, creado_en").order("nombre")
    if rol:
        q = q.in_("rol", rol if isinstance(rol, list) else [rol])
    return q.execute().data


def asignar_rol(pid, rol):
    cliente().rpc("asignar_rol", {"usuario": pid, "nuevo_rol": rol}).execute()


def asignaciones(gid=None):
    q = T("asignaciones").select("*")
    if gid:
        q = q.eq("grupo_id", gid)
    return q.execute().data


def guardar_asignacion(gid, obj, instructor_id):
    if instructor_id:
        T("asignaciones").upsert({"grupo_id": gid, "obj": obj, "instructor_id": instructor_id}).execute()
    else:
        T("asignaciones").delete().eq("grupo_id", gid).eq("obj", obj).execute()


# ------------------------------------------------------------------ archivos
def subir_archivo(gid, nombre, data: bytes, tipo: str) -> str:
    limpio = "".join(c if c.isalnum() or c in "._-" else "_" for c in nombre)[-80:]
    ruta = f"{gid}/{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}-{limpio}"
    cliente().storage.from_(BUCKET).upload(ruta, data, {"content-type": tipo or "application/octet-stream"})
    return ruta


def urls_firmadas(rutas, segundos=3600):
    if not rutas:
        return {}
    try:
        r = cliente().storage.from_(BUCKET).create_signed_urls(list(rutas), segundos)
        return {x["path"]: x.get("signedURL") or x.get("signedUrl") for x in r if not x.get("error")}
    except Exception:
        return {}


def descargar(ruta) -> bytes:
    return cliente().storage.from_(BUCKET).download(ruta)


def borrar_archivos(rutas):
    if rutas:
        try:
            cliente().storage.from_(BUCKET).remove(list(rutas))
        except Exception:
            pass


# ------------------------------------------------------------------ bitácora
def evidencias(gid):
    return T("evidencias").select("*").eq("grupo_id", gid).order("creado_en", desc=True).execute().data


def crear_evidencia(fila):
    return T("evidencias").insert(fila).execute().data[0]


def borrar_evidencia(ev):
    T("evidencias").delete().eq("id", ev["id"]).execute()
    borrar_archivos(ev.get("archivos") or [])


def analisis(gid, obj=None):
    q = T("analisis").select("*").eq("grupo_id", gid)
    if obj is not None:
        q = q.eq("obj", obj)
    return q.execute().data


def guardar_analisis(gid, obj, datos, uid):
    fila = {**datos, "grupo_id": gid, "obj": obj, "actualizado_por": uid,
            "actualizado_en": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    return T("analisis").upsert(fila).execute().data[0]


def vistos_buenos(gid=None):
    q = T("vistos_buenos").select("*").order("creado_en", desc=True)
    if gid:
        q = q.eq("grupo_id", gid)
    return q.execute().data


def dar_visto_bueno(fila):
    return T("vistos_buenos").insert(fila).execute().data[0]


def revisiones(gid=None, tipo=None):
    q = T("revisiones").select("*").order("creado_en", desc=True)
    if gid:
        q = q.eq("grupo_id", gid)
    if tipo:
        q = q.eq("tipo", tipo)
    return q.execute().data


def crear_revision(fila):
    return T("revisiones").insert(fila).execute().data[0]


def validar_revision(rid, datos):
    T("revisiones").update(datos).eq("id", rid).execute()


# ------------------------------------------------------------------ tablero
def resumen_todos():
    """Datos livianos para el tablero de todos los grupos."""
    return {
        "evidencias": T("evidencias").select("grupo_id, obj").execute().data,
        "analisis": T("analisis").select("grupo_id, obj, estado").execute().data,
        "vistos": T("vistos_buenos").select("grupo_id, obj, estado, creado_en").order("creado_en", desc=True).execute().data,
        "finales": T("revisiones").select("grupo_id, tipo, estado, nota, aprueba, creado_en").eq("tipo", "final").order("creado_en", desc=True).execute().data,
        "asignaciones": T("asignaciones").select("*").execute().data,
    }
