import streamlit as st
import pandas as pd
import httpx
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

# Perform a search using ScraperAPI
def perform_search(entities, prompt, main_column, scraperapi_key):
    results = {}
    for entity in entities:
        try:
            search_query = prompt.replace(f"{{{main_column}}}", str(entity))
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            url = f"http://api.scraperapi.com?api_key={scraperapi_key}&url={search_url}"
            logging.info(f"Performing search query: {search_query}")
            response = httpx.get(url, timeout=10)

            if response.status_code == 200:
                # Extract search snippets
                snippets = re.findall(r'<div class="BNeawe s3v9rd AP7Wnd">(.*?)</div>', response.text)
                results[entity] = snippets[0] if snippets else "No relevant snippet found"
            else:
                results[entity] = f"Error: HTTP {response.status_code}"
            time.sleep(2)  # Delay to avoid rate-limiting
        except Exception as e:
            logging.error(f"Error during search for {entity}: {e}")
            results[entity] = "Search error"
    return results

# Batch data processing
def batch_data(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]

# Streamlit app
st.title("AI Agent for Automated Information Retrieval")

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
if not data.empty:
    main_column = st.selectbox("Select Main Column for Entities", data.columns)
    prompt = st.text_input("Enter Query (e.g., Get {main_column} for {Company})")
    scraperapi_key = st.text_input("Enter ScraperAPI Key", type="password")

    if st.button("Run Search") and main_column and prompt and scraperapi_key:
        st.write("Processing Data...")
        progress = st.progress(0)
        final_results = {}

        # Perform search in batches
        entities = data[main_column].dropna().tolist()
        total_batches = len(entities)
        for idx, batch in enumerate(batch_data(entities, batch_size=10)):
            batch_results = perform_search(batch, prompt, main_column, scraperapi_key)
            final_results.update(batch_results)
            progress.progress((idx + 1) / total_batches)

        # Display results
        st.subheader("Search Results")
        results_df = pd.DataFrame.from_dict(final_results, orient='index', columns=['Snippet'])
        st.write(results_df)

        # Download results
        results_csv = results_df.to_csv().encode('utf-8')
        st.download_button("Download Results as CSV", results_csv, "search_results.csv", "text/csv")
