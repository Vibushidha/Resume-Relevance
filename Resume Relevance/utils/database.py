import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_name TEXT,
            jd_name TEXT,
            score REAL,
            verdict TEXT,
            missing_skills TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_result(resume_name, jd_name, score, verdict, missing_skills):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO results (resume_name, jd_name, score, verdict, missing_skills)
        VALUES (?, ?, ?, ?, ?)
    ''', (resume_name, jd_name, score, verdict, missing_skills))
    conn.commit()
    conn.close()
