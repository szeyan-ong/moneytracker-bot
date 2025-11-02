from __future__ import print_function
import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes — read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authorize_gmail():
    creds = None

    # token.pickle stores the user’s access and refresh tokens
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # If there are no valid credentials, log in via browser
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    service = build("gmail", "v1", credentials=creds)
    print("✅ Gmail authorization complete.")
    return service


if __name__ == "__main__":
    service = authorize_gmail()
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No messages found.")
    else:
        print("Latest message IDs:")
        for msg in messages:
            print(msg["id"])
