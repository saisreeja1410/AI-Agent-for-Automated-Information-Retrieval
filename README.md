# AI-Agent-for-Automated-Information-Retrieval
This project creates an AI-powered agent capable of reading a dataset (CSV or Google Sheets), performing automated web searches for specific information, and extracting data based on user-defined prompts. It includes a user-friendly dashboard for file uploads, search customization, and result download.
## Features
- **File Upload**: Users can upload a CSV or connect a Google Sheet to use as the data source.
- **Custom Prompt Input**: Dynamically input queries to retrieve specific information for entities in the selected column.
- **Automated Web Search**: Conducts a search for each entity and retrieves relevant information.
- **LLM-based Data Extraction**: Processes search results through an LLM to extract targeted information.
- **Data Display & Download**: Presents extracted data in a table format and allows download as CSV or updates to the Google Sheet.

---

## Setup Instructions

### 1. Prerequisites
Ensure you have the following installed:
- **Python** (3.8+)
- **Pip** for Python package management
- **API Keys**: 
  - **LLM API** (e.g., OpenAI API or Groq API)
  - **Search API** (e.g., SerpAPI or ScraperAPI)
  - **Google Sheets API** (optional, if connecting to Google Sheets)

### 2. Environment Setup
Clone this repository and navigate to the project directory:
```bash
git clone https://github.com/saisreeja1410/AI-Agent-for-Automated-Information-Retrieval.git
cd AI-Agent-for-Automated-Information-Retrieval
