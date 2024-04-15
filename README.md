# Concordia University

Department of Computer Science and Software Engineering COMP 6741

INTELLIGENT SYSTEMS

Project Group FS_G_07

## Authors

Name: Jatin Arora <br/>
Applicant ID: 40225129

Name: Devanshi Patel <br/>
Applicant ID: 40172139

## High Level Description of Project

The overall goal of this project is to build Roboprof, an intelligent agent that answer university courses and student related questions, using a knowledge graph and natural language processing.

## Contents

1. **Datasets folder**: This folder contains datasets used to generate RDF graphs for the knowledge base. It includes:

   - **COMP6721 folder**: Contains files and folders related to the course content COMP 6721.
   - **COMP6741 folder**: Contains files and folders related to the course content COMP 6741.
   - **ProcessedTextFiles folder**: Contains all files related to course content in text format. 
   - **courses_data.csv**: A CSV file downloaded from [Concordia Open Data](https://opendata.concordia.ca/datasets/) listing information about Concordia courses.
   - **students_data.csv**: A manually created CSV file with sample student entries used to generate the students graph.
   - **topics_data.csv**: A manually created CSV file with sample entries used to generate the topics graph used for first part of the project.
   - **entity-urls.csv**: Contains topic related data (filename, entities, DBpediaURI) used in second part of the project.

2. **KnowledgeBase Folder**: Contains all the generated knowledge bases in both .ttl and .nt format.

3. **OUTPUT folder**: Contains text files with queries for the questions (q1.txt, q2.txt, ...) and the full output of queries when run on the knowledge base (q1-out.csv, q2-out.csv, ...).
4. **pre-processing.py**: Python script to convert the course materials into text files.  Run with `python3 pre-processing.py`. Ensure necessary libraries are installed.
5. **entity-linking.py**: Python script to extract entites from the text files and link them to their respective DBpedia URIs.  Run with `python3 entity-linking.py`. Ensure necessary libraries are installed.
6. **buildKB.py**: Python script to generate the knowledge base. Run with `python3 buildKB.py`. Ensure necessary libraries are installed.

7. **Generating_Output.py**: Python script to generate the OUTPUT folder. Run with `python3 Generating_Output.py`. Ensure necessary libraries are installed. This file reads queries one by one from queries.rq and produces the output in the OUTPUT folder by executing SPARQL queries on Apache Fuseki Server.

8. **queries.rq**: Contains a list of all the SPARQL queries.

9. **Vocabulary.ttl**: The schema modeled by us for generating the knowledge base.

## Requirements to run the code

SPARQLWrapper &nbsp;&nbsp;&nbsp;&nbsp; 2.0.0 <br/>
rdflib &nbsp;&nbsp;&nbsp;&nbsp; 7.0.0 <br/>
DBpedia spotlight <br/>


## Execution Steps

```
> Clone the repo
    >> git clone https://github.com/jatin51997/roboprof.git
> Ensure Python 3 is installed on your system.
> Install required libraries using pip.
    >> pip install SPARQLWrapper rdflib.
>Run pre-processing.py using the command to generate text files.
   >>python3 pre-processing.py
>Run entity-linking.py using the command to generate entity-urls.csv file.
   >>python3 entity-linking.py
> Run buildKB.py using the command to generate the knowledge base files.
    >> python3 buildKB.py
> Start Apache Fuseki and load the generated knowledge base files.
> Run Generating_Output.py to execute queries and generate output in the OUTPUT folder.
    >> python3 Generating_Output.py
```
