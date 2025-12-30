# Payment API Documentation

## Table of Contents
- [Overview](#overview)
- [Stripe Integration](#stripe-integration)
  - [Create Payment Intent](#create-payment-intent)
  - [Stripe Webhook](#stripe-webhook)
- [Wallet System](#wallet-system)
  - [Wallet Detail](#wallet-detail)
  - [Wallet Transfer](#wallet-transfer)
  - [Accessing Wallet Information](#accessing-wallet-information)
- [Enhanced Wallet APIs](#enhanced-wallet-apis)
  - [Transaction History](#transaction-history)
  - [Transfer Validation](#transfer-validation)
  - [Withdrawal System](#withdrawal-system)
- [Fee Tracking System](#fee-tracking-system)
  - [Automatic Fee Collection](#automatic-fee-collection)
  - [Fee Analytics API](#fee-analytics-api)
  - [Revenue Reporting](#revenue-reporting)
- [Exchange Rate Integration](#exchange-rate-integration)
- [Frontend Implementation Guide](#frontend-implementation-guide)
  - [Prerequisites](#prerequisites)
  - [Complete Payment Implementation](#complete-payment-implementation)
  - [Integration Checklist](#integration-checklist)
  - [Testing Guidelines](#testing-guidelines)
  - [Common Issues & Solutions](#common-issues--solutions)
- [Data Models](#data-models)
- [Features](#features)
- [Contract Integration](#contract-integration)
- [Implementation Notes](#implementation-notes)

## Overview
The payment system provides secure payment processing using Stripe integration and includes a wallet system for managing user balances and transfers. The system supports deposits via Stripe, wallet-to-wallet transfers, and contract-based escrow payments.

### Fee Structure
1. **Stripe Service Fee**: 
   - Configurable fee percentage (default 5%) deducted from all wallet recharges through Stripe
   - Fee percentage is managed through the Dashboard System Configuration
   - This fee is automatically calculated and deducted before adding funds to the wallet
   - For example, if a user adds $100 USD (converted to IQD at the current exchange rate), they will receive 95% of the IQD amount in their wallet
   
2. **Platform Contract Fee**:
   - Configurable fee percentage (default 10%) deducted from all payments released to technicians for completed contract stages
   - Fee percentage is managed through the Dashboard System Configuration
   - The fee is automatically calculated and deducted when stage payments are released

## Exchange Rate Integration

The payment system integrates with the Dashboard Exchange Rate Management system for currency conversion:

### How Exchange Rates Work
- **Source**: Exchange rates are managed through the Dashboard API (`/api/dashboard/exchange-rate/`)
- **Automatic Retrieval**: Payment processing automatically fetches the current USD to IQD exchange rate
- **Fallback**: If no exchange rate is configured, the system defaults to 1300.00 IQD per USD
- **Real-time Conversion**: All USD payments are converted to IQD using the most recent exchange rate

### Get Current Exchange Rate
- **URL**: `/api/dashboard/exchange-rate/`
- **Method**: `GET`
- **Description**: Get the current USD to IQD exchange rate
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
{
    "id": 1,
    "rate": 1200.00,
    "effective_date": "2023-09-15T14:30:00Z",
    "updated_by": "admin"
}
```
- **Frontend Notes**:
  - This endpoint can be called directly to get the current exchange rate
  - Use this for real-time rate display in payment forms
  - Cache the rate but refresh periodically for accuracy
  - Display the effective_date to users to show when the rate was last updated
  - No authentication required, making it suitable for public rate displays

### Exchange Rate Usage in Payments
```python
# Automatic exchange rate retrieval in payment processing
current_rate = ExchangeRate.get_current_rate()
if current_rate:
    exchange_rate = current_rate.rate
else:
    exchange_rate = Decimal('1300.00')  # Default fallback

# Convert USD to IQD
amount_iqd = amount_usd * exchange_rate

# Apply fees and update wallet
system_config = SystemConfig.get_settings()
fee_amount = amount_iqd * (system_config.STRIPE_FEE_PERCENTAGE / 100)
final_amount = amount_iqd - fee_amount
```

### Frontend Integration Notes
- **Display Current Rate**: Show the current exchange rate in payment forms
- **Rate Updates**: Exchange rates are updated by administrators through the dashboard
- **Calculation Preview**: Show users the expected IQD amount before payment confirmation
- **Transaction History**: Display both USD and IQD amounts with the exchange rate used
- **Real-time Updates**: Call `/api/dashboard/exchange-rate/` to get current rate before processing payments
- **Error Handling**: Implement fallback behavior if exchange rate API is unavailable

## Stripe Integration

### Create Payment Intent
- **URL**: `/api/payments/create-payment/`
- **Method**: `POST`
- **Description**: Create a Stripe payment intent for depositing funds
- **Authentication**: Required
- **Request Body**:
```json
{
    "amount": "decimal"  // Amount in USD
}
```
- **Response**:
  - Success (200):
```json
{
    "client_secret": "string",
    "id": "string",
    "publishable_key": "string",
    "exchange_rate": "decimal",
    "estimated_iqd_amount": "decimal",
    "fee_percentage": "decimal",
    "estimated_final_amount": "decimal"
}
```
  - Error (400):
```json
{
    "error": "Amount is required.|Invalid amount."
}
```
- **Frontend Notes**:
  - Use the Stripe Elements JS library for secure payment form
  - Store publishable_key in your frontend config
  - Display the estimated_iqd_amount and estimated_final_amount to users before payment
  - Show the current exchange_rate and fee_percentage for transparency
  - Use client_secret to confirm payment with Stripe.js
  - Handle loading and error states during payment processing
  - Implement UI feedback for successful payments
  - Once payment is confirmed on the client side, the webhook will automatically update the wallet balance

### Confirm Payment (Manual)
- **URL**: `/api/payments/confirm-payment/`
- **Method**: `POST`
- **Description**: Manually confirm a payment and update wallet balance (for testing/development)
- **Authentication**: Required
- **Request Body**:
```json
{
    "payment_intent_id": "string"  // Stripe payment intent ID
}
```
- **Response**:
  - Success (200):
```json
{
    "status": "success",
    "message": "Your wallet has been credited with X IQD ($Y USD)",
    "transaction_id": "integer",
    "new_balance": "decimal",
    "exchange_rate": "decimal",
    "fee_percentage": "decimal",
    "fee_amount": "decimal"
}
```
  - Error (400/403):
```json
{
    "error": "Payment intent ID is required.|Payment not successful.|This payment intent was not created by you.|This payment has already been processed."
}
```

### Stripe Webhook
- **URL**: `/api/payments/stripe-webhook/`
- **Method**: `POST`
- **Description**: Handles Stripe webhook events for payment processing
- **Headers**:
  - `Stripe-Signature`: Webhook signature from Stripe
- **Events Handled**:
  - `payment_intent.succeeded`: Updates user's wallet balance
- **Frontend Notes**:
  - No direct frontend interaction with this endpoint
  - Webhook receives payment confirmations from Stripe servers
  - After successful payment, poll user wallet to see updated balance

### Wallet Detail
- **URL**: `/api/payments/wallet-detail/`
- **Method**: `GET`
- **Description**: Get detailed wallet information including recent transactions and current exchange rate
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
    "wallet_id": "integer",
    "transaction_id": "string",
    "balance": "string",
    "username": "string",
    "user_id": "integer",
    "current_exchange_rate": {
        "rate": "decimal",
        "updated_at": "datetime"
    },
    "recent_transactions": [
        {
            "id": "integer",
            "type": "string",
            "amount": "string",
            "amount_usd": "string|null",
            "exchange_rate": "string|null",
            "description": "string",
            "created_at": "string"
        }
    ]
}
```

## Wallet System

### Wallet Transfer
- **URL**: `/api/payments/transfer/`
- **Method**: `POST`
- **Description**: Transfer funds between user wallets
- **Authentication**: Required
- **Request Body**:
```json
{
    "transaction_id": "string",  // Recipient's wallet transaction ID
    "amount": "decimal"  // Amount to transfer
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "Transfer successful."
}
```
  - Error (400/404):
```json
{
    "error": "Invalid transfer amount.|Insufficient funds.|Recipient not found.|You cannot transfer funds to yourself."
}
```
- **Frontend Notes**:
  - Implement recipient transaction ID input field (12-character ID)
  - Add amount input with validation for positive numbers
  - Display user's current balance to prevent insufficient funds errors
  - Show clear success/error messages after transfer attempts
  - Update wallet balance display after successful transfer

### Accessing Wallet Information
- **Note**: Wallet information is accessed through user profile endpoints
- **Client Profile**: `GET /api/accounts/client/me/` or `GET /api/accounts/client/<uuid:pk>/`
- **Technician Profile**: `GET /api/accounts/technician/<uuid:pk>/`
- **Authentication**: Required
- **Response Example** (wallet information included in profile response):
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
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    },
    // other profile fields...
}
```
- **Frontend Notes**:
  - Display wallet balance in user dashboard/profile area
  - Show transaction ID for sharing with others (needed for transfers)
  - Consider masking transaction ID partially for security
  - Cache wallet information but refresh regularly

## Enhanced Wallet APIs

This section covers the comprehensive wallet APIs designed for advanced wallet page functionality, including paginated transaction history, transfer validation, and withdrawal management.

### Transaction History
- **URL**: `/api/payments/transactions/`
- **Method**: `GET`
- **Description**: Get paginated transaction history with filtering options
- **Authentication**: Required
- **Query Parameters**:
  - `page`: Page number (default: 1)
  - `limit`: Items per page (default: 20, max: 100)
  - `type`: Filter by transaction type (optional)
    - Values: `deposit`, `transfer_in`, `transfer_out`, `escrow`, `release`, `refund`, `withdrawal`
  - `date_from`: Start date filter in YYYY-MM-DD format (optional)
  - `date_to`: End date filter in YYYY-MM-DD format (optional)
- **Response**:
  - Success (200):
```json
{
    "count": 150,
    "next": "http://api.example.com/api/payments/transactions/?page=2",
    "previous": null,
    "results": [
        {
            "id": 789,
            "type": "deposit",
            "amount": "153000.00",
            "amount_usd": "100.00",
            "exchange_rate": "1530.00",
            "description": "Wallet deposit via Stripe",
            "created_at": "2025-01-04T13:00:00Z",
            "contract": null
        },
        {
            "id": 788,
            "type": "transfer_out",
            "amount": "-50000.00",
            "amount_usd": "-32.68",
            "exchange_rate": "1530.00",
            "description": "Transfer to john_doe",
            "created_at": "2025-01-04T12:30:00Z",
            "contract": null
        }
    ]
}
```
- **Frontend Notes**:
  - Implement pagination controls (page numbers, next/previous buttons)
  - Add filter dropdowns for transaction types and date ranges
  - Display transactions in chronological order (newest first)
  - Show both IQD and USD amounts with exchange rates
  - Use different styling for positive/negative amounts
  - Include search functionality for transaction descriptions
  - Implement infinite scroll or load more functionality

### Transfer Validation
- **URL**: `/api/payments/validate-transfer/`
- **Method**: `POST`
- **Description**: Validate a transfer request before execution
- **Authentication**: Required
- **Request Body**:
```json
{
    "transaction_id": "ABC123XYZ789",
    "amount": 50000.00
}
```
- **Response**:
  - Success (200):
```json
{
    "valid": true,
    "transfer_details": {
        "sender": {
            "username": "current_user",
            "transaction_id": "DEF456GHI012",
            "current_balance": "200000.00",
            "balance_after_transfer": "150000.00"
        },
        "recipient": {
            "username": "john_doe",
            "transaction_id": "ABC123XYZ789"
        },
        "amount_iqd": "50000.00",
        "amount_usd": "32.68",
        "current_exchange_rate": "1530.00"
    }
}
```
  - Error (400/404):
```json
{
    "error": "Insufficient funds.",
    "details": {
        "available_balance": "25000.00",
        "requested_amount": "50000.00"
    }
}
```
- **Frontend Notes**:
  - Call this endpoint before showing transfer confirmation dialog
  - Display transfer preview with sender/recipient information
  - Show balance after transfer to help users understand impact
  - Use this for real-time validation as user types amount
  - Implement clear error messages for various validation failures
  - Cache recipient information for frequently used recipients

### Withdrawal System

#### Request Withdrawal
- **URL**: `/api/payments/withdraw/`
- **Method**: `POST`
- **Description**: Request withdrawal to dealership account
- **Authentication**: Required
- **Request Body**:
```json
{
    "dealership_id": "uuid",
    "amount": 100000.00,
    "withdrawal_method": "cash",
    "verification_type": "standard"
}
```
- **Response**:
  - Success (201):
```json
{
    "status": "success",
    "message": "Withdrawal request created successfully.",
    "withdrawal": {
        "id": "uuid",
        "withdrawal_code": "ABC123XYZ",
        "amount": "100000.00",
        "dealership": {
            "id": "uuid",
            "office_name": "Downtown Exchange",
            "address": "123 Main St, Baghdad",
            "phone_number": "07701234567"
        },
        "status": "pending",
        "qr_code_data": "TIQANI-WD:ABC123XYZ:user_id:dealership_id:100000.00",
        "created_at": "2025-01-04T15:30:00Z"
    },
    "wallet_balance": "450000.00"
}
```
  - Error (400/404):
```json
{
    "error": "Insufficient funds.",
    "details": {
        "available_balance": "50000.00",
        "requested_amount": "100000.00"
    }
}
```
- **Frontend Notes**:
  - Implement dealership selection with map integration
  - Show dealership information (location, hours, rating)
  - Display withdrawal limits and fees clearly
  - Generate QR code from qr_code_data for dealership verification
  - Show withdrawal code prominently for reference
  - Provide clear instructions for next steps
  - Update wallet balance immediately after successful request

#### Withdrawal History
- **URL**: `/api/payments/withdrawals/`
- **Method**: `GET`
- **Description**: Get user's withdrawal history with pagination
- **Authentication**: Required
- **Query Parameters**:
  - `page`: Page number (default: 1)
  - `limit`: Items per page (default: 20, max: 100)
  - `status`: Filter by withdrawal status (optional)
    - Values: `pending`, `approved`, `processing`, `completed`, `cancelled`, `disputed`
- **Response**:
  - Success (200):
```json
{
    "count": 25,
    "next": "http://api.example.com/api/payments/withdrawals/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "withdrawal_code": "ABC123XYZ",
            "dealership": {
                "id": "uuid",
                "office_name": "Downtown Exchange",
                "address": "123 Main St, Baghdad",
                "phone_number": "07701234567",
                "governorate": "Baghdad"
            },
            "amount": "100000.00",
            "status": "completed",
            "verification_type": "standard",
            "created_at": "2025-01-04T15:30:00Z",
            "processed_at": "2025-01-04T16:00:00Z",
            "completed_at": "2025-01-04T16:15:00Z",
            "qr_code_data": "TIQANI-WD:ABC123XYZ:user_id:dealership_id:100000.00",
            "dealership_notes": "Cash withdrawal completed successfully",
            "user_satisfied": true,
            "user_feedback": "Quick and professional service"
        }
    ]
}
```
- **Frontend Notes**:
  - Display withdrawal status with colored indicators
  - Show timeline of withdrawal progress (requested → processing → completed)
  - Include dealership contact information for user reference
  - Allow filtering by status and date range
  - Show QR code for pending withdrawals
  - Implement feedback collection for completed withdrawals
  - Display withdrawal codes prominently for easy reference

## Fee Tracking System

The platform automatically tracks and aggregates all fees collected from user transactions. This system provides comprehensive revenue analytics and reporting for administrators.

### Automatic Fee Collection

The system automatically collects and tracks fees from two main sources:

#### **1. Stripe Deposit Fees**
- **Source**: User wallet deposits via Stripe payments
- **Calculation**: Configurable percentage (default 5%) of deposit amount
- **Tracking**: Automatically recorded when payment is processed
- **Example**: User deposits $100 USD → System collects ~$5 USD fee → Remaining ~$95 USD converted to IQD and added to wallet

#### **2. Platform Contract Fees**
- **Source**: Contract stage payments released to technicians
- **Calculation**: Configurable percentage (default 10%) of stage payment
- **Tracking**: Automatically recorded when stage payment is released
- **Example**: Client pays 100,000 IQD for completed stage → System collects 10,000 IQD fee → Technician receives 90,000 IQD

### Fee Analytics API

#### Get Comprehensive Fee Analytics
- **URL**: `/api/dashboard/admin/fee-analytics/`
- **Method**: `GET`
- **Description**: Get detailed fee collection analytics and revenue data
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (200):
```json
{
    "summary": {
        "total_revenue_iqd": "2456789.50",
        "total_revenue_usd": "1821.45",
        "total_fee_transactions": 1247,
        "average_fee_per_transaction_iqd": "1970.12",
        "average_fee_per_transaction_usd": "1.46"
    },
    "breakdown_by_type": {
        "stripe_deposit": {
            "display_name": "Stripe Deposit Fees",
            "amount_iqd": "1234567.25",
            "amount_usd": "915.23",
            "transaction_count": 823,
            "current_fee_percentage": "5.00",
            "last_transaction": "2025-01-04T16:30:00Z",
            "average_per_transaction_iqd": "1500.08",
            "average_per_transaction_usd": "1.11"
        },
        "platform_contract": {
            "display_name": "Platform Contract Fees",
            "amount_iqd": "1222222.25",
            "amount_usd": "906.22",
            "transaction_count": 424,
            "current_fee_percentage": "10.00",
            "last_transaction": "2025-01-04T15:45:00Z",
            "average_per_transaction_iqd": "2882.60",
            "average_per_transaction_usd": "2.14"
        }
    },
    "fee_collections": [
        {
            "fee_type": "stripe_deposit",
            "display_name": "Stripe Deposit Fee",
            "amount_iqd": "1234567.25",
            "amount_usd": "915.23",
            "current_fee_percentage": "5.00",
            "transaction_count": 823,
            "last_transaction_date": "2025-01-04T16:30:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "last_updated": "2025-01-04T16:30:00Z"
        }
    ]
}
```

### Revenue Reporting

#### Dashboard Integration
Fee analytics are automatically included in the admin dashboard:

- **URL**: `/api/dashboard/admin/dashboard/`
- **Method**: `GET`
- **Description**: Admin dashboard includes revenue analytics summary
- **Revenue Analytics Section**:
```json
{
    "revenue_analytics": {
        "total_revenue_iqd": "2456789.50",
        "total_revenue_usd": "1821.45",
        "total_fee_transactions": 1247,
        "stripe_fees": {
            "amount_iqd": "1234567.25",
            "amount_usd": "915.23",
            "transaction_count": 823,
            "fee_percentage": "5.00"
        },
        "platform_fees": {
            "amount_iqd": "1222222.25",
            "amount_usd": "906.22",
            "transaction_count": 424,
            "fee_percentage": "10.00"
        }
    }
}
```

### Implementation Details

#### **Automatic Tracking**
- Fees are automatically tracked when transactions occur
- No manual intervention required
- Real-time updates to fee totals
- Thread-safe atomic operations

#### **Data Aggregation**
- Total amounts in both IQD and USD
- Transaction count tracking
- Current fee percentage recording
- Last transaction timestamp

#### **Analytics Features**
- Revenue breakdown by fee type
- Average fee per transaction calculations
- Historical transaction count
- Performance metrics for administrators

### Frontend Integration Notes

#### **Admin Dashboard**
- Display total revenue prominently in dashboard
- Show breakdown between Stripe and platform fees
- Include transaction count and averages
- Real-time updates when new fees are collected

#### **Fee Analytics Page**
- Create dedicated analytics page for detailed fee data
- Include charts and graphs for revenue trends
- Allow filtering by date range and fee type
- Export functionality for reporting

#### **Revenue Monitoring**
- Set up alerts for revenue milestones
- Track fee percentage effectiveness
- Monitor transaction volume trends
- Compare revenue across different time periods

## Data Models

### Wallet
```json
{
    "user": "integer",  // User ID
    "balance": "decimal",
    "transaction_id": "string"  // 12-character unique identifier
}
```

### Wallet Transaction
```json
{
    "wallet": "integer",  // Wallet ID
    "contract": "uuid|null",  // Optional contract reference
    "transaction_type": "deposit|transfer_in|transfer_out|escrow|release|refund|withdrawal",
    "amount": "decimal",
    "amount_usd": "decimal|null",  // USD amount for reference
    "exchange_rate": "decimal|null",  // Exchange rate at transaction time
    "description": "string",
    "created_at": "datetime"
}
```

## Features

1. **Stripe Integration**:
   - Secure payment processing
   - Webhook handling for payment events
   - Automatic wallet updates
   - 5% service fee deduction
   - **Frontend Notes**:
     - Implement Stripe Elements for secure credit card collection
     - Never store credit card details in your application
     - Handle payment confirmation and failure flows
     - Show loading indicators during payment processing
     - Clearly display information about the service fee before and after payment

2. **Wallet Management**:
   - Unique transaction IDs for each wallet
   - Balance tracking
   - Secure transfers between wallets
   - Paginated transaction history with filtering
   - Transfer validation and preview
   - Withdrawal requests to dealerships
   - **Frontend Notes**:
     - Display current balance prominently in user dashboard
     - Create intuitive transfer form with recipient ID validation
     - Show transaction history in tabular format with pagination
     - Implement comprehensive filters for transaction types and date ranges
     - Add transfer validation with preview before execution
     - Integrate dealership selection for withdrawal requests
     - Display withdrawal status and progress tracking

3. **Transaction Types**:
   - Deposits (via Stripe)
   - Wallet-to-wallet transfers
   - Escrow holdings for contracts
   - Payment releases
   - Refunds
   - Withdrawals (to dealerships)
   - **Frontend Notes**:
     - Use distinct visual indicators for different transaction types
     - Show positive/negative amounts with appropriate styling
     - Display transaction dates in user-friendly format
     - Include related contract information when available
     - Display exchange rates for USD/IQD transactions
     - Show withdrawal status and QR codes for pending withdrawals

4. **Security**:
   - Authentication required for all operations
   - Stripe signature verification
   - Atomic transactions for transfers
   - Balance validation
   - **Frontend Notes**:
     - Implement confirmation steps for transfers
     - Require authentication refresh for high-value transfers
     - Display security tips for safe wallet usage
     - Include fraud warning about sharing transaction IDs

## Contract Integration

The payment system integrates with the contract system for:
1. **Escrow Payments**:
   - Funds held in escrow during contract execution
   - Automatic release upon stage completion
   - **Frontend Notes**:
     - Show escrow amount in contract details view
     - Clearly distinguish between available balance and funds in escrow
     - Provide explanations of how escrow protects both parties

2. **Stage Payments**:
   - Automatic payment release to technician with 10% platform fee deduction
   - Transaction logging for each payment
   - Balance updates for both parties
   - **Frontend Notes**:
     - Display payment schedule in contract timeline
     - Show payment status for each stage (pending/released)
     - Provide payment history in contract details
     - Update wallet balance display after stage approvals
     - Clearly indicate platform fee in transaction details

## Frontend Implementation Guide

This section provides comprehensive instructions for implementing Stripe payments in your frontend application.

### Prerequisites

1. **Install Stripe.js**:
```html
<!-- Add to your HTML head -->
<script src="https://js.stripe.com/v3/"></script>
```

Or via npm:
```bash
npm install @stripe/stripe-js
```

2. **Authentication Setup**:
Ensure you have proper JWT token management for API calls.

### Complete Payment Implementation

#### 1. Payment Form Component

```javascript
// PaymentForm.jsx (React example)
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';

const PaymentForm = ({ amount, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [paymentData, setPaymentData] = useState(null);

  // Step 1: Get exchange rate and payment preview
  useEffect(() => {
    fetchPaymentPreview();
  }, [amount]);

  const fetchPaymentPreview = async () => {
    try {
      const response = await fetch('/api/dashboard/exchange-rate/', {
        method: 'GET'
      });
      const exchangeData = await response.json();
      
      const estimatedIQD = parseFloat(amount) * exchangeData.rate;
      const feeAmount = estimatedIQD * 0.05; // 5% fee
      const finalAmount = estimatedIQD - feeAmount;
      
      setPaymentData({
        exchangeRate: exchangeData.rate,
        estimatedIQD: estimatedIQD.toFixed(2),
        feeAmount: feeAmount.toFixed(2),
        finalAmount: finalAmount.toFixed(2)
      });
    } catch (error) {
      console.error('Failed to fetch exchange rate:', error);
    }
  };

  // Step 2: Create payment intent
  const createPaymentIntent = async () => {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch('/api/payments/create-payment/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        amount: amount.toString()
      })
    });

    if (response.status === 401) {
      // Token expired, refresh or redirect to login
      await refreshToken();
      return createPaymentIntent(); // Retry
    }

    if (!response.ok) {
      throw new Error('Failed to create payment intent');
    }

    return response.json();
  };

  // Step 3: Process payment
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    if (!stripe || !elements) {
      return;
    }

    try {
      // Create payment intent on backend
      const { client_secret, publishable_key } = await createPaymentIntent();
      
      // Initialize Stripe with the key from backend
      const stripeInstance = await loadStripe(publishable_key);
      
      // Confirm payment
      const { error, paymentIntent } = await stripeInstance.confirmCardPayment(
        client_secret,
        {
          payment_method: {
            card: elements.getElement(CardElement),
            billing_details: {
              name: 'Customer Name',
            },
          }
        }
      );

      if (error) {
        onError(error.message);
      } else if (paymentIntent.status === 'succeeded') {
        // Payment successful
        onSuccess({
          paymentIntentId: paymentIntent.id,
          amount: paymentIntent.amount / 100,
          currency: paymentIntent.currency
        });
        
        // Poll wallet balance to see updates
        pollWalletBalance();
      }
    } catch (error) {
      onError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // Step 4: Poll for balance update (since webhook updates asynchronously)
  const pollWalletBalance = async () => {
    let attempts = 0;
    const maxAttempts = 10;
    
    const checkBalance = async () => {
      if (attempts >= maxAttempts) return;
      
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/payments/wallet-detail/', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const walletData = await response.json();
          // Check if balance was updated
          // You might want to compare with previous balance
          console.log('Updated wallet balance:', walletData.balance);
        }
      } catch (error) {
        console.error('Failed to check wallet balance:', error);
      }
      
      attempts++;
      setTimeout(checkBalance, 2000); // Check every 2 seconds
    };
    
    checkBalance();
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="payment-preview">
        <h3>Payment Preview</h3>
        <p>Amount (USD): ${amount}</p>
        {paymentData && (
          <>
            <p>Exchange Rate: {paymentData.exchangeRate} IQD/USD</p>
            <p>Estimated IQD: {paymentData.estimatedIQD} IQD</p>
            <p>Service Fee (5%): -{paymentData.feeAmount} IQD</p>
            <p><strong>Final Amount: {paymentData.finalAmount} IQD</strong></p>
          </>
        )}
      </div>
      
      <div className="card-element">
        <CardElement
          options={{
            style: {
              base: {
                fontSize: '16px',
                color: '#424770',
                '::placeholder': {
                  color: '#aab7c4',
                },
              },
            },
          }}
        />
      </div>
      
      <button type="submit" disabled={!stripe || loading}>
        {loading ? 'Processing...' : `Pay $${amount} USD`}
      </button>
    </form>
  );
};
```

#### 2. Token Management

```javascript
// auth.js - Token management utilities
export const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  
  try {
    const response = await fetch('/api/accounts/token/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh: refreshToken
      })
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      return data.access;
    } else {
      // Refresh failed, redirect to login
      window.location.href = '/login';
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    window.location.href = '/login';
  }
};

export const apiCall = async (url, options = {}) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers
    }
  });
  
  if (response.status === 401) {
    // Token expired, try to refresh
    const newToken = await refreshToken();
    if (newToken) {
      // Retry with new token
      return fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${newToken}`,
          ...options.headers
        }
      });
    }
  }
  
  return response;
};
```

#### 3. Error Handling

```javascript
// ErrorHandler.jsx
const PaymentErrorHandler = ({ error, onRetry, onCancel }) => {
  const getErrorMessage = (error) => {
    switch (error.code) {
      case 'card_declined':
        return 'Your card was declined. Please try a different payment method.';
      case 'insufficient_funds':
        return 'Insufficient funds. Please check your account balance.';
      case 'token_not_valid':
        return 'Your session has expired. Please log in again.';
      case 'authentication_required':
        return 'Authentication required. Please verify your identity.';
      default:
        return error.message || 'An unexpected error occurred. Please try again.';
    }
  };

  return (
    <div className="error-container">
      <div className="error-icon">⚠️</div>
      <h3>Payment Error</h3>
      <p>{getErrorMessage(error)}</p>
      <div className="error-actions">
        <button onClick={onRetry}>Try Again</button>
        <button onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
};
```

#### 4. Complete Integration Example

```javascript
// WalletTopUp.jsx - Complete component
import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import PaymentForm from './PaymentForm';
import PaymentErrorHandler from './PaymentErrorHandler';

const WalletTopUp = () => {
  const [amount, setAmount] = useState('');
  const [stripe, setStripe] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [walletBalance, setWalletBalance] = useState(0);

  useEffect(() => {
    // Load wallet balance
    loadWalletBalance();
  }, []);

  const loadWalletBalance = async () => {
    try {
      const response = await apiCall('/api/payments/wallet-detail/');
      if (response.ok) {
        const data = await response.json();
        setWalletBalance(data.balance);
      }
    } catch (error) {
      console.error('Failed to load wallet balance:', error);
    }
  };

  const handlePaymentSuccess = (paymentData) => {
    setSuccess(true);
    setError(null);
    
    // Refresh wallet balance
    setTimeout(() => {
      loadWalletBalance();
    }, 3000);
    
    // Show success message
    alert(`Payment successful! Your wallet will be updated shortly.`);
  };

  const handlePaymentError = (errorMessage) => {
    setError({ message: errorMessage });
    setSuccess(false);
  };

  const resetPayment = () => {
    setError(null);
    setSuccess(false);
  };

  if (success) {
    return (
      <div className="success-container">
        <h2>✅ Payment Successful!</h2>
        <p>Your wallet will be updated within a few moments.</p>
        <button onClick={resetPayment}>Make Another Payment</button>
      </div>
    );
  }

  if (error) {
    return (
      <PaymentErrorHandler
        error={error}
        onRetry={resetPayment}
        onCancel={() => window.history.back()}
      />
    );
  }

  return (
    <div className="wallet-topup">
      <h2>Add Funds to Wallet</h2>
      <p>Current Balance: {walletBalance} IQD</p>
      
      <div className="amount-input">
        <label>Amount (USD):</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Enter amount in USD"
          min="1"
          max="1000"
        />
      </div>

      {amount && (
        <Elements stripe={stripe}>
          <PaymentForm
            amount={amount}
            onSuccess={handlePaymentSuccess}
            onError={handlePaymentError}
          />
        </Elements>
      )}
    </div>
  );
};

export default WalletTopUp;
```

### Integration Checklist

- [ ] **Stripe.js Library**: Installed and properly imported
- [ ] **API Authentication**: JWT token management implemented
- [ ] **Payment Flow**: Create intent → Confirm payment → Handle result
- [ ] **Error Handling**: Proper error messages and retry logic
- [ ] **Token Refresh**: Automatic token refresh on 401 errors
- [ ] **Exchange Rate Display**: Show current rates and conversion
- [ ] **Fee Transparency**: Display all fees before payment
- [ ] **Balance Updates**: Poll or listen for wallet balance changes
- [ ] **Loading States**: Show loading indicators during processing
- [ ] **Security**: Never store sensitive payment data in frontend

### Testing Guidelines

1. **Use Stripe Test Cards**:
   - Success: `4242424242424242`
   - Decline: `4000000000000002`
   - Authentication Required: `4000002500003155`

2. **Test Scenarios**:
   - Successful payment flow
   - Card declined scenarios
   - Network failures
   - Token expiration during payment
   - Webhook processing delays

3. **Monitor Network Tab**:
   - Check API calls to `/api/payments/create-payment/`
   - Verify proper Authorization headers
   - Monitor for 401/403 errors

### Common Issues & Solutions

1. **"No request reaches Stripe"**:
   - Check if `/api/payments/create-payment/` is being called
   - Verify authentication tokens are fresh
   - Ensure proper error handling for token expiration

2. **Payment Intent Creation Fails**:
   - Check Stripe API keys configuration
   - Verify user authentication
   - Check exchange rate API availability

3. **Wallet Not Updated**:
   - Webhook processing is asynchronous
   - Implement polling or WebSocket updates
   - Check Stripe webhook configuration

## Implementation Notes

1. **Stripe Setup**:
   - Requires Stripe API keys configuration
   - Webhook endpoint must be configured in Stripe dashboard
   - Supports USD currency
   - **Frontend Notes**:
     - Create test payments using Stripe test cards
     - Handle different payment statuses
     - Implement proper error handling

2. **Transfer Security**:
   - Atomic transactions prevent race conditions
   - Balance checks before transfers
   - Transaction history maintained
   - **Frontend Notes**:
     - Add confirmation dialog for transfers
     - Display clear warnings about transaction irreversibility
     - Implement recipient verification step for large transfers

3. **Error Handling**:
   - Validation for transfer amounts
   - Insufficient funds protection
   - Invalid recipient handling
   - Stripe error handling
   - **Frontend Notes**:
     - Show specific error messages for each validation failure
     - Implement client-side validation before API calls
     - Provide helpful guidance on how to fix errors
     - Add retry options for temporary failures 