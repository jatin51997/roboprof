import requests
import csv
from pathlib import Path

# Define the URL for DBpedia Spotlight API
spotlight_url = "http://localhost:2222/rest/annotate"

# Directory and file paths
directory_path = Path("Datasets/ProcessedTextFiles")
csv_file = Path("Datasets/entity-urls.csv")


# Function to perform entity linking with DBpedia Spotlight
def link_entities(text):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"text": text, "confidence": 0.7, "support": 15}
    try:
        response = requests.post(spotlight_url, headers=headers, data=data)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch entities: {e}")
        return None


# Function to split text into chunks
def split_text(text, max_size):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        word_size = len(word.encode("utf-8")) + 1  # add 1 for space
        if current_size + word_size > max_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks


# Create or overwrite the CSV file
with csv_file.open("w", newline="", encoding="utf-8") as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(["File Name", "Entity", "URI"])

    # Process each text file
    for file_path in directory_path.rglob("*.txt"):
        with file_path.open("r", encoding="utf-8") as file:
            text = file.read()
            # Ensure each chunk does not exceed the maximum POST size
            for chunk in split_text(text, 2000000):
                linked_data = link_entities(chunk)
                if linked_data and "Resources" in linked_data:
                    for resource in linked_data["Resources"]:
                        csvwriter.writerow(
                            [
                                str(file_path).replace("\\", "/"),
                                resource["@surfaceForm"],
                                resource["@URI"],
                            ]
                        )

print(f"CSV file '{csv_file}' created.")
