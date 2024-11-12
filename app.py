import streamlit as st
import pandas as pd
import requests
import openai

def perform_search(data, main_column, prompt, api_key):
    results = {}
    for entity in data[main_column]:
        search_query = prompt.replace("{company}", str(entity))
        url = "https://serpapi.com/search"
        params = {"q": search_query, "api_key": api_key, "engine": "google"}

        response = requests.get(url, params=params)
        if response.status_code == 200:
            search_data = response.json().get("organic_results", [])
            results[entity] = search_data if search_data else "No results found."
        else:
            results[entity] = f"Error: {response.status_code}"

    return results


def extract_information(results, openai_api_key):
    openai.api_key = openai_api_key
    extracted_data = {}

    for entity, search_results in results.items():
        # Format the prompt for information extraction
        prompt_text = f"Extract relevant information about {entity} from the following: {search_results}"
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use gpt-3.5-turbo or similar model
                messages=[
                    {"role": "user", "content": prompt_text}
                ],
                max_tokens=100,
                temperature=0.5
            )
            extracted_data[entity] = response['choices'][0]['message']['content'].strip()
        
        except Exception as e:
            extracted_data[entity] = f"Error: {str(e)}"

    return extracted_data

st.title("AI Agent for Automated Information Retrieval")
st.write("Welcome to the AI Agent Dashboard!")
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(data)
    if not data.empty:
        main_column = st.selectbox("Select the main column", data.columns)
        prompt = st.text_input("Enter your query (e.g., Get City for {company})")
        serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
        openai_key = st.text_input("Enter your OpenAI API key", type="password")

        if st.button("Run Search") and main_column and prompt and serpapi_key and openai_key:
            st.write("Running search...")
            results = perform_search(data, main_column, prompt, serpapi_key)
            st.write("Search Results:")
            for entity, result in results.items():
                st.write(f"Results for {entity}: {result}")

            extracted_data = extract_information(results, openai_key)
            st.write("Extracted Information:")
            for entity, info in extracted_data.items():
                st.write(f"Extracted info for {entity}: {info}")

            if extracted_data:
                df = pd.DataFrame(list(extracted_data.items()), columns=["Entity", "Extracted Information"])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results", csv, "results.csv", "text/csv", key='download-csv')
    else:
        st.write("The uploaded file is empty. Please upload a valid CSV file.")
