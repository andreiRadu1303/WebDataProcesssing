from llama_cpp import Llama
import spacy

# Path to language model file
model_path =  "/Users/project/WebdataProvessing/models/llama-2-7b.Q4_K_M.gguf"
model_pathw = "/Users/project/WebdataProvessing/models/llama-2-13b.Q4_K_M.gguf"

# Initialize the Llama model
llm = Llama(model_path=model_path, verbose=False)

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Define the input question
question = "What is the capital of France?"

# Display query
print(f"Asking the question: \"{question}\" to the model. Please wait...")

# Query the model
output = llm(
    question,              # The input prompt/question
    max_tokens=32,         # Limit the response to 32 tokens
    stop=["Q:", "\n"],     # Stop generation if a new question or line starts
    echo=False              # Include the prompt in the output
)

# Display the raw output (B)
print("Here is the output:")
print(output['choices'])

# Extract entities from the question (A)
doc_a = nlp(question)
entities_a = [ent.text for ent in doc_a.ents]

# Extract entities from the model's output (B)
doc_b = nlp(output['choices'][0]['text'])
entities_b = [ent.text for ent in doc_b.ents]

# Display entities
print("\nEntities extracted from the question (A):")
print(entities_a)

print("\nEntities extracted from the model's output (B):")
print(entities_b)
