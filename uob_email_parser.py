import base64
import re
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# --- 1. Authenticate Gmail using the token you just created ---
def get_gmail_service():
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
    service = build('gmail', 'v1', credentials=creds)
    return service


# --- 2. Get recent UOB emails ---
def get_recent_uob_emails(max_results=5):
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        q='from:unialerts@uobgroup.com subject:transaction',
        maxResults=max_results
    ).execute()
    messages = results.get('messages', [])
    
    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_data.get('snippet', '')
        emails.append(snippet)
    return emails


# --- 3. Extract transaction info from email text ---
def parse_transaction(email_text):
    """
    Example email:
    A transaction of SGD 12.10 was made with your UOB Card ending 0223 on 28/10/25 at CHICHA SAN CHEN - STAR VI.
    """
    pattern = r'SGD\s([\d,]+\.\d{2}).*?on\s(\d{2}/\d{2}/\d{2}).*?at\s([A-Z0-9\s\-\&\.\']+)'
    match = re.search(pattern, email_text)
    
    if match:
        amount = float(match.group(1).replace(',', ''))
        date = match.group(2)
        merchant = match.group(3).strip()
        return {"amount": amount, "date": date, "merchant": merchant}
    return None


# --- 4. Test it ---
if __name__ == "__main__":
    emails = get_recent_uob_emails(3)
    for e in emails:
        txn = parse_transaction(e)
        if txn:
            print(f"✅ Parsed transaction: {txn}")
        else:
            print(f"⚠️ Could not parse: {e}")
