import requests
import spacy

# Load the SpaCy model for dependency parsing
nlp = spacy.load("en_core_web_sm")

# Map of question types to Wikidata property IDs
question_to_property_map = {
    "capital": "P36",  # Property ID for capital city
    "population": "P1082",  # Property ID for population
    "birthdate": "P569",  # Property ID for date of birth
    "deathdate": "P570",  # Property ID for date of death
    "leader": "P6",  # Property ID for leader of a country
    "country": "P17",  # Property ID for country
    # Add more predicates as needed
}

def extract_claim(statement):
    doc = nlp(statement)
    subject, predicate, obj = None, None, None

    # Check if the statement starts with "is"
    starts_with_is = doc[0].text.lower() == 'is'

    # Identify potential entities for the subject
    entities = [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC", "PERSON", "ORG"]]

    # Identify the predicate and object
    for token in doc:
        # Predicate should match the question-to-property map
        if token.lemma_ in question_to_property_map.keys():
            predicate = token.lemma_

        # The object can be a proper noun, numerical value, or descriptive noun
        if token.dep_ in ["attr", "dobj", "pobj", "nummod"] and token.text != subject:
            obj = token.text

    # Select the most likely subject from entities
    if entities:
        subject = entities[0]  # Use the first entity as the subject (likely correct in simple statements)

    # If the statement starts with "is", reverse the subject and object
    if starts_with_is:
        subject, obj = obj, subject

    return subject, predicate, obj


# Function to query Wikidata for specific relationships
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

# Function to check if the claim is true
def check_statement(statement):
    subject, predicate, obj = extract_claim(statement)

    print(f"Extracted entities for the statement: '{statement}'")
    print(f"  Subject: {subject}")
    print(f"  Predicate: {predicate}")
    print(f"  Object: {obj}")

    if not subject or not predicate or not obj:
        return "Could not parse the statement properly."

    # Query Wikidata for the relationship
    valid_objects = query_wikidata_question(subject, predicate)

    if valid_objects is None:
        return f"Could not verify the statement: {statement}"

    # Check if the object matches one of the valid objects from Wikidata
    return obj in valid_objects


# Example usage
statement = "The capital of France is Paris"
result = check_statement(statement)
print(result)  # True

statement = "The capital of Frace is Berlin"
result = check_statement(statement)
print(result)  

statement = "Is Berlin the capital of Germany"
result = check_statement(statement)
print(result)  

statement = "Is Berlin the capital of France"
result = check_statement(statement)
print(result)  # False

statement = "The population of France is 67 million"
result = check_statement(statement)
print(result)  # Could not verify or False
