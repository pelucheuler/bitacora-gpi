"""Llamadas a Claude (API de Anthropic) para la bitácora GPI.

La clave va en los secretos de Streamlit (ANTHROPIC_API_KEY). El modelo se puede cambiar
con el secreto MODELO_IA. Se activan los "fallbacks" del lado del servidor: si el modelo
principal declina una solicitud, la API la reintenta con el modelo alterno recomendado.
"""
import base64
import json
import re

import anthropic
import streamlit as st

from .catalogo import OBJ, OBJ8, RUBRICA, rubrica_texto

MODELO_POR_DEFECTO = "claude-opus-5-5"


class IAError(Exception):
    pass


@st.cache_resource
def _cliente():
    clave = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not clave:
        raise IAError("Falta ANTHROPIC_API_KEY en los secretos de la app.")
    return anthropic.Anthropic(api_key=clave, max_retries=3)


def disponible() -> bool:
    return bool(st.secrets.get("ANTHROPIC_API_KEY", ""))


def _modelo() -> str:
    return st.secrets.get("MODELO_IA", MODELO_POR_DEFECTO)


def llamar(prompt: str, imagenes=None, esfuerzo: str = "medium", max_tokens: int = 16000) -> str:
    """Envía el prompt (y fotos JPEG opcionales) y devuelve el texto de la respuesta."""
    contenido = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                     "data": base64.standard_b64encode(b).decode("utf-8")}}
        for b in (imagenes or [])
    ]
    contenido.append({"type": "text", "text": prompt})
    try:
        with _cliente().beta.messages.stream(
            model=_modelo(),
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": esfuerzo},
            messages=[{"role": "user", "content": contenido}],
        ) as s:
            msg = s.get_final_message()
    except anthropic.RateLimitError:
        raise IAError("Se alcanzó el límite de uso de la IA. Intente de nuevo en unos minutos.")
    except anthropic.AuthenticationError:
        raise IAError("La clave de la API de Anthropic no es válida. Revise los secretos de la app.")
    except anthropic.BadRequestError as e:
        raise IAError(f"La IA no aceptó la solicitud (¿contenido demasiado grande?): {e.message}")
    except anthropic.APIError as e:
        raise IAError(f"No se pudo conectar con la IA: {getattr(e, 'message', e)}")
    if msg.stop_reason == "refusal":
        raise IAError("La IA no pudo procesar este contenido. Revise las fotos o el texto e intente de nuevo.")
    texto = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    if msg.stop_reason == "max_tokens":
        raise IAError("La respuesta llegó incompleta. Reduzca el contenido e intente de nuevo.")
    return texto


FIN_JSON = "\n\nResponde ÚNICAMENTE con el objeto JSON, sin texto antes ni después."


def llamar_json(prompt: str, **kw) -> dict:
    return extraer_json(llamar(prompt + FIN_JSON, **kw))


def extraer_json(texto: str) -> dict:
    """Saca el objeto JSON de una respuesta (de la API o pegada desde claude.ai)."""
    t = re.sub(r"```(?:json)?", "", (texto or "").strip())
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise IAError("No se encontró el resultado en formato JSON. Copie la respuesta completa de Claude (el bloque que empieza con { y termina con }).")
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError:
        raise IAError("El resultado está incompleto o mal copiado. Copie de nuevo la respuesta completa de Claude.")


# ---------------------------------------------------------------- Evidencias
def describir_fotos(fotos, grupo, obj, contexto=""):
    return llamar(prompt_fotos(len(fotos), grupo, obj, contexto), imagenes=fotos, esfuerzo="low", max_tokens=8000)


def prompt_fotos(n_fotos, grupo, obj, contexto=""):
    o = OBJ[obj]
    prompt = f"""Eres asistente de aprendices de Tecnología en Gestión de la Producción Industrial (SENA, Colombia) que visitan una empresa para su proyecto productivo.
Empresa: {grupo.get('empresa', '')} ({grupo.get('sector') or 'sector sin dato'}). Contexto que dan los aprendices: "{contexto}".
Objetivo del proyecto al que asocian las fotos: {o['objetivo']} (competencia {o['competencia']}).
Describe de forma objetiva y en español lo que se observa en las {n_fotos or 'adjuntas'} fotos: equipos y herramientas, puestos de trabajo, flujo de materiales, inventarios en proceso, orden y aseo, señalización, elementos de seguridad, instrumentos de medición, documentos visibles.
Reglas: no concluyas cuál es el problema, no propongas soluciones, no inventes lo que no se ve. Si algo no se distingue, dilo. Usa viñetas cortas, agrupadas por foto ("Foto 1:", "Foto 2:"). Termina con una línea "Para confirmar en la visita:" con 2 o 3 cosas que convendría preguntar o medir."""
    return prompt


def texto_evidencias(evidencias, obj):
    sel = [e for e in evidencias if e["obj"] in (obj, 0)]
    partes = []
    for i, e in enumerate(sel, start=1):
        cab = f"[E{i}] ({'General' if e['obj'] == 0 else 'Objetivo ' + str(e['obj'])}, {e['tipo']}) {e['titulo']}"
        if e.get("fuente"):
            cab += f" | Fuente: {e['fuente']}"
        partes.append(cab + "\n" + ((e.get("descripcion") or "(solo archivos, sin descripción)")[:6000]))
    return "\n\n".join(partes)


def proponer_alternativas(grupo, obj, evidencias):
    return llamar_json(prompt_alternativas(grupo, obj, evidencias), esfuerzo="high")


def prompt_alternativas(grupo, obj, evidencias):
    o = OBJ[obj]
    prompt = f"""Eres un instructor experto en gestión de la producción que acompaña a aprendices principiantes de Tecnología en Gestión de la Producción Industrial (SENA, Colombia). Ellos visitaron su empresa proyecto y necesitan aprender a plantear un problema. Tu papel es proponer alternativas y hacer preguntas, no resolverles el trabajo.

EMPRESA: {grupo.get('empresa', '')}. Sector: {grupo.get('sector') or 'sin dato'}.
OBJETIVO DEL PROYECTO: {o['objetivo']}.
COMPETENCIA: {o['competencia']} ({o['codigo']}). Resultados de aprendizaje: {'; '.join(o['raps'])}.
TÉCNICAS DE LA COMPETENCIA: {'; '.join(o['evid'])}.

EVIDENCIAS CARGADAS POR LOS APRENDICES:
{texto_evidencias(evidencias, obj)}

TAREA: propone de 3 a 4 posibles situaciones problémicas para ESTE objetivo, cada una sustentada en evidencias concretas de la lista (cítalas como E1, E2…). Escríbelas como hipótesis por confirmar. Varía el enfoque entre alternativas. No des soluciones, no afirmes causas raíz y no inventes datos de la empresa. Si las evidencias no alcanzan, dilo en "advertencias" e indica qué recolectar.

Responde SOLO con JSON con esta forma:
{{"lectura_general":"2 o 3 frases sobre qué muestran las evidencias y qué falta",
 "alternativas":[{{"titulo":"frase corta","evidencias":["E1: qué se observó"],"por_que_podria_ser_problema":"efecto en productividad, costo, calidad, entrega o seguridad",
   "indicador":{{"nombre":"","formula":"","unidad":""}},"datos_que_faltan":["dato concreto y a quién pedirlo"],"preguntas_guia":["3 a 4 preguntas para que los aprendices analicen"],"tecnicas":["técnicas de la competencia que tendrían que aplicar"]}}],
 "advertencias":["vacíos importantes en la evidencia"]}}"""
    return prompt


def retroalimentar(obj, alternativa, analisis, evidencias):
    return llamar_json(prompt_retro(obj, alternativa, analisis, evidencias), esfuerzo="medium", max_tokens=8000)


def prompt_retro(obj, alternativa, analisis, evidencias):
    o = OBJ[obj]
    preguntas = alternativa.get("preguntas_guia") or []
    resp = analisis.get("respuestas") or []
    qa = "\n".join(f"- {q}\n  R: {resp[i] if i < len(resp) and resp[i] else '(sin responder)'}" for i, q in enumerate(preguntas))
    prompt = f"""Eres instructor de Gestión de la Producción Industrial (SENA). Da retroalimentación formativa a aprendices principiantes sobre cómo plantearon un problema de su empresa proyecto. No reescribas su texto ni les des la respuesta: señala fortalezas, vacíos y haz preguntas que los lleven a mejorar. Español claro y respetuoso.
Objetivo: {o['objetivo']}. Competencia: {o['competencia']}.
Alternativa elegida: {alternativa.get('titulo', '')}. Indicador sugerido: {(alternativa.get('indicador') or {}).get('nombre', '')}.
Evidencias disponibles:
{texto_evidencias(evidencias, obj)[:20000]}
Respuestas a preguntas guía:
{qa}
Planteamiento: {analisis.get('planteamiento', '')}
Causas a verificar: {analisis.get('causas', '')}
Indicador y medición: {analisis.get('indicador', '')}
Datos a recolectar: {analisis.get('datos', '')}
Evalúa con el criterio "Contexto y problema" de la rúbrica (nivel 1 a 4): 4 = situación real, cuantificada con 6 meses o más de datos y ligada al objetivo; 3 = clara y de la empresa con datos parciales; 2 = genérica o sin datos; 1 = sin problema definido.
Responde SOLO JSON: {{"nivel":1,"fortalezas":["…"],"a_mejorar":["…"],"preguntas":["…"],"listo_para_enviar":false}}"""
    return prompt


# ---------------------------------------------------------------- Presentación
def transcribir_imagenes(px, items, progreso=None, lote=6):
    """Transcribe tablas, gráficas y diagramas pegados como imagen. Devuelve ({diapositiva: texto}, fallidos)."""
    from .pptx_lector import a_jpeg

    out, fallidos = {}, 0
    lotes = [items[i:i + lote] for i in range(0, len(items), lote)]
    for k, bt in enumerate(lotes, start=1):
        if progreso:
            progreso(k, len(lotes))
        fotos, etiquetas = [], []
        for it in bt:
            try:
                fotos.append(a_jpeg(px["zip"].read(it["path"]), 1568, 85))
                etiquetas.append(it["slide"])
            except Exception:
                pass
        if not fotos:
            continue
        prompt = f"""Vas a recibir {len(fotos)} imágenes tomadas de una presentación de PowerPoint de un proyecto productivo (gestión de la producción industrial). Pertenecen, en este orden, a las diapositivas: {', '.join(map(str, etiquetas))}.
Para cada imagen transcribe con fidelidad lo que contiene, sin evaluar ni opinar:
- Textos: tal cual.
- Tablas: en formato | col | col |, con todas las filas, números y unidades exactamente como aparecen.
- Gráficas: tipo, ejes, series y los valores que se puedan leer.
- Diagramas (Ishikawa, flujo, layout, circuitos, Gantt, MRP): sus elementos y relaciones.
- Fotos: qué se ve en una o dos frases.
Si algo no se lee, escribe [ilegible]. No inventes valores.
Responde SOLO JSON: {{"imagenes":[{{"diapositiva":N,"contenido":"..."}}]}}"""
        try:
            r = llamar_json(prompt, imagenes=fotos, esfuerzo="low", max_tokens=12000)
            for j, im in enumerate(r.get("imagenes") or []):
                try:
                    n = int(im.get("diapositiva") or 0)
                except (TypeError, ValueError):
                    n = 0
                n = n or (etiquetas[j] if j < len(etiquetas) else 0)
                if n and im.get("contenido"):
                    out[n] = (out[n] + "\n" if n in out else "") + str(im["contenido"])
        except IAError:
            fallidos += 1
    return out, fallidos


NOTA_PDF = ("Si junto a estas instrucciones se adjuntó la presentación en PDF, úsala como fuente principal: lee en sus páginas las tablas, gráficas, diagramas y capturas pegados como imagen, y verifica los cálculos y la coherencia de las cifras entre diapositivas. El texto extraído que va abajo sirve para ubicar los números de diapositiva. Si no hay PDF y una diapositiva clave solo tiene imágenes, indícalo en alertas.")


def _nota_imagenes(transcripciones, fallidos, manual=False):
    if manual:
        return NOTA_PDF
    if transcripciones:
        t = ('Las imágenes de las diapositivas (tablas, gráficas, diagramas y capturas pegados como imagen) ya fueron transcritas y aparecen dentro de cada diapositiva como "[Contenido leído de las imágenes]". Trátalas como parte de la presentación. Verifica los cálculos y la coherencia de las cifras entre diapositivas.')
        if fallidos:
            t += f" Algunos lotes de imágenes no se pudieron leer ({fallidos}); indícalo en alertas si afecta la evaluación."
        return t
    return "No se leyeron las imágenes; si una diapositiva clave solo tiene imágenes, indícalo en alertas."


def _extension(stats):
    m = stats["minutos"]
    t = (f"TIEMPO DE EXPOSICIÓN: el grupo tiene {m} minutos para presentar. Como referencia, una diapositiva de contenido toma cerca de 1 minuto, así que lo razonable son unas {round(m * 0.8)} a {m} diapositivas incluyendo portada y conclusiones. La presentación tiene {stats['diapositivas']} diapositivas")
    if stats["densas"]:
        t += f" y estas tienen texto denso (más de 120 palabras, contando lo leído en imágenes): {', '.join(map(str, stats['densas']))}"
    return t + (".\nREGLA PARA TODAS LAS RECOMENDACIONES: no pidas agregar diapositivas. Si falta contenido, di qué reemplazar, fusionar o condensar para que quepa, o qué llevar a un anexo (Excel o documento) que se entrega pero no se expone.")


EXT_SCHEMA = """"problematicas_sugeridas":[{"obj":N,"situacion":"posible situación problémica concreta para un objetivo que la presentación no cubre o cubre en nivel 1 o 2, basada en lo que la presentación muestra de la empresa (no inventes datos)","sustento":"diapositiva o dato que la sugiere","encaje":"en cuál situación problémica existente o diapositiva se puede integrar sin alargar la presentación","indicador":"indicador para medirla","datos_que_faltan":["dato que deben pedir a la empresa"]}],
 "extension":{"adecuada":true,"diapositivas_recomendadas":12,"comentario":"1 o 2 frases sobre si cabe en el tiempo","condensar":[{"diapositivas":"4-7","sugerencia":"qué fusionar o resumir"}],"anexos":["contenido que conviene mover a anexos"]}"""


def _bitacora_texto(bitacora):
    """Resumen de los vistos buenos y análisis de la bitácora, para contrastar con la PPT."""
    if not bitacora:
        return "No hay registros de la bitácora."
    lineas = []
    for o in OBJ8:
        b = bitacora.get(o["n"]) or {}
        vb = b.get("visto_bueno")
        estado = "sin visto bueno"
        if vb:
            estado = ("VISTO BUENO" if vb["estado"] == "aprobado" else "CON AJUSTES PENDIENTES") + f" del instructor técnico ({vb.get('fecha', '')})"
            if vb.get("observaciones"):
                estado += f". Observaciones: {vb['observaciones'][:600]}"
        prob = b.get("problema")
        lineas.append(f"Objetivo {o['n']} ({o['corto']}): {estado}." + (f" Problema trabajado en la bitácora: {prob[:300]}" if prob else ""))
    return "\n".join(lineas)


def evaluar_avance(grupo, obj, px, transcripciones, fallidos, stats):
    return procesar_avance(llamar_json(prompt_avance(grupo, obj, px, transcripciones, fallidos, stats), esfuerzo="high"))


def prompt_avance(grupo, obj, px, transcripciones, fallidos, stats, manual=False):
    from .pptx_lector import texto_diapositivas

    o = OBJ[obj]
    evid = "; ".join(f"({i}) {e}" for i, e in enumerate(o["evid"], start=1))
    prompt = f"""Eres un instructor evaluador del programa Tecnología en Gestión de la Producción Industrial (SENA, Colombia). Evalúa la presentación de avance del proyecto productivo de un grupo de aprendices con la rúbrica unificada. Sé exigente y justo, y basa cada juicio en lo que aparece en las diapositivas, citando su número.

EMPRESA: {grupo.get('empresa', '')}.
OBJETIVO QUE SE REVISA: {obj}. {o['objetivo']}.
COMPETENCIA: {o['competencia']} ({o['codigo']}).
EVIDENCIAS MÍNIMAS ESPERADAS PARA ESTE OBJETIVO: {evid}.

RÚBRICA (nivel 4 a 1):
{rubrica_texto()}

{_nota_imagenes(transcripciones, fallidos, manual)}

{_extension(stats)}

CONTENIDO DE LA PRESENTACIÓN ({len(px['slides'])} diapositivas):
{texto_diapositivas(px, transcripciones, 140000)}

Responde SOLO JSON:
{{"criterios":[{{"id":"c1","nivel":3,"justificacion":"1 a 2 frases citando diapositivas"}}, …los 5…],
 "evidencias_encontradas":[{{"evidencia":"nombre de la evidencia mínima","diapositivas":"8, 9","calidad":"correcta|incompleta|con errores"}}],
 "evidencias_faltantes":["…"],
 "recomendaciones":["3 a 5 recomendaciones concretas y accionables para el grupo"],
 "oportunidades_mejora":["2 a 4 oportunidades de mejora del proyecto o de la propuesta de solución"],
 "alertas":["datos dudosos, cálculos que no cuadran, diapositivas solo con imágenes, contenido que no corresponde al objetivo"],
 {EXT_SCHEMA}}}
"problematicas_sugeridas" solo si este objetivo no aparece o su Aplicación técnica queda en nivel 1 o 2 (1 o 2 sugerencias); si no, deja la lista vacía."""
    return prompt


def procesar_avance(r):
    niveles = []
    just = []
    crit = {str(c.get("id")): c for c in (r.get("criterios") or [])}
    for c in RUBRICA:
        x = crit.get(c["id"], {})
        niveles.append(_nivel(x.get("nivel")))
        just.append(x.get("justificacion", ""))
    r["niveles"] = niveles
    r["justificaciones"] = just
    return r


def evaluar_final(grupo, px, transcripciones, fallidos, stats, bitacora):
    return procesar_final(llamar_json(prompt_final(grupo, px, transcripciones, fallidos, stats, bitacora), esfuerzo="high", max_tokens=24000))


def prompt_final(grupo, px, transcripciones, fallidos, stats, bitacora, manual=False):
    from .pptx_lector import texto_diapositivas

    objs = "\n".join(f"Objetivo {o['n']} ({o['competencia']}): {o['objetivo']}. Evidencias: {'; '.join(o['evid'])}." for o in OBJ8)
    prompt = f"""Eres un instructor evaluador del programa Tecnología en Gestión de la Producción Industrial (SENA, Colombia). Evalúa la PRESENTACIÓN FINAL del proyecto productivo de un grupo. La presentación debe desarrollar los 8 objetivos específicos a través de las propuestas de solución a las situaciones problémicas. Evalúa cada objetivo por separado con la misma rúbrica, basando cada juicio en lo que aparece en las diapositivas y citando su número. Si un objetivo no aparece, califícalo con nivel 1 en todos los criterios y dilo.

EMPRESA: {grupo.get('empresa', '')}.
OBJETIVOS Y EVIDENCIAS MÍNIMAS:
{objs}

RÚBRICA (nivel 4 a 1):
{rubrica_texto()}

BITÁCORA DEL GRUPO (vistos buenos y observaciones de los instructores técnicos de cada competencia). Úsala para verificar que la presentación recoja lo aprobado y atienda las observaciones; si una observación no se atendió, dilo en el objetivo y en alertas:
{_bitacora_texto(bitacora)}

{_nota_imagenes(transcripciones, fallidos, manual)}

{_extension(stats)}

CONTENIDO ({len(px['slides'])} diapositivas):
{texto_diapositivas(px, transcripciones, 160000)}

Responde SOLO JSON. Justificaciones de máximo 25 palabras.
{{"objetivos":[{{"obj":1,"diapositivas":"10-14","niveles":{{"c1":3,"c2":2,"c3":3,"c4":2,"c5":3}},"justificacion":"por qué esos niveles, citando diapositivas","faltantes":["evidencias mínimas que no aparecen"],"recomendaciones":["1 o 2 acciones concretas"]}}, …los 8…],
 "recomendaciones_generales":["3 a 5 recomendaciones para todo el proyecto"],
 "oportunidades_mejora":["3 a 5 oportunidades de mejora del proyecto y de sus propuestas de solución, para la empresa"],
 "alertas":["datos dudosos, cálculos que no cuadran, objetivos ausentes, observaciones de instructores no atendidas, diapositivas solo con imágenes"],
 {EXT_SCHEMA}}}
En "problematicas_sugeridas" incluye 1 o 2 por cada objetivo ausente o con Aplicación técnica en nivel 1 o 2."""
    return prompt


def procesar_final(r):
    por_obj = {}
    for x in r.get("objetivos") or []:
        try:
            por_obj[int(x.get("obj"))] = x
        except (TypeError, ValueError):
            pass
    objetivos = []
    for o in OBJ8:
        x = por_obj.get(o["n"], {})
        nv = x.get("niveles") or {}
        niveles = [_nivel(nv.get(c["id"])) for c in RUBRICA]
        objetivos.append({
            "obj": o["n"], "diapositivas": str(x.get("diapositivas") or ""), "niveles": niveles,
            "justificacion": x.get("justificacion") or "No se encontró en la presentación.",
            "faltantes": x.get("faltantes") or [], "recomendaciones": x.get("recomendaciones") or [],
        })
    r["objetivos"] = objetivos
    return r


def _nivel(v):
    try:
        return min(4, max(1, int(v)))
    except (TypeError, ValueError):
        return 1


def para_claude_ai(prompt: str) -> str:
    """Instrucciones listas para pegar en claude.ai (modo sin clave de API)."""
    return prompt + "\n\nEntrega la respuesta completa como un único bloque de código JSON, sin texto adicional."
