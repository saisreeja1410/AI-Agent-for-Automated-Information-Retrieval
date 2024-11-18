# AI Agent for Automated Information Retrieval

## Overview
This project is a Streamlit-based application that integrates with external APIs to automate information retrieval and processing. It allows users to upload data from CSV files or Google Sheets, perform web searches, and extract meaningful information using advanced APIs like RapidAPI and Groq.

## 🚀Features

- **Data Integration**: Supports CSV uploads and Google Sheets as input sources.
- **Automated Web Search**: Utilizes RapidAPI to search and retrieve relevant information.
- **AI-Powered Data Processing**: Extracts structured insights using the Groq API for enhanced interpretation.
- **Batch Processing**: Handles data in batches for efficient processing.
- **Downloadable Results**: Processed results can be exported as a CSV file.
- **User-Friendly Interface**: Streamlit-based interface for seamless user interaction.

---

## 🔧Setup Instructions

### Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.8 or later
- `pip` (Python package manager)

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/saisreeja1410/AI-Agent-for-Automated-Information-Retrieval.git
   cd AI-Agent-for-Automated-Information-Retrieval
   
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   
3. Run the Application:
   ```bash
   streamlit run app.py
   
### Configuration
- Update any API keys or credentials in the config.py file (if applicable).
- Configure the application settings (like database, endpoint URLs, etc.) in app.py or a .env file.

---
## 🖥️Usage
1. Select Data Source
   - Choose between CSV Upload or Google Sheets.
2. Upload or Connect Data
   - For CSV: Upload your file directly.
   - For Google Sheets: Provide credentials, spreadsheet ID, and range.
3. Enter Search Parameters
   - Select the main column containing entities.
   - Provide a prompt (e.g., Get {main_column} for {Company}).
   - Enter your API keys for RapidAPI and Groq.
4. Run the Search
   - Click the Run Search button to start processing.
   - Monitor progress using the displayed progress bar.
5. View and Download Results
   - Review the processed results in the app.
   - Download them as a CSV file for further use.

---
## 🔬 APIs Used
1. Google Sheets API
   - Retrieves data from Google Sheets.
   - Requires a JSON credentials file for authentication.
2. RapidAPI (Google Search API)
   - Performs web searches for the given entities.
   - Requires a RapidAPI key for access.
3. Groq API
   - Processes retrieved snippets to extract structured information.
   - Requires a Groq API key.

---
## 🛠️ Key Functions
1. Google Sheets Integration:
   - Authenticates and fetches data using Google Sheets API.
2. Search Query Execution:
   - Sends search queries to RapidAPI and retrieves results.
3. AI-Based Snippet Processing:
   - Extracts insights using Groq API from retrieved snippets.
4. Batch Processing:
   - Splits data into manageable chunks for efficient handling.
5. Result Export:
   - Converts processed results into a downloadable CSV format.

---
## ⚙️ Customizations
You can modify the following parameters as needed:

- Batch Size: Adjust in the batch_data function for optimized performance.
- APIs: Replace or add additional APIs to enhance functionality.
- Prompt: Customize the input prompt for tailored searches.

---
## 📋 Dependencies
Install the following Python libraries (listed in requirements.txt):

- streamlit
- pandas
- httpx
- google-api-python-client
- google-auth

---
## 📄License
This project is licensed under the MIT License.

---
## 🤝 Contributing
Contributions are welcome! To contribute:

1. Fork this repository.
2. Create a new feature branch: git checkout -b feature-name.
3. Commit changes: git commit -m "Add feature".
4. Push to the branch: git push origin feature-name.
5. Submit a pull request.

---
## 📬 Contact
For queries or feedback, reach out:

- Author: Sudhagani Sai Sreeja
- Email: saisreeja1410@example.com
- GitHub: saisreeja1410
