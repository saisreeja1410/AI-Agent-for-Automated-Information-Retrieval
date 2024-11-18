import streamlit as st
import pandas as pd
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


# Function to batch process entities
def batch_process(entities, batch_size, prompt, main_column):
    results = []
    for i in range(0, len(entities), batch_size):
        batch = entities.iloc[i:i + batch_size]  # Use .iloc to get rows
        for index, entity in batch.iterrows():  # Iterate over rows
            # Replace placeholder in prompt with actual value
            main_value = entity[main_column]
            query = prompt.replace("{main_column}", str(main_value))
            
            # Simulate response (replace this logic with actual API call if needed)
            response = f"Query: {query} - Response: Retrieved information about {main_value}"
            results.append({"Index": index, "Main Value": main_value, "Response": response})
        
        # Simulate rate-limiting delay
        time.sleep(1)
    return results


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
    batch_size = st.slider("Batch Size for Processing", 1, 20, 10)

    # Validate the selected column
    if main_column not in data.columns:
        st.error(f"Column '{main_column}' does not exist in the data. Please select a valid column.")
        st.stop()

    # Prepare entities as a DataFrame
    entities = data[[main_column]].dropna()

    if st.button("Run Query"):
        st.write("Processing...")

        # Debug: Display intermediate data
        st.write("Entities for processing:")
        st.dataframe(entities)

        # Call batch_process with valid DataFrame
        results = batch_process(entities, batch_size, prompt, main_column)

        # Convert results to DataFrame
        results_df = pd.DataFrame(results)

        # Debug: Display raw results
        st.write("Raw Results:")
        st.dataframe(results_df)

        # Display final results
        st.write("Final Processed Results:")
        st.dataframe(results_df)

        # Allow downloading results as a CSV
        results_csv = results_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Results as CSV", results_csv, "results.csv", "text/csv")
