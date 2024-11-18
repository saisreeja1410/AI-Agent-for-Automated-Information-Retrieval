import streamlit as st
import pandas as pd
from data_handler import load_csv, load_google_sheet
from search_api import search_entity
from llm_integration import extract_info
import utils

st.title("AI Agent Information Retrieval")

# Step 1: File Upload
st.header("Upload Data")
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# Step 2: Google Sheets Integration
google_sheet_url = st.text_input("Or, Enter Google Sheet URL")

if uploaded_file:
    df = load_csv(uploaded_file)
elif google_sheet_url:
    df = load_google_sheet(google_sheet_url)
else:
    df = None

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
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def load_csv(uploaded_file):
    return pd.read_csv(uploaded_file)

def load_google_sheet(sheet_url):
    creds = Credentials.from_service_account_file('credentials.json')
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)
import requests
import os

SERPAPI_KEY = os.getenv('SERPAPI_KEY')

def search_entity(query):
    search_url = "https://serpapi.com/search"
    params = {
        'q': query,
        'api_key': SERPAPI_KEY,
        'num': 3,  # Get top 3 results
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        return response.json().get('organic_results', [])
    return []
import openai
import os

openai.api_key = os.getenv('OPENAI_API_KEY')

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
def format_prompt(prompt, entity):
    return prompt.replace("{entity}", entity)
