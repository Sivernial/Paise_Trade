import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load API keys
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

kite = KiteConnect(api_key=API_KEY)

print("===============================================")
print(">> Login URL (open this in your browser):")
print(kite.login_url())
print("===============================================")

# After you log in on the above link, you'll be redirected to your redirect URL
# (e.g. http://127.0.0.1:8000/?request_token=XXXXXXXXX)
# Copy the request_token from the URL and paste it below:

request_token = input("Enter request token: ").strip()

# Generate session and get access token
try:
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = data["access_token"]
    print("\n✅ Access Token generated successfully!\n")
    print("ACCESS_TOKEN:", access_token)

    # Optionally save it to a file for later use
    with open("access_token.txt", "w") as f:
        f.write(access_token)

except Exception as e:
    print("❌ Error generating session:", str(e))
