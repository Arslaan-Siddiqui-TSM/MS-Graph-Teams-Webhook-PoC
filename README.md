# MS Graph Teams Webhook PoC

This small proof-of-concept shows how to create a Microsoft Graph subscription for Teams channel messages and receive notifications in a simple Flask webhook.

Files

- `app.py` - Flask app that exposes the `/graph/webhook` endpoint to handle subscription validation requests and notifications from Microsoft Graph.
- `create_subscription.py` - Script that acquires a delegated user token via MSAL device code flow and creates a subscription for messages in a Teams channel.
- `requirements.txt` - Python dependencies used by the project.

Prerequisites

- Python 3.10+ (tested with 3.11)
- An Azure AD application and appropriate permissions. For this PoC the following are relevant:
  - Delegated: ChannelMessage.Read.All (used by `create_subscription.py` when signing-in via device code)
  - Application permissions are not required for the device flow in this example, but `app.py` contains a helper to fetch an app-only token if you adapt it.
- A publicly reachable URL for the Flask webhook (e.g., using ngrok, Cloud Run, or another public host). Microsoft Graph must be able to POST to the `notificationUrl` you provide.

Environment
Create a `.env` file in the project root with the following values (examples shown):

```
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=your-client-secret     # only needed if you use app-only token flows
TEAM_ID=your-team-id
CHANNEL_ID=your-channel-id
PUBLIC_URL=https://<your-public-host>    # used by create_subscription.py as notificationUrl base
CLIENT_STATE=superSecretClientState123   # optional; used to validate notifications
```

Install

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

How it works

- `create_subscription.py` performs an MSAL device code flow to obtain a delegated access token for a user who can read channel messages. It then POSTs a subscription to `https://graph.microsoft.com/v1.0/subscriptions` requesting notifications for created/updated messages in the specified channel. The `notificationUrl` points to your running `app.py` webhook (must be publicly reachable).
- When Graph validates the subscription, it will send a GET request containing a `validationToken` to the webhook. `app.py` handles this and returns the token in plain text to complete validation.
- Subsequent notifications will be sent as POST requests to the webhook. The app prints the raw payload to stdout and performs a basic `clientState` check to guard against unsolicited messages.

Run the webhook (Flask)

```powershell
set FLASK_APP=app.py
python app.py
```

By default the Flask app listens on 0.0.0.0:5000. If you use a tunneling tool (e.g., ngrok), create a tunnel from your public URL to `localhost:5000` and set `PUBLIC_URL` accordingly.

Create the subscription

```powershell
python create_subscription.py
```

Follow the instructions printed by the script to complete device code sign-in. The script will print the subscription response including the subscription ID and expiration.

Notes and troubleshooting

- ValidationToken missing / 400: Ensure your `PUBLIC_URL` is the exact base URL Graph can reach. If using ngrok, use the `https://` forwarding URL.
- clientState mismatch: The app checks `clientState` in notifications. Make sure `CLIENT_STATE` in `.env` matches the value used when creating the subscription (or omit it if you prefer).
- 401 when creating subscription: Ensure the delegated user has consented to the `ChannelMessage.Read.All` permission and that the token was acquired successfully via device flow.
- Subscription short-lived: Microsoft Graph subscriptions for chat/messages often have short maximum lifetimes. This script sets a 30-minute expiration for simplicity; in production you'll need a renewal process.

Security

- Do not commit `.env` or secrets to source control. Use a secure key store for production secrets.
- This repository is a PoC and omits encryption/cert handling for resource data. Do not use as-is in production.

Next steps / improvements

- Add persistent storage for subscription IDs and renewal logic.
- Support app-only subscriptions if desired (requires an app certificate/secret and different permission setup).
- Add structured logging and signature verification for higher assurance.

License
MIT-style for PoC use. Adjust as needed.
