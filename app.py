import os
import json
from datetime import datetime, timedelta, timezone

from flask import Flask, request
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TEAM_ID = os.getenv("TEAM_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLIENT_STATE = os.getenv("CLIENT_STATE", "superSecretClientState123")

GRAPH_TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

app = Flask(__name__)


def get_app_token():
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials",
        "scope": "https://graph.microsoft.com/.default",
    }
    resp = requests.post(GRAPH_TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_message(resource_path: str):
    """
    resource_path is something like:
    'teams/{team-id}/channels/{channel-id}/messages/{message-id}'
    """
    access_token = get_app_token()
    url = f"{GRAPH_BASE_URL}/{resource_path.lstrip('/')}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
    resp.raise_for_status()
    return resp.json()


@app.route("/graph/webhook", methods=["GET", "POST"])
def graph_webhook():
    # 1) Subscription validation (GET or POST with validationToken)
    validation_token = request.args.get("validationToken")
    if validation_token:
        print("Received validation request from Graph.")
        print("Validation token:", validation_token)
        return validation_token, 200, {"Content-Type": "text/plain"}

    # 2) Real notifications (POST)
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        print("Raw notification payload:")
        print(json.dumps(data, indent=2))

        notifications = data.get("value", [])
        for n in notifications:
            client_state = n.get("clientState")
            if client_state and client_state != CLIENT_STATE:
                print("WARNING: clientState mismatch. Ignoring notification.")
                continue

            resource = n.get("resource")
            change_type = n.get("changeType")
            print(f"Notification: changeType={change_type}, resource={resource}")

        return "", 202

    return "", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
