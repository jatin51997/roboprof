from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import BNode, Graph, URIRef, Literal, Namespace, RDF, RDFS, FOAF
import random
import os
import csv
import urllib

voc = Namespace("file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#")
vocdata = Namespace("file:///Users/jatin/workspace/roboprof/data#")
dbp = Namespace("http://dbpedia.org/resource/")


def createUniversitiesRDF():
    sparql_query = """
        SELECT DISTINCT ?university ?name WHERE {
            ?university a dbo:University ;
                        dbp:name ?name .
        } ORDER BY ?name
    """

    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    sparql.setQuery(sparql_query)
    sparql.setReturnFormat(JSON)

    results = sparql.query().convert()

    g = Graph()
    g.bind("voc", voc)
    g.bind("vocdata", vocdata)

    university_ids = {}

    if "results" in results and "bindings" in results["results"]:
        for result in results["results"]["bindings"]:
            university_uri = URIRef(result["university"]["value"])
            name = Literal(result["name"]["value"])
            unique_id = random.randint(10**9, (10**10) - 1)
            unique_id_str = str(unique_id)
            unique_id_str_padded = unique_id_str.zfill(10)
            vocdata_uri = vocdata[unique_id_str_padded]

            university_ids[university_uri] = vocdata_uri

            g.add((vocdata_uri, RDF.type, voc.University))
            g.add((vocdata_uri, FOAF.name, name))
            g.add((vocdata_uri, RDFS.seeAlso, university_uri))

    return g, university_ids


def createCoursesRDF(csv_file, university_ids):
    g = Graph()
    g.bind("voc", voc)
    g.bind("vocdata", vocdata)

    course_ids = {}

    with open(csv_file, newline="", encoding="utf-16") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            (
                course_id,
                subject,
                catalog,
                long_title,
                class_units,
                _,
                course_description,
                _,
                _,
                _,
            ) = row

            unique_id = random.randint(10**9, (10**10) - 1)
            unique_id_str = str(unique_id)
            unique_id_str_padded = unique_id_str.zfill(10)
            vocdata_uri = vocdata[unique_id_str_padded]

            g.add((vocdata_uri, RDF.type, voc.Course))
            g.add((vocdata_uri, FOAF.name, Literal(long_title)))
            g.add((vocdata_uri, voc.courseSubject, Literal(subject)))
            g.add((vocdata_uri, voc.courseNumber, Literal(catalog)))
            g.add((vocdata_uri, voc.courseCredits, Literal(class_units)))
            g.add((vocdata_uri, voc.courseDescription, Literal(course_description)))

            if subject.startswith("COMP") and catalog in ["6741", "6721"]:
                course_ids[(subject, catalog)] = unique_id_str_padded

            university_uri = URIRef("http://dbpedia.org/resource/Concordia_University")
            if university_uri in university_ids:
                university_vocdata_id = university_ids[university_uri]
                g.add((vocdata_uri, voc.offeredBy, university_vocdata_id))

    return g, course_ids


def createLecturesRDF(graph, course_folder, courses):
    lectures_folder = os.path.join(course_folder, "lectures")
    if not os.path.exists(lectures_folder):
        print(f"No lectures folder found for course: {course_folder}")
        return

    course_code = lectures_folder.split("/")[1]
    for course_key, course_id in courses.items():
        if "".join(course_key) == course_code:
            break

    for lecture_folder in os.listdir(lectures_folder):
        lecture_path = os.path.join(lectures_folder, lecture_folder)
        if not os.path.isdir(lecture_path):
            continue

        lecture_number, lecture_name = lecture_folder.split("_")

        lecture_uri = URIRef(vocdata[urllib.parse.quote(lecture_path)])
        graph.add((lecture_uri, RDF.type, voc.Lecture))
        graph.add((lecture_uri, voc.LectureNumber, Literal(lecture_number)))
        graph.add((lecture_uri, FOAF.name, Literal(lecture_name)))
        graph.add((lecture_uri, voc.BelongsTo, vocdata[course_id]))

        for content_file in os.listdir(lecture_path):
            content_path = os.path.join(lecture_path, content_file)
            content_type = None
            if content_file.startswith("slides"):
                content_type = voc.Slides
            elif content_file.startswith("worksheet"):
                content_type = voc.Worksheets
            elif content_file.startswith("assignment"):
                content_type = voc.OtherMaterial
            elif content_file.startswith("labs"):
                content_type = voc.OtherMaterial
            elif content_file.startswith("readings"):
                content_type = voc.Readings
            elif content_file.startswith("AdditionalResources.txt"):
                content_type1 = voc.AdditionalResources
                if content_type1:
                    with open(content_path, "r") as file:
                        for line in file:
                            resource = line.strip()
                            content_uri = URIRef(urllib.parse.quote(resource))
                            graph.add((content_uri, RDF.type, content_type1))
                            graph.add((lecture_uri, voc.LectureContent, content_uri))

            if content_type:
                content_uri = URIRef(vocdata[urllib.parse.quote(content_path)])
                graph.add((content_uri, RDF.type, content_type))
                graph.add((lecture_uri, voc.LectureContent, content_uri))


def createTopicsRDF(csv_file):
    g = Graph()
    g.bind("voc", voc)
    g.bind("vocdata", vocdata)
    g.bind("dbp", dbp)
    with open(csv_file, newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            unique_id = random.randint(10**9, (10**10) - 1)
            unique_id_str = str(unique_id)
            unique_id_str_padded = unique_id_str.zfill(10)
            vocdata_uri = vocdata[unique_id_str_padded]
            topic_name = Literal(row[1])
            topic_provenance = URIRef(row[2])
            topic_link = dbp[row[3]]

            g.add((vocdata_uri, RDF.type, voc.Topic))
            g.add((vocdata_uri, FOAF.name, topic_name))
            g.add((vocdata_uri, voc.TopicProvenance, topic_provenance))
            g.add((vocdata_uri, RDFS.seeAlso, topic_link))

    return g


def createStudentsRDF(csv_file):
    g = Graph()
    g.bind("voc", voc)
    g.bind("vocdata", vocdata)

    with open(csv_file, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            student_uri = vocdata[row["ID Number"]]
            g.add((student_uri, RDF.type, voc.Student))
            g.add((student_uri, FOAF.givenName, Literal(row["First Name"])))
            g.add((student_uri, FOAF.familyName, Literal(row["Last Name"])))
            g.add((student_uri, voc.IDNumber, Literal(row["ID Number"])))
            g.add((student_uri, FOAF.mbox, Literal(row["Email"])))

            competencies_bnode = BNode()
            g.add((competencies_bnode, voc.Course, Literal(row["Completed Course"])))
            g.add((student_uri, voc.Competency, competencies_bnode))
            competencies = row["Competencies"].split(",")
            for comp in competencies:
                g.add((competencies_bnode, voc.competencies, Literal(comp.strip())))

            course_and_grade = BNode()
            g.add((student_uri, voc.CompletedCourse, course_and_grade))
            g.add((course_and_grade, voc.Course, Literal(row["Completed Course"])))
            g.add((course_and_grade, voc.Grade, Literal(row["Grade"])))
    return g


def serialize_rdf_graph(graph, output_file):
    output_folder = "KnowledgeBase"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    turtle_output_file = os.path.join(
        output_folder, output_file.replace(".ttl", "_turtle.ttl")
    )
    graph.serialize(destination=turtle_output_file, format="turtle")
    print(f"Turtle format knowledge base created and saved to {turtle_output_file}.")

    ntriples_output_file = os.path.join(
        output_folder, output_file.replace(".ttl", "_ntriples.nt")
    )
    graph.serialize(destination=ntriples_output_file, format="nt")
    print(
        f"N-Triples format knowledge base created and saved to {ntriples_output_file}."
    )


if __name__ == "__main__":

    universities_rdf, universities = createUniversitiesRDF()
    serialize_rdf_graph(universities_rdf, "universities_data.ttl")

    courses_rdf, courses = createCoursesRDF("Datasets/courses_data.csv", universities)
    serialize_rdf_graph(courses_rdf, "courses_data.ttl")

    g = Graph()
    g.bind("voc", voc)
    g.bind("vocdata", vocdata)
    courses_folders = ["Datasets/COMP6741", "Datasets/COMP6721"]
    for course_folder in courses_folders:
        createLecturesRDF(g, course_folder, courses)

    serialize_rdf_graph(g, "lectures_data.ttl")

    topics_rdf = createTopicsRDF("Datasets/topics_data.csv")
    serialize_rdf_graph(topics_rdf, "topics_data.ttl")

    students_rdf = createStudentsRDF("Datasets/students_data.csv")
    serialize_rdf_graph(students_rdf, "students_data.ttl")
