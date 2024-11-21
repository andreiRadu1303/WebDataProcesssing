from llama_cpp import Llama
import spacy
import re

# Path to language model file
model_path = "/Users/project/WebdataProvessing/models/llama-2-7b.Q4_K_M.gguf"

# Initialize the Llama model
llm = Llama(model_path=model_path, verbose=False)

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Define the input question
question = "The capital of France is called "

# Display query
print(f"Asking the question: \"{question}\" to the model. Please wait...")

# Query the model with increased tokens limit and clearer stop tokens
output = llm(
    question,              
    max_tokens=100,        # Allow more space for the answer
    stop=["\n", "."],      # More explicit stop tokens
    echo=False              
)

# Display the raw output (B)
response_text = output['choices'][0]['text']
print("Here is the output:")
print(response_text)

# Task 2: Extract the answer type (yes/no or Wikipedia entity)

# Step 1: Check for yes/no answer
yes_no_answer = None
if re.search(r'\b(yes|no)\b', response_text, re.IGNORECASE):
    yes_no_answer = re.search(r'\b(yes|no)\b', response_text, re.IGNORECASE).group(0).lower()

# Step 2: Extract Wikipedia entity using spaCy
doc_b = nlp(response_text)
entities_b = [ent.text for ent in doc_b.ents]

# If no yes/no answer, extract the first entity as the answer (assuming it's a Wikipedia-style entity)
wikipedia_entity = None
if not yes_no_answer and entities_b:
    wikipedia_entity = entities_b[0]  # Take the first entity detected (can be refined)

# Display extracted answers
print("\nExtracted Answer Type:")

if yes_no_answer:
    print(f"Yes/No Answer: {yes_no_answer.capitalize()}")
else:
    print(f"Wikipedia Entity: {wikipedia_entity}")
