import re
from typing import Dict, List

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you",
    "our", "are", "will", "have", "has", "into", "their", "they", "about",
    "role", "work", "team", "using", "use", "job", "company"
}


def _terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[A-Za-z][A-Za-z+#.-]{3,}", text.lower())
        if token not in STOPWORDS
    }


def _score(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


def _tone_score(letter: str, tone: str) -> float:
    lower = letter.lower()
    sentences = [s.strip() for s in re.split(r"[.!?]+", letter) if s.strip()]
    if not sentences:
        return 0.0

    score = 0.5
    if 4 <= len(sentences) <= 12:
        score += 0.2
    if "dear hiring manager" in lower:
        score += 0.1
    if "sincerely" in lower or "best regards" in lower:
        score += 0.1
    if tone == "Concise" and len(letter.split()) <= 300:
        score += 0.1
    if tone == "Professional" and any(word in lower for word in ("experience", "contribute", "opportunity")):
        score += 0.1
    return _score(score)


def evaluate_letter(
    resume: str,
    job_description: str,
    letter: str,
    company: str,
    role: str,
    tone: str = "Professional",
) -> Dict:
    resume_terms = _terms(resume)
    jd_terms = _terms(job_description)
    letter_terms = _terms(letter)

    relevant_terms = jd_terms & letter_terms
    resume_overlap = resume_terms & letter_terms
    unsupported = sorted(letter_terms - resume_terms)

    relevance = _score(len(relevant_terms) / max(min(len(jd_terms), 20), 1))
    grounding = _score(len(resume_overlap) / max(len(letter_terms), 1))

    required = [
        bool(company.strip()) and company.lower() in letter.lower(),
        bool(role.strip()) and role.lower() in letter.lower(),
        "dear " in letter.lower(),
        "sincerely" in letter.lower() or "best regards" in letter.lower(),
        150 <= len(letter.split()) <= 450,
    ]
    completeness = _score(sum(required) / len(required))

    return {
        "scores": {
            "relevance": relevance,
            "completeness": completeness,
            "tone": _tone_score(letter, tone),
            "groundedness": grounding,
        },
        "word_count": len(letter.split()),
        "matched_jd_terms": sorted(relevant_terms)[:20],
        "resume_term_overlap": len(resume_overlap),
        "unsupported_terms": unsupported[:30],
        "unsupported_term_count": len(unsupported),
        "method": "deterministic-baseline",
    }
