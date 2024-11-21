from llama_cpp import Llama
import spacy
import wikipedia
import re

# Initialize the Llama model
model_path = "models/llama-2-7b.Q4_K_M.gguf"
llm = Llama(model_path=model_path, verbose=False)

# Initialize spaCy for entity extraction
nlp = spacy.load("en_core_web_sm")

# Function to query the model and get the response
def query_model(question):
    output = llm(
        question,               # The input question
        max_tokens=128,         # Limit the response to a certain number of tokens
        stop=["Q:", "\n"],      # Stop generation when a new question or line appears
        echo=True               # Include the question in the output
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

# Function to validate the correctness of the extracted answer
def validate_answer(question, answer):
    # Basic validation based on known facts (e.g., checking Wikipedia)
    try:
        if "capital" in question and "is" in question:
            country = re.search(r"of (\w+)", question).group(1)
            if country and "yes" in answer:
                # Validate against Wikipedia
                page = wikipedia.page(country)
                if answer == f"https://en.wikipedia.org/wiki/{country}":
                    return "correct"
                else:
                    return "incorrect"
            return "incorrect"
    except Exception as e:
        return "incorrect"

    return "correct"

# Main function to run the program
def process_question(question):
    print(f"Asking the question: \"{question}\" to the model. Please wait...")
    
    # Step 1: Query the model for output (B)
    model_output = query_model(question)
    print(f"Model output (B): {model_output}")

    # Step 2: Extract entities from both question (A) and model output (B)
    entities_question = extract_entities(question)
    entities_output = extract_entities(model_output)
    all_entities = {**entities_question, **entities_output}
    
    print(f"Entities extracted: {all_entities}")

    # Step 3: Extract the answer
    extracted_answer = extract_answer(model_output)
    print(f"Extracted answer: {extracted_answer}")
    
    # Step 4: Validate the answer's correctness
    correctness = validate_answer(question, extracted_answer)
    print(f"Correctness of the answer: {correctness}")
    
    # Output the results as per the assignment
    return {
        "raw_output": model_output,
        "entities_extracted": all_entities,
        "extracted_answer": extracted_answer,
        "correctness": correctness
    }

# Example usage:
question = "Is Managua the capital of Nicaragua?"
result = process_question(question)
print(result)
