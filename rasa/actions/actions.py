from rasa_sdk import Action, Tracker
import requests
from typing import Any, Dict, List, Text
from rasa_sdk.executor import CollectingDispatcher
from transformers import AutoModelForCausalLM, AutoTokenizer


class ActionPersonInfo(Action):
    def name(self):
        return "action_person_info"

    def run(self, dispatcher, tracker, domain):
        person_name = tracker.get_slot("person")
        message = f"If you're asking about {person_name}, Best Human Ever!!! ;-)"
        dispatcher.utter_message(text=message)
        return []


class ActionListCourses(Action):
    def name(self):
        return "action_list_courses"

    def run(self, dispatcher, tracker, domain):
        university = tracker.get_slot("university")

        sparql_query = f"""PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
                        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                        SELECT DISTINCT (?course as ?courseURI) ?courseName  ?courseSubject ?courseNumber ?universityName (?university as ?universityURI) 
                        WHERE {{
                        ?university a voc:University;
                                    foaf:name "{university}" .  
                        ?course a voc:Course;
                                foaf:name ?courseName;
                                voc:courseSubject ?courseSubject;
                                voc:courseNumber ?courseNumber;
                                voc:offeredBy ?university .
                        ?university foaf:name ?universityName .
                        }}
                        LIMIT 20
                        """
        print(sparql_query)
        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }
        params = {"query": sparql_query}
        response = requests.post(fuseki_endpoint, headers=headers, data=params)

        if response.status_code == 200:
            sparql_results = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response(university, sparql_results)
        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[str]:
        courses = []
        for result in json_results["results"]["bindings"]:
            courses.append(result["courseName"]["value"])
        return courses

    def generate_response(self, university: str, courses: List[str]) -> str:
        if not courses:
            return f"Sorry no courses found!"

        response = f"Here are some of the courses are offered by {university}:\n"
        for course in courses:
            response += f"- {course}\n"

        return response


class ActionFindCoursesByTopic(Action):
    def name(self) -> Text:
        return "action_find_courses_by_topic"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        # topic_name = tracker.get_slot("topic")
        topic_name = next(tracker.get_latest_entity_values("topic"), None)
        sparql_query = f"""PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
                        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                        SELECT DISTINCT (?courseId as ?courseURI)  ?courseName ?courseSubject ?courseNumber ?topicName
                        WHERE {{
                        ?topic a voc:Topic ;
                            foaf:name ?topicName;
                                foaf:name "{topic_name}" ;  
                                voc:TopicProvenance ?topicProvenance .
                        ?lecture a voc:Lecture;
                                voc:LectureContent ?topicProvenance;
                                voc:BelongsTo ?courseId.
                        ?courseId a voc:Course;
                                foaf:name ?courseName;
                            voc:courseSubject ?courseSubject;
                            voc:courseNumber ?courseNumber.    
                        }}
                        """
        print(sparql_query)
        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }
        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            sparql_results = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_topic(topic_name, sparql_results)
        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[str]:
        courses = []
        for result in json_results["results"]["bindings"]:
            courses.append(result["courseName"]["value"])
        return courses

    def generate_response_for_topic(self, topic: str, courses: List[str]) -> str:
        if not courses:
            return f"Sorry no such courses found, discussing {topic}\n"

        response = f"Courses discussing {topic}:\n"
        for course in courses:
            response += f"- {course}\n"

        return response


class ActionFindTopicsInLecture(Action):
    def name(self) -> Text:
        return "action_find_topics_by_course_lecture"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        course_name = next(tracker.get_latest_entity_values("course"), None)
        lecture_number = next(tracker.get_latest_entity_values("lecture_number"), None)

        sparql_query = f"""
                     PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                    PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
                    PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
                    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                        SELECT ?topicName (COUNT(?course) as ?topicFrequency)
                        WHERE {{
                        ?course a voc:Course;
                                foaf:name ?courseName;
                                foaf:name "{course_name}" .  
                            
                        ?lectures voc:BelongsTo ?course;
                                    voc:LectureNumber ?lectureNumber;
                                    voc:LectureContent ?lectureContent.
                                    
                        ?topic a voc:Topic;
                                voc:TopicProvenance ?lectureContent;
                                foaf:name ?topicName.
                                FILTER(?lectureNumber = "{lecture_number}")
                        }}
                        GROUP BY ?topicName
                        ORDER BY DESC(COUNT(?course))
                        LIMIT 10
                                                """

        print(sparql_query)

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            sparql_results = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_lecture(
            course_name, lecture_number, sparql_results
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[str]:
        topics = []
        for result in json_results["results"]["bindings"]:
            topics.append(result["topicName"]["value"])
        return topics

    def generate_response_for_lecture(
        self, course: str, lecture_number: str, topics: List[str]
    ) -> str:
        if not topics:
            return f"Sorry, no topics found for lecture {lecture_number} in {course}.\n"

        response = f"Topics covered in lecture {lecture_number} of {course}:\n"
        for topic in topics:
            response += f"- {topic}\n"

        return response


class ActionFindCoursesBySubject(Action):
    def name(self) -> Text:
        return "action_find_courses_by_subject"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        university_name = next(tracker.get_latest_entity_values("university"), None)
        subject = next(tracker.get_latest_entity_values("subject"), None)
        sparql_query = f"""
                        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
                        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                        SELECT DISTINCT ?courseName (?courseId as ?courseURI) ?courseSubject ?courseNumber
                        WHERE {{
                        ?university foaf:name "{university_name}" . 
                        
                        ?courseId a voc:Course;
                                    voc:offeredBy ?university;
                                    voc:courseSubject ?courseSubject;
                                    foaf:name ?courseName;
                                    voc:courseNumber ?courseNumber .
                        
                        FILTER(?courseSubject = "{subject}")
                        }}
                        LIMIT 10
                        """

        print(sparql_query)

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            courses = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_subject(university_name, courses)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        courses = []
        for result in json_results["results"]["bindings"]:
            course_details = {
                "name": result["courseName"]["value"],
                "uri": result["courseURI"]["value"],
                "subject": result["courseSubject"]["value"],
                "number": result["courseNumber"]["value"],
            }
            courses.append(course_details)
        return courses

    def generate_response_for_subject(
        self, university: str, courses: List[Dict[Text, Any]]
    ) -> str:
        if not courses:
            return (
                f"Sorry, no courses found offered by {university} within the subject.\n"
            )

        response = f"Courses offered by {university} within the subject:\n"
        for course in courses:
            response += f"- Name: {course['name']}, Subject: {course['subject']}, Number: {course['number']}\n"

        return response


class ActionFindMaterialsByTopic(Action):
    def name(self) -> Text:
        return "action_find_recommended_material"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        topic_name = next(tracker.get_latest_entity_values("topic"), None)

        sparql_query = f"""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
            PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
       SELECT  (?topic as ?topicURI) ?topicName (?course as ?courseURI) ?courseNo  ?materials
        WHERE {{
        ?course a voc:Course;
                voc:courseSubject "{subject}";
                voc:courseNumber "{subjectNumber}";
                foaf:name ?courseName;
                voc:courseSubject ?courseSub;
                voc:courseNumber ?courseNum.
        
            ?lecture a voc:Lecture;
            foaf:name ?lectureName ;
            voc:LectureContent ?lectureContent;
            voc:BelongsTo ?course;
            voc:LectureContent ?materials.
        
        ?topic a voc:Topic;
            foaf:name ?topicName;
            foaf:name "{topic_name}";
            voc:TopicProvenance ?lectureContent;
        BIND(CONCAT(?courseSub, " ", ?courseNum) AS ?courseNo)
        }}LIMIT 10
        """

        print(sparql_query)

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            materials = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_topic(
            subjectNumber, topic_name, materials
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        materials = []
        for result in json_results["results"]["bindings"]:
            material_details = {
                "topic": result["topicName"]["value"],
                "course": result["courseNo"]["value"],
                "materials": result["materials"]["value"],
            }
            materials.append(material_details)
        return materials

    def generate_response_for_topic(
        self, course_number: str, topic_name: str, materials: List[Dict[Text, Any]]
    ) -> str:
        if not materials:
            return f"Sorry, no materials found for topic {topic_name} in course {course_number}.\n"

        response = (
            f"Materials recommended for topic {topic_name} in course {course_number}:\n"
        )
        for material in materials:
            response += f"- {material['materials']}\n"

        return response


class ActionFindCreditsBySubject(Action):
    def name(self) -> Text:
        return "action_find_credits"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
       SELECT (?course as ?courseURI) ?courseName ?courseSubject ?courseNumber ?type ?credits
        WHERE {{
        ?course a voc:Course;
                foaf:name ?courseName;
                voc:courseSubject ?courseSubject;
                voc:courseNumber ?courseNumber;
                voc:CourseType ?type;
                voc:courseCredits ?credits.
                
        FILTER(?courseSubject = "{subject}" && ?courseNumber = "{subjectNumber}")
        }}
        """

        print(sparql_query)

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            credits = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_credits(
            subjectNumber, subject, credits
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        credits = []
        for result in json_results["results"]["bindings"]:
            credit_details = {
                "course": result["courseName"]["value"],
                "subject": result["courseSubject"]["value"],
                "number": result["courseNumber"]["value"],
                "credits": result["credits"]["value"],
            }
            credits.append(credit_details)
        return credits

    def generate_response_for_credits(
        self, subject_number: str, subject: str, credits: List[Dict[Text, Any]]
    ) -> str:
        if not credits:
            return f"Sorry, no credits found for subject {subject} and number {subject_number}.\n"

        response = f"Credits for subject {subject} and number {subject_number}:\n"
        for credit in credits:
            response += (
                f"- Course: {credit['course']}\n  Credits: {credit['credits']}\n"
            )

        return response


class ActionFindAdditionalResources(Action):
    def name(self) -> Text:
        return "action_find_additional_resources"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        sparql_query = f"""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
            PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
       SELECT  DISTINCT (?course as ?courseURI) ?courseNo  ?additionalResources 
        WHERE {{
        ?course a voc:Course;
                voc:courseSubject "{subject}";
                voc:courseNumber "{subjectNumber}";
                foaf:name ?courseName;
                voc:courseSubject ?courseSub;
                voc:courseNumber ?courseNum.
        
            ?lecture a voc:Lecture;
            foaf:name ?lectureName ;
            voc:LectureContent ?lectureContent;
            voc:BelongsTo ?course;
            voc:LectureContent ?additionalResources.  
            ?additionalResources a voc:AdditionalResources.
        
        
        BIND(CONCAT(?courseSub, " ", ?courseNum) AS ?courseNo)
        }}LIMIT 10
        """

        print(sparql_query)

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            resources = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_resources(resources)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        resources = []
        for result in json_results["results"]["bindings"]:
            resource_details = {
                "courseNo": result["courseNo"]["value"],
                "additionalResources": result["additionalResources"]["value"],
            }
            resources.append(resource_details)
        return resources

    def generate_response_for_resources(self, resources: List[Dict[Text, Any]]) -> str:
        if not resources:
            return "Sorry, no additional resources found."

        response = "Additional Resources:\n"
        for resource in resources:
            response += f"-{resource['additionalResources']}\n"

        return response


class ActionQueryLectureContent(Action):
    def name(self) -> Text:
        return "action_query_lecture_content"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        lecture_number = next(tracker.get_latest_entity_values("lecture_number"), None)

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT (?course as ?courseURI) ?courseNo (?lecture as ?lectureURI) ?lectureName ?lectureNumber ?lectureContent
        WHERE {{
        ?course a voc:Course ;
                voc:courseSubject "{subject}" ;
                voc:courseNumber "{subjectNumber}" ;
                voc:courseSubject ?courseSub;
                voc:courseNumber ?courseNum.
        
        ?lecture a voc:Lecture ;
                voc:BelongsTo ?course ;
                voc:LectureNumber "{lecture_number}";
                voc:LectureNumber ?lectureNumber;
                foaf:name ?lectureName;
                voc:LectureContent ?lectureContent.
        BIND(CONCAT(?courseSub, " ", ?courseNum) AS ?courseNo)
        }}LIMIT 10
        """
        print(sparql_query)
        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            lecture_details = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_lecture_content(
            subjectNumber, lecture_number, lecture_details
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> Dict[Text, Any]:
        lecture_details = {}
        for result in json_results["results"]["bindings"]:
            lecture_details = {
                "course_number": result["courseNo"]["value"],
                "lecture_name": result["lectureName"]["value"],
                "lecture_number": result["lectureNumber"]["value"],
                "lecture_content": result["lectureContent"]["value"],
            }
        return lecture_details

    def generate_response_for_lecture_content(
        self, course_number: str, lecture_number: str, lecture_details: Dict[Text, Any]
    ) -> str:
        if not lecture_details:
            return f"Sorry, no lecture content found for lecture {lecture_number} in course {course_number}.\n"

        response = (
            f"Lecture content for lecture {lecture_number} in course {course_number}:\n"
        )
        response += f"- Lecture Name: {lecture_details['lecture_name']}\n"
        response += f"- Lecture Content: {lecture_details['lecture_content']}\n"

        return response


class ActionQueryReadingMaterials(Action):
    def name(self) -> Text:
        return "action_query_reading_materials"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        topic = next(tracker.get_latest_entity_values("topic"), None)
        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)

        sparql_query = f"""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
            PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT  (?topic as ?topicURI) ?topicName (?course as ?courseURI) ?courseNo  ?readingMaterials
            WHERE {{
            ?course a voc:Course;
                    voc:courseSubject "{subject}";
                    voc:courseNumber "{subjectNumber}";
                    foaf:name ?courseName;
                    voc:courseSubject ?courseSub;
                    voc:courseNumber ?courseNum.
            
                ?lecture a voc:Lecture;
                foaf:name ?lectureName ;
                voc:LectureContent ?lectureContent;
                voc:BelongsTo ?course;
                voc:LectureContent ?readingMaterials.
                ?readingMaterials a voc:Readings.
            
            ?topic a voc:Topic;
                foaf:name ?topicName;
                foaf:name "{topic}";
                voc:TopicProvenance ?lectureContent;
            BIND(CONCAT(?courseSub, " ", ?courseNum) AS ?courseNo)
            }}LIMIT 10
        """
        print(sparql_query)
        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            materials = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_reading_materials(
            subjectNumber, topic, materials
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        materials = []
        for result in json_results["results"]["bindings"]:
            material_details = {
                "course_number": result["courseNo"]["value"],
                "topic_name": result["topicName"]["value"],
                "reading_materials": result["readingMaterials"]["value"],
            }
            materials.append(material_details)
        return materials

    def generate_response_for_reading_materials(
        self, course_number: str, topic: str, materials: List[Dict[Text, Any]]
    ) -> str:
        if not materials:
            return f"Sorry, no reading materials found for topic {topic} in course {course_number}.\n"

        response = f"Reading materials recommended for studying {topic} in course {course_number}:\n"
        for material in materials:
            response += f"- {material['reading_materials']}\n"

        return response


class ActionQueryCourseCompetencies(Action):
    def name(self) -> Text:
        return "action_query_course_competencies"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        subjectNumber = subject + subjectNumber
        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT DISTINCT ?course ?competency 
        WHERE {{
        ?student a voc:Student ;
                voc:Competency ?competencyNode .
        ?competencyNode voc:Course ?course ;
                    voc:competencies ?competency .
        ?topic a voc:Topic;
                    foaf:name ?competency.
        FILTER(?course = "{subjectNumber}")
        }}LIMIT 10
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            competencies = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_competencies(
            subjectNumber, competencies
        )

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        competencies = []
        for result in json_results["results"]["bindings"]:
            competency_details = {
                "course": result["course"]["value"],
                "competency": result["competency"]["value"],
            }
            competencies.append(competency_details)
        return competencies

    def generate_response_for_competencies(
        self, course_number: str, competencies: List[Dict[Text, Any]]
    ) -> str:
        if not competencies:
            return f"Sorry, no competencies found for course {course_number}.\n"

        response = f"Competencies gained after completing course {course_number}:\n"
        for competency in competencies:
            response += f"- {competency['competency']}\n"

        return response


class ActionQueryStudentGrades(Action):
    def name(self) -> Text:
        return "action_query_student_grades"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        student_id = next(tracker.get_latest_entity_values("student_id"), None)
        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        subjectNumber = subject + subjectNumber
        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT DISTINCT (?student as ?studentURI) ?IDnumber ?givenName ?familyName ?course ?grade 
        WHERE {{
        ?student a voc:Student;
                voc:IDNumber "{student_id}";      
                voc:CompletedCourse ?completedCourse.
        
        ?completedCourse voc:Course ?course ;                   
                        voc:Grade ?grade .
        
        ?student foaf:givenName ?givenName ;
                foaf:familyName ?familyName ;
                voc:IDNumber ?IDnumber.
        
        FILTER (?course = "{subjectNumber}")
        }}
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            grades = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_grades(student_id, grades)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        grades = []
        for result in json_results["results"]["bindings"]:
            grade_details = {
                "IDnumber": result["IDnumber"]["value"],
                "givenName": result["givenName"]["value"],
                "familyName": result["familyName"]["value"],
                "course": result["course"]["value"],
                "grade": result["grade"]["value"],
            }
            grades.append(grade_details)
        return grades

    def generate_response_for_grades(
        self, student_id: str, grades: List[Dict[Text, Any]]
    ) -> str:
        if not grades:
            return f"Sorry, no grades found for student with ID number {student_id} in the specified course.\n"

        response = f"Grades achieved by student with ID number {student_id} in the specified course:\n"
        for grade in grades:
            response += f"- Name: {grade['givenName']} {grade['familyName']}\n"
            response += f"  Course: {grade['course']}\n"
            response += f"  Grade: {grade['grade']}\n"

        return response


class ActionQueryCompletedStudents(Action):
    def name(self) -> Text:
        return "action_query_completed_students"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        subject = next(tracker.get_latest_entity_values("subject"), None)
        subjectNumber = next(tracker.get_latest_entity_values("subjectNumber"), None)
        subjectNumber = subject + subjectNumber

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
       SELECT DISTINCT (?student as ?studentURI) ?studentID ?givenName ?familyName ?email
        WHERE {{
        ?student a voc:Student;
                voc:CompletedCourse ?completedCourse;
                foaf:givenName ?givenName;
                foaf:familyName ?familyName;
                voc:IDNumber ?studentID;
                foaf:mbox ?email.
        ?completedCourse voc:Course ?course ;
                
        FILTER(?course = "{subjectNumber}")
        }}
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            students = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_students(subjectNumber, students)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        students = []
        for result in json_results["results"]["bindings"]:
            student_details = {
                "studentID": result["studentID"]["value"],
                "givenName": result["givenName"]["value"],
                "familyName": result["familyName"]["value"],
                "email": result["email"]["value"],
            }
            students.append(student_details)
        return students

    def generate_response_for_students(
        self, course_number: str, students: List[Dict[Text, Any]]
    ) -> str:
        if not students:
            return f"No students found who have completed course {course_number}.\n"

        response = f"Students who have completed course {course_number}:\n"
        for student in students:
            response += f"- Name: {student['givenName']} {student['familyName']}\n"
            response += f"  Student ID: {student['studentID']}\n"
            response += f"  Email: {student['email']}\n"

        return response


class ActionQueryTranscript(Action):
    def name(self) -> Text:
        return "action_query_transcript"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        student_id = next(tracker.get_latest_entity_values("student_id"), None)

        sparql_query = f"""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
            PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            SELECT DISTINCT ?course ?grade (?course1 as ?courseURI)
            WHERE {{
            ?student a voc:Student;
                    voc:IDNumber "{student_id}";      
                    voc:CompletedCourse ?completedCourse.
            
            ?completedCourse voc:Course ?course ;
                                voc:Grade ?grade .
            BIND(REPLACE(STR(?course), "[^A-Za-z]+", "") AS ?alphabeticPrefix).
            BIND(REPLACE(STR(?course), "[^0-9]+", "") AS ?numericPart).
            
            ?course1 a voc:Course;
                        voc:courseNumber ?numericPart;
                        voc:courseSubject ?alphabeticPrefix;
                        voc:CourseType "Lecture".
            }}
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            transcript = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_transcript(student_id, transcript)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        transcript = []
        for result in json_results["results"]["bindings"]:
            transcript_details = {
                "course": result["course"]["value"],
                "grade": result["grade"]["value"],
                "courseURI": result["courseURI"]["value"],
            }
            transcript.append(transcript_details)
        return transcript

    def generate_response_for_transcript(
        self, student_id: str, transcript: List[Dict[Text, Any]]
    ) -> str:
        if not transcript:
            return f"No transcript found for student with ID number {student_id}.\n"

        response = f"Transcript for student with ID number {student_id}:\n"
        for course in transcript:
            response += f"- Course: {course['course']}\n"
            response += f"  Grade: {course['grade']}\n"
            response += f"  Course URI: {course['courseURI']}\n"

        return response


class ActionQueryCourseDetails(Action):
    def name(self) -> Text:
        return "action_query_course_description"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        course_subject = next(tracker.get_latest_entity_values("subject"), None)
        course_number = next(tracker.get_latest_entity_values("subjectNumber"), None)

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT (?course as ?courseURI) ?courseName ?courseSubject ?courseNumber ?CourseDescription
        WHERE {{
          ?course a voc:Course;
                  foaf:name ?courseName;
                  voc:courseSubject ?courseSubject;
                  voc:courseNumber ?courseNumber;
                  voc:CourseType "Lecture";
                  voc:CourseDescription ?CourseDescription.
                  
          FILTER(?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}")
        }}
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            course_details = self.parse_sparql_results(response.json())
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )
            return []

        response_text = self.generate_response_for_course_details(course_details)

        dispatcher.utter_message(text=response_text)
        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        course_details = []
        for result in json_results["results"]["bindings"]:
            details = {
                "courseURI": result["courseURI"]["value"],
                "courseName": result["courseName"]["value"],
                "courseSubject": result["courseSubject"]["value"],
                "courseNumber": result["courseNumber"]["value"],
                "CourseDescription": result["CourseDescription"]["value"],
            }
            course_details.append(details)
        return course_details

    def generate_response_for_course_details(
        self, course_details: List[Dict[Text, Any]]
    ) -> str:
        if not course_details:
            return "No course details found for the specified subject and number.\n"

        response = "Course Details:\n"
        for details in course_details:
            response += f"- Course URI: {details['courseURI']}\n"
            response += f"  Name: {details['courseName']}\n"
            response += f"  Subject: {details['courseSubject']}\n"
            response += f"  Number: {details['courseNumber']}\n"
            response += f"  Description: {details['CourseDescription']}\n"

        return response


class ActionQueryCourseEventTopics(Action):
    def name(self) -> Text:
        return "action_query_course_event_topics"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        course_subject = next(tracker.get_latest_entity_values("subject"), None)
        course_number = next(tracker.get_latest_entity_values("subjectNumber"), None)
        resource_name = next(tracker.get_latest_entity_values("courseEvent"), None)

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT DISTINCT (?course as ?courseURI) ?courseName (?lectureContent as ?resourceURI) ?ResourceName ?topicName ?wikiURI
        WHERE {{
          ?course a voc:Course;
                  voc:courseSubject ?courseSubject;
                  voc:courseNumber ?courseNumber.
          ?lecture a voc:Lecture;
                  voc:BelongsTo ?course;
                  foaf:name ?lectureName;
                  voc:LectureNumber ?lectureNum;
                  voc:LectureContent ?lectureContent.
          ?topic a voc:Topic;
                  voc:TopicProvenance ?lectureContent;
                  foaf:name ?topicName;
                  rdfs:seeAlso ?wikiURI.
          ?lectureContent voc:ResourceName ?ResourceName.
          BIND(CONCAT(?courseSubject, " ", ?courseNumber) AS ?courseName).
          FILTER(?courseSubject = "{course_subject}" && ?courseNumber = "{course_number}" && ?ResourceName ="{resource_name}" )
        }}LIMIT 10
        """
        print(sparql_query)
        fuseki_endpoint = "http://localhost:3030/roboprof/query"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )
        print(response.status_code)
        if response.status_code == 200:
            topics = self.parse_sparql_results(response.json())
            response_text = self.generate_response_for_topics(topics)
            dispatcher.utter_message(text=response_text)
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )

        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        topics = []
        for result in json_results["results"]["bindings"]:
            topic_details = {
                "resourceURI": result["resourceURI"]["value"],
                "topicName": result["topicName"]["value"],
                "wikiURI": result["wikiURI"]["value"],
            }
            topics.append(topic_details)
        return topics

    def generate_response_for_topics(self, topics: List[Dict[Text, Any]]) -> str:
        if not topics:
            return "No topics found for the specified course event."

        response = "Topics covered:\n"
        for topic in topics:
            response += (
                f"- Topic: {topic['topicName']} (See more: {topic['wikiURI']})\n"
            )

        return response


class ActionQueryTopicCoverage(Action):
    def name(self) -> Text:
        return "action_query_topic_coverage"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        topic_name = next(tracker.get_latest_entity_values("topic"), None)

        if not topic_name:
            dispatcher.utter_message(text="Please specify a topic to search for.")
            return []

        sparql_query = f"""
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX vocdata: <file:///Users/jatin/workspace/roboprof/data#>
        PREFIX voc: <file:///Users/jatin/workspace/roboprof/vocabulary.ttl/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
        SELECT ?topicName (?course as ?courseURI) ?courseName  (COUNT(?lectureNum) AS ?occurrences)  (GROUP_CONCAT(DISTINCT CONCAT("Lecture ", STR(?lectureNum)); separator=", ") AS ?lectureNumbers) (GROUP_CONCAT(DISTINCT ?Resourcename; separator=", ") AS ?ResourceName) 
        WHERE {{
          ?topic a voc:Topic;
                rdfs:seeAlso ?wikiURI;
                voc:TopicProvenance ?lectureContent;
                foaf:name ?topicName.    

          ?lectures a voc:Lecture;       
                voc:LectureContent ?lectureContent;
                voc:LectureNumber ?lectureNum;
                voc:BelongsTo ?course.

          ?course a voc:Course;
                  voc:courseSubject ?courseSubject;
                  voc:courseNumber ?courseNumber.
          ?lectureContent voc:ResourceName ?Resourcename.
           BIND(CONCAT("Lecture ", STR(?lectureNum)) AS ?lectureNumber).
          BIND(CONCAT(?courseSubject, " ", ?courseNumber) AS ?courseName).
          FILTER(?topicName = "{topic_name}").
        }}
        GROUP BY ?topicName ?course ?courseName
        ORDER BY DESC(?occurrences)
        """

        fuseki_endpoint = "http://localhost:3030/roboprof/query"
        print(sparql_query)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        }

        response = requests.post(
            fuseki_endpoint, headers=headers, data={"query": sparql_query}
        )

        if response.status_code == 200:
            results = self.parse_sparql_results(response.json())
            response_text = self.generate_response_for_topic_coverage(
                topic_name, results
            )
            dispatcher.utter_message(text=response_text)
        else:
            dispatcher.utter_message(
                text="There was an error processing your request. Please try again later."
            )

        return []

    def parse_sparql_results(self, json_results: Dict) -> List[Dict[Text, Any]]:
        coverage = []
        for result in json_results["results"]["bindings"]:
            coverage_details = {
                "courseName": result["courseName"]["value"],
                "occurrences": result["occurrences"]["value"],
                "lectureNumbers": result["lectureNumbers"]["value"],
                "ResourceName": result["ResourceName"]["value"],
            }
            coverage.append(coverage_details)
        return coverage

    def generate_response_for_topic_coverage(
        self, topic_name: str, coverage: List[Dict[Text, Any]]
    ) -> str:
        if not coverage:
            return f"No course events found covering the topic {topic_name}."

        response = f"Course events covering the topic {topic_name}:\n"
        for item in coverage:
            response += f"- {item['courseName']}: {item['occurrences']} times, in {item['lectureNumbers']}, Resources: {item['ResourceName']}\n"

        return response
