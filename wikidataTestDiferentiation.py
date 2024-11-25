import re
import requests
from fuzzywuzzy import fuzz
import spacy

nlp = spacy.load("en_core_web_sm")


# Function to send SPARQL query to Wikidata
def query_wikidata(query):
    endpoint_url = "https://query.wikidata.org/sparql"
    headers = {"User-Agent": "python-wikidata"}
    params = {
        'query': query,
        'format': 'json'
    }
    
    response = requests.get(endpoint_url, headers=headers, params=params)
    return response.json()

# Function to extract entity from the question prompt
def extract_entity_from_prompt(prompt):
    # Using regex to extract the most likely entity (e.g., "capital of France" -> "France")
    match = re.search(r"of (\w+)", prompt)
    if match:
        return match.group(1)
    return None

# Map of question types to Wikidata property IDs
question_to_property_map = {
    "capital": "P36",  # Property ID for capital city
    "population": "P1082",  # Property ID for population
    "birthdate": "P569",  # Property ID for date of birth
    "deathdate": "P570",  # Property ID for date of death
    "leader": "P6",  # Property ID for leader of a country
    "country": "P17",  # Property ID for country
}

# Function to identify the type of question
def identify_question_type(prompt):
    # Check for keywords that indicate the question type
    prompt = prompt.lower()
    for keyword in question_to_property_map:
        if keyword in prompt:
            return keyword
    return None  # Return None if no known property is found

# Function to check if the answer is yes/no type
def is_yes_no_answer(answer):
    answer = answer.lower()
    if "yes" in answer or "no" in answer:
        return True
    return False

# Function to handle yes/no answers
def handle_yes_no_answer(answer, expected_value):
    answer = answer.lower()
    if "not" in answer or "no" in answer:
        if expected_value == "no":
            return True
        else:
            return False
    else:
        if expected_value == "yes":
            return True
        else:
            return False

def extract_entities(question):
    doc = nlp(question)
    entities = [ent.text for ent in doc.ents]
    return entities

# Function to query Wikidata to verify the truth of an entity's claim
def query_wikidata_1(entity):
    # Encode entity for the API query
    entity_query = entity.replace(" ", "_")
    
    # Construct the Wikidata API URL to fetch data for the entity
    url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={entity_query}&language=en&format=json"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        if 'search' in data and len(data['search']) > 0:
            # Return True if the entity exists in Wikidata
            return True
    return False

# Function to check if a statement is true based on the question and answer
def check_answer(question, answer):
    entities = extract_entities(question)
    
    # Iterate through the entities and query Wikidata for each
    truth_values = [query_wikidata_1(entity) for entity in entities]
    
    # The result is true if all entities are valid (True), otherwise false
    if all(truth_values):
        # If the answer is 'yes', return True, meaning the statement is correct
        return answer.lower() == "yes"
    else:
        # If any entity is not valid, return False
        return False            

# Function to check for Wikidata URLs
def is_wikidata_url(answer):
    # Regex to detect Wikidata URLs (e.g., https://www.wikidata.org/wiki/Q12345)
    wikidata_url_pattern = r'https:\/\/www\.wikidata\.org\/wiki\/Q\d+'
    match = re.match(wikidata_url_pattern, answer)
    if match:
        return match.group(0)  # Return the full URL
    return None

# Function to check if the answer contains a clarification (e.g., "not X" after an answer)
def contains_clarification(answer):
    # We look for phrases like "not X" which typically means clarification (e.g., "not Madrid")
    clarification_pattern = r"not\s+(\w+)"
    if re.search(clarification_pattern, answer):
        return True
    return False

# Function to check the answer using Wikidata
def check_answer_with_wikidata(prompt, answer):

    print("Is yer or no:")
    print(is_yes_no_answer(answer))
    if is_yes_no_answer(answer):
        return check_answer(prompt, answer)

    # Extract the entity from the prompt (e.g., "France" from "What is the capital of France?")
    entity = extract_entity_from_prompt(prompt)
    if not entity:
        return False  # If no entity found, cannot validate

    # Identify the type of the question (e.g., "capital", "population")
    question_type = identify_question_type(prompt)
    if not question_type:
        return False  # If the question type is not recognized, cannot validate
    
    # Get the corresponding Wikidata property
    property_uri = question_to_property_map.get(question_type)
    if not property_uri:
        return False  # If the property is not found, cannot validate

    # Handle the case of clarification (e.g., "not Madrid" in "It's called Paris, not Madrid")
    if contains_clarification(answer):
        return True
    
    
    # If answer contains a Wikidata URL, verify it matches the entity
    wikidata_url = is_wikidata_url(answer)
    if wikidata_url:
        # Extract the entity from the URL (e.g., Q12345 from https://www.wikidata.org/wiki/Q12345)
        entity_id = wikidata_url.split("/")[-1]
        if entity_id.lower() == entity.lower():
            return True
        else:
            return False

    # Construct the SPARQL query to retrieve the entity's information
    query = f"""
    SELECT ?item ?itemLabel ?value ?valueLabel
    WHERE {{
      ?item rdfs:label "{entity}"@en.
      ?item wdt:{property_uri} ?value.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    LIMIT 1
    """
    
    # Query Wikidata
    result = query_wikidata(query)
    
    if 'results' in result and result['results']['bindings']:
        # Get the value from Wikidata (e.g., capital city, population)
        wikidata_value = result['results']['bindings'][0].get('valueLabel', {}).get('value', '').lower()

        # Use fuzzy matching to compare the Wikidata value with the provided answer
        if wikidata_value and fuzz.partial_ratio(wikidata_value, answer.lower()) > 80:  # Allow 80% match
            return True  # The answer is correct
        else:
            print(f"Answer mismatch: Expected '{wikidata_value}', got '{answer}'")
            return False  # The answer is incorrect
    else:
        return False  # Entity not found or property not available

# Example usage
prompt = "What is the capital of France?"
answer = "Paris"
print(prompt)
print(answer)

if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

answer = "Not Paris"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")    

answer = "8, surely"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

answer = "Berlin"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")


answer = "Not Berlin"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

# Case with a negative response
prompt = "Is is the capital of France called Berlin?"


answer = "Yes."
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

answer = "No."
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

# Case with a negative response
prompt = "Is the capital of France called Paris?"

answer = "yes"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

answer = "No."
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

answer = "8, surely"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")


prompt = "Is Albert Einstein a physicist?"

answer = "yes"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

prompt = "Who is Albert Einstein?"

answer = "a physicist"
print(prompt)
print(answer)
if check_answer_with_wikidata(prompt, answer):
    print("The answer is correct.")
else:
    print("The answer is incorrect.")

