from llama_cpp import Llama

# Path to language model file
model_path = "models/llama-2-7b.Q4_K_M.gguf"

# Initialize language model
llm = Llama(model_path=model_path, verbose=False)

# Define question
question = "What is the capital of Italy? "

# Display query
print(f"Asking the question: \"{question}\" to the model. Please wait...")

# Query the model
output = llm(
    question,              # The input prompt/question
    max_tokens=32,         # Limit the response to 32 tokens
    stop=["Q:", "\n"],     # Stop generation if a new question or line starts
    echo=True              # Include the prompt in the output
)

# Display the output
print("Here is the output:")
print(output['choices']) 
