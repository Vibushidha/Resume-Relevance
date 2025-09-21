import pdfplumber
import docx2txt
import re

def clean_text(text):
    text = text.lower()
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_text_from_pdf(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + ' '
    return text

def extract_text_from_docx(file_path):
    return docx2txt.process(file_path)

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        return clean_text(extract_text_from_pdf(file_path))
    elif file_path.endswith('.docx'):
        return clean_text(extract_text_from_docx(file_path))
    else:
        return ''
