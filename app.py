import os
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from groqapi import GroqClient
from serpapi import GoogleSearch
from io import StringIO
import time

# Constants
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Initialize APIs
groq_client = GroqClient(api_key=GROQ_API_KEY)

# App title
st.title("AI-Powered Data Retrieval Dashboard")

# Step 1: File upload or Google Sheets integration
st.sidebar.header("Step 1: Upload Data")
upload_option = st.sidebar.radio("Choose data source:", ["Upload CSV", "Connect Google Sheet"])

if upload_option == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("Upload your CSV file", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
elif upload_option == "Connect Google Sheet":
    google_sheet_url = st.sidebar.text_input("Enter Google Sheet URL:")
    if google_sheet_url:
        credentials = service_account.Credentials.from_service_account_info(GOOGLE_CREDENTIALS_JSON)
        service = build('sheets', 'v4', credentials=credentials)
        sheet_id = google_sheet_url.split("/")[5]
        sheet_name = "Sheet1"
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=sheet_name).execute()
        values = result.get('values', [])
        data = pd.DataFrame(values[1:], columns=values[0])

if 'data' in locals():
    st.write("Preview of uploaded data:")
    st.write(data.head())
    column = st.selectbox("Select the column to use for queries:", data.columns)

# Step 2: Query prompt input
st.sidebar.header("Step 2: Define Query")
prompt_template = st.sidebar.text_input("Enter prompt template (e.g., 'Find the email of {company}'):")

# Step 3: Execute retrieval
if st.sidebar.button("Start Retrieval") and 'data' in locals() and column and prompt_template:
    results = []
    for entity in data[column]:
        # Dynamic prompt creation
        query = prompt_template.format(company=entity)
        
        # Search the web
        search = GoogleSearch({"q": query, "api_key": SERPAPI_KEY})
        search_results = search.get_dict()
        top_results = search_results.get("organic_results", [])

        # Format input for LLM
        formatted_results = "\n".join([result.get("snippet", "") for result in top_results])
        llm_input = f"Extract information for: {query}. Results: {formatted_results}"
        
        # Call Groq API
        try:
            groq_response = groq_client.completion(prompt=llm_input)
            extracted_info = groq_response.get('text', "No information found")
        except Exception as e:
            extracted_info = f"Error: {str(e)}"
        
        # Append to results
        results.append({"Entity": entity, "Extracted Info": extracted_info})
        time.sleep(1)  # Avoid rate-limiting

    # Display results
    results_df = pd.DataFrame(results)
    st.write("Results:")
    st.dataframe(results_df)

    # Step 4: Export options
    csv = results_df.to_csv(index=False)
    st.download_button("Download Results as CSV", data=csv, file_name="results.csv", mime="text/csv")
