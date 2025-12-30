# Dashboard API Documentation

## Table of Contents
- [Fee Configuration](#fee-configuration)
  - [Get Fee Configuration](#get-fee-configuration)
  - [Update Fee Configuration](#update-fee-configuration)
- [Exchange Rate Management](#exchange-rate-management)
  - [Get Current Exchange Rate](#get-current-exchange-rate)
  - [Update Exchange Rate](#update-exchange-rate)
  - [View Exchange Rate History](#view-exchange-rate-history)
- [Fee Analytics](#fee-analytics)
  - [Get Fee Analytics](#get-fee-analytics)
  - [Revenue Dashboard Integration](#revenue-dashboard-integration)
- [Admin Dashboard](#admin-dashboard)
  - [Dashboard Statistics](#dashboard-statistics)
- [Dealership Management](#dealership-management)
  - [Dealership Analytics Overview](#dealership-analytics-overview)
  - [Dealership Statistics](#dealership-statistics)
  - [Withdrawal Analytics](#withdrawal-analytics)
  - [Performance Metrics](#performance-metrics)
- [User Management](#user-management)
  - [List and Filter Users](#list-and-filter-users)
  - [User Management Actions](#user-management-actions)
- [Transaction Management](#transaction-management)
  - [List All Transactions](#list-all-transactions)
  - [Transaction Filtering](#transaction-filtering)
  - [Transaction Summary](#transaction-summary)
- [Platform Wallet Management](#platform-wallet-management)
  - [Platform Wallet Overview](#platform-wallet-overview)
  - [Platform Transaction History](#platform-transaction-history)
  - [Platform Expense Management](#platform-expense-management)
- [Dashboard Access Controls](#dashboard-access-controls)
  - [Role-Based Access Control](#role-based-access-control)
  - [Dashboard Access Matrix](#dashboard-access-matrix)
- [Implementation Notes](#implementation-notes)
  - [Frontend Requirements](#frontend-requirements)
  - [Dashboard Integration](#dashboard-integration)
  - [Error Handling](#error-handling)

## Fee Configuration

The fee configuration module allows administrators to manage global settings for the application, including fee percentages for various transactions.

### Get Fee Configuration
- **URL**: `/api/dashboard/fee-config/`
- **Method**: `GET`
- **Description**: Get current fee configuration including fee percentages
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
{
    "STRIPE_FEE_PERCENTAGE": 5.00,
    "PLATFORM_FEE_PERCENTAGE": 10.00,
    "updated_at": "2023-09-15T14:30:00Z",
    "updated_by": "admin"
}
```

### Update Fee Configuration
- **URL**: `/api/dashboard/fee-config/`
- **Method**: `PUT`
- **Description**: Update fee configuration settings
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "STRIPE_FEE_PERCENTAGE": 5.50,
    "PLATFORM_FEE_PERCENTAGE": 9.50
}
```
- **Response**:
  - Success (200):
```json
{
    "STRIPE_FEE_PERCENTAGE": 5.50,
    "PLATFORM_FEE_PERCENTAGE": 9.50,
    "updated_at": "2023-09-15T15:45:00Z",
    "updated_by": "admin"
}
```
  - Error (403):
```json
{
    "detail": "You do not have permission to update fee configuration settings."
}
```

**Frontend Implementation Notes**:
- Display current fee percentages in an admin settings section
- Implement input validation for fee percentages:
  * STRIPE_FEE_PERCENTAGE: 0.01% to 20.00%
  * PLATFORM_FEE_PERCENTAGE: 0.01% to 30.00%
- Display the last update time and administrator who made the change
- Show a confirmation dialog before submitting changes
- Implement proper error handling for validation errors and permission issues

## Exchange Rate Management

The exchange rate management module allows administrators to maintain the currency exchange rate between USD and IQD (Iraqi Dinar).

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

### Update Exchange Rate
- **URL**: `/api/dashboard/exchange-rate/`
- **Method**: `POST`
- **Description**: Update the USD to IQD exchange rate
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "rate": 1210.50
}
```
- **Response**:
  - Success (200):
```json
{
    "id": 2,
    "rate": 1210.50,
    "effective_date": "2023-09-16T09:15:00Z",
    "updated_by": "admin"
}
```
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```

### View Exchange Rate History
- **URL**: `/api/dashboard/exchange-rate/history/`
- **Method**: `GET`
- **Description**: View history of exchange rate changes
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (200):
```json
[
    {
        "id": 2,
        "rate": 1210.50,
        "effective_date": "2023-09-16T09:15:00Z",
        "updated_by": "admin"
    },
    {
        "id": 1,
        "rate": 1200.00,
        "effective_date": "2023-09-15T14:30:00Z",
        "updated_by": "admin"
    }
]
```

**Frontend Implementation Notes**:
- Display the current exchange rate prominently in the admin dashboard
- Create a form for updating the rate with validation (must be greater than 0.01)
- Implement a history table showing past exchange rates with sorting and filtering
- Include a confirmation step when updating rates to prevent accidental changes
- Show a chart visualizing rate changes over time
- Cache the current exchange rate on the client side for better performance

## Fee Analytics

The fee analytics module provides insights into the system's fee performance and revenue generation.

### Get Fee Analytics
- **URL**: `/api/dashboard/fee-analytics/`
- **Method**: `GET`
- **Description**: Get fee analytics data
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (200):
```json
{
    "total_fees": 100000,
    "total_revenue": 120000,
    "fee_percentage": 8.33,
    "revenue_percentage": 10.00
}
```

### Revenue Dashboard Integration
- **URL**: `/api/dashboard/revenue-dashboard/`
- **Method**: `GET`
- **Description**: Get revenue dashboard data
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (200):
```json
{
    "total_revenue": 120000,
    "monthly_revenue": {
        "January": 10000,
        "February": 12000,
        "March": 15000,
        "April": 18000,
        "May": 20000,
        "June": 22000,
        "July": 25000,
        "August": 28000,
        "September": 30000,
        "October": 32000,
        "November": 35000,
        "December": 38000
    }
}
```

## Admin Dashboard

The admin dashboard provides administrators with a comprehensive overview of the system's status and key metrics.

### Dashboard Statistics
- **URL**: `/api/dashboard/admin/dashboard/`
- **Method**: `GET`
- **Description**: Get all statistics for the admin dashboard including revenue analytics
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint
- **Response**:
  - Success (200):
```json
{
    "total_users": {
        "count": 1352,
        "description": "Registered accounts"
    },
    "active_users": {
        "count": 876,
        "description": "Active in last 10 days"
    },
    "pending_technicians": {
        "count": 8,
        "description": "Awaiting approval"
    },
    "pending_dealerships": {
        "count": 3,
        "description": "Awaiting verification"
    },
    "active_projects": {
        "count": 42,
        "description": "Currently in progress"
    },
    "completed_projects": {
        "count": 284,
        "description": "Successfully finished"
    },
    "reported_content": {
        "count": 0,
        "description": "Items awaiting moderation"
    },
    "active_disputes": {
        "count": 0,
        "description": "Require admin attention"
    },
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
  - Error (403):
```json
{
    "detail": "You do not have permission to access the admin dashboard."
}
```

**Frontend Implementation Notes**:
- Create a visually appealing dashboard with cards for each statistic
- Use charts and graphs to visualize trends
- Implement real-time or periodic refresh of dashboard data
- Add links from statistics to relevant detail pages (e.g., pending technicians → list of technicians awaiting approval)
- Use color coding to highlight statistics that require attention
- Implement responsive design for desktop and mobile viewing
- Consider adding filters for date ranges to view historical trends

## Dealership Management

The dealership management module provides administrators with comprehensive tools to monitor and manage the dealership network, including cash withdrawal services, performance analytics, and operational insights.

### Dealership Analytics Overview
- **URL**: `/api/dashboard/admin/dealership-analytics/`
- **Method**: `GET`
- **Description**: Get comprehensive dealership analytics and statistics
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint
- **Response**:
  - Success (200):
```json
{
    "dealership_statistics": {
        "total": 45,
        "pending": 8,
        "approved": 35,
        "rejected": 1,
        "suspended": 1,
        "active": 34
    },
    "withdrawal_statistics": {
        "total_withdrawals": 1247,
        "pending": 23,
        "approved": 5,
        "processing": 12,
        "completed": 1198,
        "cancelled": 7,
        "disputed": 2
    },
    "top_performing_dealerships": [
        {
            "id": "uuid-string",
            "office_name": "Baghdad Exchange Center",
            "governorate": "Baghdad",
            "total_transactions": 156,
            "successful_transactions": 154,
            "success_rate": 98.72,
            "rating": 4.8
        },
        {
            "id": "uuid-string",
            "office_name": "Basra Financial Services",
            "governorate": "Basra",
            "total_transactions": 142,
            "successful_transactions": 139,
            "success_rate": 97.89,
            "rating": 4.7
        }
    ],
    "recent_pending_withdrawals": [
        {
            "id": "uuid-string",
            "withdrawal_code": "WD1234567890",
            "amount": "500000.00",
            "status": "pending",
            "dealership_name": "Al-Karada Exchange",
            "created_at": "2024-01-15T10:30:00Z",
            "user_email": "user@example.com"
        },
        {
            "id": "uuid-string",
            "withdrawal_code": "WD0987654321",
            "amount": "750000.00",
            "status": "disputed",
            "dealership_name": "Mansour Money Exchange",
            "created_at": "2024-01-14T14:22:00Z",
            "user_email": "client@domain.com"
        }
    ],
    "geographic_distribution": [
        {
            "governorate": "Baghdad",
            "count": 15
        },
        {
            "governorate": "Basra",
            "count": 8
        },
        {
            "governorate": "Erbil",
            "count": 6
        }
    ],
    "recent_activity": {
        "new_registrations": 3,
        "completed_withdrawals": 89,
        "total_withdrawal_amount": "12750000.00"
    }
}
```
  - Error (403):
```json
{
    "detail": "You do not have permission to access dealership analytics."
}
```

### Dealership Statistics

The main admin dashboard includes dealership statistics integrated into the overall system metrics:

#### Included in Main Dashboard Response
- **URL**: `/api/dashboard/admin/dashboard/`
- **Method**: `GET`
- **Description**: Admin dashboard now includes dealership analytics in the response
- **Added Fields**:
```json
{
    "dealership_analytics": {
        "total_dealerships": {
            "count": 45,
            "description": "Total registered dealerships"
        },
        "active_dealerships": {
            "count": 34,
            "description": "Active and approved dealerships"
        },
        "pending_dealerships": {
            "count": 8,
            "description": "Awaiting verification"
        },
        "suspended_dealerships": {
            "count": 1,
            "description": "Suspended dealerships"
        },
        "withdrawal_statistics": {
            "total_withdrawals": 1247,
            "completed_withdrawals": 1198,
            "pending_withdrawals": 40,
            "success_rate": 96.07
        },
        "recent_activity": {
            "withdrawals_last_30_days": 89,
            "total_amount_last_30_days": "12750000.00",
            "description": "Last 30 days activity"
        },
        "satisfaction_metrics": {
            "satisfaction_rate": 94.5,
            "total_feedback_received": 892,
            "satisfied_users": 843,
            "description": "User satisfaction with withdrawals"
        }
    }
}
```

### Withdrawal Analytics

Detailed withdrawal transaction analytics help administrators monitor the cash withdrawal system's performance:

#### Key Metrics Tracked:
- **Transaction Volume**: Total number of withdrawal requests
- **Status Distribution**: Breakdown by transaction status (pending, processing, completed, etc.)
- **Success Rate**: Percentage of successfully completed withdrawals
- **Geographic Distribution**: Withdrawal activity by governorate
- **Time-based Analysis**: Trends and patterns over time
- **User Satisfaction**: Feedback scores and satisfaction rates

#### Performance Indicators:
- **Processing Time**: Average time from request to completion
- **Dispute Rate**: Percentage of withdrawals that result in disputes
- **Cancellation Rate**: Percentage of withdrawals that are cancelled
- **Peak Activity Times**: Busiest hours and days for withdrawal requests

### Performance Metrics

#### Dealership Performance Tracking:
- **Transaction Success Rate**: Percentage of successful completions per dealership
- **User Satisfaction Scores**: Average ratings and feedback
- **Processing Efficiency**: Average time to complete withdrawals
- **Geographic Coverage**: Distribution across Iraqi governorates
- **Compliance Status**: Document verification and regulatory compliance

#### System-wide Metrics:
- **Network Growth**: Rate of new dealership registrations
- **Service Availability**: Percentage of active vs. total dealerships
- **Financial Impact**: Total withdrawal amounts processed
- **Risk Assessment**: Identification of high-risk transactions or patterns

**Frontend Implementation Notes**:
- **Dashboard Integration**: 
  - Add dealership widget to main admin dashboard
  - Show key metrics with drill-down capabilities
  - Include pending actions requiring admin attention
  
- **Analytics Interface**:
  - Create dedicated dealership analytics page
  - Implement interactive charts for geographic distribution
  - Add time-range filters for historical analysis
  - Include exportable reports for compliance

- **Performance Monitoring**:
  - Real-time status indicators for dealership network
  - Alert system for pending verifications and disputes
  - Performance ranking tables for dealership comparison
  - Trend analysis with visual representations

- **Management Tools**:
  - Quick access to pending dealership applications
  - Bulk actions for document verification
  - Direct links to individual dealership management pages
  - Integration with user management for dealership owners

- **Mobile Optimization**:
  - Responsive design for mobile dashboard access
  - Key metrics summary for mobile viewing
  - Quick action buttons for urgent tasks
  - Push notifications for critical alerts

## User Management

The user management module allows administrators to view, filter, and manage all users in the system.

### List and Filter Users
- **URL**: `/api/dashboard/admin/users/`
- **Method**: `GET`
- **Description**: List all users with filtering and pagination
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Request Parameters**:
- `search` (optional): Search users by name or email
- `role` (optional): Filter by user role (all|client|technician|dealership|admin)
- `status` (optional): Filter by user status (all|active|inactive|pending)

**Response**:
  - Success (200):
```json
{
    "users": [
        {
            "id": 1,
            "public_id": "CLIENT-123abc",
            "name": "John Doe",
            "email": "john@example.com",
            "role": "Client",
            "status": "Active",
            "created": "2023-01-15",
            "actions": {
                "can_view": true,
                "can_approve": false,
                "can_activate": false,
                "can_deactivate": true
            }
        },
        {
            "id": 2,
            "public_id": "TECH-789ghi",
            "name": "Jane Smith",
            "email": "jane@example.com",
            "role": "Technician",
            "status": "Pending",
            "created": "2023-02-10",
            "actions": {
                "can_view": true,
                "can_approve": true,
                "can_activate": false,
                "can_deactivate": false
            }
        },
        {
            "id": 3,
            "public_id": "DEALER-345mno",
            "name": "Acme Corp",
            "email": "acme@example.com",
            "role": "Dealership",
            "status": "Active",
            "created": "2023-03-05",
            "actions": {
                "can_view": true,
                "can_approve": false,
                "can_activate": false,
                "can_deactivate": true
            }
        },
        {
            "id": 4,
            "public_id": "ADMIN-901stu",
            "name": "Admin User",
            "email": "admin@example.com",
            "role": "System Administrator",
            "status": "Active",
            "created": "2023-01-01",
            "actions": {
                "can_view": true,
                "can_approve": false,
                "can_activate": false,
                "can_deactivate": false
            }
        },
        {
            "id": 5,
            "public_id": "ADMIN-567yza",
            "name": "Content Manager",
            "email": "content@example.com",
            "role": "Content Moderator",
            "status": "Active",
            "created": "2023-01-05",
            "actions": {
                "can_view": true,
                "can_approve": false,
                "can_activate": false,
                "can_deactivate": false
            }
        },
        {
            "id": 6,
            "public_id": "ADMIN-efg123",
            "name": "Finance User",
            "email": "finance@example.com",
            "role": "Financial Administrator",
            "status": "Active",
            "created": "2023-01-10",
            "actions": {
                "can_view": true,
                "can_approve": false,
                "can_activate": false,
                "can_deactivate": false
            }
        }
    ],
    "total_count": 6
}
```

### User Management Actions
- **URL**: `/api/dashboard/admin/users/`
- **Method**: `POST`
- **Description**: Perform actions on users (approve, activate, deactivate)
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint
- **Request Body**:
```json
{
    "user_id": "TECH-789ghi",
    "action": "approve|activate|deactivate"
}
```
- **Notes**:
  - The `user_id` should be the `public_id` from the user list response, not the internal database ID
  - The `approve` action will mark technician or dealership profiles as complete

- **Response**:
  - Success (200):
```json
{
    "message": "User [action] successfully"
}
```
  - Error (400):
```json
{
    "error": "Invalid action"
}
```
  - Error (404):
```json
{
    "error": "User not found"
}
```

**Frontend Implementation Notes**:
- Create a user management interface with a searchable, sortable table
- Implement filters for role and status with clear visual indicators
- Add action buttons for each user based on their current status
- Implement confirmation dialogs for potentially destructive actions
- Show success/error messages after actions are performed
- Include user details view with all relevant information
- Use the `public_id` to create navigation links to user profiles:
  - For clients: `/api/accounts/client/CLIENT-123abc/`
  - For technicians: `/api/accounts/technician/TECH-789ghi/`
  - For dealerships: `/api/accounts/dealership/DEALER-456def/`
- Consider implementing bulk actions for managing multiple users at once
- Add pagination for large user lists

## Transaction Management

The transaction management module provides administrators with a comprehensive view of all money movements across the platform, aggregating data from wallet transactions, dealership withdrawals, and other financial activities.

### List All Transactions
- **URL**: `/api/dashboard/admin/transactions/`
- **Method**: `GET`
- **Description**: Get comprehensive list of all platform transactions with filtering and pagination
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Request Parameters**:
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `type` (optional): Filter by transaction type
  - Values: `deposit`, `transfer_in`, `transfer_out`, `escrow`, `release`, `refund`, `withdrawal`, `dealership_withdrawal`
- `status` (optional): Filter by transaction status
  - Values: `completed`, `pending`, `processing`, `cancelled`, `disputed`
- `user_type` (optional): Filter by user type
  - Values: `client`, `technician`, `dealership`, `admin`
- `date_from` (optional): Start date filter in YYYY-MM-DD format
- `date_to` (optional): End date filter in YYYY-MM-DD format
- `search` (optional): Search by user name or email

**Response**:
  - Success (200):
```json
{
    "count": 1247,
    "next": "http://api.example.com/api/dashboard/admin/transactions/?page=2",
    "previous": null,
    "results": {
        "transactions": [
            {
                "id": "WT-789",
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "user_type": "client",
                "transaction_type": "deposit",
                "amount_iqd": "153000.00",
                "amount_usd": "100.00",
                "exchange_rate": "1530.00",
                "status": "completed",
                "description": "Deposit via Stripe (Payment ID: pi_xyz123). Fee: 7650 IQD (5%).",
                "created_at": "2025-01-04T15:30:00Z",
                "related_contract": null,
                "related_dealership": null,
                "fee_collected": null,
                "source": "wallet"
            },
            {
                "id": "WT-788",
                "user_name": "Jane Smith",
                "user_email": "jane@example.com",
                "user_type": "technician",
                "transaction_type": "transfer_in",
                "amount_iqd": "90000.00",
                "amount_usd": "58.82",
                "exchange_rate": "1530.00",
                "status": "completed",
                "description": "Payment received for Stage 1 of Contract CONT-ABC123. Platform fee: 10000 IQD (10%).",
                "created_at": "2025-01-04T14:45:00Z",
                "related_contract": "CONT-ABC123",
                "related_dealership": null,
                "fee_collected": null,
                "source": "wallet"
            },
            {
                "id": "DW-456",
                "user_name": "Bob Johnson",
                "user_email": "bob@example.com",
                "user_type": "client",
                "transaction_type": "dealership_withdrawal",
                "amount_iqd": "200000.00",
                "amount_usd": null,
                "exchange_rate": null,
                "status": "pending",
                "description": "Withdrawal to Downtown Exchange (Code: WD123ABC)",
                "created_at": "2025-01-04T13:20:00Z",
                "related_contract": null,
                "related_dealership": "Downtown Exchange",
                "fee_collected": null,
                "source": "dealership"
            }
        ],
        "total_count": 1247,
        "summary": {
            "total_volume_iqd": "45678900.50",
            "total_volume_usd": "33456.75",
            "total_transactions": 1247,
            "completed_transactions": 1189,
            "pending_transactions": 58,
            "transaction_types": {
                "deposit": 456,
                "transfer_in": 234,
                "transfer_out": 234,
                "escrow": 123,
                "release": 89,
                "withdrawal": 67,
                "dealership_withdrawal": 44
            }
        }
    }
}
```

### Transaction Filtering

The transaction management system supports comprehensive filtering to help administrators analyze specific transaction patterns:

#### **By Transaction Type**
```bash
# View only deposits
GET /api/dashboard/admin/transactions/?type=deposit

# View only withdrawals
GET /api/dashboard/admin/transactions/?type=withdrawal

# View only contract-related transactions
GET /api/dashboard/admin/transactions/?type=escrow
```

#### **By User Type**
```bash
# View client transactions only
GET /api/dashboard/admin/transactions/?user_type=client

# View technician transactions only
GET /api/dashboard/admin/transactions/?user_type=technician
```

#### **By Status**
```bash
# View completed transactions
GET /api/dashboard/admin/transactions/?status=completed

# View pending transactions requiring attention
GET /api/dashboard/admin/transactions/?status=pending
```

#### **By Date Range**
```bash
# View transactions from last month
GET /api/dashboard/admin/transactions/?date_from=2024-12-01&date_to=2024-12-31

# View recent transactions
GET /api/dashboard/admin/transactions/?date_from=2025-01-01
```

#### **Combined Filters**
```bash
# View pending client deposits from this week
GET /api/dashboard/admin/transactions/?type=deposit&user_type=client&status=pending&date_from=2025-01-01

# Search for specific user transactions
GET /api/dashboard/admin/transactions/?search=john@example.com
```

### Transaction Summary

The API provides comprehensive summary statistics for transaction analysis:

#### **Volume Metrics**
- **Total Volume (IQD)**: Total amount of all completed transactions in IQD
- **Total Volume (USD)**: Total amount of all completed transactions in USD
- **Transaction Count**: Total number of transactions in the filtered set

#### **Status Breakdown**
- **Completed Transactions**: Successfully processed transactions
- **Pending Transactions**: Transactions awaiting processing or approval
- **Failed/Cancelled Transactions**: Transactions that were not completed

#### **Transaction Type Distribution**
Provides count breakdown by transaction type:
- `deposit`: Stripe wallet deposits
- `transfer_in/transfer_out`: Wallet-to-wallet transfers
- `escrow`: Funds held for contracts
- `release`: Contract payments released to technicians
- `withdrawal`: Withdrawal requests
- `dealership_withdrawal`: Withdrawals processed through dealerships

**Frontend Implementation Notes**:
- **Transaction Table**: Create a comprehensive table with sortable columns for all transaction fields
- **Advanced Filtering**: Implement filter sidebar with:
  - Transaction type multiselect
  - User type radio buttons
  - Status checkboxes
  - Date range picker
  - Search input with debouncing
- **Summary Dashboard**: Display key metrics prominently:
  - Total volume cards (IQD/USD)
  - Transaction count indicators
  - Status breakdown pie chart
  - Transaction type distribution bar chart
- **Export Functionality**: Allow administrators to export filtered transaction data as CSV/Excel
- **Real-time Updates**: Consider implementing WebSocket updates for real-time transaction monitoring
- **Transaction Details**: Link each transaction to detailed view with full context:
  - User profile information
  - Related contract details (if applicable)
  - Dealership information (for withdrawals)
  - Fee collection details
  - Complete transaction history
- **Performance Optimization**:
  - Implement virtual scrolling for large transaction lists
  - Use pagination to handle large datasets
  - Cache frequently accessed data
  - Implement debounced search to reduce API calls
- **Error Handling**: Provide clear error messages for invalid filters or API failures
- **Access Control**: Ensure proper role-based access control for sensitive transaction data

## Platform Wallet Management

The platform wallet management system provides administrators with complete control over platform finances, including revenue accumulation, expense tracking, and withdrawal management. This system replaces the previous analytics-only approach with actual financial management capabilities.

### Platform Wallet Overview
- **URL**: `/api/dashboard/admin/platform-wallet/`
- **Method**: `GET`
- **Description**: Get comprehensive platform wallet status and financial overview
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Response**:
  - Success (200):
```json
{
    "current_balance": {
        "balance_iqd": "5678900.50",
        "balance_usd": "4234.75"
    },
    "lifetime_totals": {
        "total_revenue_iqd": "12456789.25",
        "total_revenue_usd": "9876.54",
        "total_expenses_iqd": "6777888.75",
        "total_expenses_usd": "5641.79"
    },
    "profitability": {
        "net_profit_iqd": "5678900.50",
        "net_profit_usd": "4234.75",
        "profit_margin_percentage": 42.85
    },
    "recent_transactions": [
        {
            "id": 157,
            "type": "fee_collection",
            "type_display": "Fee Collection",
            "amount_iqd": "15300.00",
            "amount_usd": "10.00",
            "description": "Stripe Deposit Fee - Fee collected (5%)",
            "created_at": "2025-01-04T16:30:00Z",
            "is_revenue": true,
            "source_fee_type": "stripe_deposit"
        },
        {
            "id": 156,
            "type": "expense",
            "type_display": "Platform Expense",
            "amount_iqd": "-500000.00",
            "amount_usd": "-326.80",
            "description": "Server hosting costs for Q1 2025",
            "created_at": "2025-01-01T10:00:00Z",
            "is_revenue": false,
            "source_fee_type": null
        }
    ],
    "wallet_created": "2024-01-01T00:00:00Z",
    "last_updated": "2025-01-04T16:30:00Z"
}
```

### Platform Transaction History
- **URL**: `/api/dashboard/admin/platform-wallet/transactions/`
- **Method**: `GET`
- **Description**: Get paginated platform transaction history with filtering
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Request Parameters**:
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Items per page (default: 50, max: 200)
- `type` (optional): Filter by transaction type
  - Values: `fee_collection`, `expense`, `withdrawal`, `adjustment`
- `date_from` (optional): Start date filter in YYYY-MM-DD format
- `date_to` (optional): End date filter in YYYY-MM-DD format

**Response**:
  - Success (200):
```json
{
    "count": 1247,
    "next": "http://api.example.com/api/dashboard/admin/platform-wallet/transactions/?page=2",
    "previous": null,
    "results": {
        "transactions": [
            {
                "id": 157,
                "transaction_type": "fee_collection",
                "transaction_type_display": "Fee Collection",
                "amount_iqd": "15300.00",
                "amount_usd": "10.00",
                "source_fee_type": "stripe_deposit",
                "description": "Stripe Deposit Fee - Fee collected (5%)",
                "balance_after_iqd": "5678900.50",
                "balance_after_usd": "4234.75",
                "processed_by": null,
                "created_at": "2025-01-04T16:30:00Z",
                "is_revenue": true,
                "is_expense": false
            },
            {
                "id": 156,
                "transaction_type": "expense",
                "transaction_type_display": "Platform Expense",
                "amount_iqd": "-500000.00",
                "amount_usd": "-326.80",
                "source_fee_type": null,
                "description": "Server hosting costs for Q1 2025",
                "balance_after_iqd": "5663600.50",
                "balance_after_usd": "4224.75",
                "processed_by": "admin",
                "created_at": "2025-01-01T10:00:00Z",
                "is_revenue": false,
                "is_expense": true
            }
        ],
        "total_count": 1247,
        "summary": {
            "total_revenue_iqd": "8900567.25",
            "total_expenses_iqd": "3221666.75",
            "net_amount_iqd": "5678900.50",
            "transaction_count": 1247
        }
    }
}
```

### Platform Expense Management
- **URL**: `/api/dashboard/admin/platform-wallet/expense/`
- **Method**: `POST`
- **Description**: Create platform expenses, withdrawals, or adjustments
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Request Body**:
```json
{
    "amount_iqd": "500000.00",
    "amount_usd": "326.80",
    "description": "Server hosting costs for Q1 2025",
    "expense_type": "expense"
}
```

**Request Parameters**:
- `amount_iqd` (required): Expense amount in IQD
- `amount_usd` (required): Expense amount in USD
- `description` (required): Detailed description of the expense
- `expense_type` (optional): Type of expense (default: "expense")
  - Values: `expense`, `withdrawal`, `adjustment`

**Response**:
  - Success (201):
```json
{
    "success": true,
    "transaction": {
        "id": 158,
        "type": "expense",
        "amount_iqd": "-500000.00",
        "amount_usd": "-326.80",
        "description": "Server hosting costs for Q1 2025",
        "processed_by": "admin",
        "created_at": "2025-01-04T17:00:00Z",
        "balance_after_iqd": "5178900.50",
        "balance_after_usd": "3907.95"
    },
    "message": "Platform expense processed successfully"
}
```
  - Error (400 - Insufficient Balance):
```json
{
    "error": "Insufficient platform wallet balance",
    "current_balance": {
        "iqd": "5678900.50",
        "usd": "4234.75"
    }
}
```
  - Error (400 - Validation):
```json
{
    "error": "amount_iqd, amount_usd, and description are required"
}
```

#### **Platform Expense Types**

1. **Expense** (Default):
   - General platform operating expenses
   - Server costs, marketing, staff salaries, etc.
   - Recorded as negative amounts in transaction history

2. **Withdrawal**:
   - Platform revenue withdrawals for business use
   - Investor distributions, owner withdrawals
   - Recorded as negative amounts with "withdrawal" type

3. **Adjustment**:
   - Balance corrections or adjustments
   - Accounting corrections, refunds, etc.
   - Can be positive or negative depending on adjustment type

**Frontend Implementation Notes**:
- **Platform Wallet Dashboard**: Create a comprehensive financial dashboard showing:
  - Current balance prominently displayed with both IQD and USD
  - Revenue vs expenses comparison charts
  - Profit margin trends over time
  - Recent transaction activity
- **Transaction History**: Implement searchable, filterable transaction table with:
  - Transaction type color coding (green for revenue, red for expenses)
  - Source fee type badges for revenue transactions
  - Admin user tracking for manual transactions
  - Export functionality for accounting purposes
- **Expense Management**: Create expense creation form with:
  - Currency input fields with validation
  - Expense type selection
  - Rich text description field
  - Balance check before submission
  - Confirmation dialog for large expenses
- **Financial Analytics**: Add analytics features:
  - Monthly/quarterly revenue and expense reports
  - Profit margin calculations and trends
  - Fee collection performance metrics
  - Cost per user acquisition tracking
- **Real-time Updates**: Consider implementing WebSocket updates for:
  - Real-time balance updates when fees are collected
  - Instant notification of new transactions
  - Live profit margin calculations
- **Security Features**:
  - Multi-factor authentication for expense creation
  - Approval workflow for large expenses
  - Audit logging for all financial operations
  - Role-based access control for different financial functions

#### **Automatic Fee Integration**

The platform wallet automatically receives fees from all revenue sources:

1. **Stripe Deposit Fees**: Automatically added when users make wallet deposits
2. **Platform Contract Fees**: Automatically added when contract payments are released
3. **Real-time Balance Updates**: Wallet balance updates immediately upon fee collection
4. **Complete Transaction History**: All fee collections are tracked with source information

This system ensures that all platform revenue is properly accumulated and managed, providing administrators with complete financial control and transparency.

## Dashboard Access Controls

### Role-Based Access Control

The dashboard currently implements a simple role-based access control system:

1. **Admin Access**: All dashboard endpoints require the user to have `is_staff=True` (Django admin status)
2. **Public Endpoints**: Only the following endpoints are accessible without authentication:
   - `GET /api/dashboard/fee-config/` - View current fee configuration
   - `GET /api/dashboard/exchange-rate/` - View current exchange rate

All other dashboard endpoints require both authentication and admin privileges.

**Current Implementation Note**: While the documentation describes different admin roles (System Administrator, Content Moderator, Account Manager, Financial Administrator), the current implementation only checks for the basic admin status (`is_staff=True`) and does not yet enforce fine-grained role-based permissions. This is planned for future development.

### Dashboard Access Matrix

| Dashboard Section | Admin Access | Public Access |
|------------------|--------------|---------------|
| View Fee Configuration | ✅ Yes | ✅ Yes |
| Update Fee Configuration | ✅ Yes | ❌ No |
| View Exchange Rate | ✅ Yes | ✅ Yes |
| Update Exchange Rate | ✅ Yes | ❌ No |
| View Exchange Rate History | ✅ Yes | ❌ No |
| Admin Dashboard Statistics | ✅ Yes | ❌ No |
| User Management | ✅ Yes | ❌ No |
| Transaction Management | ✅ Yes | ❌ No |
| Platform Wallet Overview | ✅ Yes | ❌ No |
| Platform Transaction History | ✅ Yes | ❌ No |
| Platform Expense Management | ✅ Yes | ❌ No |
| Technician Cards | ✅ Yes | ❌ No |

**Frontend Implementation Notes**:
- Implement conditional rendering of dashboard sections based on user role
- Validate permissions on both client and server side
- Show appropriate error messages for unauthorized access attempts
- Implement a role-based navigation menu
- Clearly indicate the current user's role in the UI
- Handle edge cases gracefully (e.g., a user whose role changes while they are using the system)

## Implementation Notes

### Frontend Requirements

1. **Technology Stack**:
   - React.js or Vue.js for the frontend
   - Responsive design using a UI framework like Material-UI or Bootstrap
   - Chart.js or D3.js for data visualization

2. **Authentication**:
   - JWT token-based authentication
   - Token refresh mechanism
   - Role-based access control
   - Session timeout handling

3. **UI Components**:
   - Dashboard overview with statistics cards
   - User management table with filtering and search
   - Forms for updating system configuration and exchange rates
   - Charts and graphs for data visualization
   - Navigation menu with role-based access
   - Modal dialogs for confirmations
   - Toast notifications for success/error messages

### Dashboard Integration

1. **API Integration**:
   - Implement API service layer with axios or fetch
   - Handle authentication and authorization
   - Implement error handling and retry logic
   - Cache responses where appropriate
   - Implement real-time updates where needed

2. **State Management**:
   - Use Redux or Vuex for global state management
   - Implement loading states for API calls
   - Cache dashboard data to reduce server load
   - Implement optimistic updates for better UX

### Error Handling

1. **Client-Side Validation**:
   - Validate form inputs before submission
   - Display clear error messages for validation failures
   - Prevent submission of invalid data

2. **Server-Side Error Handling**:
   - Handle API errors gracefully
   - Display meaningful error messages
   - Implement retry mechanisms for network failures
   - Log errors for debugging purposes

3. **Edge Cases**:
   - Handle empty data states
   - Implement loading states for all async operations
   - Handle permission denied scenarios gracefully
   - Implement timeout handling for long-running operations

### Technician Cards
- **URL**: `/api/dashboard/admin/technicians/`
- **Method**: `GET`
- **Description**: Get detailed technician information in card format with filtering options
- **Authentication**: Required (Admin users only)
- **Permission**: Only users with admin role can access this endpoint

**Request Parameters**:
- `search` (optional): Search by name or email
- `status` (optional): Filter by status (all|pending|active|inactive)
- `skill` (optional): Filter by skill name
- `min_rating` (optional): Filter by minimum rating (e.g., 4.0)
- `min_experience` (optional): Filter by minimum years of experience
- `governorate` (optional): Filter by governorate name

**Response**:
  - Success (200):
```json
{
    "technicians": [
        {
            "name": "Alex Johnson",
            "email": "alex@example.com",
            "skills": ["Web Development", "React", "Node.js", "Python", "UI/UX", "Figma", "Adobe XD"],
            "experience": "5",
            "bio": "Specialized in advanced cybernetic augmentations and neural interface systems.",
            "rating": 4.5,
            "review_count": 12,
            "applied_date": "2023-05-15",
            "profile_image": "http://example.com/media/profile_images/alex.jpg",
            "status": "Pending",
            "portfolio_url": "/api/accounts/technician/TECH-a4b5c6/",
            "governorate": "Baghdad",
            "job_title": "Senior Developer",
            "identification_verified": true,
            "profile_completion_percentage": 95.5,
            "identification_documents_url": "/media/technicians/identification_docs/a4b5c6d7e8f9_identification.zip",
            "last_active": "2024-03-20T15:30:00Z",
            "approved": false,
            "url1": "https://alex-portfolio.com",
            "url2": "https://github.com/alexjohnson"
        }
    ],
    "total_count": 1
}
```

**Frontend Implementation Notes**:
- Display technicians in a card grid layout with responsive design
- Show profile image prominently at the top of each card
- Display skills as tags or chips with a maximum display limit (e.g., show first 5 skills with a "+X more" indicator)
- Show rating as stars with the number of reviews in parentheses
- Add status indicator (Pending/Active/Inactive) with appropriate color coding:
  - Pending: Yellow/Orange
  - Active: Green
  - Inactive: Gray
- **Approval Status Indicator**: Display approval status alongside the general status:
  - Show `approved: true` technicians with a green checkmark or "Approved" badge
  - Show `approved: false` technicians with a yellow warning or "Pending Approval" badge
  - Use the `approved` field to filter technicians in dashboard views
  - Combine with general `status` field for comprehensive filtering (e.g., "Active & Approved", "Pending Approval")
- Include verification badge for technicians with verified identification
- **Profile Completion Indicator**: Display completion percentage as a progress bar or circular progress indicator:
  - Green (90-100%): Fully complete profiles
  - Yellow (70-89%): Nearly complete
  - Red (0-69%): Needs attention
  - **Required Fields for Completion**: The completion percentage includes all required fields:
    - Personal info: phone_number, profile_image, governorate, about, job_title, address, gender, date_of_birth
    - Professional info: years_of_expertise, identification_documents
    - **Portfolio URLs**: Both `url1` and `url2` are required for profile completion
    - Skills: At least one skill set must be added
- **Portfolio URLs Display**: Show both portfolio URLs when available:
  - Display `url1` and `url2` as clickable links in the technician card
  - Use appropriate icons (e.g., globe icon for portfolio, GitHub icon for code repository)
  - Show "No portfolio links" state when both URLs are null/empty
  - Open links in new tabs when clicked
  - Include these URLs in the profile completion calculation (both are required fields)
- **Document Download**: Add a "Download Documents" button when `identification_documents_url` is available:
  - Show download icon next to verification badge
  - Opens document in new tab/downloads file
  - Display "No documents" state when URL is null
- Show last active timestamp in a user-friendly format
- Add action buttons for approving/rejecting technicians
- Add "View Portfolio" button that links to the technician's profile
- **Detailed Profile View**: Access full technician profile details via:
  - URL: `/api/accounts/technician/{public_id}/` (e.g., `/api/accounts/technician/TECH-a4b5c6/`)
  - This endpoint provides complete profile information including all fields
  - Admin users can access all technician profiles regardless of approval status
  - Includes sensitive information like phone numbers, addresses, and wallet details
- Implement filters in a sidebar or top bar:
  - Search input with debouncing
  - Status dropdown
  - **Approval Status Filter**: Add filter option for approved/pending approval status
  - Skill search with autocomplete
  - Rating filter with slider
  - Experience filter with number input
  - Governorate dropdown
  - **Portfolio Completion Filter**: Add filter for technicians with/without portfolio URLs
- Consider implementing infinite scroll or pagination for large lists
- Add sorting options:
  - By rating
  - By experience
  - By application date
  - By last active date
  - **By approval status**: Sort by approved/pending approval
  - **By profile completion**: Sort by completion percentage
- Implement caching strategies:
  - Cache filter results
  - Cache technician cards data
  - Implement periodic refresh for last active status

**Performance Optimization Notes**:
- The API uses optimized database queries with:
  - Proper select_related for user data
  - Prefetch_related for skills and reviews
  - Distinct queries to prevent duplicates
- Frontend should implement:
  - Debounced search
  - Lazy loading of images
  - Virtual scrolling for large lists
  - Client-side caching of filter results