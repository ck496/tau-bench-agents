import google.generativeai as genai

# Setup your key
# genai.configure(api_key="YOUR_API_KEY")

# List models to verify connection (Optional)
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

response = model.generate_content("Explain AI in 10 words.")
print(response.text)
