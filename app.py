import os
import openai
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
GOOGLE_SHEET_CREDENTIALS = os.getenv('GOOGLE_SHEET_CREDENTIALS')

# Set up OpenAI
openai.api_key = OPENAI_API_KEY

# Streamlit App
st.title("AI Agent Information Retrieval")

# Function to load CSV file
def load_csv(uploaded_file):
    try:
        return pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error reading CSV: {e}")
        return None

# Function to load Google Sheets
def load_google_sheet(sheet_url):
    try:
        creds = Credentials.from_service_account_file('credentials.json')
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url).sheet1
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        return None

# Function to perform a web search using SerpAPI
def search_entity(query):
    try:
        search_url = "https://serpapi.com/search"
        params = {
            'q': query,
            'api_key': SERPAPI_KEY,
            'num': 3,  # Top 3 search results
        }
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            return response.json().get('organic_results', [])
        else:
            st.warning("Failed to fetch data from SerpAPI")
            return []
    except Exception as e:
        st.error(f"Error during web search: {e}")
        return []

# Function to extract specific information using OpenAI GPT
def extract_info(query, search_results):
    content = "\n".join([result['snippet'] for result in search_results if 'snippet' in result])
    prompt = f"Extract the relevant information for: {query}\n\n{content}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# Step 1: File Upload
st.header("Upload Data")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# Step 2: Google Sheets Integration
google_sheet_url = st.text_input("Or, Enter Google Sheet URL")

# Load Data
if uploaded_file:
    df = load_csv(uploaded_file)
elif google_sheet_url:
    df = load_google_sheet(google_sheet_url)
else:
    df = None

# Display Data Preview
if df is not None:
    st.write("Preview of the Data")
    st.dataframe(df.head())

    # Step 3: Selecting Column
    entity_column = st.selectbox("Select the main column (e.g., Company)", df.columns)
    
    # Step 4: Custom Query Input
    query_template = st.text_input(
        "Enter your query (use {entity} as a placeholder)", 
        "Get the email address of {entity}"
    )

    if st.button("Run AI Agent"):
        results = []
        for entity in df[entity_column].dropna():
            query = query_template.format(entity=entity)
            search_results = search_entity(query)
            extracted_data = extract_info(query, search_results)
            results.append({"Entity": entity, "Extracted Data": extracted_data})
        
        results_df = pd.DataFrame(results)
        st.write("Results")
        st.dataframe(results_df)

        # Step 5: Download Option
        st.download_button(
            label="Download CSV",
            data=results_df.to_csv(index=False),
            file_name="extracted_results.csv",
            mime="text/csv"
        )
else:
    st.info("Please upload a CSV file or connect a Google Sheet.")
