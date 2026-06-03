"""
One-time YouTube OAuth setup.
Run this once locally to generate token.json, then add it to GitHub secrets.
After that, GitHub Actions handles all uploads — no local auth needed ever again.
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    print("\n=== TrendPulse — YouTube One-Time Auth ===\n")
    print("This will open Chrome for YouTube authorization.")
    print("Sign in with: yashwanthan00@gmail.com\n")

    flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=True)

    with open("token.json", "w") as f:
        f.write(creds.to_json())

    print("\n✅ token.json saved successfully!\n")
    print("Next step — add this as a GitHub secret named YOUTUBE_TOKEN:")
    print("=" * 60)
    print(open("token.json").read())
    print("=" * 60)
    print("\nAlso add CLIENT_SECRETS secret with contents of client_secrets.json")
    print("\nGo to: github.com/yashwanthan00/TrendPulse → Settings → Secrets → Actions")

if __name__ == "__main__":
    main()
