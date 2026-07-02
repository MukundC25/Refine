"""Rule-based pre-scorer for Stage 1 of the ranking pipeline.

Scores every candidate against a ParsedJD using only structured fields —
no ML, no embeddings, no network calls. Designed to run across 100K
candidates in under 30 seconds on CPU.

Dimensions:
    experience_score  0–30  YoE vs JD range
    title_score       0–20  keyword match on current + most-recent title
    skills_score      0–25  required (×20) + preferred (×5) coverage
    industry_score    0–15  product-company ratio
    disqualifier      0 or –50  non-technical keyword-stuffer check
    total             capped at 0 minimum
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.app.core.candidate_loader import CandidateRecord
    from backend.app.core.jd_parser import ParsedJD


_OUTSOURCING_FIRMS: frozenset[str] = frozenset({
    "tcs", "tata consultancy", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis",
    "hexaware", "mastek", "niit technologies", "birlasoft",
    "ltimindtree", "lti", "mindtree", "coforge", "persistent",
    "zensar", "cyient", "kpit", "sasken", "sonata software",
})

_TECHNICAL_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "engineer", "developer", "scientist", "researcher", "architect",
    "data", "ml", "ai", "machine learning", "nlp", "search",
    "analytics", "devops", "sre", "platform", "backend", "frontend",
    "fullstack", "full stack", "software", "cloud", "infra",
    "infrastructure", "mlops", "quantitative", "computer vision",
})

_AI_ML_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "ai engineer", "ml engineer", "machine learning engineer",
    "ai/ml", "nlp engineer", "search engineer", "data scientist",
    "applied scientist", "research engineer", "applied ml",
    "computer vision engineer", "deep learning engineer",
    "senior ai", "senior ml", "principal ai", "staff ai",
    "staff ml", "principal ml",
})

_SENIOR_MARKERS: frozenset[str] = frozenset({
    "senior", "sr.", "lead", "principal", "staff", "head of",
    "director", "manager", "architect", "chief",
})

_NON_TECHNICAL_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "marketing", "sales", "hr", "human resource", "recruiter",
    "accountant", "accounting", "finance manager", "operations manager",
    "content writer", "graphic designer", "civil engineer",
    "mechanical engineer", "brand", "customer support",
    "supply chain", "logistics", "procurement", "legal",
})

_SPECIFIC_AI_SKILLS: frozenset[str] = frozenset({
    "tensorflow", "pytorch", "keras", "jax",
    "hugging face", "hugging face transformers",
    "bert", "gpt", "llm", "llms", "fine-tuning llms",
    "transformers", "diffusion models",
    "nlp", "natural language processing",
    "computer vision", "object detection", "image classification",
    "deep learning", "neural networks", "reinforcement learning",
    "mlops", "kubeflow", "mlflow", "bentoml",
    "recommendation systems", "speech recognition", "tts",
    "gans", "lora",
})

_DEFAULT_REQUIRED_SKILLS: list[str] = [
    "embeddings", "sentence transformers", "vector database",
    "pinecone", "weaviate", "qdrant", "milvus", "faiss",
    "elasticsearch", "opensearch", "python", "retrieval",
    "ranking", "nlp", "information retrieval",
    "recommendation", "search", "bert", "transformer",
]

_DEFAULT_PREFERRED_SKILLS: list[str] = [
    "fine-tuning", "lora", "qlora", "learning to rank",
    "xgboost", "langchain", "rag", "llm", "gpt", "huggingface",
]

_SKILL_ALIASES: dict[str, list[str]] = {
    "vector database": ["pinecone", "weaviate", "qdrant", "milvus", "faiss",
                        "chroma", "pgvector", "redis", "vespa", "zilliz"],
    "embeddings": ["sentence transformers", "sentence-transformers", "word2vec",
                   "fasttext", "glove", "openai embeddings", "cohere embeddings",
                   "all-minilm", "clip"],
    "retrieval": ["elasticsearch", "opensearch", "faiss", "bm25", "dense retrieval",
                  "sparse retrieval", "hybrid search", "solr"],
    "transformer": ["bert", "gpt", "t5", "roberta", "distilbert", "llm",
                    "attention", "hugging face", "transformers"],
    "ranking": ["learning to rank", "ltr", "lambdamart", "xgboost ranking",
                "bm25", "reranking", "cross-encoder"],
    "nlp": ["natural language processing", "text classification", "ner",
            "named entity recognition", "sentiment analysis", "text mining",
            "spacy", "nltk", "tokenization"],
    "python": ["python3", "python 3", "pyspark", "pandas", "numpy", "scikit"],
    "information retrieval": ["ir", "retrieval", "search engine", "lucene",
                              "elasticsearch", "opensearch", "solr"],
    "recommendation": ["collaborative filtering", "matrix factorization",
                       "recommendation system", "recommender", "recsys"],
    "search": ["information retrieval", "elasticsearch", "opensearch",
               "solr", "lucene", "faiss", "vector search"],
    "llm": ["gpt", "claude", "gemini", "llama", "mistral", "openai", "langchain",
            "large language model"],
    "rag": ["retrieval augmented generation", "retrieval-augmented", "langchain",
            "llamaindex", "llama index"],
    "fine-tuning": ["lora", "qlora", "peft", "adapter tuning", "instruction tuning",
                    "finetuning", "fine tuning"],
}


@dataclass
class RuleScore:
    candidate_id: str
    experience_score: float
    title_score: float
    skills_score: float
    industry_score: float
    disqualifier_penalty: float
    total: float


def score_experience(candidate: "CandidateRecord", jd: "ParsedJD") -> float:
    """Return 0–30 based on YoE vs JD range. Falls back to [5,9] when JD has no range."""
    yoe = candidate.profile.years_of_experience
    lo = jd.min_years_experience
    hi = jd.max_years_experience

    if lo == 0 and hi == 0:
        lo, hi = 5.0, 9.0

    if lo <= yoe <= hi:
        return 30.0
    if lo - 2 <= yoe < lo:
        return 20.0
    if yoe < lo - 2:
        return 5.0 if yoe < 2 else 10.0
    if hi < yoe <= hi + 3:
        return 20.0
    return 12.0


def _score_single_title(t: str) -> float:
    if any(kw in t for kw in _AI_ML_TITLE_KEYWORDS):
        return 20.0
    has_tech = any(kw in t for kw in _TECHNICAL_TITLE_KEYWORDS)
    has_senior = any(kw in t for kw in _SENIOR_MARKERS)
    if has_tech and has_senior:
        return 16.0
    if has_tech:
        return 12.0
    if any(kw in t for kw in ("analyst", "researcher", "scientist", "specialist")):
        return 8.0
    if any(kw in t for kw in _NON_TECHNICAL_TITLE_KEYWORDS):
        return 0.0
    return 4.0


def score_title(candidate: "CandidateRecord", jd: "ParsedJD") -> float:
    """Return 0–20. Checks current title then most-recent career entry as fallback."""
    titles = [candidate.profile.current_title]
    if candidate.career_history:
        titles.append(candidate.career_history[0].title)
    return max(_score_single_title(t.lower()) for t in titles)


def score_skills_overlap(candidate: "CandidateRecord", jd: "ParsedJD") -> float:
    """Return 0–25. required_coverage×20 + preferred_coverage×5.

    Matching uses direct name lookup, substring, alias expansion, and prose
    fallback (headline + summary + last 3 career descriptions).
    """
    required = [s.lower() for s in (jd.required_skills or _DEFAULT_REQUIRED_SKILLS)]
    preferred = [s.lower() for s in (jd.preferred_skills or _DEFAULT_PREFERRED_SKILLS)]
    cand_skills = {s.name.lower() for s in candidate.skills}
    cand_text = (
        candidate.profile.headline + " " + candidate.profile.summary + " "
        + " ".join(j.description for j in candidate.career_history[:3])
    ).lower()

    def _covered(jd_skill: str) -> bool:
        if jd_skill in cand_skills:
            return True
        if any(jd_skill in s or s in jd_skill for s in cand_skills):
            return True
        for alias in _SKILL_ALIASES.get(jd_skill, []):
            if alias in cand_skills or alias in cand_text:
                return True
        return jd_skill in cand_text

    req_cov = sum(1 for s in required if _covered(s)) / len(required) if required else 0.0
    pref_cov = sum(1 for s in preferred if _covered(s)) / len(preferred) if preferred else 0.0
    return round(req_cov * 20.0 + pref_cov * 5.0, 4)


def score_industry_background(candidate: "CandidateRecord") -> float:
    """Return 0–15 based on fraction of career months at product vs. outsourcing firms."""
    total = 0
    product = 0
    for job in candidate.career_history:
        months = max(job.duration_months, 1)
        total += months
        if not any(firm in job.company.lower().strip() for firm in _OUTSOURCING_FIRMS):
            product += months
    if total == 0:
        return 0.0
    ratio = product / total
    if ratio >= 0.60:
        return 15.0
    if ratio >= 0.30:
        return 10.0
    if ratio >= 0.10:
        return 5.0
    return 2.0


def apply_disqualifiers(candidate: "CandidateRecord", jd: "ParsedJD") -> float:
    """Return -50 if a hard disqualifier fires, else 0.

    Fires when ALL of: entire career is non-technical, 4+ specific AI/ML skills
    claimed, and no technical prose in career descriptions (keyword stuffer).
    Also fires for non-technical current title + no tech history + YoE < 2.
    """
    current = candidate.profile.current_title.lower()
    all_titles = [j.title.lower() for j in candidate.career_history]
    all_nontechnical = all(
        not any(kw in t for kw in _TECHNICAL_TITLE_KEYWORDS)
        for t in [current] + all_titles
    )

    if all_nontechnical:
        skill_names = {s.name.lower() for s in candidate.skills}
        ai_hits = [s for s in skill_names if s in _SPECIFIC_AI_SKILLS]
        career_text = " ".join(
            f"{j.title} {j.description}" for j in candidate.career_history
        ).lower()
        has_tech_prose = any(
            re.search(r"\b" + re.escape(kw) + r"\b", career_text)
            for kw in ("python", "sql", "machine learning", "data pipeline",
                       "software engineer", "data science", "deep learning",
                       "model training", "api", "tensorflow", "pytorch")
        )
        if len(ai_hits) >= 4 and not has_tech_prose:
            return -50.0

    is_nontechnical_current = (
        any(kw in current for kw in _NON_TECHNICAL_TITLE_KEYWORDS)
        and not any(kw in current for kw in _TECHNICAL_TITLE_KEYWORDS)
    )
    if is_nontechnical_current:
        has_tech_history = any(
            any(kw in j.title.lower() for kw in _TECHNICAL_TITLE_KEYWORDS)
            for j in candidate.career_history
        )
        if not has_tech_history and candidate.profile.years_of_experience < 2:
            return -50.0

    if jd.disqualifying_signals:
        career_desc = " ".join(j.description.lower() for j in candidate.career_history)
        for phrase in jd.disqualifying_signals:
            p = phrase.lower().strip()
            if len(p.split()) >= 3 and p in career_desc:
                return -50.0

    return 0.0


def score_candidate(candidate: "CandidateRecord", jd: "ParsedJD") -> RuleScore:
    """Score a single candidate. All components are pure — same input always same output."""
    exp = score_experience(candidate, jd)
    title = score_title(candidate, jd)
    skills = score_skills_overlap(candidate, jd)
    industry = score_industry_background(candidate)
    disq = apply_disqualifiers(candidate, jd)
    return RuleScore(
        candidate_id=candidate.candidate_id,
        experience_score=exp,
        title_score=title,
        skills_score=skills,
        industry_score=industry,
        disqualifier_penalty=disq,
        total=max(0.0, exp + title + skills + industry + disq),
    )


def batch_score(candidates: "list[CandidateRecord]", jd: "ParsedJD") -> "list[RuleScore]":
    """Score a list of candidates in input order."""
    return [score_candidate(c, jd) for c in candidates]
