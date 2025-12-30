# Dealership API Documentation

## Table of Contents
- [Overview](#overview)
- [API Endpoints](#api-endpoints)
  - [Dealerships](#dealerships)
    - [List Dealerships](#list-dealerships)
    - [Get Dealership Details](#get-dealership-details)
    - [Register Dealership](#register-dealership)
    - [Update Dealership](#update-dealership)
    - [My Dealership](#my-dealership)
    - [Upload Document](#upload-document)
  - [Withdrawals](#withdrawals)
    - [List Withdrawals](#list-withdrawals)
    - [Get Withdrawal Details](#get-withdrawal-details)
    - [Create Withdrawal Request](#create-withdrawal-request)
    - [Verify Withdrawal](#verify-withdrawal)
    - [Complete Withdrawal](#complete-withdrawal)
    - [Submit Feedback](#submit-feedback)
  - [Documents](#documents)
    - [List Documents](#list-documents)
    - [Get Document Details](#get-document-details)
    - [Delete Document](#delete-document)
  - [Admin Endpoints](#admin-endpoints)
    - [Admin Dealership Management](#admin-dealership-management)
    - [Change Dealership Status](#change-dealership-status)
    - [Update Transaction Limits](#update-transaction-limits)
    - [Verify Document](#verify-document)
    - [Pending Applications](#pending-applications)
    - [Search Dealerships](#search-dealerships)
- [Data Models](#data-models)
  - [Dealership](#dealership)
  - [DealershipWithdrawal](#dealershipwithdrawal)
  - [DealershipDocument](#dealershipdocument)
  - [DealershipVerificationLog](#dealershipverificationlog)
- [Withdrawal Process Flow](#withdrawal-process-flow)
  - [User Perspective](#user-perspective)
  - [Dealership Perspective](#dealership-perspective)
  - [Security Measures](#security-measures)
- [Integration with Wallet System](#integration-with-wallet-system)
- [Admin Dashboard Integration](#admin-dashboard-integration)
- [Frontend Implementation Notes](#frontend-implementation-notes)
  - [Dealership Registration](#dealership-registration)
  - [Withdrawal Request UI](#withdrawal-request-ui)
  - [Verification Process](#verification-process)
- [Security Considerations](#security-considerations)
  - [Fraud Prevention](#fraud-prevention)
  - [Transaction Verification](#transaction-verification)
  - [Audit Logging](#audit-logging)

## Overview

The Dealership system provides a secure infrastructure for users to withdraw cash from their Tiqani wallet through authorized exchange offices (dealerships). The system includes comprehensive registration, verification, and transaction tracking mechanisms to ensure secure and accountable cash withdrawals.

### Key Features

- **Secure Withdrawal Process**: QR code-based verification for secure cash withdrawals
- **Dealership Management**: Registration and verification of exchange offices as dealerships
- **Document Verification**: Upload and verification of business documents
- **Transaction Tracking**: Complete logs of all withdrawal activities
- **Multi-step Verification**: Customizable verification processes for different transaction amounts
- **Geographic Coverage**: Support for dealerships across different governorates
- **Admin Dashboard Integration**: Real-time statistics and metrics for administrators

## API Endpoints

### Dealerships

#### List Dealerships
- **URL**: `/api/dealership/dealerships/`
- **Method**: `GET`
- **Description**: List all approved and active dealerships
- **Authentication**: Not required
- **Query Parameters**:
  - `governorate` (optional): Filter dealerships by governorate
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "office_name": "string",
    "governorate": "string",
    "address": "string",
    "phone_number": "string",
    "opening_time": "time",
    "closing_time": "time",
    "weekend_days": "string",
    "profile_image": "url|null",
    "office_image": "url|null",
    "rating": "decimal",
    "total_transactions": "integer",
    "successful_transactions": "integer",
    "success_rate": "float",
    "is_active": "boolean",
    "maximum_transaction": "decimal"
  }
]
```
- **Frontend Notes**:
  - Display dealerships on a map or in a list
  - Use governorate filter for location-based search
  - Show operating hours and weekend days
  - Display success rate and transaction counts for trust indicators
  - Show maximum transaction amount

#### Get Dealership Details
- **URL**: `/api/dealership/dealerships/{id}/`
- **Method**: `GET`
- **Description**: Get detailed information about a specific dealership
- **Authentication**: Required for full details
- **Response**:
  - Success (200):
```json
{
  "id": "uuid",
  "user": {
    "id": "integer",
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string"
  },
  "office_name": "string",
  "registration_number": "string",
  "tax_id": "string",
  "governorate": "string",
  "address": "string",
  "phone_number": "string",
  "secondary_phone": "string|null",
  "owner_name": "string",
  "owner_id_number": "string",
  "opening_time": "time",
  "closing_time": "time",
  "weekend_days": "string",
  "bank_name": "string|null",
  "bank_account_number": "string|null",
  "bank_branch": "string|null",
  "documents": "url|null",
  "profile_image": "url|null",
  "office_image": "url|null",
  "status": "string",
  "daily_withdrawal_limit": "decimal",
  "maximum_transaction": "decimal",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_active": "boolean",
  "requires_enhanced_verification": "boolean",
  "security_deposit_amount": "decimal",
  "security_deposit_paid": "boolean",
  "aml_compliance_agreed": "boolean",
  "background_check_consent": "boolean",
  "total_transactions": "integer",
  "successful_transactions": "integer",
  "rating": "decimal",
  "individual_documents": [
    {
      "id": "uuid",
      "document_type": "string",
      "file": "url",
      "upload_date": "datetime",
      "description": "string",
      "is_verified": "boolean"
    }
  ],
  "success_rate": "float",
  "is_available": "boolean"
}
```
- **Frontend Notes**:
  - Create detailed dealership profile view
  - Include operating hours, contact information
  - Display images for the office and profile
  - Show transaction statistics prominently
  - Display document verification status

#### Register Dealership
- **URL**: `/api/dealership/dealerships/`
- **Method**: `POST`
- **Description**: Register a new dealership
- **Authentication**: Not required
- **Request Body**:
```json
{
  "username": "string",
  "email": "string",
  "password": "string",
  "confirm_password": "string",
  "office_name": "string",
  "registration_number": "string",
  "tax_id": "string",
  "governorate": "string",
  "address": "string",
  "phone_number": "string",
  "secondary_phone": "string",
  "owner_name": "string",
  "owner_id_number": "string",
  "opening_time": "time",
  "closing_time": "time",
  "weekend_days": "string",
  "bank_name": "string",
  "bank_account_number": "string",
  "bank_branch": "string",
  "documents": "file",
  "profile_image": "file",
  "office_image": "file",
  "aml_compliance_agreed": "boolean",
  "background_check_consent": "boolean"
}
```
- **Response**:
  - Success (201): Full dealership object
- **Frontend Notes**:
  - Create multi-step registration form
  - Include document upload functionality
  - Implement validation for all fields
  - Explain verification process to users

#### Update Dealership
- **URL**: `/api/dealership/dealerships/{id}/`
- **Method**: `PUT`/`PATCH`
- **Description**: Update dealership information
- **Authentication**: Required (owner only)
- **Request Body**: Same as registration but without authentication fields
- **Response**:
  - Success (200): Updated dealership object
- **Frontend Notes**:
  - Allow owners to update basic information
  - Indicate which fields cannot be changed after registration
  - Show current status and verification notes

#### My Dealership
- **URL**: `/api/dealership/dealerships/my_dealership/`
- **Method**: `GET`
- **Description**: Get the current user's dealership
- **Authentication**: Required
- **Response**:
  - Success (200): Full dealership object
  - Error (404): User has no dealership
- **Frontend Notes**:
  - Use for dealership dashboard
  - Show verification status prominently
  - Display administrative notes and requirements

#### Upload Document
- **URL**: `/api/dealership/dealerships/{id}/upload_document/`
- **Method**: `POST`
- **Description**: Upload an individual document for a dealership
- **Authentication**: Required (owner only)
- **Request Body**:
```json
{
  "document_type": "business_license|tax_certificate|owner_id|lease_agreement|bank_statement|other",
  "file": "file",
  "description": "string"
}
```
- **Response**:
  - Success (201): Document object
- **Frontend Notes**:
  - Create document upload interface
  - Show document verification status
  - Allow description input for each document

### Withdrawals

#### List Withdrawals
- **URL**: `/api/dealership/withdrawals/`
- **Method**: `GET`
- **Description**: List withdrawals (filtered by user role)
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "withdrawal_code": "string",
    "dealership": {
      "id": "uuid",
      "office_name": "string",
      "governorate": "string",
      "address": "string",
      "phone_number": "string",
      "opening_time": "time",
      "closing_time": "time",
      "weekend_days": "string",
      "profile_image": "url|null",
      "office_image": "url|null",
      "rating": "decimal",
      "total_transactions": "integer",
      "successful_transactions": "integer",
      "success_rate": "float",
      "is_active": "boolean",
      "maximum_transaction": "decimal"
    },
    "amount": "decimal",
    "status": "pending|approved|processing|completed|cancelled|disputed",
    "created_at": "datetime",
    "processed_at": "datetime|null",
    "completed_at": "datetime|null",
    "verification_type": "standard|enhanced|video",
    "qr_code_data": "string",
    "user_signature": "url|null",
    "dealership_notes": "string",
    "location_latitude": "decimal|null",
    "location_longitude": "decimal|null",
    "user_satisfied": "boolean|null",
    "user_feedback": "string"
  }
]
```
- **Frontend Notes**:
  - Display different views for users and dealerships
  - Use status indicators with clear colors
  - Show withdrawal code prominently
  - Include timestamps for tracking

#### Get Withdrawal Details
- **URL**: `/api/dealership/withdrawals/{id}/`
- **Method**: `GET`
- **Description**: Get detailed information about a specific withdrawal
- **Authentication**: Required
- **Response**:
  - Success (200): Withdrawal object
- **Frontend Notes**:
  - Display QR code for verification
  - Show all transaction details
  - Include dealership contact information
  - Use status indicators with timestamps

#### Create Withdrawal Request
- **URL**: `/api/dealership/withdrawals/`
- **Method**: `POST`
- **Description**: Create a new withdrawal request
- **Authentication**: Required
- **Request Body**:
```json
{
  "dealership_id": "uuid",
  "amount": "decimal",
  "verification_type": "standard|enhanced|video"
}
```
- **Response**:
  - Success (201): Withdrawal object
- **Frontend Notes**:
  - Validate amount against user's wallet balance
  - Check against maximum transaction limit
  - Generate QR code from returned data
  - Show clear instructions for next steps

#### Verify Withdrawal
- **URL**: `/api/dealership/withdrawals/{id}/verify/`
- **Method**: `POST`
- **Description**: Verify a withdrawal by dealership
- **Authentication**: Required (dealership owner only)
- **Request Body**: None
- **Response**:
  - Success (200): Updated withdrawal object
- **Frontend Notes**:
  - Implement QR code scanner
  - Confirm verification with dealership
  - Update status visually in real-time
  - Show clear next steps

#### Complete Withdrawal
- **URL**: `/api/dealership/withdrawals/{id}/complete/`
- **Method**: `POST`
- **Description**: Complete a withdrawal by dealership
- **Authentication**: Required (dealership owner only)
- **Request Body**:
```json
{
  "dealership_notes": "string"
}
```
- **Response**:
  - Success (200): Updated withdrawal object
- **Frontend Notes**:
  - Confirm cash handover
  - Collect digital signature if needed
  - Prompt for satisfaction rating
  - Show transaction summary

#### Submit Feedback
- **URL**: `/api/dealership/withdrawals/{id}/feedback/`
- **Method**: `POST`
- **Description**: Submit feedback for a completed withdrawal
- **Authentication**: Required (withdrawal requester only)
- **Request Body**:
```json
{
  "user_satisfied": "boolean",
  "user_feedback": "string"
}
```
- **Response**:
  - Success (200): Updated withdrawal object
- **Frontend Notes**:
  - Only available after withdrawal completion
  - Include satisfaction rating and optional text feedback
  - Show feedback confirmation
  - Update withdrawal record with feedback

### Documents

#### List Documents
- **URL**: `/api/dealership/documents/`
- **Method**: `GET`
- **Description**: List documents for a dealership
- **Authentication**: Required (dealership owner or admin)
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "document_type": "string",
    "file": "url",
    "upload_date": "datetime",
    "description": "string",
    "is_verified": "boolean"
  }
]
```
- **Frontend Notes**:
  - Group documents by type
  - Show verification status
  - Allow document management
  - Display upload date

#### Get Document Details
- **URL**: `/api/dealership/documents/{id}/`
- **Method**: `GET`
- **Description**: Get document details
- **Authentication**: Required (dealership owner or admin)
- **Response**:
  - Success (200): Document object
- **Frontend Notes**:
  - Show document preview if possible
  - Display all metadata
  - Include verification status

#### Delete Document
- **URL**: `/api/dealership/documents/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a document
- **Authentication**: Required (dealership owner only)
- **Response**:
  - Success (204): No content
- **Frontend Notes**:
  - Confirm deletion
  - Update document list after deletion
  - Warn about verification impact

### Admin Endpoints

#### Admin Dealership Management
- **URL**: `/api/dealership/admin/`
- **Method**: `GET`, `PUT`, `PATCH`, `DELETE`
- **Description**: Admin interface for managing dealerships
- **Authentication**: Required (admin only)
- **Response**:
  - Success (200): List of all dealerships with complete details
- **Frontend Notes**:
  - Create admin dashboard for dealership management
  - Include filtration and search
  - Show verification status and documents

#### Change Dealership Status
- **URL**: `/api/dealership/admin/{id}/change_status/`
- **Method**: `POST`
- **Description**: Change the status of a dealership
- **Authentication**: Required (admin only)
- **Request Body**:
```json
{
  "status": "pending|approved|rejected|suspended",
  "verification_notes": "string"
}
```
- **Response**:
  - Success (200): Updated dealership object
- **Frontend Notes**:
  - Include reason for status change
  - Log administrative actions
  - Send notification to dealership
  - Update `is_active` flag automatically based on status

#### Update Transaction Limits
- **URL**: `/api/dealership/admin/{id}/update_limits/`
- **Method**: `POST`
- **Description**: Update transaction limits for a dealership
- **Authentication**: Required (admin only)
- **Request Body**:
```json
{
  "daily_withdrawal_limit": "decimal",
  "maximum_transaction": "decimal"
}
```
- **Response**:
  - Success (200): Updated dealership object
- **Frontend Notes**:
  - Allow adjustment of financial limits
  - Show current and new limits for comparison
  - Log limit changes for audit purposes
  - Validate limits are reasonable

#### Verify Document
- **URL**: `/api/dealership/admin/{id}/verify_document/`
- **Method**: `POST`
- **Description**: Verify a specific document for a dealership
- **Authentication**: Required (admin only)
- **Request Body**:
```json
{
  "document_id": "uuid",
  "admin_notes": "string"
}
```
- **Response**:
  - Success (200): Updated document object
- **Frontend Notes**:
  - Show document preview
  - Include verification checklist
  - Allow admin notes
  - Update verification status visually

#### Pending Applications
- **URL**: `/api/dealership/admin/pending/`
- **Method**: `GET`
- **Description**: Get all pending dealership applications
- **Authentication**: Required (admin only)
- **Response**:
  - Success (200): List of pending dealerships
- **Frontend Notes**:
  - Sort by application date
  - Show document completion status
  - Include quick actions
  - Highlight urgent applications

#### Search Dealerships
- **URL**: `/api/dealership/admin/search/`
- **Method**: `GET`
- **Description**: Search dealerships by name, registration number, owner, or phone number
- **Authentication**: Required (admin only)
- **Query Parameters**:
  - `q`: Search query
- **Response**:
  - Success (200): List of matching dealerships
- **Frontend Notes**:
  - Implement dynamic search
  - Include auto-suggestions
  - Show search results with key data
  - Search across multiple fields (name, registration, owner, phone)

## Data Models

### Dealership

The main model representing exchange offices that facilitate withdrawals.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user | ForeignKey | Reference to User |
| office_name | String | Name of the exchange office |
| registration_number | String | Business registration/license number |
| tax_id | String | Tax identification number |
| governorate | String | Iraqi governorate location |
| address | String | Detailed street address |
| phone_number | String | Primary contact number (format: 07X-XXXXXXXX) |
| secondary_phone | String | Secondary contact number (optional) |
| owner_name | String | Full name of the business owner |
| owner_id_number | String | National ID number of the owner |
| opening_time | Time | Daily opening time |
| closing_time | Time | Daily closing time |
| weekend_days | String | Days closed (comma separated) |
| bank_name | String | Bank name (optional) |
| bank_account_number | String | Bank account number (optional) |
| bank_branch | String | Bank branch name (optional) |
| documents | File | ZIP file containing all required documents |
| profile_image | Image | Profile image of the dealership |
| office_image | Image | Image of the office/storefront |
| status | String | Status (pending, approved, rejected, suspended) |
| verification_notes | Text | Admin notes during verification process |
| daily_withdrawal_limit | Decimal | Maximum daily withdrawal amount |
| maximum_transaction | Decimal | Maximum single transaction amount |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |
| is_active | Boolean | Whether dealership is active in the system |
| requires_enhanced_verification | Boolean | Flag for additional verification |
| security_deposit_amount | Decimal | Required security deposit |
| security_deposit_paid | Boolean | Whether security deposit has been paid |
| aml_compliance_agreed | Boolean | Anti-Money Laundering compliance agreement |
| background_check_consent | Boolean | Background check consent |
| total_transactions | Integer | Count of total transactions |
| successful_transactions | Integer | Count of successful transactions |
| rating | Decimal | Average rating |

### DealershipWithdrawal

Model for tracking withdrawal transactions processed by dealerships.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| withdrawal_code | String | Unique code for the withdrawal |
| dealership | ForeignKey | Reference to Dealership |
| user | ForeignKey | Reference to User requesting withdrawal |
| amount | Decimal | Amount to withdraw |
| status | String | Status (pending, approved, processing, completed, cancelled, disputed) |
| created_at | DateTime | Creation timestamp |
| processed_at | DateTime | When processing began (optional) |
| completed_at | DateTime | When completed (optional) |
| verification_type | String | Verification type (standard, enhanced, video) |
| qr_code_data | Text | Data encoded in QR code for verification |
| user_signature | Image | User signature (optional) |
| dealership_notes | Text | Notes from dealership (optional) |
| admin_notes | Text | Admin notes (optional) |
| location_latitude | Decimal | Latitude where transaction occurred (optional) |
| location_longitude | Decimal | Longitude where transaction occurred (optional) |
| user_satisfied | Boolean | Whether user was satisfied (optional) |
| user_feedback | Text | User feedback (optional) |

### DealershipDocument

Model for individual documents uploaded by dealerships.

| Field | Type | Description |
|-------|------|-------------|
| dealership | ForeignKey | Reference to Dealership |
| document_type | String | Type of document |
| file | File | The document file |
| upload_date | DateTime | When document was uploaded |
| description | String | Description of document (optional) |
| is_verified | Boolean | Whether document has been verified |
| admin_notes | Text | Admin notes (optional) |

### DealershipVerificationLog

Model for logging verification events and access to dealership functions.

| Field | Type | Description |
|-------|------|-------------|
| dealership | ForeignKey | Reference to Dealership |
| withdrawal | ForeignKey | Reference to Withdrawal (optional) |
| timestamp | DateTime | When the event occurred |
| action | String | Action description |
| ip_address | IP | IP address of the user |
| user_agent | String | User agent string |
| success | Boolean | Whether action was successful |
| details | Text | Additional details (optional) |

## Withdrawal Process Flow

### User Perspective

1. **Request Withdrawal**:
   - User selects a dealership from available options
   - User specifies amount to withdraw
   - System validates against wallet balance and transaction limits
   - System generates QR code for verification

2. **Visit Dealership**:
   - User visits selected dealership during operating hours
   - User presents QR code to dealership staff
   - Dealership scans QR code to verify withdrawal request

3. **Receive Cash**:
   - Dealership verifies user identity (if required)
   - Dealership processes withdrawal and provides cash
   - User confirms receipt and provides feedback (optional)

### Dealership Perspective

1. **Verification Process**:
   - Dealership logs into system and scans user's QR code
   - System verifies the withdrawal request details
   - Verification type determines additional requirements

2. **Transaction Processing**:
   - Dealership confirms verification and begins processing
   - Dealership provides cash to user
   - Dealership marks transaction as completed

3. **Transaction Records**:
   - System logs all verification steps with timestamps
   - Dealership can view all transaction history
   - Performance metrics are updated based on transactions

### Security Measures

1. **QR Code Security**:
   - QR codes contain encrypted transaction details
   - Codes are single-use and time-limited
   - Contains verification hash for validation

2. **Verification Levels**:
   - Standard verification for regular amounts
   - Enhanced verification for larger transactions
   - Video verification for very large amounts or high-risk situations

3. **Fraud Prevention**:
   - IP address and device logging
   - Location tracking (optional)
   - Digital signatures for completed transactions

## Integration with Wallet System

The Dealership system integrates with the Tiqani Wallet system to handle cash withdrawals:

1. **Balance Verification**:
   - System checks user's wallet balance before allowing withdrawal
   - Wallet balance is reduced when withdrawal is initiated

2. **Transaction Status Updates**:
   - Wallet transactions are updated based on withdrawal status
   - Completed withdrawals trigger wallet balance updates
   - Cancelled withdrawals result in funds being returned to wallet

3. **Financial Reporting**:
   - Withdrawals are included in wallet transaction history
   - Financial reports include dealership withdrawal data
   - Reconciliation processes ensure balance accuracy

## Admin Dashboard Integration

The Dealership system is integrated into the main admin dashboard, providing key metrics and statistics:

### Dashboard Metrics

- **Total Dealerships**: Count of all registered dealerships
- **Active Dealerships**: Count of approved and active dealerships
- **Pending Applications**: Count of dealerships awaiting approval
- **Suspended Dealerships**: Count of suspended dealerships
- **Withdrawal Statistics**: Total withdrawals processed, amounts, success rates
- **Performance Metrics**: Average processing times, user satisfaction rates

### Integration Points

1. **Main Dashboard**: `/api/dashboard/admin/dashboard/`
   - Includes dealership counts and key metrics
   - Shows recent withdrawal activity
   - Displays pending applications requiring attention

2. **Dealership Management**: Direct links to dealership admin endpoints
   - Quick access to pending applications
   - Performance monitoring tools
   - Document verification workflows

3. **Financial Integration**: 
   - Withdrawal amounts tracked in transaction management
   - Integration with platform wallet system
   - Revenue impact analysis

## Frontend Implementation Notes

### Dealership Registration

1. **Multi-step Form**:
   - Business information collection
   - Owner information collection
   - Document upload interface
   - Terms and compliance agreements

2. **Document Requirements**:
   - Business license/registration
   - Tax registration certificate
   - Owner identification
   - Lease agreement
   - Bank statements
   - Other supporting documents

3. **Status Tracking**:
   - Clear indication of application status
   - Display of verification notes from admin
   - Document verification status tracking

### Withdrawal Request UI

1. **Dealership Selection**:
   - Map-based selection interface
   - Filtering by location and rating
   - Display of key dealership information

2. **Amount Specification**:
   - Balance check and display
   - Transaction limit indicator
   - Fee calculation (if applicable)

3. **QR Code Generation**:
   - Clear, high-contrast QR code
   - Withdrawal details summary
   - Expiration timer for security

### Verification Process

1. **Dealership Interface**:
   - QR code scanner integration
   - Verification checklist
   - Transaction processing confirmation

2. **User Confirmation**:
   - Digital signature capture
   - Receipt generation
   - Satisfaction feedback collection

3. **Status Updates**:
   - Real-time status changes
   - Push notifications for status updates
   - Transaction history display

## Security Considerations

### Fraud Prevention

1. **Identity Verification**:
   - QR code verification
   - Photo ID checks for larger transactions
   - Transaction limits based on user history

2. **Dealership Verification**:
   - Comprehensive background checks
   - Security deposit requirements
   - Regular compliance reviews

3. **Anomaly Detection**:
   - Monitoring for unusual transaction patterns
   - Location-based verification
   - Time-based transaction restrictions

### Transaction Verification

1. **Multi-factor Authentication**:
   - QR code as primary factor
   - PIN or OTP as secondary factor for larger transactions
   - Biometric verification for enhanced security

2. **Transaction Validation**:
   - Dealership validation of withdrawal details
   - System validation of transaction limits
   - Temporal validation of request timeliness

3. **Completion Confirmation**:
   - User confirmation of receipt
   - Digital signature capture
   - Transaction receipt generation

### Audit Logging

1. **Comprehensive Logging**:
   - All actions logged with timestamps
   - IP address and device information captured
   - User agent and system details recorded

2. **Immutable Records**:
   - Logs cannot be modified or deleted
   - Complete audit trail for all transactions
   - Regular backup of log data

3. **Reporting**:
   - Transaction reports by dealership
   - Anomaly detection reporting
   - Compliance and audit reporting 