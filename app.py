import streamlit as st
import pandas as pd
import httpx
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Function to authenticate Google Sheets
def authenticate_google_sheets(credentials_file):
    try:
        creds = service_account.Credentials.from_service_account_file(credentials_file)
        return creds
    except Exception as e:
        st.error(f"Error authenticating Google Sheets: {e}")
        return None

# Function to load data from Google Sheets
def load_google_sheet(creds, spreadsheet_id, range_name):
    try:
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
        values = result.get('values', [])
        if not values:
            st.warning("No data found in the specified range.")
            return pd.DataFrame()
        return pd.DataFrame(values[1:], columns=values[0])  # Use the first row as header
    except Exception as e:
        st.error(f"Error loading Google Sheet: {e}")
        return pd.DataFrame()

# Placeholder function for batch processing
def batch_process(entities, batch_size, prompt, main_column, rapidapi_key):
    results = []
    for i in range(0, len(entities), batch_size):
        batch = entities[i:i + batch_size]
        # Simulate processing with a placeholder response
        for entity in batch:
            results.append({"entity": entity, "response": f"Processed {entity} with prompt: {prompt}"})
        time.sleep(1)  # Simulate a delay for rate limiting
    return results

# Placeholder function to process results with LLM
def process_with_llm(results, llm_api_key):
    # Simulate LLM processing
    final_results = {}
    for result in results:
        final_results[result["entity"]] = f"Final output for {result['entity']}"
    return final_results

# Streamlit App
st.title("AI Agent for Automated Information Retrieval")

data_source = st.radio("Choose Data Source", ["Upload CSV", "Google Sheets"])
data = pd.DataFrame()  # Initialize an empty DataFrame

# Handle CSV Upload
if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload a CSV File", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
        st.write("Uploaded Data Preview:")
        st.dataframe(data)

# Handle Google Sheets
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

# Only proceed if data is loaded
if not data.empty:
    main_column = st.selectbox("Select Main Column", data.columns)
    prompt = st.text_input("Enter Query Template (e.g., Get information about {main_column})")
    rapidapi_key = st.text_input("Enter RapidAPI Key", type="password")
    llm_api_key = st.text_input("Enter LLM API Key", type="password")
    batch_size = st.slider("Batch Size for Processing", 1, 20, 10)

    # Validate the selected column
    if main_column not in data.columns:
        st.error(f"Column '{main_column}' does not exist in the data. Please select a valid column.")
        st.stop()

    # Convert to strings and drop NaN values
    entities = data[main_column].dropna().astype(str).tolist()

    if st.button("Run Query") and main_column and prompt and rapidapi_key and llm_api_key:
        st.write("Processing...")
        progress = st.progress(0)

        # Ensure that the prompt contains the placeholder
        if f"{{{main_column}}}" not in prompt:
            st.error(f"The prompt must contain the placeholder {{{main_column}}}")
        else:
            # Call batch_process with valid entities
            results = batch_process(entities, batch_size, prompt, main_column, rapidapi_key)

            # Process with LLM
            final_results = process_with_llm(results, llm_api_key)

            # Display results
            st.write("Results:")
            results_df = pd.DataFrame.from_dict(final_results, orient="index", columns=["Extracted Information"])
            st.dataframe(results_df)

            # Download results
            results_csv = results_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Results as CSV", results_csv, "results.csv", "text/csv")
