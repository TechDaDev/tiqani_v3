# Notification System API Documentation

## Table of Contents
- [Overview](#overview)
- [API Endpoints](#api-endpoints)
  - [Notification Types](#notification-types)
    - [List Notification Types](#list-notification-types)
    - [Get Notification Type Details](#get-notification-type-details)
  - [Notification Preferences](#notification-preferences)
    - [List User's Preferences](#list-users-preferences)
    - [Create/Update Preference](#createupdate-preference)
    - [Get Preference Details](#get-preference-details)
    - [Update Preference](#update-preference)
    - [Delete Preference](#delete-preference)
    - [Get All Notification Types with Preferences](#get-all-notification-types-with-preferences)
  - [Notifications](#notifications)
    - [List User's Notifications](#list-users-notifications)
    - [Get Notification Details](#get-notification-details)
    - [Mark as Read](#mark-as-read)
    - [Mark All as Read](#mark-all-as-read)
    - [Get Unread Count](#get-unread-count)
  - [Device Tokens](#device-tokens)
    - [List User's Device Tokens](#list-users-device-tokens)
    - [Register Device Token](#register-device-token)
    - [Get Device Token Details](#get-device-token-details)
    - [Update Device Token](#update-device-token)
    - [Delete Device Token](#delete-device-token)
    - [Deactivate Device Token](#deactivate-device-token)
- [Data Models](#data-models)
  - [NotificationType](#notificationtype)
  - [UserNotificationPreference](#usernotificationpreference)
  - [Notification](#notification)
  - [NotificationDeliveryLog](#notificationdeliverylog)
  - [DeviceToken](#devicetoken)
- [Usage Guide](#usage-guide)
  - [Creating Notifications](#creating-notifications)
  - [Managing Notification Types](#managing-notification-types)
  - [Managing User Preferences](#managing-user-preferences)
  - [Handling Different Notification Channels](#handling-different-notification-channels)
- [Integration with Other Systems](#integration-with-other-systems)
  - [Authentication Integration](#authentication-integration)
  - [Contracts Integration](#contracts-integration)
  - [Payments Integration](#payments-integration)
  - [Chat Integration](#chat-integration)
  - [Ratings Integration](#ratings-integration)
- [User Type-Specific Notifications](#user-type-specific-notifications)
  - [Client Notifications](#client-notifications)
  - [Technician Notifications](#technician-notifications)
  - [Dealership Notifications](#dealership-notifications)
- [Frontend Implementation Notes](#frontend-implementation-notes)
  - [Notification Display](#notification-display)
  - [Preference Management UI](#preference-management-ui)
  - [Push Notification Setup](#push-notification-setup)
- [System Configuration](#system-configuration)
  - [Default Notification Types](#default-notification-types)
  - [Template System](#template-system)
  - [Quiet Hours](#quiet-hours)
- [Testing Guide](#testing-guide)
  - [Testing Notification Creation](#testing-notification-creation)
  - [Testing Delivery Channels](#testing-delivery-channels)
  - [Testing User Preferences](#testing-user-preferences)
- [Security Considerations](#security-considerations)
  - [Data Privacy](#data-privacy)
  - [Authentication and Authorization](#authentication-and-authorization)
  - [Rate Limiting](#rate-limiting)
- [Current Implementation Status](#current-implementation-status)
- [Admin Interface](#admin-interface)
- [Future Enhancements](#future-enhancements)

## Overview

The Notification System is a flexible, multi-channel notification infrastructure designed to support in-app, email, and push notifications for the Tiqani platform. It provides comprehensive functionality for creating, managing, and delivering notifications to users across different channels based on their preferences.

### Key Features

- **Multi-channel Support**: Send notifications via in-app, email, and push channels
- **User Preferences**: Allow users to configure their notification preferences per notification type
- **Templating System**: Flexible template-based notification content
- **Quiet Hours**: Support for user-defined quiet hours
- **Delivery Tracking**: Comprehensive logging of notification delivery attempts
- **Device Management**: Support for multiple devices per user for push notifications

## API Endpoints

### Notification Types

#### List Notification Types
- **URL**: `/api/notification/types/`
- **Method**: `GET`
- **Description**: List all active notification types
- **Authentication**: Required
- **Query Parameters**:
  - `category` (optional): Filter notification types by category
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "code": "string",
    "name": "string",
    "description": "string",
    "category": "string",
    "icon": "string",
    "color": "string",
    "is_active": "boolean",
    "default_email": "boolean",
    "default_push": "boolean",
    "default_in_app": "boolean"
  }
]
```
- **Frontend Notes**:
  - Use this endpoint to display available notification types to the user
  - Group notification types by category for easier navigation
  - Use the icon and color fields for visual representation
  - Show default channel settings for user reference

#### Get Notification Type Details
- **URL**: `/api/notification/types/{id}/`
- **Method**: `GET`
- **Description**: Get details for a specific notification type
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
  "id": "uuid",
  "code": "string",
  "name": "string",
  "description": "string",
  "category": "string",
  "icon": "string",
  "color": "string",
  "is_active": "boolean",
  "default_email": "boolean",
  "default_push": "boolean",
  "default_in_app": "boolean"
}
```
- **Frontend Notes**:
  - Use this endpoint to show detailed information about a specific notification type
  - Display description prominently to help users understand the notification purpose
  - Show default channel settings with appropriate visual indicators

### Notification Preferences

#### List User's Preferences
- **URL**: `/api/notification/preferences/`
- **Method**: `GET`
- **Description**: List all notification preferences for the authenticated user
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "notification_type": {
      "id": "uuid",
      "code": "string",
      "name": "string",
      "description": "string",
      "category": "string",
      "icon": "string",
      "color": "string",
      "is_active": "boolean",
      "default_email": "boolean",
      "default_push": "boolean",
      "default_in_app": "boolean"
    },
    "email_enabled": "boolean",
    "push_enabled": "boolean",
    "in_app_enabled": "boolean",
    "quiet_hours_start": "time|null",
    "quiet_hours_end": "time|null",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```
- **Frontend Notes**:
  - Display preferences grouped by notification type category
  - Use toggle switches for each channel preference
  - Implement time pickers for quiet hours
  - Show helpful tooltips explaining each preference option

#### Create/Update Preference
- **URL**: `/api/notification/preferences/`
- **Method**: `POST`
- **Description**: Create or update a notification preference
- **Authentication**: Required
- **Request Body**:
```json
{
  "notification_type_id": "uuid",
  "email_enabled": "boolean",
  "push_enabled": "boolean",
  "in_app_enabled": "boolean",
  "quiet_hours_start": "time|null",
  "quiet_hours_end": "time|null"
}
```
- **Response**:
  - Success (201):
```json
{
  "id": "uuid",
  "notification_type": {
    "id": "uuid",
    "code": "string",
    "name": "string",
    "description": "string",
    "category": "string",
    "icon": "string",
    "color": "string",
    "is_active": "boolean",
    "default_email": "boolean",
    "default_push": "boolean",
    "default_in_app": "boolean"
  },
  "email_enabled": "boolean",
  "push_enabled": "boolean",
  "in_app_enabled": "boolean",
  "quiet_hours_start": "time|null",
  "quiet_hours_end": "time|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```
- **Frontend Notes**:
  - Use this endpoint to create new preferences or update existing ones
  - Implement form validation for time fields
  - Show success message after saving
  - Update the UI immediately after successful save

#### Get Preference Details
- **URL**: `/api/notification/preferences/{id}/`
- **Method**: `GET`
- **Description**: Get details for a specific notification preference
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
  "id": "uuid",
  "notification_type": {
    "id": "uuid",
    "code": "string",
    "name": "string",
    "description": "string",
    "category": "string",
    "icon": "string",
    "color": "string",
    "is_active": "boolean",
    "default_email": "boolean",
    "default_push": "boolean",
    "default_in_app": "boolean"
  },
  "email_enabled": "boolean",
  "push_enabled": "boolean",
  "in_app_enabled": "boolean",
  "quiet_hours_start": "time|null",
  "quiet_hours_end": "time|null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### Update Preference
- **URL**: `/api/notification/preferences/{id}/`
- **Method**: `PUT`/`PATCH`
- **Description**: Update a notification preference
- **Authentication**: Required
- **Request Body**:
```json
{
  "email_enabled": "boolean",
  "push_enabled": "boolean",
  "in_app_enabled": "boolean",
  "quiet_hours_start": "time|null",
  "quiet_hours_end": "time|null"
}
```
- **Response**:
  - Success (200): Updated preference object

#### Delete Preference
- **URL**: `/api/notification/preferences/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a notification preference (resets to defaults)
- **Authentication**: Required
- **Response**:
  - Success (204): No content

#### Get All Notification Types with Preferences
- **URL**: `/api/notification/preferences/notification_types/`
- **Method**: `GET`
- **Description**: Get all notification types with the user's preferences
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "notification_type": {
      "id": "uuid",
      "code": "string",
      "name": "string",
      "description": "string",
      "category": "string",
      "icon": "string",
      "color": "string",
      "is_active": "boolean",
      "default_email": "boolean",
      "default_push": "boolean",
      "default_in_app": "boolean"
    },
    "email_enabled": "boolean",
    "push_enabled": "boolean",
    "in_app_enabled": "boolean",
    "quiet_hours_start": "time|null",
    "quiet_hours_end": "time|null",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```
- **Frontend Notes**:
  - This endpoint is ideal for building the notification settings page
  - It returns all notification types with the user's preferences (created on-demand if they don't exist)
  - Group results by category for better organization
  - Implement bulk update functionality if needed

### Notifications

#### List User's Notifications
- **URL**: `/api/notification/notifications/`
- **Method**: `GET`
- **Description**: List all notifications for the authenticated user
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "notification_type": {
      "id": "uuid",
      "code": "string",
      "name": "string",
      "category": "string",
      "icon": "string",
      "color": "string"
    },
    "title": "string",
    "content": "string",
    "status": "pending|delivered|read|failed|cancelled",
    "is_read": "boolean",
    "created_at": "datetime",
    "delivered_at": "datetime|null",
    "read_at": "datetime|null",
    "action_url": "string",
    "metadata": "json|null",
    "related_object": {
      "type": "string",
      "id": "string"
    }
  }
]
```
- **Frontend Notes**:
  - Display notifications in a list or feed format
  - Use the icon and color from notification_type for visual styling
  - Highlight unread notifications
  - Implement click handling to navigate using action_url
  - Add appropriate timestamps/date formatting
  - Consider implementing infinite scroll or pagination for large lists

#### Get Notification Details
- **URL**: `/api/notification/notifications/{id}/`
- **Method**: `GET`
- **Description**: Get details for a specific notification
- **Authentication**: Required
- **Response**:
  - Success (200): Same as List response for a single notification

#### Mark as Read
- **URL**: `/api/notification/notifications/{id}/mark_as_read/`
- **Method**: `PATCH`
- **Description**: Mark a notification as read
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
  "status": "success"
}
```
- **Frontend Notes**:
  - Update UI immediately after marking as read
  - Update notification counter/badge
  - Consider adding visual feedback for the read status change

#### Mark All as Read
- **URL**: `/api/notification/notifications/mark_all_as_read/`
- **Method**: `POST`
- **Description**: Mark all or filtered notifications as read
- **Authentication**: Required
- **Request Body**:
```json
{
  "before": "datetime|null",
  "notification_type_id": "uuid|null"
}
```
- **Response**:
  - Success (200):
```json
{
  "status": "success",
  "count": "integer"
}
```
- **Frontend Notes**:
  - Provide a "Mark All as Read" button
  - Consider adding confirmation dialog for this action
  - Update UI immediately after success
  - Show success message with count of affected notifications

#### Get Unread Count
- **URL**: `/api/notification/notifications/unread_count/`
- **Method**: `GET`
- **Description**: Get count of unread notifications
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
{
  "count": "integer"
}
```
- **Frontend Notes**:
  - Use this to display notification badges/counters
  - Poll this endpoint periodically to keep count updated
  - Consider implementing WebSockets for real-time updates

### Device Tokens

#### List User's Device Tokens
- **URL**: `/api/notification/devices/`
- **Method**: `GET`
- **Description**: List all device tokens for the authenticated user
- **Authentication**: Required
- **Response**:
  - Success (200):
```json
[
  {
    "id": "uuid",
    "token": "string",
    "device_type": "ios|android|web",
    "device_name": "string",
    "is_active": "boolean",
    "last_used_at": "datetime",
    "created_at": "datetime"
  }
]
```
- **Frontend Notes**:
  - Display registered devices in user settings
  - Show device type with appropriate icons
  - Allow user to manage their devices
  - Display last activity timestamp

#### Register Device Token
- **URL**: `/api/notification/devices/`
- **Method**: `POST`
- **Description**: Register a new device token or update existing one
- **Authentication**: Required
- **Request Body**:
```json
{
  "token": "string",
  "device_type": "ios|android|web",
  "device_name": "string",
  "is_active": "boolean"
}
```
- **Response**:
  - Success (201):
```json
{
  "id": "uuid",
  "token": "string",
  "device_type": "ios|android|web",
  "device_name": "string",
  "is_active": "boolean",
  "last_used_at": "datetime",
  "created_at": "datetime"
}
```
- **Frontend Notes**:
  - Register device token when user enables push notifications
  - Auto-detect device type when possible
  - Use user-friendly device name (e.g., "My iPhone 13")
  - Handle permission requests appropriately

#### Get Device Token Details
- **URL**: `/api/notification/devices/{id}/`
- **Method**: `GET`
- **Description**: Get details for a specific device token
- **Authentication**: Required
- **Response**:
  - Success (200): Device token object

#### Update Device Token
- **URL**: `/api/notification/devices/{id}/`
- **Method**: `PUT`/`PATCH`
- **Description**: Update a device token
- **Authentication**: Required
- **Request Body**:
```json
{
  "device_name": "string",
  "is_active": "boolean"
}
```
- **Response**:
  - Success (200): Updated device token object

#### Delete Device Token
- **URL**: `/api/notification/devices/{id}/`
- **Method**: `DELETE`
- **Description**: Delete a device token
- **Authentication**: Required
- **Response**:
  - Success (204): No content

#### Deactivate Device Token
- **URL**: `/api/notification/devices/{id}/deactivate/`
- **Method**: `DELETE`
- **Description**: Deactivate a device token instead of deleting it
- **Authentication**: Required
- **Response**:
  - Success (204): No content
- **Frontend Notes**:
  - Prefer deactivation over deletion for audit/history purposes
  - Update UI to reflect deactivated status
  - Allow reactivation if needed

## Data Models

### NotificationType

Defines the types of notifications available in the system.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| code | String | Unique identifier code |
| name | String | Human-readable name |
| description | Text | Description of when this notification is triggered |
| email_subject_template | String | Template for email subject |
| email_body_template | Text | Template for email body |
| push_title_template | String | Template for push notification title |
| push_body_template | Text | Template for push notification body |
| in_app_title_template | String | Template for in-app notification title |
| in_app_body_template | Text | Template for in-app notification body |
| icon | String | Icon identifier for the notification |
| color | String | Color code for the notification |
| is_active | Boolean | Whether this notification type is active |
| category | String | Category for grouping notifications |
| default_email | Boolean | Whether to send email by default |
| default_push | Boolean | Whether to send push notification by default |
| default_in_app | Boolean | Whether to create in-app notification by default |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### UserNotificationPreference

Stores user preferences for notifications.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user | ForeignKey | Reference to User |
| notification_type | ForeignKey | Reference to NotificationType |
| email_enabled | Boolean | Whether to send email notifications |
| push_enabled | Boolean | Whether to send push notifications |
| in_app_enabled | Boolean | Whether to show in-app notifications |
| quiet_hours_start | Time | Start time for quiet hours (optional) |
| quiet_hours_end | Time | End time for quiet hours (optional) |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Last update timestamp |

### Notification

The actual notification instances sent to users.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user | ForeignKey | Reference to User |
| notification_type | ForeignKey | Reference to NotificationType |
| title | String | Notification title |
| content | Text | Notification content |
| status | String | Status (pending, delivered, read, failed, cancelled) |
| is_read | Boolean | Whether the notification has been read |
| created_at | DateTime | Creation timestamp |
| delivered_at | DateTime | When the notification was delivered (optional) |
| read_at | DateTime | When the notification was read (optional) |
| content_type | ForeignKey | Content type for generic relation (optional) |
| object_id | String | Object ID for generic relation (optional) |
| metadata | JSON | Additional context data (optional) |
| action_url | String | URL to navigate to when clicked (optional) |
| sent_email | Boolean | Whether email was sent |
| sent_push | Boolean | Whether push notification was sent |

### NotificationDeliveryLog

Tracks notification delivery attempts.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| notification | ForeignKey | Reference to Notification |
| channel | String | Delivery channel (email, push, in_app) |
| status | String | Delivery status (success, failure) |
| timestamp | DateTime | When the delivery attempt was made |
| error_message | Text | Error details for failed deliveries (optional) |
| attempts | Integer | Number of delivery attempts |

### DeviceToken

Stores device tokens for push notifications.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user | ForeignKey | Reference to User |
| token | Text | Device token for push notifications |
| device_type | String | Device type (ios, android, web) |
| device_name | String | User-friendly device name (optional) |
| is_active | Boolean | Whether the device is active |
| last_used_at | DateTime | When the token was last used |
| created_at | DateTime | Creation timestamp |

## Usage Guide

### Creating Notifications

Notifications can be created using the `create_notification` utility function:

```python
from notification.utils import create_notification

create_notification(
    user_id=user.id,
    notification_type_code='payment_received',
    context_data={
        'amount': '500,000',
        'currency': 'IQD',
    },
    related_object=payment_obj,
    action_url='/payments/123/',
    send_immediately=True
)
```

The function handles:
- Checking user preferences
- Respecting quiet hours
- Rendering templates with context data
- Sending via appropriate channels

#### Parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | Integer | The ID of the user to notify |
| notification_type_code | String | Code of the notification type |
| context_data | Dict | Template context data (optional) |
| related_object | Model | Related object for the notification (optional) |
| action_url | String | URL to direct user when clicked (optional) |
| send_immediately | Boolean | Whether to send notification immediately (default: True) |

### Managing Notification Types

The system includes a management command to initialize default notification types:

```bash
python manage.py init_notification_types
```

This creates a set of default notification types for various system events.

To create custom notification types programmatically:

```python
from notification.models import NotificationType

notification_type = NotificationType.objects.create(
    code='custom_notification',
    name='Custom Notification',
    description='Description of when this notification is triggered',
    category='custom',
    email_subject_template='Custom email subject with {{ variable }}',
    email_body_template='Custom email body with {{ variable }}',
    push_title_template='Custom push title with {{ variable }}',
    push_body_template='Custom push body with {{ variable }}',
    in_app_title_template='Custom in-app title with {{ variable }}',
    in_app_body_template='Custom in-app body with {{ variable }}',
    icon='custom-icon',
    color='#FF5733',
    default_email=True,
    default_push=True,
    default_in_app=True
)
```

### Managing User Preferences

When a user is created, default notification preferences are automatically created for all active notification types. Similarly, when a new notification type is created, preferences are created for all existing users.

To update user preferences programmatically:

```python
from notification.models import UserNotificationPreference, NotificationType

# Get notification type
notification_type = NotificationType.objects.get(code='payment_received')

# Update or create preference
preference, created = UserNotificationPreference.objects.update_or_create(
    user=user,
    notification_type=notification_type,
    defaults={
        'email_enabled': True,
        'push_enabled': False,
        'in_app_enabled': True,
        'quiet_hours_start': '22:00:00',
        'quiet_hours_end': '08:00:00'
    }
)
```

### Handling Different Notification Channels

The notification system supports three channels:

1. **In-App Notifications**: Stored in the database and displayed in the application interface
2. **Email Notifications**: Sent via email (using Django's email backend)
3. **Push Notifications**: Sent to registered device tokens

Each channel has its own templates and delivery mechanism:

```python
# Manually sending via specific channels
from notification.utils import send_email_notification, send_push_notification

# Get an existing notification
notification = Notification.objects.get(id='uuid')

# Send via email
send_email_notification(notification)

# Send via push notification
send_push_notification(notification)
```

## Integration with Other Systems

The notification system integrates with other parts of the Tiqani platform:

### Authentication Integration

- **Welcome Notification**: Sent when a user creates a new account
  ```python
  # Example code for sending welcome notification
  from notification.utils import create_notification
  
  def send_welcome_notification(user):
      create_notification(
          user_id=user.id,
          notification_type_code='auth_welcome',
          context_data={
              'user_name': user.first_name,
              'user_type': get_user_type(user)  # Function to determine user type
          },
          action_url='/dashboard/'
      )
  ```

- **Password Reset**: Sent when a user requests a password reset
  ```python
  # Example code for sending password reset notification
  def send_password_reset_notification(user, reset_token):
      create_notification(
          user_id=user.id,
          notification_type_code='auth_password_reset',
          context_data={
              'user_name': user.first_name,
              'reset_link': f'/reset-password/{reset_token}/'
          },
          action_url=f'/reset-password/{reset_token}/'
      )
  ```

### Contracts Integration

- **New Contract**: Sent when a new contract is created
  ```python
  # Example code for sending new contract notification
  def notify_new_contract(contract):
      # Notify technician about new contract request
      create_notification(
          user_id=contract.technician.user.id,
          notification_type_code='contract_new',
          context_data={
              'client_name': contract.client.user.get_full_name(),
              'contract_title': contract.title,
              'contract_amount': str(contract.total_amount)
          },
          related_object=contract,
          action_url=f'/contracts/{contract.id}/'
      )
  ```

## User Type-Specific Notifications

The notification system supports different notification types and templates for each user type in the platform: client, technician, and dealership.

### Client Notifications

Client users receive notifications about:
- Technician responses to their service requests
- Contract status updates
- Payment confirmations
- Review reminders after service completion
- Chat messages from technicians
- System announcements

**Example**: When a technician accepts a client's contract request, the client receives a notification with a link to view the accepted contract.

### Technician Notifications

Technician users receive notifications about:
- New service requests in their area
- Client contract approvals or rejections
- Payment received notifications
- Review notifications when clients leave reviews
- Chat messages from clients
- System announcements

**Example**: When a client approves a completed milestone, the technician receives a notification about the payment being processed.

### Dealership Notifications

Dealership users receive notifications about:
- Payment processing requests
- Transaction status updates
- Withdrawal requests from technicians
- System announcements
- Administrative alerts

**Example**: When a technician requests a withdrawal, the dealership receives a notification to process the payment.

## Frontend Implementation Notes

### Notification Display

1. **Notification Center**: Implement a dropdown or sidebar notification center
   - Show list of recent notifications sorted by date
   - Highlight unread notifications
   - Show notification type icon and color
   - Display relative timestamps (e.g., "2 hours ago")
   - Include action buttons for each notification

2. **Notification Badges**: Display unread count in the UI
   - Poll the unread count endpoint periodically
   - Update badge in real-time
   - Clear badge when notifications are read

3. **Detail View**: When a notification is clicked:
   - Mark it as read automatically
   - Navigate to the related content using action_url
   - Show full notification details if needed

### Preference Management UI

1. **Settings Page**: Create a dedicated notification settings page
   - Group preferences by category
   - Use toggles for each notification channel
   - Implement time pickers for quiet hours
   - Show notification type descriptions
   - Allow bulk actions (enable/disable all)

2. **Quick Settings**: Consider adding quick preference toggles
   - Allow quick muting of specific notification types
   - Provide temporary "Do Not Disturb" mode
   - Remember user preferences across sessions

### Push Notification Setup

1. **Permission Request**: Request permission to send push notifications
   - Show clear explanation of benefits
   - Handle permission denial gracefully
   - Provide option to enable later

2. **Device Registration**: Register device token with backend
   - Auto-detect device type
   - Generate friendly device name
   - Handle token refreshes

3. **Service Worker**: Set up service worker for web push notifications
   - Handle notification clicks
   - Display notification even when app is closed
   - Support offline notifications

## System Configuration

### Default Notification Types

The system comes pre-configured with the following notification types:

| Category | Code | Name | Description |
|----------|------|------|-------------|
| authentication | auth_welcome | Welcome | Sent when a user creates a new account |
| authentication | auth_password_reset | Password Reset | Sent when a user requests a password reset |
| contracts | contract_new | New Contract | Sent when a new contract is created |
| contracts | contract_accepted | Contract Accepted | Sent when a contract is accepted |
| contracts | contract_rejected | Contract Rejected | Sent when a contract is rejected |
| contracts | contract_milestone_completed | Milestone Completed | Sent when a milestone is completed |
| payments | payment_received | Payment Received | Sent when a payment is received |
| payments | payment_sent | Payment Sent | Sent when a payment is sent |
| payments | payment_withdrawal_ready | Withdrawal Ready | Sent when a withdrawal is ready for pickup |
| chat | chat_new_message | New Message | Sent when a new chat message is received |
| ratings | rating_received | New Rating | Sent when a new rating is received |
| profile | technician_approved | Profile Approved | Sent when a technician profile is approved by admin |
| profile | technician_rejected | Profile Rejected | Sent when a technician profile is rejected by admin |
| system | system_announcement | System Announcement | Sent for system-wide announcements |

### Template System

Notification templates support Django template language syntax:

- **Variables**: Use `{{ variable_name }}` to insert dynamic content
- **Conditionals**: Use `{% if condition %}...{% endif %}` for conditional content
- **Filters**: Use `{{ variable|filter }}` to format content

Example email template:
```
Hello {{ user.first_name }},

You have received a payment of {{ amount }} {{ currency }}.

{% if sender %}
The payment was sent by {{ sender.username }}.
{% endif %}

Best regards,
The Tiqani Team
```

### Quiet Hours

Users can set quiet hours during which no push notifications or emails will be sent:

- **Start Time**: Time when quiet hours begin (e.g., 22:00)
- **End Time**: Time when quiet hours end (e.g., 08:00)

Notifications created during quiet hours are still stored but delayed until quiet hours end.

## Testing Guide

### Testing Notification Creation

To test notification creation:

1. **Django Management Command**
   ```bash
   python manage.py test_notification --user_id=1 --type=auth_welcome
   ```

2. **Using Django Shell**
   ```python
   from notification.utils import create_notification
   
   # Create a test notification
   notification = create_notification(
       user_id=1,  # Replace with an actual user ID
       notification_type_code='auth_welcome',
       context_data={'user_name': 'Test User'},
       action_url='/dashboard/'
   )
   ```

### Testing Delivery Channels

To test the different delivery channels:

1. **In-App Notifications**: Access the notifications endpoint to verify in-app notifications:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/notification/notifications/
   ```

2. **Email Notifications**: Currently, email sending is implemented as a placeholder. Check the server logs to see if the email notification was logged:
   ```bash
   tail -f debug.log | grep "Would send email"
   ```

3. **Push Notifications**: Currently, push notifications are implemented as a placeholder. Check the server logs:
   ```bash
   tail -f debug.log | grep "Would send push notification"
   ```

## Security Considerations

### Data Privacy

- **Sensitive Information**: The notification system is designed to never include sensitive information like passwords, authentication tokens, or personal identity information in notifications.
- **Data Retention**: Notifications are stored in the database and should be cleaned up periodically. Consider implementing a data retention policy.

### Authentication and Authorization

- All notification API endpoints require authentication
- Users can only access their own notifications
- Device token management is restricted to the owner
- Notification preferences are user-specific and cannot be accessed by other users

### Rate Limiting

Consider implementing rate limiting for notification-related endpoints:

```python
# Example rate limiting configuration
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/day',  # General user rate limit
        'notification_creation': '10/minute',  # Limit for creating notifications
        'notification_marking': '60/minute',  # Limit for marking notifications as read
    }
}
```

## Current Implementation Status

The notification system is currently implemented with the following status:

1. **In-App Notifications**: ✅ Fully implemented and functional
2. **Email Notifications**: ⚠️ Partially implemented (placeholder only)
   - The system currently logs what would be sent, but does not actually send emails
   - To enable, implement the email sending logic in `utils.py`
3. **Push Notifications**: ⚠️ Partially implemented (placeholder only)
   - The system supports registering device tokens
   - Actual push notification delivery needs to be implemented using Firebase, OneSignal, or similar

**Next Steps for Full Implementation**:
1. Implement actual email sending in the `send_email_notification` function
2. Integrate with a push notification service like Firebase Cloud Messaging
3. Add background workers for asynchronous notification processing

## Admin Interface

The notification system includes a comprehensive Django admin interface for system management and monitoring:

### Notification Types Management
- **List View Features**:
  - Display: name, code, category, active status, creation date
  - Filtering: by category and active status
  - Search: by name, code, and description
- **Detail View Sections**:
  - Basic Information: code, name, description, category, active status
  - Email Templates: subject and body templates, default email setting
  - Push Notification Templates: title and body templates, default push setting
  - In-App Notification Templates: title and body templates, default in-app setting
  - Styling: icon and color settings

### User Notification Preferences
- **List View Features**:
  - Display: user, notification type, enabled channels (email, push, in-app)
  - Filtering: by enabled channels
  - Search: by username, email, notification type name
- **Quick Actions**: Enable/disable channels for multiple preferences
- **User-specific Views**: Filter preferences by user

### Notifications Monitor
- **List View Features**:
  - Display: title, user, notification type, status, read status, creation date
  - Filtering: by status, read status, delivery channels, creation date
  - Search: by title, content, username, email
- **Detail View Sections**:
  - Basic Information: user, type, title, content
  - Status Information: status, read status, timestamps
  - Related Object Details: linked content and action URL
  - Delivery Channel Status: email and push notification status
  - Additional Data: metadata and context
- **Inline Delivery Logs**: View delivery attempts and status
- **Admin Actions**:
  - Mark notifications as read
  - Mark notifications as delivered
  - View delivery history

### Notification Delivery Logs
- **List View Features**:
  - Display: notification, channel, status, attempts, timestamp
  - Filtering: by channel, status, timestamp
  - Search: by notification details and error messages
- **Monitoring Features**:
  - Track delivery success/failure rates
  - Monitor delivery attempts
  - Debug delivery issues
  - View error messages for failed deliveries

### Device Token Management
- **List View Features**:
  - Display: user, device type, token status, last used date
  - Filtering: by device type and active status
  - Search: by user and device details
- **Token Operations**:
  - Activate/deactivate tokens
  - View token usage history
  - Monitor device registrations

### Best Practices for Admin Usage
1. **Notification Types**:
   - Review templates before activation
   - Test new notification types in development
   - Monitor usage patterns

2. **User Preferences**:
   - Respect user channel preferences
   - Monitor opt-out patterns
   - Review quiet hours settings

3. **Delivery Monitoring**:
   - Regular review of delivery logs
   - Track failure patterns
   - Monitor channel performance

4. **Security**:
   - Regular token cleanup
   - Monitor suspicious patterns
   - Review access logs

## Future Enhancements

Potential areas for future enhancement:

1. **Third-party Integration**: Integration with popular notification services
   - Firebase Cloud Messaging (FCM) for push notifications
   - SendGrid or Mailgun for transactional emails
   - OneSignal for cross-platform push notifications

2. **Rich Content**: Support for rich content in notifications
   - Images and media content
   - Interactive action buttons
   - Rich formatting options
   - Interactive elements

3. **Advanced Targeting**: Enhanced user targeting capabilities
   - User segmentation for system announcements
   - Behavior-based notifications
   - Location-based notifications
   - Language and locale support

4. **Analytics**: Notification engagement analytics
   - Open and click-through rates
   - Conversion tracking
   - User engagement metrics
   - Channel effectiveness comparison

5. **A/B Testing**: Testing different notification strategies
   - Content variations
   - Timing optimization
   - Channel preference analysis
   - Automated optimization based on engagement 