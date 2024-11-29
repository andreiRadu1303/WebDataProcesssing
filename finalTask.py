import requests
import spacy
from rapidfuzz import fuzz
from llama_cpp import Llama


# Path to language model file
model_path =  "models/llama-2-13b.Q4_K_M.gguf"

nlp = spacy.load("en_core_web_sm")

question_to_property_map = {
    "capital": "P36",
    "population": "P1082",
    "birthdate": "P569",
    "deathdate": "P570",
    "leader": "P6",
    "country": "P17",
}

def QueryModel(question):
    # Display query
    print(f"Asking the question: \"{question}\" to the model. Please wait...")
    llm = Llama(model_path=model_path, verbose=False)
    # Query the model
    output = llm(
        question,              # The input prompt/question
        max_tokens=32,         # Limit the response to 32 tokens
        stop=["Q:", "\n"],     # Stop generation if a new question or line starts
        echo=False             # Include the prompt in the output
    )
    # Display the raw output (B)
    raw_text = output['choices'][0]['text'] if 'choices' in output and output['choices'] else ""
    print("Here is the output:")
    print(raw_text)
    return raw_text

def extract_claim(question):
    doc = nlp(question)
    subject, predicate, obj = None, None, None
    entities = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC", "PERSON", "ORG"]]
    for token in doc:
        if token.lemma_ in question_to_property_map.keys():
            predicate = token.lemma_
        if token.dep_ in ["attr", "dobj", "pobj", "nummod"]:
            obj = token.text
    if entities:
        subject = entities[0]
    return subject, predicate, obj
def extract_entities_with_urls(text):
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents]
    output_lines = []

    for entity in entities:
        # Format the Wikipedia URL (replace spaces with underscores for valid URLs)
        wikipedia_url = f"https://en.wikipedia.org/wiki/{entity.replace(' ', '_')}"
        output_lines.append(f"{entity}\t{wikipedia_url}")
    
    if(entities):
        print("Entities extracted:\n" + "\n".join(output_lines))
    return "\n".join(output_lines)

def query_wikidata_entity(entity_name):
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={entity_name}&language=en&format=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'search' in data and len(data['search']) > 0:
            entity_id = data['search'][0]['id']
            return entity_id
    return None
def query_wikidata_relationship(subject, predicate):
    subject_id = query_wikidata_entity(subject)
    if not subject_id:
        return None
    property_id = question_to_property_map.get(predicate)
    if not property_id:
        return None
    query = f"""
    SELECT ?objectLabel WHERE {{
      wd:{subject_id} wdt:{property_id} ?object.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params={"query": query})
    if response.status_code == 200:
        data = response.json()
        objects = [item["objectLabel"]["value"] for item in data["results"]["bindings"]]
        return objects
    return None
def query_wikidata_question(subject, predicate):
    if predicate not in question_to_property_map:
        return None  # Unsupported predicate

    predicate_id = question_to_property_map[predicate]
    
    # Query Wikidata for the subject
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={subject}&language=en&format=json"
    response = requests.get(url)
    if response.status_code != 200:
        return None

    data = response.json()
    if not data['search']:
        return None  # Subject not found
    
    subject_id = data['search'][0]['id']  # Get the Wikidata entity ID for the subject

    # Query Wikidata for the specific property (predicate)
    sparql_query = f"""
    SELECT ?objectLabel WHERE {{
      wd:{subject_id} wdt:{predicate_id} ?object.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    sparql_url = "https://query.wikidata.org/sparql"
    sparql_response = requests.get(sparql_url, params={"query": sparql_query, "format": "json"})
    
    if sparql_response.status_code != 200:
        return None

    sparql_data = sparql_response.json()
    objects = [binding['objectLabel']['value'] for binding in sparql_data['results']['bindings']]
    return objects

def process_question_and_answer(question, answer):
    extract_entities_with_urls(question)
    extract_entities_with_urls(answer)
    subject, predicate, obj = extract_claim(question)
    if not subject or not predicate:
        return "Could not parse the question properly."
    processed_answer = normalize_answer(answer)
    if not processed_answer:
        return "Could not process the answer."
    print(f"Processed answer: {processed_answer}")  # Print processed answer
    if (processed_answer == 'yes' or processed_answer == 'no'):
        return check_statement(question, processed_answer)
    return verify_answer(subject, predicate, processed_answer)

def normalize_answer(answer):
    yes_variants = ["yes", "yeah", "yep", "sure", "correct", "affirmative"]
    no_variants = ["no", "nope", "nah", "incorrect", "negative"]
    answer_lower = answer.lower()
    if any(variant in answer_lower for variant in yes_variants):
        return "yes"
    if any(variant in answer_lower for variant in no_variants):
        return "no"
    doc = nlp(answer)
    entities = [ent.text for ent in doc.ents]
    if entities:
        return entities[0]
    return answer.strip()

def check_statement(statement, processed_answer):
    subject, predicate, obj = extract_claim(statement)

    if not subject or not predicate or not obj:
        return "Could not parse the statement properly."

    # Query Wikidata for the relationship
    valid_objects = query_wikidata_question(subject, predicate)

    if valid_objects is None:
        return f"Could not verify the statement: {statement}"
    match_found = any(fuzz.ratio(obj.lower(), valid_obj.lower()) > 85 for valid_obj in valid_objects)
    expected_truth = processed_answer.lower() == "yes"

    if match_found == expected_truth:
        return "correct"
    else:
        return "incorrect"
def verify_answer(subject, predicate, answer):
        valid_objects = query_wikidata_relationship(subject, predicate)
        if valid_objects is None:
            return f"Could not verify the statement about {subject}."

        match_found = any(fuzz.ratio(answer.lower(), obj.lower()) > 85 for obj in valid_objects)
        if match_found:
            return "correct"
        else:
            return "incorrect"


questions_and_answers = [
    ("What is the capital of France?", "It is called Paris"),
    ("What is the capital of France?", "I think it's Berlin"),
    ("The capital of France called Paris", "yes it is"),
    ("The capital of France called Paris", "no it isn't"),
    ("The capital of France called Berlin", "yes it is"),
    ("The capital of France called Berlin", "no it isn't"),
    ("The capital of France is called Berlin or Paris", "it is Paris, it isn't Berlin"),
    ("The capital of France is called Berlin or Paris", "it is Berlin, it isn't Paris"),
    ("The capital of France is called Berlin or Paris", "it is Berlin"),
    ("Who is the leader of Germany?", "It is Olaf Scholz"),
    ("Who is the leader of Germany?", "It is Fritz Fritzgerald"),
]

#* Can be commented out to just run the auto-tests*#
result = process_question_and_answer("What is the capital of France?" ,QueryModel("What is the capital of France?"))
print(f"Question: What is the capital of France? -> Paris -> Result: {result}")
print("*--------------*-------------*--------------*")

for question, answer in questions_and_answers:
    result = process_question_and_answer(question, answer)
    print(f"Question: {question} -> Answer: {answer} -> Result: {result}")
    print("*--------------*-------------*--------------*")
