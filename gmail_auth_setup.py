from google_auth_oauthlib.flow import InstalledAppFlow

# Define the Gmail API scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    # Run OAuth flow to get credentials interactively
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the token for future use
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    print("✅ Gmail authorization complete! token.json has been saved.")

if __name__ == '__main__':
    main()
