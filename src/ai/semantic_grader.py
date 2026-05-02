import math
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from typing import Dict, List, Set

from ai.models import ReferenceAnswer


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

    def concept_match_score(self, student_answer: str, key_concepts: List[Dict]) -> Dict:
        student_norm = self.normalize_text(student_answer)
        student_tokens = self.tokenize(student_answer)
        expanded_tokens = self.expand_with_synonyms(student_tokens)

        detected = []
        partial = []
        missing = []

        for concept_data in key_concepts:
            concept = concept_data["concept"]
            weight = concept_data["weight"]

            concept_norm = self.normalize_text(concept)

            # Coincidencia exacta del concepto completo
            if concept_norm in student_norm:
                detected.append((concept, weight))
                continue

            concept_tokens = concept_norm.split()

            # Coincidencia por tokens presentes
            if all(token in expanded_tokens for token in concept_tokens):
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

        score_over_10 = round(final_ratio * 10, 2)

        detected_concepts = [concept for concept, _ in concept_result["detected"]]
        partial_concepts = [concept for concept, _ in concept_result["partial"]]
        missing_concepts = [concept for concept, _ in concept_result["missing"]]

        if score_over_10 >= 8:
            feedback = "La respuesta es correcta y recoge la mayor parte de los conceptos esperados."
        elif score_over_10 >= 5:
            feedback = "La respuesta es parcialmente correcta, pero faltan algunos elementos importantes."
        else:
            feedback = "La respuesta es insuficiente o demasiado incompleta respecto a la referencia esperada."

        return {
            "student_answer": student_answer,
            "score_over_10": score_over_10,
            "detected_concepts": detected_concepts,
            "partial_concepts": partial_concepts,
            "missing_concepts": missing_concepts,
            "concept_ratio": round(concept_ratio, 3),
            "similarity_ratio": round(similarity, 3),
            "length_penalty": round(length_penalty, 3),
            "feedback": feedback,
        }