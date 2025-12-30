# Wallet Page Documentation

## Overview
The wallet page is a comprehensive financial management interface that allows users to view their balance, add funds, transfer money, withdraw funds, and view transaction history. The page displays real-time exchange rates and provides detailed transaction filtering capabilities.

## Page Components

### 1. Header
- **Navigation**: Standard header with user profile and notifications
- **Title**: "My Wallet" page title

### 2. Wallet Balance Section
- **Available Balance**: Shows current balance in IQD and USD equivalent
- **Exchange Rate Display**: Current USD to IQD exchange rate with last update timestamp
- **Real-time Updates**: Balance updates automatically after transactions

### 3. Wallet Actions Section
Three main action buttons:
- **Add Funds**: Add money via credit card (Stripe integration)
- **Transfer**: Send money to another user's wallet
- **Withdraw**: Withdraw funds to dealership account

### 4. Transaction History Section
- **Filter Options**: All, Deposit, Transfer In, Transfer Out, Escrow, Release, Refund
- **Transaction List**: Paginated list of all wallet transactions
- **Transaction Details**: Amount, type, date, description, and related contract info

## Required Backend APIs

### 1. Wallet Management APIs

#### Get Wallet Details
```
GET /api/payments/wallet-detail/
```
**Purpose**: Get comprehensive wallet information including balance, transaction ID, and recent transactions
**Authentication**: Required
**Response**:
```json
{
    "wallet_id": 123,
    "transaction_id": "ABC123XYZ789",
    "balance": "1530000.00",
    "username": "john_doe",
    "user_id": 456,
    "current_exchange_rate": {
        "rate": 1530.00,
        "updated_at": "2025-01-04T14:30:00Z"
    },
    "recent_transactions": [
        {
            "id": 789,
            "type": "deposit",
            "amount": "153000.00",
            "amount_usd": "100.00",
            "exchange_rate": "1530.00",
            "description": "Wallet deposit via Stripe",
            "created_at": "2025-01-04T13:00:00Z",
            "contract": null
        }
    ]
}
```

#### Get Transaction History
```
GET /api/payments/transactions/
```
**Purpose**: Get paginated transaction history with filtering options
**Authentication**: Required
**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `type`: Filter by transaction type (optional)
- `date_from`: Start date filter (optional)
- `date_to`: End date filter (optional)

**Response**:
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
        }
    ]
}
```

### 2. Payment Integration APIs

#### Create Payment Intent (Stripe)
```
POST /api/payments/create-payment/
```
**Purpose**: Create Stripe payment intent for adding funds
**Authentication**: Required
**Request Body**:
```json
{
    "amount": 100.00
}
```
**Response**:
```json
{
    "client_secret": "pi_1234567890_secret_abcdef",
    "id": "pi_1234567890",
    "publishable_key": "pk_test_...",
    "exchange_rate": 1530.00,
    "estimated_iqd_amount": 153000.00,
    "fee_percentage": 5.0,
    "estimated_final_amount": 145350.00
}
```

#### Stripe Webhook Handler
```
POST /api/payments/stripe-webhook/
```
**Purpose**: Handle Stripe webhook events for payment confirmations
**Authentication**: Stripe signature verification
**Headers**: 
- `Stripe-Signature`: Webhook signature
**Body**: Stripe event payload

#### Manual Payment Confirmation (Development)
```
POST /api/payments/confirm-payment/
```
**Purpose**: Manually confirm payment for testing purposes
**Authentication**: Required
**Request Body**:
```json
{
    "payment_intent_id": "pi_1234567890"
}
```

### 3. Transfer APIs

#### Transfer Funds
```
POST /api/payments/transfer/
```
**Purpose**: Transfer funds to another user's wallet
**Authentication**: Required
**Request Body**:
```json
{
    "transaction_id": "ABC123XYZ789",
    "amount": 50000.00
}
```
**Response**:
```json
{
    "message": "Transfer successful."
}
```

#### Validate Transfer
```
POST /api/payments/validate-transfer/
```
**Purpose**: Validate transfer before execution (optional)
**Authentication**: Required
**Request Body**:
```json
{
    "transaction_id": "ABC123XYZ789",
    "amount": 50000.00
}
```

### 4. Withdrawal APIs

#### Request Withdrawal
```
POST /api/payments/withdraw/
```
**Purpose**: Request withdrawal to dealership account
**Authentication**: Required (Dealership users only)
**Request Body**:
```json
{
    "amount": 100000.00,
    "withdrawal_method": "bank_transfer",
    "account_details": {
        "account_number": "1234567890",
        "bank_name": "Iraqi Bank",
        "branch": "Baghdad Main"
    }
}
```

#### Get Withdrawal History
```
GET /api/payments/withdrawals/
```
**Purpose**: Get user's withdrawal history
**Authentication**: Required
**Query Parameters**:
- `page`: Page number
- `status`: Filter by status (pending, approved, completed, rejected)

### 5. Exchange Rate APIs

#### Get Current Exchange Rate
```
GET /api/dashboard/exchange-rate/
```
**Purpose**: Get current USD to IQD exchange rate
**Authentication**: Not required (public endpoint)
**Response**:
```json
{
    "id": 1,
    "rate": 1530.00,
    "effective_date": "2025-01-04T14:30:00Z",
    "updated_by": "admin"
}
```

#### Update Exchange Rate (Admin)
```
POST /api/dashboard/exchange-rate/
```
**Purpose**: Update exchange rate (Admin only)
**Authentication**: Required (Admin)
**Request Body**:
```json
{
    "rate": 1535.00
}
```

### 6. Configuration APIs

#### Get Fee Configuration
```
GET /api/dashboard/fee-config/
```
**Purpose**: Get current fee configuration
**Authentication**: Required
**Response**:
```json
{
    "STRIPE_FEE_PERCENTAGE": 5.0,
    "PLATFORM_FEE_PERCENTAGE": 10.0,
    "updated_at": "2025-01-04T14:30:00Z",
    "updated_by": "admin"
}
```

#### Update Fee Configuration (Admin)
```
PUT /api/dashboard/fee-config/
```
**Purpose**: Update fee configuration (Admin only)
**Authentication**: Required (Admin)
**Request Body**:
```json
{
    "STRIPE_FEE_PERCENTAGE": 5.5,
    "PLATFORM_FEE_PERCENTAGE": 10.0
}
```

## Data Models

### Wallet Model
```python
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    transaction_id = models.CharField(max_length=12, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Wallet Transaction Model
```python
class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
        ('escrow', 'Escrow Hold'),
        ('release', 'Payment Release'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
    ]
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_usd = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.CharField(max_length=255)
    contract = models.ForeignKey('Contract', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reference_id = models.CharField(max_length=100, null=True, blank=True)  # For Stripe payment IDs
```

### Exchange Rate Model
```python
class ExchangeRate(models.Model):
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
```

### System Configuration Model
```python
class SystemConfig(models.Model):
    STRIPE_FEE_PERCENTAGE = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    PLATFORM_FEE_PERCENTAGE = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=100)
```

## Business Logic Requirements

### 1. Wallet Creation
- Automatically create wallet when user registers
- Generate unique 12-character transaction ID
- Initialize balance to 0

### 2. Add Funds Flow
1. User enters USD amount
2. System fetches current exchange rate
3. Calculate IQD amount and fees
4. Create Stripe payment intent
5. Process payment via Stripe
6. Webhook updates wallet balance
7. Create transaction record

### 3. Transfer Flow
1. Validate recipient transaction ID
2. Check sender has sufficient balance
3. Perform atomic transaction:
   - Deduct from sender
   - Add to recipient
   - Create transaction records
4. Send notifications to both parties

### 4. Withdrawal Flow
1. Validate user is dealership type
2. Check sufficient balance
3. Create withdrawal request
4. Admin approval required
5. Process withdrawal
6. Update balance and create transaction

### 5. Exchange Rate Updates
- Only admins can update exchange rates
- Rate changes affect new transactions only
- Historical transactions retain original rates
- Rate updates are logged with timestamp

## Security Considerations

### 1. Authentication
- All wallet operations require valid JWT token
- API endpoints validate user permissions
- Sensitive operations require additional verification

### 2. Input Validation
- Validate all amounts for positive values
- Check transaction ID format (12 characters)
- Sanitize all user inputs
- Rate limiting on API endpoints

### 3. Transaction Integrity
- Use database transactions for atomic operations
- Implement proper error handling and rollback
- Log all wallet operations
- Prevent double-spending scenarios

### 4. Stripe Integration
- Validate webhook signatures
- Handle webhook retries properly
- Store minimal payment information
- Implement idempotency keys

## Error Handling

### Common Error Responses
```json
{
    "error": "Insufficient funds",
    "code": "INSUFFICIENT_FUNDS",
    "details": {
        "available_balance": "50000.00",
        "requested_amount": "100000.00"
    }
}
```

### Error Codes
- `INSUFFICIENT_FUNDS`: Not enough balance
- `INVALID_TRANSACTION_ID`: Invalid recipient ID
- `PAYMENT_FAILED`: Stripe payment failed
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_AMOUNT`: Invalid amount specified
- `PERMISSION_DENIED`: User lacks permission

## Frontend Integration Notes

### 1. Real-time Updates
- Implement WebSocket for real-time balance updates
- Poll wallet balance after payment completion
- Update UI immediately after successful operations

### 2. Loading States
- Show loading indicators during API calls
- Disable forms while processing
- Provide clear feedback for all operations

### 3. Error Handling
- Display user-friendly error messages
- Provide retry options for failed operations
- Log errors for debugging purposes

### 4. Responsive Design
- Mobile-first approach
- Touch-friendly interface
- Optimized for various screen sizes

## Testing Requirements

### 1. Unit Tests
- Test all API endpoints
- Validate business logic
- Test error scenarios
- Mock external services

### 2. Integration Tests
- Test Stripe webhook integration
- Test database transactions
- Test API error handling
- Test authentication flows

### 3. Performance Tests
- Load testing for high transaction volumes
- Database query optimization
- API response time benchmarks
- Memory usage monitoring

This documentation provides a complete overview of the wallet page functionality and all required backend APIs. The backend team can use this as a reference to implement the necessary endpoints and business logic. 