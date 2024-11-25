from llama_cpp import Llama
import spacy
import wikipedia
from wikipedia.exceptions import DisambiguationError
from SPARQLWrapper import SPARQLWrapper, JSON
import re
import requests

# Initialize the Llama model
model_path = "/Users/project/WebdataProvessing/models/llama-2-7b.Q4_K_M.gguf"
llm = Llama(model_path=model_path, verbose=False)

# Initialize spaCy for entity extraction
nlp = spacy.load("en_core_web_sm")

# Function to query the model and get the response
def query_model(question):
    output = llm(
        question,               # The input question
        max_tokens=128,         # Limit the response to a certain number of tokens
        stop=["Q:", "\n"],      # Stop generation when a new question or line appears
        echo=False               # Include the question in the output
    )
    return output['choices'][0]['text']

# Function to extract entities using spaCy
def extract_entities(text):
    doc = nlp(text)
    entities = {}
    for ent in doc.ents:
        entities[ent.text] = f"https://en.wikipedia.org/wiki/{ent.text.replace(' ', '_')}"
    return entities

# Function to determine the answer (yes/no or Wikipedia entity)
def extract_answer(text):
    yes_no_answers = ["yes", "no"]
    
    # Check if the answer is yes/no
    text_lower = text.lower()
    if any(ans in text_lower for ans in yes_no_answers):
        return "yes" if "yes" in text_lower else "no"
    
    # Otherwise, look for Wikipedia entity (like city names, countries, etc.)
    # Use regular expressions to identify proper nouns (likely entities)
    match = re.search(r"([A-Z][a-z]+(?: [A-Z][a-z]+)*)", text)
    if match:
        return f"https://en.wikipedia.org/wiki/{match.group(1).replace(' ', '_')}"
    
    return None

# Function to classify the question type
def classify_question(question):
    if question.lower().startswith(("is", "does", "can", "are")):
        return "yes_no"
    if question.lower().startswith(("what", "who", "where")):
        return "entity"
    return "unknown"

# SPARQL query function for Wikidata
def query_wikidata(entity_label, relation_label):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    
    # Map relation to Wikidata property (this needs a predefined mapping)
    relation_mapping = {
        "capital of": "P36",
        # Add more relations as needed
    }
    relation = relation_mapping.get(relation_label.lower())
    if not relation:
        return []

    # Query for the entity's ID
    entity_query = f"""
    SELECT ?entity WHERE {{
      ?entity rdfs:label "{entity_label}"@en .
    }}
    """
    sparql.setQuery(entity_query)
    sparql.setReturnFormat(JSON)
    try:
        entity_results = sparql.query().convert()
        entity_ids = [res["entity"]["value"].split("/")[-1] for res in entity_results["results"]["bindings"]]
        if not entity_ids:
            return []
        entity_id = entity_ids[0]
    except Exception as e:
        return []
    
    # Query for the desired relation
    sparql.setQuery(f"""
    SELECT ?answer WHERE {{
      wd:{entity_id} wdt:{relation} ?answer .
    }}
    """)
    try:
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        return [res["answer"]["value"].split("/")[-1] for res in results["results"]["bindings"]]
    except Exception as e:
        return []

# Extract entities and relations from a question
def extract_entities_and_relation(question):
    doc = nlp(question)
    entities = [ent.text for ent in doc.ents]
    relation = None

    # Extract potential relation
    if "capital" in question.lower():
        relation = "capital of"
    # Add more relations as needed

    return entities, relation

# Function to get the capital city using Wikidata (more reliable than parsing Wikipedia text)
def get_capital_from_wikidata(country):
    # Prepare the country name for querying (capitalize first letter for standard formatting)
    country = country.capitalize()

    # Wikidata API URL to get the country's claims
    url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&sites=en&titles={country}&props=claims&format=json"
    
    # Make a request to Wikidata API
    response = requests.get(url).json()

    try:
        # Check if the entity exists and if claims for the capital (P36) are present
        entities = response.get("entities", {})
        if entities:
            entity_id = list(entities.keys())[0]
            claims = entities[entity_id].get("claims", {})
            
            # Capital is typically stored under claim P36 (the capital of a country)
            if "P36" in claims:
                capital_entity_id = claims["P36"][0]["mainsnak"]["datavalue"]["value"]["entity-id"]
                capital_name_url = f"https://www.wikidata.org/wiki/{capital_entity_id}"
                return capital_name_url
        return None  # Return None if no capital is found
    except KeyError:
        return KeyError  # Return None in case of any key errors during extraction

# Function to validate the extracted answer
def validate_answer(question, extracted_answer):
    # Extract the country from the question
    country_match = re.search(r"capital of (\w+)", question)
    print(country_match)
    if country_match:
        country = country_match.group(1)
        print(country)  
        # Get capital from Wikidata
        capital_url = get_capital_from_wikidata(country)
        print(capital_url)
        if capital_url:
            # Extract the capital city name from the URL
            capital_name = capital_url.split("/")[-1].lower()
            extracted_city = extracted_answer.split('/')[-1].lower()
            print(extracted_city)
            print(capital_name)
            # Compare the extracted answer with the capital city
            if capital_name == extracted_city:
                return "correct"
            else:
                return "incorrect"
        else:
            return "incorrect"
    
    return "unknown"

# Main processing function
def process_question(question, model_output):
    # Extract entities using spaCy
    entities = extract_entities_and_relation(question)[0]
    print(f"Entities extracted: {entities}")

    # Extract answer
    extracted_answer = extract_answer(model_output)
    print(f"Extracted answer: {extracted_answer}")

    # Validate correctness
    correctness = validate_answer(question, extracted_answer)
    print(f"Correctness: {correctness}")

    return {
        "question": question,
        "raw_output": model_output,
        "entities_extracted": entities,
        "extracted_answer": extracted_answer,
        "correctness": correctness
    }

# Example usage:
question = "What is the capital of France?"
model_output = "Paris"  # Simulated model output
result = process_question(question, model_output)
print(result)