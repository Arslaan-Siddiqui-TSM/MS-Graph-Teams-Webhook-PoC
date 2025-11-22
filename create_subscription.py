import os
from datetime import datetime, timedelta, timezone

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
TEAM_ID = os.getenv("TEAM_ID")
CHANNEL_ID = os.getenv("CHANNEL_ID")
CLIENT_STATE = os.getenv("CLIENT_STATE", "superSecretClientState123")
PUBLIC_URL = os.getenv("PUBLIC_URL")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# For channel messages: ChannelMessage.Read.All
# For chat messages: use Chat.Read and change resource accordingly
SCOPES = ["ChannelMessage.Read.All"]  # delegated scope


def acquire_user_token():
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
    )

    # Try silent first (if cache is in-memory; for PoC this will almost always miss)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print("Got token silently.")
            return result["access_token"]

    # Interactive via device code
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Failed to create device flow")

    print("To sign in, use a browser to visit:")
    print(flow["verification_uri"])
    print("and enter the code:")
    print(flow["user_code"])

    result = app.acquire_token_by_device_flow(flow)  # blocks until complete or error
    if "access_token" in result:
        print("Sign-in successful.")
        return result["access_token"]

    raise RuntimeError(f"Could not acquire token: {result}")


def create_subscription():
    access_token = acquire_user_token()

    expiration = datetime.now(timezone.utc) + timedelta(minutes=30)  # < 1 hour is simpler
    expiration_str = expiration.isoformat(timespec="seconds").replace("+00:00", "Z")

    subscription_payload = {
        "changeType": "created,updated",
        "notificationUrl": f"{PUBLIC_URL}/graph/webhook",
        "resource": f"/teams/{TEAM_ID}/channels/{CHANNEL_ID}/messages",
        "expirationDateTime": expiration_str,
        "clientState": CLIENT_STATE,
        # For now we keep includeResourceData=false by omission (default)
        # so we don't need encryption certs in this PoC
    }

    print("Creating subscription with payload:")
    print(subscription_payload)

    resp = requests.post(
        f"{GRAPH_BASE_URL}/subscriptions",
        json=subscription_payload,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    print("Status code:", resp.status_code)
    print("Response:", resp.text)
    resp.raise_for_status()

    sub = resp.json()
    print("\nSubscription created!")
    print("ID:", sub["id"])
    print("Expires:", sub["expirationDateTime"])


if __name__ == "__main__":
    create_subscription()
