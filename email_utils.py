from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import re

def get_gmail_service():
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
    return build('gmail', 'v1', credentials=creds)

def get_recent_uob_emails(max_results=5):
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me',
        q='from:unialerts@uobgroup.com subject:transaction',
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])
    if not messages:
        return []

    transactions = []
    for msg in messages:
        txt = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        snippet = txt.get('snippet', '')

        # Example: A transaction of SGD 12.10 was made with your UOB Card ending 0223 on 28/10/25 at CHICHA SAN CHEN - STAR VI.
        match = re.search(r'SGD\s([\d\.]+).*?on\s(\d{2}/\d{2}/\d{2}).*?at\s(.+?)(?:\.|If)', snippet)
        if match:
            amount, date, merchant = match.groups()
            transactions.append({
                "amount": float(amount),
                "date": date,
                "merchant": merchant.strip()
            })
    return transactions
