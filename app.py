import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from serpapi import GoogleSearch
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import json
import time
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Configure API keys and settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

# Initialize LLM
llm = ChatGroq(
    temperature=0.1,
    groq_api_key=GROQ_API_KEY,
    model_name="mixtral-8x7b-32768"
)
output_parser = StrOutputParser()

class AIAgent:
    def __init__(self):
        self.search_results_cache = {}
        
    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Perform web search using SerpAPI
        """
        try:
            search = GoogleSearch({
                "q": query,
                "api_key": SERPAPI_API_KEY,
                "num": num_results
            })
            results = search.get_dict()
            
            # Extract organic results
            if "organic_results" in results:
                return [
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "link": result.get("link", "")
                    }
                    for result in results["organic_results"]
                ]
            return []
            
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def extract_information(self, entity: str, search_results: List[Dict], prompt: str) -> str:
        """
        Extract specific information using Groq LLM
        """
        try:
            # Prepare context from search results
            context = "\n\n".join([
                f"Title: {result['title']}\nSnippet: {result['snippet']}\nURL: {result['link']}"
                for result in search_results
            ])
            
            # Prepare the extraction prompt
            extraction_prompt = f"""
            Based on the following search results about {entity}, {prompt}
            
            Search Results:
            {context}
            
            Extract the requested information in a clear, concise format. If the information is not found, 
            state "Information not found" explicitly.
            """
            
            messages = [HumanMessage(content=extraction_prompt)]
            response = llm.invoke(messages)
            return output_parser.invoke(response)
            
        except Exception as e:
            st.error(f"Extraction error: {str(e)}")
            return "Error during extraction"

def setup_google_sheets():
    """
    Set up Google Sheets API connection
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    try:
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                
        return build('sheets', 'v4', credentials=creds)
        
    except Exception as e:
        st.error(f"Google Sheets setup error: {str(e)}")
        return None

def main():
    st.title("AI Information Extraction Agent")
    st.write("Upload a CSV file or connect to Google Sheets to extract information about entities.")
    
    # Initialize AI Agent
    agent = AIAgent()
    
    # File upload section
    data_source = st.radio("Choose data source:", ["CSV Upload", "Google Sheets"])
    
    df = None
    
    if data_source == "CSV Upload":
        uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            
    else:  # Google Sheets
        sheet_url = st.text_input("Enter Google Sheet URL")
        if sheet_url:
            try:
                sheets_service = setup_google_sheets()
                if sheets_service:
                    # Extract sheet ID from URL
                    sheet_id = sheet_url.split('/')[5]
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=sheet_id, range='A1:Z1000').execute()
                    values = result.get('values', [])
                    if values:
                        df = pd.DataFrame(values[1:], columns=values[0])
            except Exception as e:
                st.error(f"Error accessing Google Sheet: {str(e)}")
    
    if df is not None:
        st.write("Preview of uploaded data:")
        st.dataframe(df.head())
        
        # Column selection
        entity_column = st.selectbox("Select the entity column:", df.columns)
        
        # Query input
        prompt_template = st.text_area(
            "Enter your prompt template:",
            "Find the official website and contact email for {entity}"
        )
        
        if st.button("Extract Information"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            total_entities = len(df[entity_column])
            
            for idx, entity in enumerate(df[entity_column]):
                status_text.text(f"Processing {entity}...")
                
                # Search web
                search_query = prompt_template.format(entity=entity)
                search_results = agent.search_web(search_query)
                
                # Extract information
                extracted_info = agent.extract_information(entity, search_results, prompt_template)
                
                results.append({
                    "Entity": entity,
                    "Extracted Information": extracted_info
                })
                
                # Update progress
                progress = (idx + 1) / total_entities
                progress_bar.progress(progress)
                
                # Add delay to respect API rate limits
                time.sleep(1)
            
            # Create results DataFrame
            results_df = pd.DataFrame(results)
            
            # Display results
            st.write("Extracted Information:")
            st.dataframe(results_df)
            
            # Download button
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="Download results as CSV",
                data=csv,
                file_name="extracted_information.csv",
                mime="text/csv"
            )
            
            # Update Google Sheet if selected
            if data_source == "Google Sheets" and st.button("Update Google Sheet"):
                try:
                    sheets_service = setup_google_sheets()
                    if sheets_service:
                        sheet_id = sheet_url.split('/')[5]
                        range_name = 'ExtractedInfo!A1:B' + str(len(results_df) + 1)
                        
                        values = [results_df.columns.values.tolist()] + results_df.values.tolist()
                        body = {'values': values}
                        
                        sheets_service.spreadsheets().values().update(
                            spreadsheetId=sheet_id,
                            range=range_name,
                            valueInputOption='RAW',
                            body=body
                        ).execute()
                        
                        st.success("Google Sheet updated successfully!")
                except Exception as e:
                    st.error(f"Error updating Google Sheet: {str(e)}")

if __name__ == "__main__":
    main()
