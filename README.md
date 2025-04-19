## Introduction
EmailGenius is an AI-driven email categorization tool that automates the process of sorting and labeling emails . It connects to an IMAP server, fetches emails, and categorizes them based on user-defined criteria. The project also includes a Streamlit interface for an interactive user experience.

## Requirements
- Python 3.x
- there are two ways tto categorize
- this is the first one
- This is an optional procedure since it is not free
- LLAMA API Key (I used https://deepinfra.com, needs `openai==0.28`)
- IMAP Server Credentials (refer [accessing-gmail-inbox-using-python-imaplib-module](https://pythoncircle.com/post/727/accessing-gmail-inbox-using-python-imaplib-module/) to create your gmail python app password)
- second way doesnot need any apikey
- except the firebase key for database purpose
- Streamlit
- for login page use the respective email and its app password 

## Installation
1. Clone the repository:
   ```
   git clone https://github.com/srishti9368/Email-classifier.git
   ```
2. Navigate to the project directory:
   ```
   cd Email-classifier
   ```
3. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

## Usage
1. To ingest emails from your IMAP server to a `data/email_data.json` file:
   ```
   streamlit run src/main.py -- --ingest true
   ```
2. To run the Streamlit app for categorization:
   ```
    streamlit run src/main.py
   ```
3. To use it in production:
   ```
    streamlit run src/main.py -- --approve true
   ```

### Streamlit App
- Launch the app and enter a category in the text input field.
- Click 'Submit' to categorize emails based on the specified category.
- The app displays the processed emails along with their categorization.
- In production mode (using the --approve flag), labels are generated and the actual sorting of emails into these labels occurs.

## Screenshots
![Screenshot 2023-11-28 at 9 44 10 PM](https://github.com/0xrushi/emailgenius/assets/6279035/e94d70f1-6ba2-43a3-915b-6d4b8eb29e79)
![Screenshot 2023-11-28 at 9 49 00 PM](https://github.com/0xrushi/emailgenius/assets/6279035/4c6370f4-abca-4b50-bdd0-11ecfb11cb4a)
![Screenshot 2023-11-28 at 10 12 53 PM](https://github.com/0xrushi/emailgenius/assets/6279035/4dfa487c-ff54-45e1-92b6-0feba8fb62e5)
![Screenshot 2023-11-28 at 10 13 08 PM](https://github.com/0xrushi/emailgenius/assets/6279035/024cda90-eff3-4e7e-b595-614e7da4b6d6)

 

