import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

DEFAULT_EMPTY_SCHEMA = {
    "skills": [],
    "experience": [],
    "education": [],
    "languages": [],
    "certifications": []
}

def clean_json_response(raw_text):
    if not raw_text:
        return DEFAULT_EMPTY_SCHEMA.copy()

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        data = json.loads(cleaned)
        result = {}
        for key in ["skills", "experience", "education", "languages", "certifications"]:
            val = data.get(key, [])
            if isinstance(val, list):
                result[key] = [str(item).strip() for item in val if item]
            elif isinstance(val, str) and val.strip():
                result[key] = [val.strip()]
            else:
                result[key] = []
        return result
    except Exception as e:
        print(f"[Warning] Failed to parse JSON from LLM response: {e}")
        return DEFAULT_EMPTY_SCHEMA.copy()

def extract_information(text, target_type="CV"):
    if not text or not text.strip():
        return DEFAULT_EMPTY_SCHEMA.copy()

    prompt = f"""
You are an expert HR AI assistant. Analyze the following {target_type} and extract the structured information.

Extract and classify items into these exact categories:
1. "skills": Technical and soft skills mentioned.
2. "experience": Work history, years of experience, or roles mentioned.
3. "education": Degrees, universities, diplomas, or fields of study.
4. "languages": Languages spoken or required (e.g. English, Arabic).
5. "certifications": Professional certifications, licenses, or courses.

CRITICAL INSTRUCTIONS:
- Return ONLY valid JSON format with keys: "skills", "experience", "education", "languages", "certifications".
- Each key must contain a list of clear, concise strings.
- Do not include explanation, greetings, or markdown text outside the JSON.

{target_type} Content:
\"\"\"
{text}
\"\"\"
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.1
        }
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        raw_output = response.json().get("response", "")
        return clean_json_response(raw_output)

    except requests.exceptions.ConnectionError:
        print(f"[Warning] Could not connect to Ollama at {OLLAMA_URL}. Is Ollama running?")
        print(f"[Fallback] Returning basic fallback extraction for {target_type}.")
        return fallback_rule_extractor(text)
    except requests.exceptions.Timeout:
        print(f"[Warning] Ollama request timed out for {target_type}.")
        return fallback_rule_extractor(text)
    except Exception as e:
        print(f"[Error] Error during AI extraction: {e}")
        return fallback_rule_extractor(text)

def fallback_rule_extractor(text):
    text_lower = text.lower()
    common_skills = [
        "python", "machine learning", "artificial intelligence", "deep learning",
        "git", "github", "fastapi", "docker", "sql", "pytorch", "tensorflow",
        "nlp", "data science", "linux", "c++", "java", "javascript"
    ]
    detected_skills = [s.title() for s in common_skills if s in text_lower]

    common_languages = ["english", "arabic", "french", "german", "spanish"]
    detected_langs = [l.title() for l in common_languages if l in text_lower]

    education = []
    if "bachelor" in text_lower or "b.sc" in text_lower or "degree" in text_lower:
        education.append("Bachelor's Degree in Computer Science or related field")
    if "master" in text_lower or "m.sc" in text_lower:
        education.append("Master's Degree")

    exp_matches = re.findall(r"(\d+\+?\s*(?:years?|yrs?)(?:\s+of\s+experience)?)", text, re.IGNORECASE)

    return {
        "skills": detected_skills,
        "experience": exp_matches if exp_matches else [],
        "education": education,
        "languages": detected_langs,
        "certifications": []
    }