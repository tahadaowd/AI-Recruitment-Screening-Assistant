import os
import re
import json
import requests
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as e:
            print(f"[Warning] Failed to load SentenceTransformer: {e}")
            _embedding_model = None
    return _embedding_model

def rule_based_check(requirement, candidate_items, full_cv_text=""):
    req_clean = requirement.lower().strip()

    for item in candidate_items:
        item_str = str(item).lower().strip()
        if req_clean in item_str or item_str in req_clean:
            return True, item

    tokens = [t for t in re.split(r'[\s,/]+', req_clean) if len(t) > 2]
    if tokens and full_cv_text:
        cv_lower = full_cv_text.lower()
        matched_tokens = [t for t in tokens if re.search(r'\b' + re.escape(t) + r'\b', cv_lower)]
        if len(matched_tokens) == len(tokens):
            return True, "Found in CV text"

    return False, None

def compute_semantic_similarity(requirement, candidate_items):
    model = get_embedding_model()
    if not model or not candidate_items:
        return 0.0, None

    try:
        req_embedding = model.encode([requirement])
        items_embeddings = model.encode([str(item) for item in candidate_items])

        similarities = cosine_similarity(req_embedding, items_embeddings)[0]
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])
        best_item = candidate_items[best_idx]

        return round(best_score, 3), best_item
    except Exception as e:
        print(f"[Warning] Semantic similarity calculation error: {e}")
        return 0.0, None

def get_ai_evidence_and_verdict(requirement, cv_text):
    if not cv_text or not cv_text.strip():
        return "Does Not Meet", "No evidence found in CV"

    prompt = f"""
Evaluate the candidate's CV against this specific job requirement:
Requirement: "{requirement}"

Candidate CV Text:
\"\"\"
{cv_text[:3000]}
\"\"\"

Instructions:
1. Determine if the candidate: "Meets", "Partially Meets", or "Does Not Meet" the requirement.
2. Provide direct quotation or evidence from the CV.
3. If the CV does not contain sufficient information or mention the requirement, set result to "Does Not Meet" and evidence to "No evidence found in CV".

Return ONLY valid JSON format with keys:
{{
  "verdict": "Meets" | "Partially Meets" | "Does Not Meet",
  "evidence": "Direct quote or No evidence found in CV"
}}
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=40)
        response.raise_for_status()
        raw = response.json().get("response", "")
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        clean = re.sub(r"\s*```$", "", clean).strip()
        data = json.loads(clean)

        verdict = data.get("verdict", "Does Not Meet")
        evidence = data.get("evidence", "No evidence found in CV")
        if not evidence.strip():
            evidence = "No evidence found in CV"

        if verdict not in ["Meets", "Partially Meets", "Does Not Meet"]:
            verdict = "Partially Meets" if "partial" in verdict.lower() else "Does Not Meet"

        return verdict, evidence
    except Exception:
        return None, None

def evaluate_requirement(category, requirement, candidate_info, cv_text=""):
    candidate_items = candidate_info.get(category, [])
    rule_matched, matched_item = rule_based_check(requirement, candidate_items, cv_text)
    sim_score, best_item = compute_semantic_similarity(requirement, candidate_items)

    ai_verdict, ai_evidence = get_ai_evidence_and_verdict(requirement, cv_text)

    if ai_verdict and ai_evidence:
        verdict = ai_verdict
        evidence = ai_evidence
    else:
        if rule_matched or sim_score >= 0.70:
            verdict = "Meets"
            evidence = f"Matched: {matched_item or best_item}"
        elif sim_score >= 0.45:
            verdict = "Partially Meets"
            evidence = f"Similar item found: {best_item}"
        else:
            verdict = "Does Not Meet"
            evidence = "No evidence found in CV"

    return {
        "category": category,
        "requirement": requirement,
        "result": verdict,
        "similarity_score": sim_score,
        "rule_matched": rule_matched,
        "evidence": evidence
    }

def match_candidate(job_info, candidate_info, cv_text=""):
    results = []
    categories = ["skills", "experience", "education", "languages", "certifications"]

    for cat in categories:
        req_list = job_info.get(cat, [])
        for req in req_list:
            eval_res = evaluate_requirement(cat, req, candidate_info, cv_text)
            results.append(eval_res)

    return results