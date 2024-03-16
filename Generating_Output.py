from SPARQLWrapper import SPARQLWrapper, JSON
import csv
import os

sparql_endpoint = "http://localhost:3030/roboprof/query"


output_directory = "./OUTPUT"

if not os.path.exists(output_directory):
    os.makedirs(output_directory)

with open("queries.rq", "r") as file:
    file_content = file.read()

parts = file_content.split("\n\n")
prefixes = parts[0]  # Assuming the first part contains the prefix declarations
queries = parts[1:]  # The rest are the actual queries

sparql = SPARQLWrapper(sparql_endpoint)
sparql.setReturnFormat(JSON)

for i, query_str in enumerate(queries, start=1):
    query_filename = os.path.join(output_directory, f"q{i}.txt")
    output_filename = os.path.join(output_directory, f"q{i}-out.csv")
    # Write the query to a text file
    try:
        with open(query_filename, 'w') as query_file:
            query_file.write(prefixes + "\n" + query_str.strip())
    except Exception as e:
        print(f"Error writing to file: {query_filename}")
        print(e)
        continue

    full_query = prefixes + "\n" + query_str.strip()  # Prepend prefixes

    if full_query.strip():  # Check if the query is not empty
        # Set the query
        sparql.setQuery(full_query)

        try:
            # Execute the query
            results = sparql.query().convert()

            # Open CSV file for writing the results
            with open(output_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                # Assuming the first row of results contains all possible columns
                columns = results['head']['vars']
                writer.writerow(columns)  # Write header
                print(f"Results for Query {i}:")
                print(", ".join(columns))  # Print header to console
                for result in results['results']['bindings']:
                    row = [result[var]['value'] if var in result else "" for var in columns]
                    writer.writerow(row)
                    print(", ".join(row))  # Print each row to console
                print()  # Blank line for separation
        except Exception as e:
            print(f"Error executing query: {query_str}")
            print(e)
