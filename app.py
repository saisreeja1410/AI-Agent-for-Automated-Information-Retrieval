import streamlit as st
import pandas as pd
import requests
import openai
import time

# Load data with caching
@st.cache_data
def load_data(uploaded_file):
    return pd.read_csv(uploaded_file)

@st.cache_data
def perform_search_cached(data, main_column, prompt, api_key):
    return perform_search(data, main_column, prompt, api_key)

def perform_search(data, main_column, prompt, api_key):
    results = {}
    for entity in data[main_column]:
        search_query = prompt.replace("{company}", str(entity))
        url = "https://serpapi.com/search"
        params = {"q": search_query, "api_key": api_key, "engine": "google"}  

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            search_data = response.json().get("organic_results", [])

            # Debugging statements
            st.write(f"Query for {entity}: {search_query}")
            st.write(f"Response JSON for {entity}: {response.json()}")  # Check if the JSON contains what you expect

            results[entity] = search_data if search_data else "No results found."
        except requests.exceptions.RequestException as e:
            results[entity] = f"Error: {e}"
            st.write(f"Error for {entity}: {e}")

        time.sleep(1)

    return results
    # Displaying the results in Streamlit
if results:
    st.write("Search Results:")
    for entity, result in results.items():
        st.write(f"Results for {entity}:")
        if isinstance(result, list):
            for res in result:
                st.write(res)
        else:
            st.write(result)


    openai.api_key = openai_api_key
    extracted_data = {}
    for entity, search_results in results.items():
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

uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
if uploaded_file is not None:
    data = load_data(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(data)

    if not data.empty:
        main_column = st.selectbox("Select the main column", data.columns)
        prompt = st.text_input("Enter your query (e.g., Get email address for {company})")
        serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
        openai_key = st.text_input("Enter your OpenAI API key", type="password")

        if st.button("Run Search") and main_column and prompt and serpapi_key and openai_key:
            st.write("Running search...")

            results = perform_search_cached(data, main_column, prompt, serpapi_key)
            st.write("Search Results:")
            st.write(results)

            extracted_data = extract_information(results, openai_key)
            st.write("Extracted Information:")
            st.write(extracted_data)

            if extracted_data:
                df = pd.DataFrame(list(extracted_data.items()), columns=["Entity", "Extracted Information"])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results", csv, "results.csv", "text/csv", key='download-csv')
    else:
        st.write("The uploaded file is empty. Please upload a valid CSV file.")
# Hardcoded test for a single query
test_query = "Get email address for Microsoft"
test_params = {"q": test_query, "api_key": api_key, "engine": "google"}
response = requests.get(url, params=test_params)
st.write("Test Query Response:", response.json())

