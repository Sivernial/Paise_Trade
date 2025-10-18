import os
import time
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

kite = KiteConnect(api_key=API_KEY)

print("===============================================")
print(">> Login URL (open this in your browser):")
print(kite.login_url())
print("===============================================")

print("\n🚀 Waiting for request token from Flask server (token_server.py)...\n")

# Wait until Flask server saves the token
request_token = None
while not request_token:
    if os.path.exists("request_token.txt"):
        with open("request_token.txt", "r") as f:
            request_token = f.read().strip()
    else:
        time.sleep(2)

# Generate session and get access token
try:
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = data["access_token"]
    print("\n✅ Access Token generated successfully!!\n")
    print("ACCESS_TOKEN:", access_token)

    with open("access_token.txt", "w") as f:
        f.write(access_token)

except Exception as e:
    print("❌ Error generating session:", str(e))
