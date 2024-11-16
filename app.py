import streamlit as st
import pandas as pd
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

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

# Perform a search using ScraperAPI
def perform_search(entities, prompt, api_key):
    results = {}
    for entity in entities:
        search_query = prompt.replace("{company}", str(entity))
        url = "http://api.scraperapi.com"
        params = {
            "api_key": api_key,
            "url": f"https://www.google.com/search?q={search_query}"
        }
        response = requests.get(url, params=params)

        if response.status_code == 200:
            try:
                # Parse and use meaningful parts of the response
                results[entity] = response.text[:200]  # Return the first 200 characters as a mock result
            except Exception as e:
                results[entity] = f"Error processing response: {str(e)}"
        else:
            results[entity] = f"Error: {response.status_code}"
    return results

# Use Groq API to extract information
def extract_information(results, groq_api_key):
    extracted_data = {}
    headers = {"Authorization": f"Bearer {groq_api_key}"}

    for entity, search_results in results.items():
        payload = {
            "input": search_results,
            "instruction": f"Extract relevant information about {entity} from the given search results."
        }
        try:
            response = requests.post("https://api.groq.com/process", headers=headers, json=payload)
            if response.status_code == 200:
                extracted_data[entity] = response.json().get("result", "No information extracted.")
            else:
                extracted_data[entity] = f"Groq API error {response.status_code}: {response.text}"
        except Exception as e:
            extracted_data[entity] = f"Error: {str(e)}"
    return extracted_data

# Split data into batches
def batch_data(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

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

    # API keys for ScraperAPI and Groq
    scraperapi_key = st.text_input("Enter your ScraperAPI key", type="password")
    groq_api_key = st.text_input("Enter your Groq API key", type="password")

    # Run the search and extract information
    if st.button("Run Search") and main_column and prompt and scraperapi_key and groq_api_key:
        st.write("Running search...")
        progress_bar = st.progress(0)

        # Initialize results storage
        final_results = {}
        extracted_information = {}

        # Process in batches
        entities = data[main_column].tolist()
        total_batches = len(entities)
        for idx, batch in enumerate(batch_data(entities, batch_size=10)):
            # Perform the search
            batch_results = perform_search(batch, prompt, scraperapi_key)
            final_results.update(batch_results)

            # Extract information
            batch_extracted = extract_information(batch_results, groq_api_key)
            extracted_information.update(batch_extracted)

            # Update progress
            progress_bar.progress((idx + 1) / total_batches)

        # Display the results
        st.write("Search Results:")
        for entity, result in final_results.items():
            st.write(f"Results for {entity}: {result}")

        st.write("Extracted Information:")
        for entity, info in extracted_information.items():
            st.write(f"Information for {entity}: {info}")

        # Option to download results as CSV
        results_df = pd.DataFrame.from_dict(extracted_information, orient='index', columns=['Extracted Information'])
        results_csv = results_df.to_csv().encode('utf-8')
        st.download_button("Download CSV", results_csv, "extracted_information.csv", "text/csv", key='download-csv')
