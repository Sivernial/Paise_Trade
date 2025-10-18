from flask import Flask, request
import json

app = Flask(__name__)

@app.route("/")
def get_request_token():
    token = request.args.get("request_token")
    if token:
        print(f"\n✅ Request Token received: {token}")
        # Save to file for use by main.py
        with open("request_token.txt", "w") as f:
            f.write(token)
        return "✅ Request token received successfully! You can close this tab and return to your terminal."
    else:
        return "❌ No request token found in URL. Did you open the correct login link?"

if __name__ == "__main__":
    print("🚀 Waiting for Zerodha redirect... (Ctrl+C to exit)")
    app.run(host="127.0.0.1", port=8000)
