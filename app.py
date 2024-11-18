import streamlit as st
import pandas as pd
from langchain_community.chat_models import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
from serpapi import GoogleSearch
import os
import json

# Page config
st.set_page_config(page_title="AI Agent for Information Retrieval", layout="wide")

# Initialize session state
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = None

def authenticate_google_sheets(credentials_content):
    """Authenticate Google Sheets with provided credentials"""
    try:
        credentials_dict = json.loads(credentials_content)
        creds = service_account.Credentials.from_service_account_info(credentials_dict)
        return creds
    except Exception as e:
        st.error(f"Error authenticating Google Sheets: {e}")
        return None

def load_google_sheet(creds, spreadsheet_id, range_name):
    """Load data from Google Sheets"""
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
        st.error(f"Error loading Google Sheet: {e}")
        return pd.DataFrame()

def perform_web_search(query, serp_api_key):
    """Perform web search using SerpAPI"""
    try:
        search = GoogleSearch({
            "q": query,
            "api_key": serp_api_key,
            "num": 5  # Limit to top 5 results
        })
        results = search.get_dict()
        
        if 'organic_results' not in results:
            return "No results found."
            
        # Extract relevant information from results
        extracted_results = []
        for result in results['organic_results'][:5]:
            snippet = result.get('snippet', '')
            link = result.get('link', '')
            extracted_results.append(f"URL: {link}\nSnippet: {snippet}\n")
            
        return "\n".join(extracted_results)
    except Exception as e:
        return f"Error performing search: {str(e)}"

def process_entity(entity, search_template, extraction_template, llm_chain, serp_api_key):
    """Process a single entity through search and LLM extraction"""
    try:
        # Perform web search
        search_query = search_template.format(entity=entity)
        search_results = perform_web_search(search_query, serp_api_key)
        
        # Process through LLM
        llm_prompt = f"""
        Based on the following search results:
        {search_results}
        
        {extraction_template.format(entity=entity)}
        
        Return ONLY the extracted information without any additional text or explanation.
        """
        extracted_info = llm_chain.run(query=llm_prompt)
        
        return extracted_info.strip()
    except Exception as e:
        return f"Error processing entity: {str(e)}"

# Main App UI
st.title("🤖 AI Agent for Information Retrieval")

# API Keys Section
with st.expander("API Configuration", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        groq_api_key = st.text_input("Enter Groq API Key", type="password")
    with col2:
        serp_api_key = st.text_input("Enter SerpAPI Key", type="password")

# Data Source Selection
data_source = st.radio("Choose Data Source", ["Upload CSV", "Google Sheets"])
data = pd.DataFrame()

# Handle CSV Upload
if data_source == "Upload CSV":
    uploaded_file = st.file_uploader("Upload a CSV File", type=["csv"])
    if uploaded_file:
        data = pd.read_csv(uploaded_file)
        st.write("Data Preview:")
        st.dataframe(data.head())

# Handle Google Sheets
elif data_source == "Google Sheets":
    credentials_file = st.file_uploader("Upload Google Credentials JSON File", type=["json"])
    spreadsheet_id = st.text_input("Enter Google Sheet ID")
    range_name = st.text_input("Enter Data Range (e.g., 'Sheet1!A1:D100')")
    
    if credentials_file and spreadsheet_id and range_name:
        credentials_content = credentials_file.read().decode()
        creds = authenticate_google_sheets(credentials_content)
        if creds:
            data = load_google_sheet(creds, spreadsheet_id, range_name)
            st.write("Data Preview:")
            st.dataframe(data.head())

# Query Configuration
if not data.empty:
    with st.expander("Query Configuration", expanded=True):
        main_column = st.selectbox("Select Main Column (entities to search)", data.columns)
        search_template = st.text_input(
            "Enter Search Query Template",
            value="Information about {entity}",
            help="Use {entity} as placeholder for each item in your selected column"
        )
        extraction_template = st.text_input(
            "Enter Information Extraction Template",
            value="Extract the following information about {entity}:\n1. Description\n2. Contact information\n3. Location",
            help="Specify what information should be extracted from search results"
        )
        batch_size = st.slider("Batch Size", min_value=1, max_value=20, value=5)

    # Process Button
    if st.button("Start Processing"):
        if not groq_api_key or not serp_api_key:
            st.error("Please enter both Groq API and SerpAPI keys.")
        else:
            try:
                # Initialize Groq LLM
                llm = ChatGroq(
                    api_key=groq_api_key,
                    model_name="mixtral-8x7b-32768",  # Using Mixtral model
                    temperature=0.3,
                    max_tokens=1000
                )
                
                # Create LLM Chain
                prompt = PromptTemplate(
                    input_variables=["query"],
                    template="{query}"
                )
                llm_chain = LLMChain(llm=llm, prompt=prompt)
                
                # Process entities
                results = []
                entities = data[main_column].dropna().unique()
                
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, entity in enumerate(entities):
                    status_text.text(f"Processing: {entity}")
                    
                    # Process entity
                    extracted_info = process_entity(
                        entity,
                        search_template,
                        extraction_template,
                        llm_chain,
                        serp_api_key
                    )
                    
                    results.append({
                        "Entity": entity,
                        "Extracted Information": extracted_info
                    })
                    
                    # Update progress
                    progress = (i + 1) / len(entities)
                    progress_bar.progress(progress)
                    
                    # Rate limiting
                    time.sleep(1)
                
                # Store results in session state
                st.session_state.processed_results = pd.DataFrame(results)
                
                # Clear progress indicators
                status_text.empty()
                progress_bar.empty()
                
                st.success("Processing completed!")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Display Results
if st.session_state.processed_results is not None:
    st.subheader("Results")
    st.dataframe(st.session_state.processed_results)
    
    # Download button
    csv = st.session_state.processed_results.to_csv(index=False)
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="extracted_results.csv",
        mime="text/csv"
    )
    
    # Optional: Update Google Sheet
    if data_source == "Google Sheets" and st.button("Update Google Sheet with Results"):
        try:
            service = build('sheets', 'v4', credentials=creds)
            sheet = service.spreadsheets()
            
            # Prepare values to write
            values = [st.session_state.processed_results.columns.tolist()]
            values.extend(st.session_state.processed_results.values.tolist())
            
            # Write to a new sheet in the same spreadsheet
            body = {
                'values': values
            }
            result = sheet.values().update(
                spreadsheetId=spreadsheet_id,
                range='Results!A1',  # Write to a sheet named 'Results'
                valueInputOption='RAW',
                body=body
            ).execute()
            
            st.success("Results written to Google Sheet!")
        except Exception as e:
            st.error(f"Error updating Google Sheet: {str(e)}")
