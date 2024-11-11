import streamlit as st
import pandas as pd
import requests
import openai
# Define the function for searching with SerpAPI
import requests

def perform_search(data, main_column, prompt, api_key):
    results = {}
    for entity in data[main_column]:
        # Customize the search query by replacing {company} in the prompt with the actual entity
        search_query = prompt.replace("{company}", str(entity))
        
        # Define the SerpAPI search endpoint with your query and API key
        url = "https://serpapi.com/search"
        params = {
            "q": search_query,
            "api_key": api_key,
            "engine": "google"
        }

        # Make the request to SerpAPI
        response = requests.get(url, params=params)
        
        # Check if the response is successful
        if response.status_code == 200:
            # Extract relevant search results
            search_data = response.json().get("organic_results", [])
            results[entity] = search_data if search_data else "No results found."
        else:
            results[entity] = f"Error: {response.status_code}"

    return results

# Define the function for extracting information using OpenAI GPT
def extract_information(results, openai_api_key):
    openai.api_key = openai_api_key
    extracted_data = {}
    for entity, search_results in results.items():
        # Format prompt for LLM
        prompt_text = f"Extract relevant information about {entity} from the following: {search_results}"
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt_text,
            max_tokens=100
        )
        extracted_data[entity] = response.choices[0].text.strip()
    
    return extracted_data
st.title("AI Agent for Automated Information Retrieval")
st.write("Welcome to the AI Agent Dashboard!")

# Upload a CSV file
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    # Read the uploaded CSV file
    data = pd.read_csv(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(data)

    # Let the user select the main column to use (e.g., company names)
    if not data.empty:
        main_column = st.selectbox("Select the main column", data.columns)
        st.write(f"Main column selected: {main_column}")

        # Enter a custom query
        prompt = st.text_input("Enter your query (e.g., Get email address for {company})")
        
        # Get API keys from user input
        serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
        openai_key = st.text_input("Enter your OpenAI API key", type="password")
        
        # Run search when the button is clicked and all inputs are provided
        if st.button("Run Search") and main_column and prompt and serpapi_key and openai_key:
            st.write("Running search...")

            # Perform search
            results = perform_search(data, main_column, prompt, serpapi_key)
            st.write("Search Results:")
            st.write(results)

            # Extract information from the results
            extracted_data = extract_information(results, openai_key)
            st.write("Extracted Information:")
            st.write(extracted_data)

            # Download option for the extracted information
            if extracted_data:
                df = pd.DataFrame(list(extracted_data.items()), columns=["Entity", "Extracted Information"])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results", csv, "results.csv", "text/csv", key='download-csv')
    else:
        st.write("The uploaded file is empty. Please upload a valid CSV file.")
