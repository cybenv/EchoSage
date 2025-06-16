"""
Web server for handling Telegram webhook requests in serverless environment.
This file acts as the entry point for the gunicorn server defined in Dockerfile.
"""
import json
import logging
from flask import Flask, request, jsonify

from bot import handler

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init Flask
app = Flask(__name__)

@app.route("/", methods=["POST"])
def webhook():
    """Process incoming webhook requests from Telegram"""
    try:
        # Log the incoming request
        logger.info("Received webhook request")
        
        # Create the event structure expected by the handler function
        event = {
            "body": request.data.decode("utf-8")
        }
        
        import asyncio
        # Process the webhook with the existing handler using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(handler(event, {}))
        loop.close()
        
        # Return result
        return jsonify(json.loads(result.get("body", '{"ok": false}')))
    
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    """Check endpoint"""
    return jsonify({"status": "ok", "message": "EchoSage bot is running"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
