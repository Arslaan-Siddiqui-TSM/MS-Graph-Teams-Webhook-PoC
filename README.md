# MS Graph Teams Webhook PoC — Step-by-step setup and run

This repository is a minimal proof-of-concept that demonstrates how to:

- Create a Microsoft Graph subscription for Teams channel messages.
- Receive and validate Microsoft Graph notifications in a Flask webhook.

The instructions below are intentionally detailed so you can follow them end-to-end.

Repository files

- `app.py` — Flask app exposing `/graph/webhook` to handle validation and notifications.
- `create_subscription.py` — Uses MSAL device code flow to get a delegated token and create a subscription for a channel's messages.
- `requirements.txt` — Project Python dependencies.

High-level flow

1. Register an Azure AD application and grant the delegated permission `ChannelMessage.Read.All`.
2. Run the Flask webhook locally and expose it publicly (e.g., ngrok).
3. Run the `create_subscription.py` script and follow the device-code sign-in to create a subscription pointing at your public webhook.
4. Microsoft Graph validates the webhook and sends notifications which `app.py` prints.

Section A — Azure AD app registration (detailed)

1. Sign in to the Azure portal (https://portal.azure.com) as an admin or an account with permission to register apps.
2. Navigate to "Azure Active Directory" → "App registrations" → "New registration".
   - Name: ms-graph-teams-poc (or something meaningful)
   - Supported account types: choose what fits (single-tenant is fine for PoC).
   - Redirect URI: not needed for device code flow — leave empty.
3. After creation, open the app's "Authentication" page and ensure "Allow public client flows" is enabled if present (device code requires this flag in some tenants).
4. Go to "API permissions" → "Add a permission" → Microsoft Graph → Delegated permissions.
   - Search and add: ChannelMessage.Read.All
5. (Optional) If you want to use app-only flows later, go to "Certificates & secrets" → "New client secret" and save the value to use as `CLIENT_SECRET`.
6. Note the values you'll need: `Directory (tenant) ID`, `Application (client) ID`. Keep them handy.

Section B — Create a Teams channel and get IDs

1. In Microsoft Teams, create or choose a team and a channel to monitor.
2. Get the `TEAM_ID` and `CHANNEL_ID`:
   - You can obtain these via Graph Explorer (https://developer.microsoft.com/graph/graph-explorer) or via the Teams client with developer tools.
   - Example Graph calls (use Graph Explorer while signed-in as a user with access):
     - List teams for user: `GET /me/joinedTeams`
     - List channels in a team: `GET /teams/{team-id}/channels`

Section C — Prepare a public webhook URL (ngrok)

Microsoft Graph must reach your webhook over HTTPS. The easiest local solution is ngrok.

1. Download ngrok (https://ngrok.com/) and sign up for a free account.
2. Install and authenticate ngrok on your machine following their instructions.
3. Start an HTTPS tunnel pointing at the Flask port (default 5000):

```powershell
ngrok http 5000
```

4. Note the `https://` Forwarding URL printed by ngrok (e.g., `https://abcd-1234.ngrok.io`).

Section D — Create `.env` (project config)

In the project root create a file named `.env` with these keys (no quotes, replace placeholders):

```
TENANT_ID=<your-tenant-id>
CLIENT_ID=<your-client-id>
# CLIENT_SECRET is NOT required for device flow but include if you plan to use app-only tokens later
CLIENT_SECRET=<your-client-secret-or-empty>
TEAM_ID=<your-team-id>
CHANNEL_ID=<your-channel-id>
PUBLIC_URL=<your-public-base-url>   # e.g. https://abcd-1234.ngrok.io
CLIENT_STATE=superSecretClientState123
```

Important: Do not commit `.env` to source control. Add it to `.gitignore` if not already ignored.

Section E — Create and activate a Python virtual environment + install deps

Open a cmd/PowerShell prompt in the repository root and run:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Section F — Run the Flask webhook locally

1. Ensure `.env` is filled and `PUBLIC_URL` matches the ngrok `https://` forwarding URL (no trailing slash).
2. Start the Flask application:

```powershell
set FLASK_APP=app.py
python app.py
```

3. You should see Flask output indicating it's serving on 0.0.0.0:5000. Leave this terminal running.

Section G — Create the subscription (device code flow)

1. In a separate terminal (with the virtualenv activated), run:

```powershell
python create_subscription.py
```

2. The script will print a device code flow message with a verification URL and code. Open the URL in a browser, sign in with the delegated user account (one that is in the same tenant and has access to the team/channel), and enter the code to grant the delegated consent.
3. After successful sign-in the script will send a POST to Microsoft Graph to create the subscription. It will print the subscription `id` and `expirationDateTime`.

Section H — Validate subscription creation and Graph validation step

1. When you create the subscription, Graph will perform a validation request to the `notificationUrl` you supplied. The validation request contains a query parameter `validationToken`.
2. `app.py` contains logic to detect `validationToken` and return it as plain text. If the validation succeeds you should see a 200 response from Graph in the `create_subscription.py` output (or in the ngrok request inspector).

Section I — Trigger and observe notifications

1. Post a message in the monitored channel (or update a message) to trigger a notification.
2. Graph will POST a notification payload to your webhook. `app.py` prints the raw notification JSON to stdout.
3. If you need more details about the message, use the `get_message()` helper inside `app.py` (or call Graph manually) to fetch the message resource using an app or user token.

Verification checklist

- Flask app running and reachable from the public URL (use ngrok's web UI to confirm incoming requests).
- `.env` values match Azure app and Teams IDs.
- `create_subscription.py` completed device flow and returned a 201 response with subscription details.
- A `validationToken` exchange was completed (visible in logs or ngrok requests).
- Notifications arrive when messages are created/updated in the channel and are printed by `app.py`.

Troubleshooting (common failures)

- 400/404 on validation: confirm `PUBLIC_URL` is correct, includes `https://`, and Graph can reach it. Use ngrok's web UI to inspect the request.
- 401 when calling Graph: ensure the token was obtained and has the correct scopes. For device flow you must have delegated `ChannelMessage.Read.All` consented.
- clientState mismatch: ensure `CLIENT_STATE` in `.env` matches the value used during subscription creation.
- Subscription expires quickly: Graph subscriptions for messages have short maximum TTLs. Implement a renewal mechanism in production.

Optional: .env.example (create locally)

Create a `.env.example` (do NOT commit secrets) containing the same keys as `.env` but with placeholders. Example:

```
TENANT_ID=your-tenant-id
CLIENT_ID=your-client-id
CLIENT_SECRET=
TEAM_ID=your-team-id
CHANNEL_ID=your-channel-id
PUBLIC_URL=https://abcd-1234.ngrok.io
CLIENT_STATE=superSecretClientState123
```

Security and production notes

- Never store secrets in plaintext in source control. Use a secret manager.
- For production you should:
  - Use a durable store for subscriptions and implement renewal.
  - Consider app-only subscriptions (requires certs/secrets and different permission model).
  - Verify and validate requests (clientState, signature, encryption when resource data included).

If you want, I can also:

- Add a `.env.example` file to the repo.
- Add a small renewal script that refreshes subscriptions before expiration.
- Add a small example showing how to call `get_message()` in `app.py` to fetch message details.

License

MIT-style for PoC use. Adjust as needed.
