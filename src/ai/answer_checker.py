"""
answer_checker.py — Corrector DETERMINISTA de respuestas numéricas/simbólicas
para Matemáticas y Física.

A diferencia del SemanticGrader (que mide presencia de conceptos), aquí lo que
importa es si el RESULTADO es correcto:

  - Matemáticas: se extrae la respuesta final del alumno y se compara con la
    solución por equivalencia matemática (no textual) con SymPy. Así
    "x = -3", "x=-6/2" y "x = -3.0" se consideran iguales, y se detecta cuando
    la conclusión es errónea aunque aparezcan los símbolos correctos.
  - Física: se compara VALOR + UNIDAD. El valor admite una tolerancia relativa
    (redondeos) y la unidad se normaliza para equiparar variantes (m/s ≡ m·s⁻¹).

Es interpretable (se ve qué se ha extraído y por qué) y no usa LLM.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import sympy
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations, implicit_multiplication_application,
)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


# ── Utilidades de parseo ─────────────────────────────────────────────────────

def _clean_math(text: str) -> str:
    """Normaliza un fragmento matemático para SymPy."""
    t = text.strip()
    t = t.replace("−", "-").replace("·", "*").replace("×", "*")
    t = t.replace("^", "**")
    t = t.replace(",", ".")          # coma decimal española
    t = re.sub(r"\s+", " ", t).strip(" .")
    return t


def _rhs(expr_text: str) -> str:
    """Si hay 'algo = valor', se queda con la parte derecha (la respuesta)."""
    if "=" in expr_text:
        return expr_text.rsplit("=", 1)[1]
    return expr_text


def _to_expr(text: str) -> Optional[sympy.Expr]:
    try:
        return parse_expr(_clean_math(text), transformations=_TRANSFORMS, evaluate=True)
    except Exception:
        return None


def _extract_candidates(student_text: str) -> List[str]:
    """
    Saca de la respuesta del alumno los posibles 'resultados finales':
    cualquier 'x = ...' / '= ...' y, como respaldo, el último número suelto.
    Se devuelven de la última a la primera aparición (la conclusión suele ir al final).
    """
    cands: List[str] = []
    # patrones tipo "x = -3", "resultado = 5/2", "= 9.8"
    for m in re.finditer(r"=\s*([\-+]?[\d\.,/\*\^\(\)a-zA-Z\s]+)", student_text):
        frag = m.group(1).strip()
        # cortar en conectores típicos ("x=-3 porque...", "x = 2, y = 3")
        frag = re.split(r"[;\n]|porque|luego|pero|entonces", frag)[0].strip(" .")
        if frag:
            cands.append(frag)
    # respaldo: último número
    nums = re.findall(r"[\-+]?\d+(?:[\.,]\d+)?", student_text)
    if nums:
        cands.append(nums[-1])
    # de más reciente (final del texto) a más antiguo, sin duplicados
    seen, ordered = set(), []
    for c in reversed(cands):
        if c not in seen:
            seen.add(c); ordered.append(c)
    return ordered


# ── Matemáticas ──────────────────────────────────────────────────────────────

def _expr_equal(a: sympy.Expr, b: sympy.Expr) -> bool:
    try:
        diff = sympy.simplify(a - b)
        return diff == 0 or sympy.nsimplify(diff) == 0
    except Exception:
        try:
            return abs(float(a) - float(b)) < 1e-9
        except Exception:
            return False


def check_math(student_answer: str, expected: str) -> Dict[str, Any]:
    """
    Compara el resultado del alumno con `expected` por equivalencia matemática.
    `expected` puede ser "x = -3", "-3", "5/2" o varias soluciones "2, -2".
    """
    expected_parts = [p for p in re.split(r"[,;]| y ", _rhs(expected)) if p.strip()]
    expected_exprs = [e for e in (_to_expr(p) for p in expected_parts) if e is not None]
    if not expected_exprs:
        return {"correct": False, "extracted": None, "expected": expected,
                "method": "math", "detail": "No se pudo interpretar la solución esperada."}

    candidates = _extract_candidates(student_answer)
    for cand in candidates:
        ce = _to_expr(cand)
        if ce is None:
            continue
        if any(_expr_equal(ce, ee) for ee in expected_exprs):
            return {"correct": True, "extracted": cand, "expected": expected,
                    "method": "math", "detail": f"'{cand}' es matemáticamente equivalente a la solución."}

    return {"correct": False, "extracted": candidates[0] if candidates else None,
            "expected": expected, "method": "math",
            "detail": "El resultado final no coincide con la solución esperada."}


# ── Física (valor + unidad) ──────────────────────────────────────────────────

# Normalización ligera de unidades (sin dependencia pesada tipo pint).
_UNIT_CANON = {
    "metros": "m", "metro": "m", "segundos": "s", "segundo": "s",
    "newton": "n", "newtons": "n", "julios": "j", "julio": "j", "joule": "j",
    "·": "", "*": "", " ": "", "⁻": "-", "metro/segundo": "m/s",
}


def _canon_unit(unit: str) -> str:
    u = unit.strip().lower()
    for k, v in _UNIT_CANON.items():
        u = u.replace(k, v)
    u = u.replace("**", "^")
    # m/s2 ≡ m/s^2 ; quitar separadores
    u = re.sub(r"(?<=[a-z])(\d)", r"^\1", u)   # s2 -> s^2
    u = u.replace("^^", "^")
    return u


def _split_value_unit(text: str):
    """Extrae (valor_float, unidad) del primer 'número + unidad' del texto."""
    m = re.search(r"([\-+]?\d+(?:[\.,]\d+)?)\s*([a-zA-Zµ°/\^\d\s·\*⁻]*)", text)
    if not m:
        return None, ""
    value = float(m.group(1).replace(",", "."))
    unit = m.group(2).strip()
    # recortar palabras que no son unidad
    unit = re.split(r"\b(porque|ya|que|pues|y|con)\b", unit)[0].strip()
    return value, unit


def check_physics(student_answer: str, expected: str, rel_tol: float = 0.05) -> Dict[str, Any]:
    """
    Compara el resultado físico (valor + unidad). El valor admite tolerancia
    relativa `rel_tol` (5% por defecto, para redondeos).
    """
    exp_val, exp_unit = _split_value_unit(expected)
    if exp_val is None:
        return {"correct": False, "extracted": None, "expected": expected,
                "method": "physics", "detail": "No se pudo interpretar la solución esperada."}

    denom = abs(exp_val) if exp_val != 0 else 1.0

    def value_ok(v: float) -> bool:
        return abs(v - exp_val) / denom <= rel_tol

    def unit_ok(u: str) -> bool:
        return (not exp_unit) or (bool(u) and _canon_unit(u) == _canon_unit(exp_unit))

    # Parseamos los candidatos (de más final a más inicial) + el texto completo.
    parsed = []
    for cand in _extract_candidates(student_answer) + [student_answer]:
        v, u = _split_value_unit(cand)
        if v is not None:
            parsed.append((v, u))

    # La respuesta final suele llevar UNIDAD; priorizamos esos candidatos para no
    # confundir una constante citada en el procedimiento (p.ej. g=9.8) con el
    # resultado. Un acierto pleno en cualquier posición gana siempre.
    with_unit = [(v, u) for v, u in parsed if u]
    for v, u in with_unit:
        if value_ok(v) and unit_ok(u):
            return {"correct": True, "extracted": f"{v} {u}".strip(), "expected": expected,
                    "method": "physics", "value_ok": True, "unit_ok": True,
                    "detail": "Valor y unidad correctos (dentro de la tolerancia)."}

    if with_unit:
        # No hay acierto pleno: manda el candidato con unidad MÁS FINAL.
        v, u = with_unit[0]
        if value_ok(v):
            return {"correct": False, "extracted": f"{v} {u}".strip(), "expected": expected,
                    "method": "physics", "value_ok": True, "unit_ok": False,
                    "detail": f"Valor correcto pero la unidad ('{u}') no coincide con '{exp_unit}'."}
        return {"correct": False, "extracted": f"{v} {u}".strip(), "expected": expected,
                "method": "physics", "value_ok": False, "unit_ok": False,
                "detail": "El valor no coincide con la solución esperada."}

    # Ningún candidato con unidad: valoramos solo el número (unidad ausente).
    for v, _u in parsed:
        if value_ok(v):
            if not exp_unit:
                return {"correct": True, "extracted": str(v), "expected": expected,
                        "method": "physics", "value_ok": True, "unit_ok": True,
                        "detail": "Valor correcto."}
            return {"correct": False, "extracted": str(v), "expected": expected,
                    "method": "physics", "value_ok": True, "unit_ok": False,
                    "detail": "Valor correcto pero falta la unidad."}

    return {"correct": False, "extracted": None, "expected": expected,
            "method": "physics", "value_ok": False, "unit_ok": False,
            "detail": "El valor no coincide con la solución esperada."}


# ── Entrada unificada → nota 0-10 ────────────────────────────────────────────

def grade_numeric(student_answer: str, expected: str, kind: str = "math",
                  rel_tol: float = 0.05) -> Dict[str, Any]:
    """
    Devuelve un veredicto con nota 0-10:
      - correcto                       → 10
      - física: valor ok, unidad mal   → 6  (crédito parcial)
      - incorrecto / en blanco         → 0

    El crédito por 'procedimiento bien aunque el número falle' lo da, si se
    quiere, la segunda opinión del LLM (grade_steps). Aquí solo cuenta el
    resultado, de forma interpretable.
    """
    if not student_answer.strip():
        return {"score_over_10": 0.0, "correct": False, "extracted": None,
                "expected": expected, "method": kind, "detail": "Respuesta en blanco."}

    res = check_physics(student_answer, expected, rel_tol) if kind == "physics" \
        else check_math(student_answer, expected)

    if res.get("correct"):
        score = 10.0
    elif res.get("value_ok") and not res.get("unit_ok"):
        score = 6.0
    else:
        score = 0.0
    res["score_over_10"] = score
    return res
