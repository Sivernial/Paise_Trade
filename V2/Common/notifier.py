import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class Notifier:
    """
    Handles sending notifications to external services (Telegram, Slack, etc.)
    """
    def __init__(self):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.telegram_token and self.telegram_chat_id)
        
        if self.enabled:
            logger.info("Telegram Notifications Enabled ✅")
        else:
            logger.info("Telegram Config missing. Alerts will be console only.")

    def send(self, message: str):
        """
        Send alert message. Defaults to console + Telegram if configured.
        """
        # Always log to console
        logger.info(f"🚨 ALERT: {message}")
        
        if self.enabled:
            self._send_telegram(message)

    def _send_telegram(self, message: str):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code != 200:
                logger.error(f"Failed to send Telegram alert: {resp.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")

# Global instance
notifier = Notifier()
