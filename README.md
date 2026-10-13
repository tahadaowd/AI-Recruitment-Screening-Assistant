# 💼 AI Recruitment Screening Assistant

An intelligent, end-to-end recruitment screening assistant designed to help HR teams process, evaluate, rank, and shortlist job applicants automatically using **Ollama LLM**, **Semantic Embeddings**, **FastAPI**, and **Streamlit**.

---

## 🚀 Key Features

1. **Automated Gmail Ingestion**: Reads incoming application emails, filters supported attachments (`.pdf`, `.docx`), and prevents duplicate evaluations.
2. **AI Requirement Extraction**: Uses local LLMs (via Ollama) to extract structured qualifications (Skills, Experience, Education, Languages, Certifications) from raw Job Descriptions and CVs.
3. **Semantic & Rule-Based Matching**: Evaluates each candidate using hybrid matching (SentenceTransformers `all-MiniLM-L6-v2` + cosine similarity + rule verification).
4. **Must-Have vs. Nice-to-Have Logic**: Candidates missing any mandatory (Must-Have) requirement are automatically separated into a review pool, while qualified candidates are ranked by score.
5. **AI Evidence Generation**: Provides direct quotes and excerpts from the candidate's CV justifying each qualification result.
6. **FastAPI Backend**: Clean, modular RESTful API with Pydantic validation for job configuration, screening execution, and HR actions.
7. **Streamlit HR Dashboard**: Interactive web UI allowing HR to customize requirements, trigger screening, inspect evidence, and mark candidates as **Shortlist**, **Review Later**, or **Reject**.

---

## 🛠️ Tech Stack

- **Backend API**: FastAPI, Pydantic, Uvicorn
- **Frontend UI**: Streamlit, Pandas
- **AI & NLP**: Ollama (`qwen3:8b`), Sentence-Transformers (`all-MiniLM-L6-v2`), Scikit-Learn
- **Document Processing**: `pypdf`, `python-docx`
- **Email Ingestion**: Google Gmail API, OAuth 2.0

---

## ⚙️ Installation & Setup

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd AI-Recruitment-Screening-Assistant

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate
