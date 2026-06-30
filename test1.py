from google import genai

# Define your API key directly
API_KEY = "AIzaSyBGLM-Sm1mNNGr8QD9l81P_gZci6o2v0oE"

# Initialize the updated client
client = genai.Client(api_key=API_KEY)

# Use the standard generate_content API
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="write a poem about a beautiful and strong girl"
)

print(response.text)