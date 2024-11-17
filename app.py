import streamlit as st
import pandas as pd
import httpx
import re
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

# Perform a search using DuckDuckGo HTML scraping
def perform_search(entities, prompt, main_column):
    results = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
    }

    for entity in entities:
        try:
            search_query = prompt.replace(f"{{{main_column}}}", str(entity))
            url = f"https://html.duckduckgo.com/html/?q={search_query.replace(' ', '+')}"
            response = httpx.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Extract search snippets using regex
                snippets = re.findall(r'<a rel="nofollow" class="result__a" href=".*?">(.*?)</a>', response.text)
                results[entity] = snippets[0] if snippets else "No relevant snippet found"
            else:
                results[entity] = f"Error: HTTP {response.status_code}"
            time.sleep(2)  # Delay to avoid being blocked
        except Exception as e:
            logging.error(f"Error during search for {entity}: {e}")
            results[entity] = "Search error"
    return results

def process_with_groq_api(results, groq_api_key):
    processed_results = {}
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}

    for entity, snippet in results.items():
        if snippet in ["No relevant snippet found", "Search error"]:
            processed_results[entity] = snippet
            continue

        try:
            # Prepare the messages for the Groq API
            messages = [
                {"role": "user", "content": f"Extract relevant details about {entity} from this snippet: {snippet}"}
            ]
            payload = {
                "model": "llama3-8b-8192",
                "messages": messages
            }
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                # Parse the response and extract content
                processed_results[entity] = response.json().get("choices", [{}])[0].get("message", {}).get("content", "No result extracted.")
            else:
                logging.error(f"Groq API response for {entity}: {response.status_code}, {response.text}")
                processed_results[entity] = f"Groq API Error: {response.status_code}"
        except Exception as e:
            logging.error(f"Groq API error for {entity}: {e}")
            processed_results[entity] = "Processing error"
    return processed_results

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

# Perform searches and process results
if not data.empty:
    main_column = st.selectbox("Select Main Column for Entities", data.columns)
    prompt = st.text_input("Enter Query (e.g., Get {main_column} for {Company})")
    groq_api_key = st.text_input("Enter Groq API Key", type="password")

    if st.button("Run Search") and main_column and prompt and groq_api_key:
        st.write("Processing Data...")
        progress = st.progress(0)
        final_results = {}

        # Perform search in batches
        entities = data[main_column].dropna().tolist()
        total_batches = len(entities)
        for idx, batch in enumerate(batch_data(entities, batch_size=10)):
            batch_results = perform_search(batch, prompt, main_column)
            processed_results = process_with_groq_api(batch_results, groq_api_key)
            final_results.update(processed_results)
            progress.progress((idx + 1) / total_batches)

        # Display results
        st.subheader("Processed Results")
        results_df = pd.DataFrame.from_dict(final_results, orient='index', columns=['Extracted Information'])
        st.write(results_df)

        # Download results
        results_csv = results_df.to_csv().encode('utf-8')
        st.download_button("Download Results as CSV", results_csv, "processed_results.csv", "text/csv")
