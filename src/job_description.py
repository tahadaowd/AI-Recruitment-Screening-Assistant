JOB_DESCRIPTION_TEXT = """
Job Title: AI Developer

Overview:
We are looking for an AI Developer to join our team to build intelligent automation tools, NLP pipelines, and machine learning models.

Essential Requirements (Must-Have):
- Required Skills: Python, Machine Learning, Artificial Intelligence, Git
- Experience: Minimum 2 years of professional experience in Python development or AI/ML solutions.
- Education: Bachelor's degree in Computer Science, Artificial Intelligence, Data Science, Software Engineering, or related technical field.
- Languages: Professional working proficiency in English.

Optional / Preferred Requirements (Nice-to-Have):
- Skills: FastAPI, Docker, Ollama / Hugging Face Transformers, Vector Databases, Prompt Engineering
- Experience: Experience with LLM integration and retrieval-augmented generation (RAG).
- Certifications: Recognized Machine Learning or AI certification (e.g., AWS Certified Machine Learning, DeepLearning.AI, TensorFlow Developer, Microsoft Azure AI).
"""

JOB_STRUCTURE = {
    "title": "AI Developer",
    "must_have": {
        "skills": ["Python", "Machine Learning", "Artificial Intelligence", "Git"],
        "experience": ["2 years of experience in Python or AI/ML solutions"],
        "education": ["Bachelor's degree in Computer Science, Artificial Intelligence, Data Science or related field"],
        "languages": ["English"],
        "certifications": []
    },
    "nice_to_have": {
        "skills": ["FastAPI", "Docker", "Hugging Face", "Vector Databases", "Prompt Engineering"],
        "experience": ["Experience with LLM integration"],
        "education": [],
        "languages": [],
        "certifications": ["Machine Learning or AI certification"]
    }
}

def get_job_description():
    return JOB_DESCRIPTION_TEXT.strip()

def get_structured_job_requirements():
    return JOB_STRUCTURE