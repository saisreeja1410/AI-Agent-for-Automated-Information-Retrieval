import streamlit as st
import pandas as pd
import httpx
import openai
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
import os

# Ensure log file exists and configure logging
log_file_path = "app.log"
if not os.path.exists(log_file_path):
    with open(log_file_path, "w") as log_file:
        log_file.write("")  # Create an empty log file

logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Authenticate Google Sheets API
@st.cache_resource
def authenticate_google_sheets(credentials_file):
    try:
        creds = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        return creds
    except Exception as e:
        st.error("Google Sheets authentication failed. Please check the credentials file.")
        logging.error(f"Google Sheets authentication error: {e}")
        return None

# Load data from Google Sheets
def load_google_sheet(creds, spreadsheet_id, range_name):
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            st.warning("No data found in the specified range.")
            return pd.DataFrame()
        return pd.DataFrame(values[1:], columns=values[0])
    except Exception as e:
        st.error("Failed to load Google Sheets data. Check the Spreadsheet ID and range.")
        logging.error(f"Error loading Google Sheets: {e}")
        return pd.DataFrame()

# OpenAI integration for query enhancement or search
def query_openai(api_key, prompt, temperature=0.7, max_tokens=100):
    try:
        openai.api_key = api_key
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].text.strip()
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "Error using OpenAI API"

# Perform a search using DuckDuckGo or OpenAI
def perform_search(entities, query_prompt, api_key):
    results = {}
    for entity in entities:
        try:
            # Customize the query using OpenAI
            prompt = query_prompt.replace("{entity}", entity)
            enhanced_query = query_openai(api_key, f"Generate a better query for: {prompt}")
            
            # Search using DuckDuckGo
            url = f"https://api.duckduckgo.com/?q={enhanced_query}&format=json&pretty=1"
            response = httpx.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                snippet = data.get("AbstractText", "No relevant snippet found")
                results[entity] = snippet
            else:
                results[entity] = f"Error: HTTP {response.status_code}"
        except Exception as e:
            logging.error(f"Error during search for {entity}: {e}")
            results[entity] = "Search error"
    return results

# Batch data processing
def batch_data(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

# Streamlit app
st.title("AI Agent for Automated Information Retrieval (OpenAI Enhanced)")

# OpenAI API key input
openai_api_key = st.text_input("Enter OpenAI API Key", type="password")

# Data source options
data_source = st.radio("Choose Data Source", ["Upload CSV", "Google Sheets"])
data = pd.DataFrame()

# Handle CSV upload
if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload a CSV File", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
        st.write("Uploaded Data Preview:")
        st.dataframe(data)

# Handle Google Sheets integration
if data_source == "Google Sheets":
    credentials_file = st.file_uploader("Upload Google Credentials JSON File", type=["json"])
    spreadsheet_id = st.text_input("Enter Google Sheet ID")
    range_name = st.text_input("Enter Data Range (e.g., 'Sheet1!A1:D100')")
    if credentials_file and spreadsheet_id and range_name:
        creds = authenticate_google_sheets(credentials_file)
        if creds:
            data = load_google_sheet(creds, spreadsheet_id, range_name)
            st.write("Google Sheets Data Preview:")
            st.dataframe(data)

# Perform searches
if not data.empty and openai_api_key:
    main_column = st.selectbox("Select Main Column for Entities", data.columns)
    query_prompt = st.text_input("Enter Query Prompt (e.g., Get details for {entity})")

    if st.button("Run Search") and main_column and query_prompt:
        st.write("Processing Data...")
        progress = st.progress(0)
        final_results = {}

        # Process in batches
        entities = data[main_column].dropna().tolist()
        total_batches = len(entities)
        for idx, batch in enumerate(batch_data(entities, batch_size=10)):
            batch_results = perform_search(batch, query_prompt, openai_api_key)
            final_results.update(batch_results)
            progress.progress((idx + 1) / total_batches)

        # Display results
        st.subheader("Search Results")
        results_df = pd.DataFrame.from_dict(final_results, orient='index', columns=['Snippet'])
        st.write(results_df)

        # Download results
        results_csv = results_df.to_csv().encode('utf-8')
        st.download_button("Download Results as CSV", results_csv, "results.csv", "text/csv")

# Footer to display logs
st.write("### Logs")
try:
    with open(log_file_path, "r") as log_file:
        logs = log_file.read()
        st.text_area("Application Logs", logs, height=300)
except FileNotFoundError:
    st.warning("Log file not found. No logs to display.")
