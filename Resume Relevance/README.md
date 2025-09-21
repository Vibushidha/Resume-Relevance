# Automated Resume Relevance Check System

## How to Run

1. Install dependencies:
```
pip install -r requirements.txt
```
2. Run Streamlit app:
```
streamlit run app.py
```
3. Upload a Job Description (PDF/DOCX) and multiple resumes (PDF/DOCX) to see relevance scores.

## Features
- Hard match (keyword-based)
- Semantic match (embedding-based)
- Relevance score (0-100)
- Verdict (High/Medium/Low)
- Missing skills detection
- Batch resume upload
