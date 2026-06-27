import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Set

from ai.models import ReferenceAnswer


# Marcadores de negación para el análisis de polaridad. Lista deliberadamente
# CONSERVADORA: el peor error de un corrector es castigar una respuesta correcta,
# así que solo incluimos negadores inequívocos y dejamos fuera "sin" (p.ej. "sin
# duda", "sin embargo") y cuantificadores ambiguos.
_NEGATION_TOKENS = {"no", "ni", "nunca", "tampoco", "jamas",
                    "ningun", "ninguna", "ninguno", "ningunos", "ningunas"}
# "no" seguido de estas palabras NO es una negación, sino una unidad léxica:
#  - "no solo / solamente / únicamente ... sino" es enfático;
#  - "no metales / no metal / no metálico" es un término químico (los no metales).
_NO_EXCEPTIONS = {
    "solo", "solamente", "unicamente",
    "metales", "metal", "metalico", "metalica", "metalicos", "metalicas",
}
_NEGATION_PHRASES = ("en lugar de", "en vez de", "lejos de")
# Conjunciones/puntuación que cierran una cláusula a efectos del alcance de la negación.
_CLAUSE_SPLIT_RE = re.compile(
    r"[.,;:!?\n]+|\bpero\b|\baunque\b|\bsino\b|\bmientras\b|\bporque\b"
)

# Palabras vacías que se ignoran al comparar los SINÓNIMOS por concepto, para que
# una variante ("el último que entra es el primero en salir") empareje aunque el
# alumno cambie los conectores. No afecta a la detección del concepto principal.
_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "en",
    "y", "o", "u", "a", "al", "que", "se", "su", "sus", "es", "lo", "por",
    "con", "para", "e", "como", "más", "mas",
}


class SemanticGrader:
    def __init__(self):
        self.synonym_map = {
            "producir": ["genera", "producir", "produce", "fabricar", "obtiene"],
            "energia": ["energía", "energia", "energetica", "energética", "energetico", "energético"],
            "celula": ["célula", "celula", "celular"],
            "respiracion celular": ["respiración celular", "respiracion celular"],
            "atp": ["atp"],
            "mitocondria": ["mitocondria", "mitocondrias"],
        }

    def normalize_text(self, text: str) -> str:
        text = text.lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def tokenize(self, text: str) -> List[str]:
        return self.normalize_text(text).split()

    def expand_with_synonyms(self, tokens: List[str]) -> Set[str]:
        expanded = set(tokens)

        for canonical, variants in self.synonym_map.items():
            group = {self.normalize_text(canonical)}
            for variant in variants:
                group.add(self.normalize_text(variant))

            if group & expanded:
                expanded |= group

        return expanded

    def split_clauses(self, text: str) -> List[List[str]]:
        """
        Divide la respuesta en cláusulas (por puntuación y conjunciones) y
        devuelve cada una como lista de tokens normalizados. El alcance de una
        negación se limita a su cláusula, para no propagarla a frases vecinas.
        """
        normed = self.normalize_text(text)  # sin acentos ni puntuación útil
        # Re-troceamos sobre el texto con puntuación: normalizamos solo
        # acentos/minúsculas y partimos antes de eliminar los separadores.
        lowered = text.lower()
        lowered = unicodedata.normalize("NFD", lowered)
        lowered = "".join(ch for ch in lowered if unicodedata.category(ch) != "Mn")
        clauses = []
        for part in _CLAUSE_SPLIT_RE.split(lowered):
            cleaned = re.sub(r"[^a-z0-9\s]", " ", part)
            toks = re.sub(r"\s+", " ", cleaned).strip().split()
            if toks:
                clauses.append(toks)
        return clauses or [normed.split()]

    def _negation_before(self, tokens: List[str], pos: int) -> bool:
        """¿Hay un negador en la cláusula, antes de la posición `pos`?"""
        window = tokens[:pos]
        for j, w in enumerate(window):
            if w in _NEGATION_TOKENS:
                if w == "no" and j + 1 < len(window) and window[j + 1] in _NO_EXCEPTIONS:
                    continue  # "no solo ... sino" es enfático, no negación
                return True
        joined = " ".join(window)
        return any(ph in joined for ph in _NEGATION_PHRASES)

    def concept_polarity(self, concept_norm: str, clauses: List[List[str]]) -> str:
        """
        'affirmed' / 'negated' / 'absent' según cómo aparezca el concepto en las
        cláusulas. Si aparece afirmado en alguna, prevalece la afirmación
        (damos el beneficio de la duda al alumno).
        """
        ctoks = concept_norm.split()
        n = len(ctoks)
        affirmed = negated = False
        for toks in clauses:
            pos = None
            for i in range(len(toks) - n + 1):
                if toks[i:i + n] == ctoks:
                    pos = i
                    break
            if pos is None:
                continue
            if self._negation_before(toks, pos):
                negated = True
            else:
                affirmed = True
        if affirmed:
            return "affirmed"
        if negated:
            return "negated"
        return "absent"

    def phrase_polarity(self, phrase_norm: str, clauses: List[List[str]]) -> str:
        """
        Como `concept_polarity` pero para una paráfrasis (sinónimo): localiza sus
        tokens de contenido en cada cláusula con tolerancia morfológica y mira si
        van precedidos de una negación. Necesario porque un sinónimo casa de forma
        difusa (p.ej. "etiqueta"≈"etiquetas") y el alumno puede negarlo
        ("aprende sin ningún dato ni etiqueta").
        """
        content = [t for t in phrase_norm.split() if t not in _STOPWORDS]
        if not content:
            return "absent"

        def fuzzy_in(tok: str, target: str) -> bool:
            return tok == target or SequenceMatcher(None, tok, target).ratio() >= 0.80

        affirmed = negated = False
        for toks in clauses:
            pos = None
            present = 0
            for i, w in enumerate(toks):
                if any(fuzzy_in(c, w) for c in content):
                    present += 1
                    if pos is None:
                        pos = i
            if pos is None or present < max(1, len(content) // 2):
                continue
            if self._negation_before(toks, pos):
                negated = True
            else:
                affirmed = True
        if affirmed:
            return "affirmed"
        if negated:
            return "negated"
        return "absent"

    def synonym_matches(self, synonym: str, student_norm: str,
                        student_tokens: List[str]) -> bool:
        """
        ¿Aparece en la respuesta una variante/paráfrasis declarada por el profesor?

        Empareja si el sinónimo normalizado es subcadena exacta, o si TODOS sus
        tokens de contenido (sin palabras vacías) están presentes en la respuesta
        con tolerancia morfológica (mismo umbral fuzzy 0.80 que el resto del
        grader, p.ej. "metes"≈"meter"). Exigir todos los tokens de contenido lo
        hace estricto: difícil casarlo por azar.
        """
        syn_norm = self.normalize_text(synonym)
        if not syn_norm:
            return False
        if syn_norm in student_norm:
            return True
        content = [t for t in syn_norm.split() if t not in _STOPWORDS]
        if not content:
            return False
        for ct in content:
            if not any(
                ct == st or SequenceMatcher(None, ct, st).ratio() >= 0.80
                for st in student_tokens
            ):
                return False
        return True

    def concept_match_score(self, student_answer: str, key_concepts: List[Dict]) -> Dict:
        student_norm = self.normalize_text(student_answer)
        student_tokens = self.tokenize(student_answer)
        expanded_tokens = self.expand_with_synonyms(student_tokens)
        clauses = self.split_clauses(student_answer)

        detected = []
        partial = []
        missing = []
        negated = []

        for concept_data in key_concepts:
            concept = concept_data["concept"]
            weight = concept_data["weight"]
            synonyms = concept_data.get("synonyms") or []

            concept_norm = self.normalize_text(concept)
            concept_tokens = concept_norm.split()

            # Coincidencia exacta del concepto completo o por tokens presentes.
            exact = concept_norm in student_norm
            by_tokens = all(token in expanded_tokens for token in concept_tokens)
            if exact or by_tokens:
                # Antes de contarlo, comprobamos la POLARIDAD: si el alumno niega
                # el concepto ("la mitocondria NO produce ATP"), no se acredita.
                if self.concept_polarity(concept_norm, clauses) == "negated":
                    negated.append((concept, weight))
                else:
                    detected.append((concept, weight))
                continue

            # Sinónimos/paráfrasis declarados por el profesor para ESTE concepto.
            # Acreditan el concepto aunque el alumno no use el término exacto
            # ("último en entrar primero en salir" cuenta como "LIFO").
            syn_hit = next(
                (s for s in synonyms
                 if self.synonym_matches(s, student_norm, student_tokens)),
                None,
            )
            if syn_hit is not None:
                if self.phrase_polarity(self.normalize_text(syn_hit), clauses) == "negated":
                    negated.append((concept, weight))
                else:
                    detected.append((concept, weight))
                continue

            # Coincidencia parcial aproximada
            best_similarity = 0.0
            for token in student_tokens:
                for ctoken in concept_tokens:
                    sim = SequenceMatcher(None, token, ctoken).ratio()
                    best_similarity = max(best_similarity, sim)

            if best_similarity >= 0.80:
                partial.append((concept, weight))
            else:
                missing.append((concept, weight))

        exact_score = sum(weight for _, weight in detected)
        partial_score = sum(weight * 0.5 for _, weight in partial)
        total_score = exact_score + partial_score
        max_score = sum(item["weight"] for item in key_concepts)

        return {
            "detected": detected,
            "partial": partial,
            "missing": missing,
            "negated": negated,
            "raw_score": total_score,
            "max_score": max_score,
        }

    def cosine_similarity(self, text1: str, text2: str) -> float:
        tokens1 = self.tokenize(text1)
        tokens2 = self.tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        counter1 = Counter(tokens1)
        counter2 = Counter(tokens2)

        vocab = set(counter1.keys()) | set(counter2.keys())

        dot_product = sum(counter1[word] * counter2[word] for word in vocab)
        norm1 = math.sqrt(sum(counter1[word] ** 2 for word in vocab))
        norm2 = math.sqrt(sum(counter2[word] ** 2 for word in vocab))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def length_factor(self, student_answer: str, ideal_answer: str) -> float:
        len_student = len(self.tokenize(student_answer))
        len_ideal = len(self.tokenize(ideal_answer))

        if len_ideal == 0:
            return 1.0

        ratio = len_student / len_ideal

        if ratio >= 0.6:
            return 1.0
        if ratio >= 0.4:
            return 0.9
        if ratio >= 0.2:
            return 0.8
        return 0.7

    def grade(self, student_answer: str, reference: ReferenceAnswer) -> Dict:
        concept_result = self.concept_match_score(student_answer, reference.key_concepts)

        concept_ratio = (
            concept_result["raw_score"] / concept_result["max_score"]
            if concept_result["max_score"] > 0
            else 0.0
        )

        similarity = self.cosine_similarity(student_answer, reference.ideal_answer)
        length_penalty = self.length_factor(student_answer, reference.ideal_answer)

        final_ratio = (
            0.95 * concept_ratio +
            0.05 * similarity
        ) * length_penalty

        # Si los conceptos esenciales/comunes están razonablemente cubiertos,
        # evitamos suspensos absurdos por brevedad
        if concept_ratio >= 0.6:
            min_floor = 0.6
        else:
            min_floor = 0.0

        final_ratio = max(final_ratio, min_floor)
        final_ratio = max(0.0, min(final_ratio, 1.0))

        # Bonus por términos técnicos (opcional, p.ej. Filosofía). Aditivo sobre
        # el ratio, capeado a 1.0 para no romper la escala 0-10.
        bonus_hits = []
        student_norm = self.normalize_text(student_answer)
        for bt in getattr(reference, "bonus_terms", []) or []:
            term = str(bt.get("term", "")).strip()
            weight = float(bt.get("weight", 0.0))
            if not term:
                continue
            if self.normalize_text(term) in student_norm:
                bonus_hits.append({"term": term, "weight": weight})
        if bonus_hits:
            final_ratio = min(final_ratio + sum(b["weight"] for b in bonus_hits), 1.0)

        score_over_10 = round(final_ratio * 10, 2)

        detected_concepts = [concept for concept, _ in concept_result["detected"]]
        partial_concepts = [concept for concept, _ in concept_result["partial"]]
        missing_concepts = [concept for concept, _ in concept_result["missing"]]
        negated_concepts = [concept for concept, _ in concept_result["negated"]]

        if score_over_10 >= 8:
            feedback = "La respuesta es correcta y recoge la mayor parte de los conceptos esperados."
        elif score_over_10 >= 5:
            feedback = "La respuesta es parcialmente correcta, pero faltan algunos elementos importantes."
        else:
            feedback = "La respuesta es insuficiente o demasiado incompleta respecto a la referencia esperada."

        if negated_concepts:
            feedback += (
                " Atención: la respuesta NIEGA o atribuye erróneamente "
                + ", ".join(negated_concepts)
                + "; esos conceptos no se han acreditado."
            )

        return {
            "student_answer": student_answer,
            "score_over_10": score_over_10,
            "detected_concepts": detected_concepts,
            "partial_concepts": partial_concepts,
            "missing_concepts": missing_concepts,
            "negated_concepts": negated_concepts,
            "concept_ratio": round(concept_ratio, 3),
            "similarity_ratio": round(similarity, 3),
            "length_penalty": round(length_penalty, 3),
            "bonus_hits": bonus_hits,
            "feedback": feedback,
        }