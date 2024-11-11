import streamlit as st
import pandas as pd
import requests
import openai
import time

# Function to load data from uploaded CSV
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

# Function to perform search using SerpAPI
def perform_search(data, main_column, prompt, api_key):
    results = {}
    for entity in data[main_column]:
        # Format the search query by replacing {company} placeholder
        search_query = prompt.replace("{company}", str(entity))
        url = "https://serpapi.com/search"
        params = {"q": search_query, "api_key": api_key, "engine": "google"}

        # Debugging output for each request
        st.write(f"Searching for: {search_query}")

        try:
            # Make the API request
            response = requests.get(url, params=params)
            st.write(f"Status Code for {entity}: {response.status_code}")  # Display each status code

            if response.status_code == 200:
                # Get search results
                search_data = response.json().get("organic_results", [])
                results[entity] = search_data if search_data else "No results found."
                st.write(f"Results for {entity}: {search_data}")  # Display raw results for each entity
            else:
                results[entity] = f"Error: {response.status_code}"
        except requests.exceptions.RequestException as e:
            st.write(f"Error for {entity}: {e}")
            results[entity] = f"Error: {e}"

        # Add a short delay to respect rate limits
        time.sleep(1)

    return results

# Function to extract information from search results using OpenAI
def extract_information(results, openai_api_key):
    openai.api_key = openai_api_key
    extracted_data = {}
    for entity, search_results in results.items():
        # Create prompt for OpenAI
        prompt_text = f"Extract relevant information about {entity} from the following: {search_results}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_text}],
            max_tokens=100
        )
        extracted_data[entity] = response.choices[0].message['content'].strip()
    
    return extracted_data

# Streamlit app layout
st.title("AI Agent for Automated Information Retrieval")
st.write("Welcome to the AI Agent Dashboard!")

# File upload and initial setup
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
if uploaded_file is not None:
    data = load_data(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(data)

    # Select main column for entity names
    if not data.empty:
        main_column = st.selectbox("Select the main column", data.columns)
        prompt = st.text_input("Enter your query (e.g., Get email address for {company})")
        serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
        openai_key = st.text_input("Enter your OpenAI API key", type="password")

        # Sample test button to verify SerpAPI works independently
        if st.button("Run Sample Test"):
            url = "https://serpapi.com/search"
            params = {
                "q": "Get email address for Microsoft",
                "api_key": serpapi_key,
                "engine": "google"
            }
            try:
                response = requests.get(url, params=params)
                st.write("Sample Test Status Code:", response.status_code)
                st.write("Sample Test JSON:", response.json())
            except requests.exceptions.RequestException as e:
                st.write(f"Request failed: {e}")

        # Main search function execution
        if st.button("Run Search") and main_column and prompt and serpapi_key and openai_key:
            st.write("Running search...")
            results = perform_search(data, main_column, prompt, serpapi_key)
            st.write("Final Results Dictionary:", results)  # Display final results dictionary

            # Extract relevant information from search results
            st.write("Extracting information using OpenAI...")
            extracted_data = extract_information(results, openai_key)
            st.write("Extracted Information:")
            st.write(extracted_data)

            # Provide download option for extracted information
            if extracted_data:
                df = pd.DataFrame(list(extracted_data.items()), columns=["Entity", "Extracted Information"])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results", csv, "results.csv", "text/csv", key='download-csv')
    else:
        st.write("The uploaded file is empty. Please upload a valid CSV file.")
