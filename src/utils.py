import os
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import re
import json

# Email server settings
IMAP_SERVER = 'imap.gmail.com'
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587


def remove_long_urls(text):
    """Remove URLs from the given text."""
    return re.sub(r'https?:\/\/(www\.)?([a-zA-Z0-9.-]+).*?(\s|$)', '', text).strip()


def clean_text(text):
    """Remove non-ASCII characters from the given text."""
    ascii_text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return ' '.join(ascii_text.split())


def clean_html(html_content):
    """Convert HTML content to plain text and remove script/style tags."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    return soup.get_text(separator='\n')


def read_json_file(file_path):
    """Read email data from a JSON file."""
    email_entries = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                email_data = json.loads(line)
                email_entries.append(email_data)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
    return email_entries


def connect_to_imap():
    """Connect to the IMAP server."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(os.environ['USERNAME'], os.environ['PASSWORD'])
    return mail


def connect_to_smtp():
    """Connect to the SMTP server."""
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(os.environ['USERNAME'], os.environ['PASSWORD'])
    return server


def fetch_emails(mail, search_criteria='ALL'):
    """Fetch emails matching the search criteria."""
    mail.select('inbox')
    result, data = mail.search(None, search_criteria)
    if result != 'OK':
        print("Error fetching emails.")
        return []
    email_ids = data[0].split()
    return email_ids


def get_email_body(mail, email_id):
    """Retrieve the body of an email by ID."""
    result, data = mail.fetch(email_id, '(RFC822)')
    if result != 'OK':
        print(f"Error fetching email {email_id}.")
        return None
    raw_email = data[0][1]
    email_message = BeautifulSoup(raw_email, 'html.parser')
    return clean_html(email_message.get_text())


def send_email(to_email, subject, body):
    """Send an email using SMTP."""
    from_email = os.environ['USERNAME']
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = connect_to_smtp()
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()
    print(f"Email sent to {to_email}")


def move_email_to_label(mail, email_id, label_name):
    """Move an email to a specified IMAP label."""
    mail.select('inbox')
    result, _ = mail.uid('STORE', email_id, '+X-GM-LABELS', label_name)
    if result == 'OK':
        print(f"Email with ID {email_id} has been moved to {label_name}")
    else:
        print(f"Failed to move email with ID {email_id}")


def main():
    # Connect to IMAP
    mail = connect_to_imap()

    # Fetch all emails
    email_ids = fetch_emails(mail, 'ALL')
    print(f"Fetched {len(email_ids)} emails.")

    # Process emails
    for email_id in email_ids[:5]:  # Limit to first 5 for demonstration
        body = get_email_body(mail, email_id)
        if body:
            clean_body = clean_text(body)
            print(f"Cleaned Email Body:\n{clean_body}")

    # Move an email to a label (example)
    if email_ids:
        move_email_to_label(mail, email_ids[0], 'TestLabel')

    # Send a test email
    send_email('recipient@example.com', 'Test Subject', 'This is a test email.')

    # Logout
    mail.logout()


if __name__ == '__main__':
    main()
 