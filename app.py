import streamlit as st
import pandas as pd
import httpx
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from urllib.parse import quote
import time
import math

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
        st.error("Google Sheets authentication failed. Check the credentials file.")
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
        st.error("Failed to load Google Sheets data. Check Spreadsheet ID and range.")
        logging.error(f"Error loading Google Sheets: {e}")
        return pd.DataFrame()

# Perform a web search
def perform_search(entities, prompt, main_column, rapidapi_key, rate_limit_delay=1):
    results = {}
    headers = {
        "X-RapidAPI-Host": "google-search3.p.rapidapi.com",
        "X-RapidAPI-Key": rapidapi_key,
    }

    for entity in entities:
        if not isinstance(entity, str) or not entity.strip():
            logging.warning(f"Skipping invalid entity: {entity}")
            results[entity] = "Invalid entity"
            continue

        try:
            search_query = quote(prompt.replace(f"{{{main_column}}}", entity.strip()))
            url = f"https://google-search3.p.rapidapi.com/api/v1/search/q={search_query}"
            response = httpx.get(url, headers=headers, timeout=10)

            if response.status_code == 429:
                logging.warning(f"429 Too Many Requests for {entity}: Retrying after delay.")
                time.sleep(rate_limit_delay * 2)
                continue

            response.raise_for_status()
            data = response.json()
            snippets = [result.get("description", "") for result in data.get("results", [])]
            results[entity] = snippets[0] if snippets else "No relevant snippet found"

        except httpx.RequestError as e:
            logging.error(f"Request error for {entity}: {e}")
            results[entity] = "Request error"
        except Exception as e:
            logging.error(f"Unexpected error for {entity}: {e}")
            results[entity] = "Unknown error"

        time.sleep(rate_limit_delay)

    return results

# Process snippets with LLM
def process_with_llm(results, llm_api_key):
    processed_results = {}
    headers = {"Authorization": f"Bearer {llm_api_key}", "Content-Type": "application/json"}

    for entity, snippet in results.items():
        if snippet in ["No relevant snippet found", "Request error", "Unknown error", "Invalid entity"]:
            processed_results[entity] = snippet
            continue

        try:
            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": f"Extract details about {entity}: {snippet}"}],
            }
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            processed_results[entity] = response.json().get("choices", [{}])[0].get("message", {}).get("content", "No result extracted.")
        except Exception as e:
            logging.error(f"LLM error for {entity}: {e}")
            processed_results[entity] = "Processing error"

    return processed_results

# Batch processing for search
def batch_process(entities, batch_size, prompt, main_column, rapidapi_key, rate_limit_delay=1):
    results = {}
    total_batches = math.ceil(len(entities) / batch_size)

    for i in range(total_batches):
        batch = entities[i * batch_size:(i + 1) * batch_size]
        batch_results = perform_search(batch, prompt, main_column, rapidapi_key, rate_limit_delay)
        results.update(batch_results)
        logging.info(f"Processed batch {i + 1}/{total_batches}")
        time.sleep(rate_limit_delay * 5)  # Delay between batches

    return results

# Streamlit App
st.title("AI Agent for Automated Information Retrieval")

data_source = st.radio("Choose Data Source", ["Upload CSV", "Google Sheets"])
data = pd.DataFrame()

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

if not data.empty:
    main_column = st.selectbox("Select Main Column", data.columns)
    prompt = st.text_input("Enter Query Template (e.g., Get information about {main_column})")
    rapidapi_key = st.text_input("Enter RapidAPI Key", type="password")
    llm_api_key = st.text_input("Enter LLM API Key", type="password")
    batch_size = st.slider("Batch Size for Processing", 1, 20, 10)

    if st.button("Run Query") and main_column and prompt and rapidapi_key and llm_api_key:
        st.write("Processing...")
        progress = st.progress(0)
        entities = data[main_column].dropna().tolist()

        if f"{{{main_column}}}" not in prompt:
            st.error(f"The prompt must contain the placeholder {{{main_column}}}")
        else:
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
