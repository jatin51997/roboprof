import os
import shutil
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        text = soup.get_text()
    return text

def save_text_to_file(text, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(text)

def process_files_in_directory(root_dir):
    processed_dir = os.path.join(root_dir, "ProcessedTextFiles")
    os.makedirs(processed_dir, exist_ok=True)

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            output_dir = os.path.join(processed_dir, os.path.relpath(root, root_dir))
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, os.path.splitext(file)[0] + ".txt")

            if file.endswith(".pdf"):
                text = extract_text_from_pdf(file_path)
                save_text_to_file(text, output_file)
                print(f"Converted {file_path} to {output_file}")
            elif file.endswith(".html"):
                text = extract_text_from_html(file_path)
                save_text_to_file(text, output_file)
                print(f"Converted {file_path} to {output_file}")
            elif file.endswith(".txt"):
                # Directly copy the txt file as it is
                shutil.copy2(file_path, output_file)
                print(f"Copied {file_path} to {output_file}")


process_files_in_directory('Datasets')