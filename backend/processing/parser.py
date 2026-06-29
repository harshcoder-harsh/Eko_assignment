import fitz # PyMuPDF
import docx
import os
import re

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 250, overlap: int = 50):
    words = text.split()
    chunks = []
    # all-MiniLM-L6-v2 has a max token length of 256. If we make chunks larger than 250 words, 
    # the embedding model truncates the rest of the text, causing massive data loss and broken RAG!
    for i in range(0, len(words), max(1, chunk_size - overlap)):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def extract_text_from_pdf(filepath: str) -> str:
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def extract_text_from_docx(filepath: str) -> str:
    doc = docx.Document(filepath)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def extract_text_from_txt(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def _process_single_file(file):
    filepath = file['path']
    ext = os.path.splitext(filepath)[1].lower()
    local_chunks = []

    try:
        text = ""
        if ext == '.pdf':
            text = extract_text_from_pdf(filepath)
        elif ext == '.docx':
            text = extract_text_from_docx(filepath)
        elif ext == '.txt':
            text = extract_text_from_txt(filepath)
        else:
            print(f"Unsupported file extension: {ext}")
            return []

        cleaned_text = clean_text(text)
        if not cleaned_text:
            return []

        file_chunks = chunk_text(cleaned_text, chunk_size=250, overlap=50)
        for i, c in enumerate(file_chunks):
            local_chunks.append({
                "id": f"{file['id']}_chunk_{i}",
                "doc_id": file['id'],
                "text": c
            })
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        
    return local_chunks

def process_single_file(file):
    return _process_single_file(file)

def process_files(files):
    import gc
    all_chunks = []
    for file in files:
        chunk_list = _process_single_file(file)
        all_chunks.extend(chunk_list)
        gc.collect()
            
    return all_chunks
