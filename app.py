import streamlit as st
import pandas as pd
import requests
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from groq import Groq

# Authenticate Google Sheets API
def authenticate_google_sheets():
    creds = service_account.Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return creds

# Load data from Google Sheets
def load_google_sheet(spreadsheet_id, range_name):
    creds = authenticate_google_sheets()
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])
    if not values:
        return pd.DataFrame()
    else:
        df = pd.DataFrame(values[1:], columns=values[0])
        return df

# Perform a search using SerpAPI
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

# Extract information using Groq API
def extract_information(results, groq_api_key):
    client = Groq(api_key=groq_api_key)
    extracted_data = {}

    for entity, search_results in results.items():
        # Prepare messages for the Groq API
        messages = [
            {"role": "user", "content": f"Extract relevant information about {entity} from the following: {search_results}"}
        ]
        
        try:
            response = client.chat.completions.create(
                messages=messages,
                model="llama3-8b-8192",
                max_tokens=100,
                temperature=0.5
            )
            extracted_data[entity] = response.choices[0].message.content.strip()
        
        except Exception as e:
            extracted_data[entity] = f"Error: {str(e)}"

    return extracted_data

# Streamlit app setup
st.title("AI Agent for Automated Information Retrieval")

# Option to upload CSV or connect to Google Sheets
data_source = st.radio("Choose data source", ("Upload CSV", "Google Sheets"))

data = pd.DataFrame()
if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data:")
        st.dataframe(data)

elif data_source == "Google Sheets":
    spreadsheet_id = st.text_input("Enter Google Sheet ID")
    range_name = st.text_input("Enter the range (e.g., 'Sheet1!A1:D100')")
    if spreadsheet_id and range_name:
        data = load_google_sheet(spreadsheet_id, range_name)
        st.write("Preview of Google Sheets data:")
        st.dataframe(data)

# Select main column and set prompt if data is loaded
if not data.empty:
    main_column = st.selectbox("Select the main column for entities", data.columns)
    prompt = st.text_input("Enter your query (e.g., Get email address for {company})")

    # API keys for SerpAPI and Groq
    serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
    groq_api_key = st.text_input("Enter your Groq API key", type="password")

    # Run the search and extract information
    if st.button("Run Search") and main_column and prompt and serpapi_key and groq_api_key:
        st.write("Running search...")

        # Perform the search
        results = perform_search(data, main_column, prompt, serpapi_key)
        st.write("Search Results:")
        for entity, result in results.items():
            st.write(f"Results for {entity}: {result}")

        # Extract information using Groq API
        extracted_data = extract_information(results, groq_api_key)
        st.write("Extracted Information:")
        for entity, info in extracted_data.items():
            st.write(f"Information for {entity}: {info}")

        # Option to download results as CSV
        if st.button("Download Results"):
            results_df = pd.DataFrame.from_dict(extracted_data, orient='index', columns=['Extracted Information'])
            results_csv = results_df.to_csv().encode('utf-8')
            st.download_button("Download CSV", results_csv, "extracted_information.csv", "text/csv", key='download-csv')

# Add additional error handling for the entire application
try:
    pass  # Placeholder for additional logic if needed
except Exception as e:
    st.error(f"An error occurred: {str(e)}")
