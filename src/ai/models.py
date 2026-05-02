from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class RubricItem:
    criterion: str
    points: float


@dataclass
class ReferenceAnswer:
    question: str
    subject: str
    education_level: str
    expected_answer_type: str
    ideal_answer: str
    # List[Dict[str, Any]] at runtime: each dict has "concept" (str) and "weight" (float),
    # as consumed by SemanticGrader.concept_match_score(). Legacy generators may
    # populate this with plain strings — those paths are not used by reference_db.
    key_concepts: List[Any] = field(default_factory=list)
    rubric: List[RubricItem] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    confidence: float = 0.0
