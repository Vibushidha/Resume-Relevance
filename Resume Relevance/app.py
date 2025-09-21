import streamlit as st
import os
import sqlite3
import re
import pandas as pd
import altair as alt
from datetime import datetime
from docx2txt import process
import PyPDF2

from utils.scoring import calculate_relevance_score, get_verdict, generate_llm_feedback

# -------------------
# Setup
# -------------------
TECH_SKILLS = [
    "Python", "JavaScript", "SQL", "Pandas", "NumPy", "TensorFlow", "PyTorch",
    "React", "Angular", "Flask", "Django", "AWS", "Azure", "GCP", "Docker",
    "Kubernetes", "Git", "GitHub", "API", "REST", "Machine Learning",
    "Deep Learning", "Data Science", "Natural Language Processing", "NLP", "Computer Vision"
]

conn = sqlite3.connect('resume_results.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS results (
    resume_name TEXT,
    jd_name TEXT,
    score REAL,
    verdict TEXT,
    missing_keywords TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
c.execute('''
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    event_type TEXT NOT NULL,
    item_name TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

os.makedirs('data/resumes', exist_ok=True)
os.makedirs('data/jobs', exist_ok=True)

# -------------------
# Utility Functions
# -------------------
def extract_text_from_file(file_path):
    try:
        if file_path.lower().endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        elif file_path.lower().endswith('.docx'):
            return process(file_path)
        else:
            return None
    except Exception as e:
        st.error(f"Error extracting text from {file_path}: {e}")
        return None

def save_to_db(resume_name, jd_name, score, verdict, missing_skills):
    c.execute(
        "INSERT INTO results (resume_name, jd_name, score, verdict, missing_keywords) VALUES (?, ?, ?, ?, ?)",
        (resume_name, jd_name, score, verdict, ", ".join(missing_skills))
    )
    conn.commit()

def log_event(event_type, item_name):
    c.execute("INSERT INTO audit_log (event_type, item_name) VALUES (?, ?)", (event_type, item_name))
    conn.commit()

def highlight_missing_skills(resume_text, missing_skills, context_chars=50):
    snippets = []
    text = resume_text.replace('\n', ' ')
    for skill in missing_skills:
        pattern = re.compile(r"(.{0,%d}%s.{0,%d})" % (context_chars, re.escape(skill), context_chars), re.IGNORECASE)
        m = pattern.search(text)
        snippet = m.group(0) if m else text[:min(100, len(text))]
        snippet = snippet.replace('<', '&lt;').replace('>', '&gt;')
        snippet = re.sub(r'(?i)(' + re.escape(skill) + r')', r'<mark>\1</mark>', snippet)
        snippets.append(f"<p><strong>{skill}:</strong> ...{snippet}...</p>")
    return "".join(snippets)

# -------------------
# Streamlit UI
# -------------------
st.set_page_config(layout="wide", page_title="Resume Relevance Checker — Enhanced UI")
st.title("🤖 Automated Resume Relevance Check System")
st.caption("Upload a JD and candidate resumes — get visual scores, feedback, and analytics.")
st.markdown("---")

# -------------------
# Sidebar
# -------------------
with st.sidebar:
    st.header("⚙️ Settings")
    max_compare = st.slider("Max compare candidates", min_value=2, max_value=4, value=3)
    st.markdown("---")
    st.write("**Export / Cleanup**")
    if st.button("Clear DB & Files"):
        if st.checkbox("Confirm delete all results and uploaded files", value=False):
            c.execute("DELETE FROM results")
            c.execute("DELETE FROM audit_log")
            conn.commit()
            for folder in ['data/resumes', 'data/jobs']:
                for f in os.listdir(folder):
                    try:
                        os.remove(os.path.join(folder, f))
                    except Exception:
                        pass
            st.success("Database and files cleared.")

# -------------------
# JD Upload
# -------------------
st.header("📄 1. Upload Job Description (JD)")
jd_file = st.file_uploader('Upload JD (PDF or DOCX)', type=['pdf', 'docx'])
jd_path = None
jd_text = None
jd_skills = []

if jd_file:
    jd_path = os.path.join('data/jobs', jd_file.name)
    with open(jd_path, 'wb') as f:
        f.write(jd_file.getbuffer())
    st.success(f'Uploaded JD: **{jd_file.name}**')
    log_event('JD_UPLOADED', jd_file.name)

    jd_text = extract_text_from_file(jd_path)
    if jd_text:
        st.text_area('JD Text', jd_text, height=200)
        jd_skills = [skill for skill in TECH_SKILLS if re.search(r'\b' + re.escape(skill) + r'\b', jd_text, re.IGNORECASE)]
        if jd_skills:
            st.info(f"Identified Skills from JD: {', '.join(jd_skills)}")
        else:
            st.warning("Could not identify skills from JD. Using basic approach.")

st.markdown('---')

# -------------------
# Resume Upload
# -------------------
st.header("👤 2. Upload Resumes")
resume_files = st.file_uploader('Upload Resume(s) (PDF or DOCX)', type=['pdf', 'docx'], accept_multiple_files=True)
run_analysis = st.button('Run Analysis')

# -------------------
# Run Analysis
# -------------------
if run_analysis:
    if not resume_files or not jd_file:
        st.warning('Please upload both JD and at least one resume.')
    else:
        st.subheader('🚀 Analysis Results')
        results = []
        for resume_file in resume_files:
            resume_path = os.path.join('data/resumes', resume_file.name)
            with open(resume_path, 'wb') as f:
                f.write(resume_file.getbuffer())

            resume_text = extract_text_from_file(resume_path)
            if not resume_text:
                st.error(f"Failed to extract text from {resume_file.name}")
                continue

            final_score, hard_score, sem_score, missing_skills = calculate_relevance_score(jd_text, resume_text, jd_skills)
            verdict_label = get_verdict(final_score)
            feedback = generate_llm_feedback(final_score, missing_skills)

            save_to_db(resume_file.name, jd_file.name, final_score, verdict_label, missing_skills)
            log_event('RESULT_SAVED', resume_file.name)

            results.append({
                'Resume': resume_file.name,
                'Score': float(f"{final_score:.2f}"),
                'Verdict': verdict_label,
                'Missing Skills': ", ".join(missing_skills) if missing_skills else 'None',
                'Feedback': feedback,
                'SnippetHTML': highlight_missing_skills(resume_text, missing_skills) if missing_skills else ''
            })

        if results:
            st.success('Analysis complete!')
            st.session_state['results_df'] = pd.DataFrame(results)

# -------------------
# Display Results & Analytics
# -------------------
if 'results_df' in st.session_state and not st.session_state['results_df'].empty:
    results_df = st.session_state['results_df']

    st.subheader('📊 Candidate Pool Overview')
    st.dataframe(results_df[['Resume', 'Score', 'Verdict', 'Missing Skills']], use_container_width=True, height=300)

    # verdict distribution pie chart
    verdict_counts = results_df['Verdict'].value_counts().reset_index()
    verdict_counts.columns = ['Verdict', 'Count']
    pie = alt.Chart(verdict_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field='Verdict', type='nominal'),
        tooltip=['Verdict', 'Count']
    ).properties(width=300, height=300)

    # score bar chart
    score_bar = alt.Chart(results_df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('Score:Q'),
        y=alt.Y('Resume:N', sort='-x'),
        tooltip=['Resume', 'Score', 'Verdict', 'Missing Skills']
    ).properties(width=600, height=300)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.altair_chart(pie, use_container_width=True)
    with col2:
        st.altair_chart(score_bar, use_container_width=True)

    # -------------------
    # Compare Candidates
    # -------------------
    st.subheader('👥 Compare Candidates')
    st.info(f'Select up to {max_compare} candidates to compare.')
    compare_options = st.multiselect('Select Resumes to Compare', options=results_df['Resume'].tolist(), max_selections=max_compare)

    if compare_options:
        cols = st.columns(len(compare_options))
        for i, resume_name in enumerate(compare_options):
            with cols[i]:
                selected_resume = results_df[results_df['Resume'] == resume_name].iloc[0]
                st.metric('Score', f"{selected_resume['Score']:.2f}")
                st.write(f"**Verdict:** {selected_resume['Verdict']}")
                with st.expander('Details'):
                    st.write(f"**Missing Skills:** {selected_resume['Missing Skills']}")
                    st.write(f"**Feedback:** {selected_resume['Feedback']}")
                    if selected_resume['SnippetHTML']:
                        st.markdown(selected_resume['SnippetHTML'], unsafe_allow_html=True)

# -------------------
# Audit Trail
# -------------------
st.markdown('---')
st.subheader('📜 Audit Trail')
c.execute("SELECT event_type, item_name, timestamp FROM audit_log ORDER BY timestamp DESC LIMIT 50")
logs = c.fetchall()
if logs:
    log_df = pd.DataFrame(logs, columns=['Event Type', 'Item', 'Timestamp'])
    log_df['Timestamp'] = pd.to_datetime(log_df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    st.dataframe(log_df, use_container_width=True)
else:
    st.info('No events logged yet.')

# Footer
st.markdown('---')
st.caption('Built with ❤️ — enhanced UX, analytics, comparison mode, without dark mode.')

try:
    conn.close()
except Exception:
    pass
