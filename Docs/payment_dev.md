# Payment API - Development Guide

## Table of Contents
- [Overview](#overview)
- [Local Development Setup](#local-development-setup)
  - [Stripe CLI Setup](#stripe-cli-setup)
  - [Webhook Testing](#webhook-testing)
- [Development Endpoints](#development-endpoints)
  - [Confirm Payment](#confirm-payment)
  - [Test Webhook Process](#test-webhook-process)
- [Debugging Tools](#debugging-tools)
- [Troubleshooting](#troubleshooting)

## Overview
This document contains development-specific information for the payment system. It includes details about setting up the local development environment, testing tools, and debugging endpoints that should not be used in production.

## Local Development Setup

### Stripe CLI Setup
1. **Install Stripe CLI**:
   - Download from [https://stripe.com/docs/stripe-cli](https://stripe.com/docs/stripe-cli)
   - Follow the installation instructions for your operating system

2. **Login to Stripe CLI**:
   ```bash
   stripe login
   ```

3. **Configure API Keys**:
   - Add these to your environment or .env file:
     ```
     STRIPE_SECRET_KEY=sk_test_...
     STRIPE_PUBLISHABLE_KEY=pk_test_...
     ```

### Webhook Testing
1. **Start Webhook Forwarding**:
   ```bash
   stripe listen --forward-to localhost:8000/api/payments/stripe-webhook/
   ```

2. **Use Webhook Signing Secret**:
   - When you run the listen command, Stripe CLI will display a webhook signing secret
   - Set this in your environment or .env file:
     ```
     STRIPE_WEBHOOK_SECRET=whsec_...
     ```

3. **Testing Webhook Events**:
   ```bash
   stripe trigger payment_intent.succeeded
   ```

## Development Endpoints

### Confirm Payment
- **URL**: `/api/payments/confirm-payment/`
- **Method**: `POST`
- **Description**: Manual payment confirmation endpoint for testing without webhooks
- **Authentication**: Required
- **Request Body**:
```json
{
    "payment_intent_id": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "status": "success",
    "message": "Your wallet has been credited with $X.XX",
    "transaction_id": "integer",
    "new_balance": "decimal"
}
```
  - Error (400/403):
```json
{
    "error": "Payment intent ID is required.|Payment not successful.|This payment intent was not created by you."
}
```
- **Usage Notes**:
  - This endpoint should only be used when webhook setup is not possible
  - It bypasses the normal Stripe webhook flow to manually update wallet balance
  - Useful for early development and testing before proper webhook configuration

### Test Webhook Process
- **URL**: `/api/payments/test-webhook/`
- **Method**: `POST`
- **Description**: Developer endpoint to manually simulate webhook processing
- **Authentication**: Required
- **Request Body**:
```json
{
    "payment_intent_id": "string",
    "amount": "decimal",
    "user_id": "integer" // Optional, defaults to authenticated user
}
```
- **Response**:
  - Success (200):
```json
{
    "status": "success",
    "message": "Test webhook processed successfully",
    "user": "string",
    "previous_balance": "string",
    "new_balance": "string",
    "transaction_id": "integer"
}
```
- **Usage Notes**:
  - Only available when DEBUG mode is enabled
  - Allows testing wallet updates without actual Stripe payments
  - Useful for testing the entire payment flow without using real credit cards

## Debugging Tools

### Wallet Detail Endpoint
- **URL**: `/api/payments/wallet-detail/`
- **Method**: `GET`
- **Description**: Get detailed wallet information including recent transactions
- **Authentication**: Required
- **Debug Information**:
  - Shows current balance and transaction history
  - Useful for verifying payment processing
  - Helps track transaction status and history
- **Frontend Development Notes**:
  - Add refresh button for balance updates
  - Display transaction timestamps in local timezone
  - Show transaction types with distinct styling

### Logging Configuration
- **In settings.py**:
  ```python
  LOGGING = {
      # ... existing logging config ...
      'loggers': {
          'payment': {
              'handlers': ['console', 'file'],
              'level': 'DEBUG',
              'propagate': True,
          },
      }
  }
  ```
- **Log Output**:
  - Payment processing logs
  - Webhook verification details
  - Transaction events
  - Error messages and stack traces

## Troubleshooting

### Common Webhook Issues
1. **Signature Verification Failed**:
   - Check that the correct webhook secret is being used
   - Ensure the webhook secret matches what Stripe CLI provides

2. **No Payment Intent ID in Metadata**:
   - Verify that `metadata={'user_id': user.id}` is being included when creating the PaymentIntent

3. **Wallet Not Updated**:
   - Check logs for any errors in the webhook processing
   - Verify the payment intent has 'succeeded' status
   - Check if transaction already exists (duplicate webhook events)

### Testing with Stripe Test Cards
- **Test Card Success**: `4242 4242 4242 4242`
- **Test Card Requires Auth**: `4000 0025 0000 3155`
- **Test Card Declined**: `4000 0000 0000 9995`
- **Expiry Date**: Any future date
- **CVC**: Any 3 digits
- **ZIP**: Any 5 digits