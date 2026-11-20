"""Objetivos/competencias del proyecto productivo GPI y rúbrica unificada."""
import json
from pathlib import Path

_d = json.loads((Path(__file__).parent / "catalogo.json").read_text(encoding="utf-8"))
RUBRICA = _d["rubrica"]          # [{id, nombre, peso, n:[nivel1..nivel4]}]
OBJ = _d["objetivos"]            # índice 0 = General, 1..8 = objetivos
OBJ8 = [o for o in OBJ if o["n"] > 0]


def etiqueta(n: int) -> str:
    o = OBJ[n]
    return "General (contexto de la empresa)" if n == 0 else f"{n}. {o['corto']} · {o['competencia']}"


def nota(niveles) -> float:
    s = sum(c["peso"] * (niveles[i] if i < len(niveles) and niveles[i] else 1) for i, c in enumerate(RUBRICA))
    return round(1 + (4 / 3) * (s - 1), 1)


def aprueba(niveles) -> bool:
    return nota(niveles) >= 3.5 and not any((x or 1) <= 1 for x in niveles)


def nota_final(objetivos) -> float:
    return round(sum(nota(o["niveles"]) for o in objetivos) / len(objetivos), 1) if objetivos else 1.0


def aprueba_final(objetivos) -> bool:
    return nota_final(objetivos) >= 3.5 and all(aprueba(o["niveles"]) for o in objetivos)


def rubrica_texto() -> str:
    return "\n".join(
        f"{c['id']} {c['nombre']} ({round(c['peso'] * 100)}%): 4={c['n'][3]}; 3={c['n'][2]}; 2={c['n'][1]}; 1={c['n'][0]}"
        for c in RUBRICA
    )
