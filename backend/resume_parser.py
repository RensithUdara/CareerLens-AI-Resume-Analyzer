"""
Extracts plain text from an uploaded PDF or DOCX resume.
"""
import os
import pdfplumber
from docx import Document


def extract_text(file_path: str) -> str:
    """Detect file type from extension and pull out all readable text."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return _extract_from_pdf(file_path)
    elif ext == ".docx":
        return _extract_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Please upload a PDF or DOCX file.")


def _extract_from_pdf(file_path: str) -> str:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    text_parts = [p.text for p in doc.paragraphs if p.text.strip()]

    # Also pull text out of any tables (many resumes use tables for layout)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_parts.append(cell.text)

    return "\n".join(text_parts).strip()
