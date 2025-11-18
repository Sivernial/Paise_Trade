import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

def login():
    if not API_KEY or not API_SECRET:
        logger.error("API_KEY or API_SECRET not found in environment")
        return None
    
    kite = KiteConnect(api_key=API_KEY)
    
    print("=" * 50)
    print("Login URL:")
    print(kite.login_url())
    print("=" * 50)
    
    request_token = input("Enter request token: ").strip()
    
    try:
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = data["access_token"]
        
        logger.info("Access token generated successfully")
        
        with open("access_token.txt", "w") as f:
            f.write(access_token)
        
        kite.set_access_token(access_token)
        
        return kite
    
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return None

def get_kite_instance():
    if not API_KEY:
        logger.error("API_KEY not found")
        return None
    
    kite = KiteConnect(api_key=API_KEY)
    
    if os.path.exists("access_token.txt"):
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
        kite.set_access_token(access_token)
        logger.info("Using saved access token")
        return kite
    else:
        logger.warning("No saved access token, please login")
        return login()

if __name__ == "__main__":
    kite = login()
    if kite:
        print("Login successful!")
        profile = kite.profile()
        print(f"Logged in as: {profile['user_name']}")

