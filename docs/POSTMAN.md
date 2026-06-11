# Postman Collections — tiqani_v3

## Available Collections

| Collection | File | Phase |
|---|---|---|
| Admin Dashboard | `postman/Tiqani_v3_Phase_7_Admin_Dashboard.postman_collection.json` | Phase 7 |
| Security Hardening | `postman/Tiqani_v3_Phase_8_Security_Hardening.postman_collection.json` | Phase 8 |

## How to Import

1. Open Postman
2. Click **Import** → **Upload Files**
3. Select one or all `.json` files from the `postman/` directory
4. Click **Import**

Or drag the files directly into the Postman window.

## Required Variables

Each collection uses variables. Set them in Postman:

| Variable | Description |
|---|---|
| `base_url` | API base URL (e.g., `http://127.0.0.1:8000`) |
| `admin_token` | JWT token for system_admin user |
| `finance_token` | JWT token for finance_admin user |
| `moderator_token` | JWT token for content_moderator user |
| `account_manager_token` | JWT token for account_manager user |
| `client_token` | JWT token for client user |
| `technician_token` | JWT token for technician user |
| `normal_token` | JWT token for normal (non-admin) user |
| `user_id` | UUID of a user |
| `technician_id` | UUID of a technician profile |
| `contract_id` | UUID of a contract |
| `review_id` | UUID of a review |
| `withdrawal_id` | UUID of a withdrawal request |
| `payment_intent_id` | UUID of a payment intent |

### Setting Variables in Postman

1. Select the collection
2. Go to **Variables** tab
3. Enter values in the **Current Value** column
4. Save

Collections that reference variables without values will return 401/403 errors, which is expected for security smoke tests.

## Authentication

Most endpoints require a JWT token. To get a token:

1. `POST {{base_url}}/api/auth/login/` with valid credentials
2. Copy the `access` token from the response
3. Set it as the value for the appropriate token variable
