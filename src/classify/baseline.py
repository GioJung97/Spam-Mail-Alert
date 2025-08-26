from __future__ import annotations
import re, json, pathlib
from typing import Tuple, List, Dict
import tldextract
import numpy as np

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.utils.validation import check_is_fitted
from sklearn.exceptions import NotFittedError

MODEL_PATH = pathlib.Path(__file__).resolve().parents[1] / "model.joblib"

# We avoid heavy deps; use joblib from sklearn
from joblib import dump, load

SUSPICIOUS_WORDS = [
    "winner","prize","lottery","bitcoin","crypto","viagra","sex","casino","act now",
    "urgent","final notice","verify account","password reset","unusual activity","gift card",
    "investment","double your","work from home","earn $$$","limited time","risk-free"
]
URL_RE = re.compile(r"https?://", re.I)

def _normalize_sender(sender: str) -> str:
    # Extract domain from "Name <email@domain>"
    m = re.search(r"<[^@>]+@([^>]+)>", sender)
    domain = (m.group(1) if m else sender.split("@")[-1]).strip().lower()
    return domain

def _heuristics(subject: str, snippet: str, sender: str) -> Tuple[float, List[str]]:
    text = f"{subject}\n{snippet}".lower()
    reasons = []
    score = 0.0

    # suspicious phrases
    hits = [w for w in SUSPICIOUS_WORDS if w in text]
    if hits:
        score += min(0.4, 0.05 * len(hits))
        reasons.append(f"suspicious terms: {', '.join(hits[:5])}")

    # many links
    n_links = len(URL_RE.findall(text))
    if n_links >= 2:
        score += 0.15
        reasons.append(f"{n_links} links")

    # sender domain oddities (many subdomains or strange TLDs)
    domain = _normalize_sender(sender)
    ext = tldextract.extract(domain)
    sub_len = len([p for p in [ext.subdomain] if p and p.strip() != ""])
    if sub_len >= 1:
        score += 0.05
        reasons.append("nested subdomain")
    if ext.suffix in {"zip","tokyo","top","xyz","loan","click","country","gq","work","review"}:
        score += 0.1
        reasons.append(f"suspicious TLD: .{ext.suffix}")

    # all-caps subject
    if subject and subject.isupper() and len(subject) >= 6:
        score += 0.05
        reasons.append("ALL-CAPS subject")

    return max(0.0, min(score, 0.9)), reasons

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            strip_accents="unicode",
            lowercase=True,
            stop_words="english",
            max_features=5000,
            ngram_range=(1,2)
        )),
        ("lr", LogisticRegression(max_iter=200))
    ])

def load_or_init() -> Pipeline:
    if MODEL_PATH.exists():
        try:
            return load(MODEL_PATH)
        except Exception:
            pass
    return build_pipeline()

def save_model(pipe: Pipeline) -> None:
    dump(pipe, MODEL_PATH)

def train(pipe: Pipeline, texts: List[str], labels: List[int]) -> Pipeline:
    # labels: 1 = spam, 0 = ham
    pipe.fit(texts, labels)
    save_model(pipe)
    return pipe

def predict(pipe: Pipeline, texts: List[str]) -> np.ndarray:
    # returns probabilities for class 1 (spam)
    try:
        check_is_fitted(pipe)
    except NotFittedError:
        # cold start: return 0.5 neutral
        return np.array([0.5] * len(texts))
    proba = pipe.predict_proba(texts)
    # proba columns order is model-dependent; find the spam class (1)
    if pipe.named_steps["lr"].classes_[1] == 1:
        return proba[:,1]
    else:
        return proba[:,0]

def combine_scores(heur: float, model: float) -> float:
    # Weighted blend; start by trusting heuristics a bit until the model is trained.
    return float(0.6 * heur + 0.4 * model)

def explain(heur_reasons: List[str], model_score: float) -> str:
    parts = []
    if heur_reasons:
        parts.append("; ".join(heur_reasons))
    parts.append(f"model={model_score:.2f}")
    return " | ".join(parts)
