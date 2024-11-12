import streamlit as st
import pandas as pd
import requests
import openai

# Define the search function to perform searches using SerpAPI
def perform_search(data, main_column, prompt, api_key):
    results = {}
    for entity in data[main_column]:
        # Replace {company} in the prompt with each entity in the main column
        search_query = prompt.replace("{company}", str(entity))
        print(f"Running search for: {search_query}")  # Debug: display the search query

        # SerpAPI endpoint and parameters
        url = "https://serpapi.com/search"
        params = {
            "q": search_query,
            "api_key": api_key,
            "engine": "google"
        }

        # Send request to SerpAPI
        response = requests.get(url, params=params)
        print(f"Response Status Code: {response.status_code}")  # Debug: display status code

        # Check for successful response and process results
        if response.status_code == 200:
            search_data = response.json().get("organic_results", [])
            print(f"Search results for {entity}: {search_data}")  # Debug: display search results
            results[entity] = search_data if search_data else "No results found."
        else:
            results[entity] = f"Error: {response.status_code}"

    return results

# Define the information extraction function using OpenAI API
def extract_information(results, openai_api_key):
    openai.api_key = openai_api_key
    extracted_data = {}
    for entity, search_results in results.items():
        # Format prompt for LLM
        prompt_text = f"Extract relevant information about {entity} from the following: {search_results}"
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt_text,
            max_tokens=100
        )
        extracted_data[entity] = response.choices[0].text.strip()
    return extracted_data

# Set up the Streamlit app layout
st.title("AI Agent for Automated Information Retrieval")
st.write("Welcome to the AI Agent Dashboard!")

# Step 1: Upload a CSV file
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    # Read and preview the uploaded CSV file
    data = pd.read_csv(uploaded_file)
    st.write("Preview of uploaded data:")
    st.dataframe(data)

    # Step 2: Let the user select the main column to use (e.g., company names)
    if not data.empty:
        main_column = st.selectbox("Select the main column", data.columns)
        st.write(f"Main column selected: {main_column}")

        # Step 3: Enter a custom query with {company} placeholder
        prompt = st.text_input("Enter your query (e.g., Get City for {company})")
        
        # Step 4: Get API keys for SerpAPI and OpenAI
        serpapi_key = st.text_input("Enter your SerpAPI key", type="password")
        openai_key = st.text_input("Enter your OpenAI API key", type="password")

        # Step 5: Run search when the button is clicked, and display results
        if st.button("Run Search") and main_column and prompt and serpapi_key and openai_key:
            st.write("Running search...")

            # Perform search using SerpAPI
            results = perform_search(data, main_column, prompt, serpapi_key)
            
            # Display the search results
            st.write("Search Results:")
            for entity, result in results.items():
                st.write(f"Results for {entity}: {result}")

            # Extract information from results using OpenAI API
            extracted_data = extract_information(results, openai_key)
            st.write("Extracted Information:")
            for entity, info in extracted_data.items():
                st.write(f"Extracted info for {entity}: {info}")

            # Step 6: Provide download option for extracted information
            if extracted_data:
                df = pd.DataFrame(list(extracted_data.items()), columns=["Entity", "Extracted Information"])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("Download Results", csv, "results.csv", "text/csv", key='download-csv')
    else:
        st.write("The uploaded file is empty. Please upload a valid CSV file.")
