import spacy
import csv
from pathlib import Path
import urllib
from urllib.parse import quote
from rdflib import URIRef

# Initialize SpaCy
nlp = spacy.load("en_core_web_md")
nlp.max_length = 2000000
entity_linker = nlp.add_pipe("entityLinker", last=True)

# Directory path
directory_path = Path("Datasets/ProcessedTextFiles")

# CSV file preparation
csv_file = Path("Datasets/entity-urls.csv")

with csv_file.open("w", newline="", encoding="utf-8") as csvfile:

    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["File Name", "Entity", "URL"])

    for file_path in directory_path.rglob("*.txt"):
        with file_path.open("r", encoding="utf-8") as file:
            text = file.read()
            doc = nlp(text)
            for ent in doc._.linkedEntities:
                entity_span = ent.get_span()
                entity_text = entity_span.text

                # Check for a mix of POS tags indicative of named entities
                if any(token.pos_ in ["PROPN", "NOUN", "ADJ"] for token in entity_span):
                    if len(entity_text) > 3:
                        url = ent.get_url()
                        csvwriter.writerow(
                            [str(file_path).replace("\\", "/"), entity_text, url]
                        )

print(f"CSV file '{csv_file}' created.")
