import streamlit as st
import pandas as pd
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
from io import BytesIO


# Authenticate Google Sheets
def authenticate_google_sheets(credentials_file):
    try:
        creds = service_account.Credentials.from_service_account_file(credentials_file)
        return creds
    except Exception as e:
        st.error(f"Error authenticating Google Sheets: {e}")
        return None


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


# Streamlit App
st.title("AI Agent with LangChain")

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
        creds = authenticate_google_sheets(credentials_file.read())
        if creds:
            data = load_google_sheet(creds, spreadsheet_id, range_name)
            st.write("Google Sheets Data Preview:")
            st.dataframe(data)

# Ensure data is loaded
if not data.empty:
    main_column = st.selectbox("Select Main Column", data.columns)
    query_template = st.text_input("Enter Query Template (e.g., Get information about {main_value})")
    openai_api_key = st.text_input("Enter OpenAI API Key", type="password")
    batch_size = st.slider("Batch Size for Processing", 1, 20, 10)

    if not openai_api_key:
        st.error("Please enter a valid OpenAI API Key.")
        st.stop()

    if main_column not in data.columns:
        st.error(f"Column '{main_column}' does not exist in the data. Please select a valid column.")
        st.stop()

    if "{main_value}" not in query_template:
        st.error("Query template must contain the placeholder '{main_value}'.")
        st.stop()

    entities = data[[main_column]].dropna()

    if st.button("Run Query"):
        st.write("Processing with LangChain...")

        # Initialize LangChain
        llm = ChatOpenAI(openai_api_key=openai_api_key)
        prompt = PromptTemplate(
            input_variables=["main_value"],
            template=query_template
        )
        chain = LLMChain(llm=llm, prompt=prompt)

        # Process entities in batches
        results = []
        with st.spinner("Processing..."):
            for i in range(0, len(entities), batch_size):
                batch = entities.iloc[i:i + batch_size]
                for _, row in batch.iterrows():
                    main_value = row[main_column]
                    query = chain.run({"main_value": main_value})
                    results.append({"Main Value": main_value, "Response": query})

                time.sleep(1)  # Simulate rate-limiting

        # Display results
        results_df = pd.DataFrame(results)
        if not results_df.empty:
            st.write("Results:")
            st.dataframe(results_df)

            # Download results
            results_csv = results_df.to_csv(index=False).encode("utf-8")
            st.download_button("Download Results as CSV", results_csv, "results.csv", "text/csv")
        else:
            st.warning("No results were generated.")
