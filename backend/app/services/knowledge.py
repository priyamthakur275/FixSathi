"""Small text helpers shared by retrieval code."""
import math, re

WORD = re.compile(r'[a-z0-9]+')
STOP = {'the', 'a', 'is', 'it', 'and', 'or', 'of', 'to', 'in', 'my', 'not', 'on', 'with', 'hai', 'nahi', 'ka', 'ki', 'raha', 'rahi'}


def tokens(t: str) -> set[str]:
    return {w for w in WORD.findall(t.lower()) if w not in STOP and len(w) > 1}


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b)); na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
