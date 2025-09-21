# utils/scoring.py
import re
from difflib import SequenceMatcher

# -------------------
# Scoring Functions
# -------------------

def calculate_relevance_score(jd_text, resume_text, jd_skills):
    """
    Calculate the relevance of a resume to a job description.
    Returns:
        final_score: 0-100 float
        hard_score: keyword matching score
        sem_score: semantic / soft matching score (basic here)
        missing_skills: list of skills not found
    """
    jd_text_lower = jd_text.lower()
    resume_text_lower = resume_text.lower()

    # Hard skill match
    found_skills = []
    missing_skills = []

    for skill in jd_skills:
        if re.search(r'\b' + re.escape(skill.lower()) + r'\b', resume_text_lower):
            found_skills.append(skill)
        else:
            missing_skills.append(skill)

    hard_score = (len(found_skills) / len(jd_skills)) * 100 if jd_skills else 0

    # Semantic / soft match using SequenceMatcher
    sm = SequenceMatcher(None, jd_text_lower, resume_text_lower)
    sem_score = sm.ratio() * 100

    # Weighted final score
    final_score = 0.7 * hard_score + 0.3 * sem_score

    return final_score, hard_score, sem_score, missing_skills


def get_verdict(score):
    """
    Convert numerical score to a verdict label.
    """
    if score >= 85:
        return "Strong Match"
    elif score >= 60:
        return "Moderate Match"
    else:
        return "Weak Match"


def generate_llm_feedback(score, missing_skills):
    """
    Generates a simple feedback string.
    """
    feedback = []
    if score >= 85:
        feedback.append("Excellent match with the JD. Minimal improvements required.")
    elif score >= 60:
        feedback.append("Good match, consider strengthening these areas:")
    else:
        feedback.append("Low match. Significant skill improvements needed:")

    if missing_skills:
        feedback.append(", ".join(missing_skills))

    return " ".join(feedback)
