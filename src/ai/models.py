from dataclasses import dataclass, field
from typing import List


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
    key_concepts: List[str] = field(default_factory=list)
    rubric: List[RubricItem] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    confidence: float = 0.0