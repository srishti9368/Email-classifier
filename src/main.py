import streamlit as st
import firebase_admin
from firebase_admin import auth, credentials
import json
import openai
import pandas as pd
from imap_tools import MailBox, AND
from utils import remove_long_urls, clean_text, read_json_file, clean_html
from nltk.corpus import wordnet
import nltk
from sentence_transformers import SentenceTransformer
from functools import lru_cache
from datetime import datetime, timedelta

nltk.download('wordnet')
model = SentenceTransformer('all-MiniLM-L6-v2')

# Theme selector
theme = st.selectbox("🎨 Choose Theme", ["Light", "Dark"])

# Theme styling
if theme == "Dark":
    st.markdown("""<style>
    body, .stApp { background-color: #202124; color: #e8eaed; font-family: "Roboto", sans-serif; }
    .stTextInput > div > div > input, .stTextArea > div > textarea, .stSelectbox > div > div,
    .stNumberInput > div, .stButton > button, .stDataFrame {
        background-color: #303134 !important; color: #e8eaed !important; border: 1px solid #333333 !important;
        border-radius: 6px;
    }
    .stButton > button:hover { background-color: #3c3f41 !important; color: #ffffff !important; }
    .stTextInput > label, .stSelectbox > label, .stNumberInput > label, .stTextArea > label {
        color: #e8eaed !important;
    }
    .stAlert-success {
        background-color: #263b27 !important; color: #b9f6ca !important; font-weight: 500;
    }
    [data-testid="stExpander"] {
        background-color: #303134; padding: 1.5rem; border-radius: 10px; border: 2px solid #555; margin-top: 1rem;
    }
    [data-testid="stExpander"] summary {
        font-size: 1.2rem; font-weight: bold; color: #e8eaed;
    }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    body, .stApp { background-color: #e5e5e5; color: #202124; font-family: "Roboto", sans-serif; }
    .stTextInput>div>div>input, .stButton>button, .stDataFrame {
        background-color: #d2d4d6; color: #202124; border: none; border-radius: 6px;
    }
    .stTextInput>label, .stButton>button:hover { color: #202124; }
    .stAlert-success {
        background-color: #c8f7c5 !important; color: #1e4620 !important; font-weight: 500;
    }
    label[for="number_input_Fetch_emails_from_past_N_days:"] {
        color: black !important; font-weight: bold;
    }
    </style>""", unsafe_allow_html=True)

# Firebase setup
cred = credentials.Certificate("firebase_credentials.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Session defaults
st.session_state.setdefault("user", None)
st.session_state.setdefault("gmail_app_password", None)
st.session_state.setdefault("OPENAI_API_KEY", None)
st.session_state.setdefault("API_VALID", False)
st.session_state.setdefault("category_keywords", {
    "Urgent": ["urgent", "asap", "important", "immediate", "priority"],
    "Finance": ["invoice", "payment", "refund", "billing", "transaction"],
    "Meetings": ["meeting", "appointment", "schedule", "conference", "calendar"],
    "Offers": ["offer", "discount", "sale", "promo", "deal"]
})

# Gmail verification
def verify_gmail_connection(email, app_password):
    try:
        with MailBox('imap.gmail.com').login(email, app_password, initial_folder='INBOX'):
            return True, None
    except Exception as e:
        return False, str(e)

# Firebase login
def google_login(email, app_password):
    try:
        auth.get_user_by_email(email)
        st.session_state.user = email
        st.session_state.gmail_app_password = app_password
        success, msg = verify_gmail_connection(email, app_password)
        if success:
            st.success(f"Login successful for {email}! ✅ Gmail connection verified.")
        else:
            st.warning(f"Login successful, but Gmail connection failed: {msg}")
    except Exception as e:
        st.error(f"Login failed: {e}")

# 🔐 Login/Signup logic
query_params = st.query_params
mode = query_params.get("mode", "login")

if not st.session_state.user:
    st.title("Google Account Login (Use App Password)")
    st.write("🔹 **Use a Google App Password instead of your regular Google password.**")

    email = st.text_input("Google Email")
    app_password = st.text_input("Google App Password", type="password")

    if mode == "login":
        if st.button("Log In"):
            if email and app_password:
                try:
                    auth.get_user_by_email(email)
                    google_login(email, app_password)
                except:
                    st.warning('No account found for this email. You can [Sign Up here](?mode=signup)', icon="⚠️")
    else:  # signup
        if st.button("Sign Up"):
            try:
                auth.create_user(email=email)
                st.success(f"✅ Account created for {email}. You can now [Log In here](?mode=login)")
            except Exception as e:
                st.error(f"Signup failed: {e}")
else:
    st.success(f"✅ Logged in as {st.session_state.user}")

# API Key section
if st.session_state.user:
    with st.expander("🔐 Enter DeepInfra API Key", expanded=True):
        api_key_input = st.text_input("DeepInfra API Key", type="password", key="deepinfra_input")
        if st.button("Validate & Save API Key"):
            openai.api_key = api_key_input
            openai.api_base = 'https://api.deepinfra.com/v1/openai'
            try:
                test_response = openai.ChatCompletion.create(
                    model="meta-llama/Llama-2-70b-chat-hf",
                    messages=[{"role": "user", "content": "Say Hello"}],
                    stream=False,
                    max_tokens=5,
                )
                st.session_state.OPENAI_API_KEY = api_key_input
                st.session_state.API_VALID = True
                st.success("✅ API Key is valid and saved.")
            except Exception as e:
                st.session_state.API_VALID = False
                st.error(f"❌ Invalid API Key: {e}")

# Logout
if st.session_state.user and st.button("Logout"):
    st.session_state.user = None
    st.session_state.gmail_app_password = None
    st.session_state.OPENAI_API_KEY = None
    st.session_state.API_VALID = False
    open('data/email_data.json', 'w').close()
    st.success("Logged out successfully. Emails cleared.")

# Email classification
if st.session_state.user:
    st.title("Email Classification")
    input_category = st.text_input("Enter a category:")
    days_limit = st.number_input("Fetch emails from past N days:", min_value=1, max_value=30, value=7)

    @lru_cache(maxsize=1024)
    def get_synonyms_cached(word):
        synonyms = set()
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name().replace("_", " "))
        return synonyms

    def update_category_keywords(user_category):
        if user_category not in st.session_state.category_keywords:
            words = user_category.lower().split()
            expanded_keywords = set(words)
            for word in words:
                expanded_keywords.update(get_synonyms_cached(word))
            st.session_state.category_keywords[user_category] = list(expanded_keywords)

    def ingest_emails(username, app_password, imap_server, days):
        json_file = 'data/email_data.json'
        since_date = (datetime.now() - timedelta(days=days)).date()
        with open(json_file, 'w') as file:
            with MailBox(imap_server).login(username, app_password, initial_folder='INBOX') as mailbox:
                for msg in mailbox.fetch(AND(date_gte=since_date)):
                    email_body = msg.text or clean_html(msg.html)
                    cleaned_body = clean_text(email_body)
                    email_data = {
                        'id': msg.uid,
                        'date': msg.date.strftime('%Y-%m-%d %H:%M:%S'),
                        'from': msg.from_,
                        'to': msg.to,
                        'subject': msg.subject,
                        'body': cleaned_body,
                    }
                    file.write(json.dumps(email_data) + '\n')

    if st.button("Fetch Emails"):
        if st.session_state.gmail_app_password:
            ingest_emails(st.session_state.user, st.session_state.gmail_app_password, 'imap.gmail.com', days_limit)
            st.success("Emails fetched successfully!")
        else:
            st.error("Please log in first.")

    if st.button("Classify Emails (Keyword Detection)"):
        try:
            update_category_keywords(input_category)
            emails = read_json_file('data/email_data.json')
            matched_keywords = st.session_state.category_keywords[input_category]
            classified_emails = []
            for msg in emails:
                email_text = f"{msg['subject']} {msg['body']}".lower()
                detected_keywords = [kw for kw in matched_keywords if kw in email_text]
                if detected_keywords:
                    classified_emails.append({
                        'Date/Time': msg.get('date', 'N/A'),
                        'From': msg['from'],
                        'Subject': msg['subject'],
                        'Matched Keywords': ", ".join(detected_keywords)
                    })
            if classified_emails:
                st.write(f"📌 **Classified Emails Under '{input_category}':**")
                st.dataframe(pd.DataFrame(classified_emails))
            else:
                st.info("No emails matched the selected category.")
        except Exception as e:
            st.error(f"Error in classification: {e}")

    if st.button("Classify Emails (AI-based)"):
        if st.session_state.API_VALID:
            emails = read_json_file('data/email_data.json')
            df = pd.DataFrame(columns=['From', 'Subject', 'Label'])
            prompt_template = """Assess whether the email falls under the '{category}' category.
            Email: {email}.
            If yes, return {{"Output": 1}}, else {{"Output": 0}}."""

            for msg in emails:
                email_content = f"{msg['from']}\n{msg['subject']}\n{msg['body']}"
                prompt = prompt_template.format(category=input_category, email=email_content)
                prompt = remove_long_urls(clean_text(prompt))

                chat_completion = openai.ChatCompletion.create(
                    model="meta-llama/Llama-2-70b-chat-hf",
                    messages=[{"role": "user", "content": prompt}],
                    stream=False,
                    max_tokens=256,
                )
                response = chat_completion.choices[0].message.content.strip()
                try:
                    label = str(json.loads(response)['Output'])
                except json.JSONDecodeError:
                    label = "N/A"

                df = pd.concat([df, pd.DataFrame({'From': [msg['from']], 'Subject': [msg['subject']], 'Label': [label]})])

            st.write("Classified Emails:")
            st.dataframe(df[df['Label'] == "1"])
        else:
            st.warning("Please enter your DeepInfra API Key after login.")
