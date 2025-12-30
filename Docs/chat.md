# Chat API Documentation

## Table of Contents
- [Overview](#overview)
- [WebSocket Connection](#websocket-connection)
  - [Connect to Chat Room](#connect-to-chat-room)
  - [Global Overview Socket](#global-overview-socket)
- [Message Types](#message-types)
  - [Text Message](#1-text-message)
  - [File Message](#2-file-message)
  - [Typing Status](#3-typing-status)
  - [Edit Message](#4-edit-message)
  - [Read Status](#5-read-status)
  - [Chat Room Update](#6-chat-room-update)
- [Data Models](#data-models)
  - [Chat Room](#chat-room)
  - [Chat Message](#chat-message)
  - [Message Read Status](#message-read-status)
- [Features](#features)
  - [Real-time Communication](#1-real-time-communication)
  - [File Sharing](#2-file-sharing)
  - [Message Persistence](#3-message-persistence)
  - [Room Management](#4-room-management)
  - [Security](#5-security)
  - [Message Editing](#6-message-editing)
  - [Rate Limiting](#7-rate-limiting)
- [WebSocket Events](#websocket-events)
  - [Connection](#1-connection)
  - [Message Handling](#2-message-handling)
  - [Disconnection](#3-disconnection)
- [Implementation Notes](#implementation-notes)
  - [Room Names](#1-room-names)
  - [File Handling](#2-file-handling)
  - [Error Handling](#3-error-handling)
  - [WebSocket Connection on Heroku](#4-websocket-connection-on-heroku)
  - [Deployment Considerations](#5-deployment-considerations)
- [User Type Specific Implementation](#user-type-specific-implementation)
  - [Client Frontend Implementation](#client-frontend-implementation)
  - [Technician Frontend Implementation](#technician-frontend-implementation)
  - [Shared Features (Both User Types)](#shared-features-both-user-types)
  - [Technician-Specific UI Components](#technician-specific-ui-components)
- [API Endpoints](#api-endpoints)
  - [Chat Room List API](#chat-room-list-api)
  - [Chat Room Creation API](#chat-room-creation-api)
  - [Chat Room Detail API](#chat-room-detail-api)

## Overview
The chat system provides real-time communication between clients and technicians using WebSocket connections. It supports text messages, file sharing, typing indicators, and message editing capabilities.

## WebSocket Connection

### Connect to Chat Room
- **URL**: `ws://domain/ws/chat/<room_name>/`
- **Description**: Establish WebSocket connection to a specific chat room
- **Authentication**: Required
- **Parameters**:
  - `room_name`: The unique identifier of the chat room (room ID)
- **Frontend Notes**:
  - Connect using the WebSocket API or a library like socket.io, ReconnectingWebSocket, or SockJS
  - Store the room ID in application state after loading the chat interface
  - Implement automatic reconnection if connection drops
  - Handle authentication with JWT tokens in WebSocket handshake
  - Display loading/connecting states during connection setup
  - When "Contact Technician" button is clicked on technician profile, create a chat room by:
    1. Call POST to `/api/chat/rooms/create/` with `technician_id` (supports both UUID format and "TECH-{id}" format)
    2. Use the returned room ID to establish WebSocket connection
    3. Navigate to chat interface

### Global Overview Socket
- **URL**: `ws://domain/ws/chat/overview/`
- **Description**: Opens a single WebSocket (per logged-in user) that delivers real-time updates for **all** chat rooms – e.g. new last-message preview, unread counters, or participant presence.
- **Authentication**: Required (JWT access token query parameter `?token=<access_token>`)
- **Frontend Notes**:
  - Establish this connection right after the user logs in and keep it alive across the app lifecycle.
  - Listen for `chat_room_update` events and merge the `room` payload into your local store/cache so the sidebar refreshes instantly (no polling needed).
  - This socket is currently read-only – the client does not need to send any messages on it.

## Message Types

### 1. Text Message
- **Send Message**:
```json
{
    "type": "message",
    "message": "string"
}
```
- **Receive Message**:
```json
{
    "type": "message",
    "message_id": "integer",
    "message": "string",
    "sender": "string",
    "file_url": null,
    "timestamp": "ISO datetime string"
}
```
- **Frontend Notes**:
  - Implement message input with character limit (max 1000 characters)
  - Display messages in chat bubbles with sender name and timestamp
  - Different styles for client vs technician messages:
    ```javascript
    // Example: Determine message sender type
    const isSenderTechnician = (message, room) => {
        return message.sender.id === room.technician.user.id;
    };

    // Example: Message component with sender identification
    const MessageBubble = ({ message, room }) => {
        const isTechnician = isSenderTechnician(message, room);
        return (
            <div className={`message ${isTechnician ? 'technician-message' : 'client-message'}`}>
                <div className="sender-info">
                    <img src={message.sender.profile_image} alt={message.sender.first_name} />
                    <span className="sender-type">
                        {isTechnician ? '👨‍🔧 Technician' : '👤 Client'}
                    </span>
                    <span className="sender-name">
                        {`${message.sender.first_name} ${message.sender.last_name}`}
                    </span>
                </div>
                <div className="message-content">{message.message}</div>
            </div>
        );
    };
    ```
  - Show loading/sending indicator until message is acknowledged
  - Store messages in local state for immediate display
  - Handle errors from rate limiting or validation
  - Display sender's profile image alongside their messages

### 2. File Message
- **Send File**:
```json
{
    "type": "message",
    "file_data": "data:mimetype/extension;base64,base64EncodedData",
    "message": "string" // Optional message with the file
}
```
- **Receive File Message**:
```json
{
    "type": "message",
    "message_id": "integer",
    "message": "string or null",
    "sender": "string",
    "file_url": "string", // URL to access the uploaded file
    "timestamp": "ISO datetime string"
}
```
- **Frontend Notes**:
  - Implement file selector or drag-and-drop interface
  - Show preview of files before sending
  - Display upload progress indicator
  - Validate file type and size before sending (max 10MB)
  - Render file attachments based on type (image, document, etc.)
  - Include thumbnails for image files
  - Add download buttons for files

### 3. Typing Status
- **Send Typing Status**:
```json
{
    "type": "typing",
    "is_typing": true/false
}
```
- **Receive Typing Status**:
```json
{
    "type": "typing",
    "user": "string", // username of person typing
    "is_typing": true/false
}
```
- **Frontend Notes**:
  - Send typing=true when user starts typing
  - Send typing=false when user stops typing or sends message
  - Add debounce to prevent too many typing events (e.g., 300ms delay)
  - Display "<user> is typing..." message when typing=true
  - Clear typing indicator when typing=false or after timeout

### 4. Edit Message
- **Send Edit Request**:
```json
{
    "type": "edit",
    "message_id": "integer",
    "new_text": "string"
}
```
- **Receive Edited Message**:
```json
{
    "type": "edited",
    "message_id": "integer",
    "new_text": "string",
    "sender": "string",
    "edited_at": "ISO datetime string"
}
```
- **Frontend Notes**:
  - Only allow editing own messages
  - Implement edit UI (e.g., through message context menu)
  - Show edited indicator on messages
  - Disable edit option after 1 hour (message edit time limit)
  - Update message in UI immediately but revert if error occurs
  - Maintain character limit validation (max 1000 characters)

### 5. Read Status
- **Receive Read Status**:
```json
{
    "type": "message_read",
    "message_id": "integer",
    "user_id": "integer",
    "user_name": "string",
    "user_image": "url|null",
    "timestamp": "ISO datetime string"
}
```
- **Frontend Notes**:
  - Read status is sent automatically when a user connects to a chat room
  - All unread messages are marked as read when entering a room
  - Update message UI to show read status (e.g., checkmarks or "read by" list)
  - Display timestamp when message was read in tooltip or info panel
  - Implement read receipts with avatars/names for group chats
  - Consider grouping read statuses to reduce UI clutter
  - Display user profile images in read receipts for visual identification

### 6. Chat Room Update
- **Receive Room Update**:
```json
{
  "type": "chat_room_update",
  "room": {
     "id": 42,
     "last_message": { /* ... */ },
     "unread_count": 3,
     /* same shape as GET /api/chat/rooms/<id>/ */
  }
}
```
- **Triggered When**:
  - A new message is stored in the room.
  - One of the participants reads messages (unread count changes).
  - A participant's presence/online status changes.
- **Frontend Notes**:
  - Merge/replace the incoming `room` object in your cache; update sidebar badges, previews, and presence indicators immediately.

## Data Models

### Chat Room
```json
{
    "id": "integer",
    "client": {
        "id": "integer",
        "username": "string",
        "first_name": "string",
        "last_name": "string",
        "profile_image": "url|null"
    },
    "technician": {
        "id": "uuid",
        "user": {
            "username": "string",
            "first_name": "string",
            "last_name": "string"
        },
        "profile_image": "url|null"
    },
    "created_at": "datetime"
}
```
- **Frontend Notes**:
  - Use room ID for WebSocket connection
  - Display participant information in chat header
  - Show creation date for context if needed
  - Implement access controls based on participant status
  - Display participant profile images in the chat header and message bubbles

### Chat Message
```json
{
    "id": "integer",
    "room": "integer",
    "sender": {
        "id": "integer",
        "username": "string",
        "first_name": "string",
        "last_name": "string",
        "profile_image": "url|null",
        "is_technician": "boolean"  // Determined by checking if sender matches room.technician.user.id
    },
    "message": "string|null",
    "file": "url|null",
    "timestamp": "datetime",
    "edited_at": "datetime|null",
    "read_by": [
        {
            "user": {
                "id": "integer",
                "username": "string",
                "email": "string",
                "first_name": "string",
                "last_name": "string",
                "profile_image": "url|null"
            },
            "read_at": "datetime"
        }
    ]
}
```
- **Frontend Notes**:
  - Store message ID for edit/delete operations
  - Display timestamp in user-friendly format
  - Show edited indicator when edited_at is present
  - Handle both text and file messages in the same UI
  - Implement message status indicators (sent, delivered, read)
  - Use the read_by array to show which users have read the message
  - Display sender's profile image next to their messages
  - Use default avatar placeholders when profile_image is null

### Message Read Status
```json
{
    "message": "integer",
    "user": {
        "id": "integer",
        "username": "string",
        "email": "string",
        "first_name": "string",
        "last_name": "string",
        "profile_image": "url|null"
    },
    "read_at": "datetime"
}
```
- **Frontend Notes**:
  - Use to track which users have read each message
  - Display appropriate read indicators in the UI
  - Consider showing read times for important messages
  - Group read statuses for better UI organization
  - Show small profile images or avatars in read receipts

## Features

### 1. Real-time Communication
- Instant message delivery
- Typing indicators
- Online status (based on connection state)
- **Frontend Notes**:
  - Design chat UI with real-time updates in mind
  - Implement optimistic updates for better UX
  - Show connection status indicator
  - Handle offline/reconnection scenarios gracefully

### 2. File Sharing
- Support for file uploads
- Automatic file storage in 'chat_files/' directory
- File URL sharing in chat
- **Frontend Notes**:
  - Create intuitive file upload UX
  - Support preview for common file types
  - Implement progress indicators for uploads
  - Show error messages for unsupported files
  - Enforce size limitations client-side (max 10MB)

### 3. Message Persistence
- All messages are stored in the database
- Messages include timestamp information
- Support for message history retrieval
- **Frontend Notes**:
  - Implement chat history loading on room entry
  - Create infinite scroll or pagination for message history
  - Store message cache locally for offline viewing
  - Show clear date separators between messages from different days

### 4. Room Management
- Unique rooms for client-technician pairs
- Room creation initiated from technician profile page
- Room history preservation
- **Frontend Notes**:
  - Display "Contact Technician" button on technician profile for initiating chat
  - Create room navigation UI for users with multiple chats
  - Display last message preview in room list
  - Show unread message indicators
  - Implement room switching without page reload
  - Handle room creation and WebSocket connection flow:
    1. User clicks "Contact Technician" on technician profile
    2. Frontend calls POST to `/api/chat/rooms/create/` with technician_id (can be in format "TECH-{id}")
    3. Upon successful response, establish WebSocket connection using returned room ID
    4. Navigate user to chat interface
  - Integration with technician profile:
    ```javascript
    // Example code for "Contact Technician" button handler
    async function contactTechnician(technicianId) {
      try {
        // Create or get chat room
        const response = await fetch('/api/chat/rooms/create/', {
          method: 'POST',
          headers: { 
            'Authorization': 'Bearer ' + authToken, 
            'Content-Type': 'application/json' 
          },
          body: JSON.stringify({ technician_id: technicianId })
        });
        
        if (!response.ok) {
          throw new Error('Failed to create chat room');
        }
        
        const room = await response.json();
        
        // Navigate to chat UI for this room
        navigateTo(`/chat/${room.id}`);
        
        // In chat UI component, establish WebSocket connection
        // const socket = new WebSocket(`ws://domain/ws/chat/${room.id}/?token=${authToken}`);
      } catch (error) {
        console.error('Error creating chat room:', error);
        // Show error notification
      }
    }
    ```

### 5. Security
- Authentication required for WebSocket connections
- Users can only access their own chat rooms
- Secure file storage and access
- **Frontend Notes**:
  - Implement secure token handling
  - Never expose sensitive information in UI
  - Handle authentication errors gracefully
  - Implement timeout/auto-logout features

### 6. Message Editing
- Edit own messages within 1 hour of sending
- Edit history tracking
- Real-time updates of edited messages
- **Frontend Notes**:
  - Show edit UI only for eligible messages
  - Indicate edited status clearly
  - Implement optimistic UI updates for editing
  - Show timestamp of edit when relevant

### 7. Rate Limiting
- Maximum 5 messages per 5-second window
- Prevents message flooding
- Error feedback on rate limit exceeded
- **Frontend Notes**:
  - Implement client-side throttling to prevent rate limit errors
  - Show feedback when rate limit is reached
  - Disable send button briefly after hitting limit
  - Queue messages if user tries to send too quickly

## WebSocket Events

### 1. Connection
- Client connects to specific room
- Server adds client to room group
- Connection confirmation sent
- **Automatic Read Status Update**:
  - All unread messages are automatically marked as read
  - Other participants are notified of read status changes
- **Frontend Notes**:
  - Implement connection status indicators
  - Add retry logic for failed connections
  - Handle gracefully when users don't have access to a room
  - Show appropriate error messages for connection issues
  - Update UI to reflect read status of messages

### 2. Message Handling
- Text messages processed and broadcast to room
- Files uploaded and stored
- File URLs broadcast to room
- **Frontend Notes**:
  - Implement different UI for different message types
  - Handle message delivery status (sent, delivered, read)
  - Show error states for failed messages
  - Allow retrying failed message sends

### 3. Disconnection
- Client disconnects from room
- Server removes client from room group
- Resources cleaned up
- **Frontend Notes**:
  - Detect disconnections and show appropriate UI
  - Implement automatic reconnection attempts
  - Cache unsent messages during disconnection
  - Resume session seamlessly after reconnection

## Implementation Notes

### 1. Room Names
- Room names are derived from the room ID
- Format: `chat_<room_id>`
- Used internally for WebSocket group management
- Frontend should use the numeric room ID when connecting

### 2. File Handling
- Files are uploaded as base64-encoded strings
- Maximum file size: 10MB
- Supported file types: images, documents, PDFs
- Files are stored in media directory with unique names
- URLs are returned for file access after upload

### 3. Error Handling
- Connection errors return appropriate HTTP status codes
- Message validation errors are sent as error messages
- Rate limiting errors include retry-after information
- Authentication failures close the connection with error code

### 4. WebSocket Connection on Heroku
- The WebSocket implementation uses a synchronous approach that doesn't require Redis
- Custom session middleware (`SimpleSessionMiddleware`) provides session functionality without Redis dependency
- `SyncChatConsumer` is used instead of the asynchronous consumer to avoid Redis channel layer requirements
- In-memory channel layer is used for development and production environments
- Authentication is handled through JWT tokens passed as query parameters

### 5. Deployment Considerations
- WebSocket connections require proper proxy configuration on Heroku
- The application uses the `channels` library with custom middleware to handle connections
- SSL termination is handled by Heroku, so WebSocket connections should use `wss://` protocol
- Connection URL format: `wss://your-app-name.herokuapp.com/ws/chat/<room_id>/?token=<jwt_token>`
- No Redis dependency is required for basic WebSocket functionality

## User Type Specific Implementation

### Client Frontend Implementation
- **Primary Use Case**: Initiating conversations with technicians
- **Key Features**:
  - Browse technician profiles and click "Contact Technician" to start chat
  - View list of existing conversations with different technicians
  - Send messages, files, and manage ongoing conversations
- **Integration Points**:
  - Technician profile pages with "Contact Technician" button
  - Client dashboard with chat room list
  - Notification system for new messages from technicians

### Technician Frontend Implementation
- **Primary Use Case**: Responding to client inquiries and managing conversations
- **Key Features**:
  - Receive notifications when clients initiate conversations
  - View list of conversations with different clients
  - Respond to client messages and share files/portfolio items
  - Online status automatically tracked and displayed
  - Last active time shown when offline
- **Online Status Implementation**:
  ```javascript
  // Example: Fetch technician's online status
  const fetchTechnicianStatus = async (technicianId) => {
    const response = await fetch(`/api/accounts/technician/${technicianId}/`);
    const data = await response.json();
    
    if (data.is_online) {
      // Show online indicator (green dot)
      showOnlineStatus();
    } else {
      // Show last seen time
      const lastSeen = new Date(data.last_active);
      showLastSeenStatus(lastSeen);
    }
  };

  // Example: Format last seen time
  const formatLastSeen = (lastActive) => {
    const now = new Date();
    const lastSeen = new Date(lastActive);
    const diffMinutes = Math.floor((now - lastSeen) / 60000);
    
    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes/60)}h ago`;
    return lastSeen.toLocaleDateString();
  };
  ```
- **UI Implementation**:
  - Green dot indicator for online users
  - "Last seen" text for offline users
  - Automatic status refresh every 1-2 minutes
  - Status updates when receiving WebSocket messages
  - Mark conversations as resolved or transfer to other technicians if needed
- **Dashboard Integration**:
  - Chat notification counter in technician dashboard
  - Quick access to recent conversations
  - Integration with contract discussions (link chats to specific contracts)
- **Business Features**:
  - Share portfolio images/documents directly in chat
  - Provide quotes and estimates through chat
  - Schedule appointments or consultations via chat
  - Professional response templates for common inquiries
- **Frontend Notes**:
  - Implement priority indicators for urgent client messages
  - Show client information sidebar (profile, previous contracts, etc.)
  - Add quick action buttons (e.g., "Send Quote", "Schedule Call")
  - Display conversation context (how the client found the technician)
  - Implement availability status (online/offline/busy)
  - **Chat Room Management for Technicians**:
    ```javascript
    // Example: Fetch technician's chat rooms with client details
    const response = await fetch('/api/chat/rooms/', {
      headers: { 'Authorization': 'Bearer ' + authToken }
    });
    const rooms = await response.json();
    
    // Filter and sort for technician dashboard
    const activeChats = rooms.filter(room => 
      room.technician.id === currentTechnicianId
    ).sort((a, b) => 
      new Date(b.last_message?.timestamp || b.created_at) - 
      new Date(a.last_message?.timestamp || a.created_at)
    );
    ```
  - **Notification Handling**:
    ```javascript
    // Listen for new messages in technician dashboard
    socket.onmessage = function(event) {
      const data = JSON.parse(event.data);
      if (data.type === 'chat_message' && data.sender_id !== currentUserId) {
        // Show notification for new client message
        showNotification(`New message from ${data.sender_name}`);
        updateChatList(); // Refresh chat list to show unread indicator
      }
    };
    ```

### Shared Features (Both User Types)
- Real-time messaging with typing indicators
- File sharing and image preview
- Message editing and read receipts
- Conversation history and search
- Mobile-responsive chat interface
- Online status indicators:
  - Automatically tracked by backend (`last_active` field)
  - Updated through middleware on each request
  - Shows "online" if active in last 5 minutes
  - Shows "last seen" time when offline
  - Available through technician profile API endpoint

### Technician-Specific UI Components
- **Chat List View**:
  - Display client name, profile image, and last message preview
  - Show unread message count for each conversation
  - Highlight urgent or new conversations
  - Filter options: All, Unread, Active Projects, Archived
  - Search functionality to find specific clients
- **Individual Chat Interface**:
  - Client profile panel showing:
    - Client's basic information (name, location)
    - Previous contracts/work history
    - Current project status (if applicable)
    - Client rating/feedback history
  - Quick action toolbar:
    - Send portfolio/work samples
    - Create contract/quote
    - Schedule appointment
    - Mark as important/priority
  - Professional response templates:
    - Initial greeting for new clients
    - Service availability responses
    - Quote/estimate templates
    - Follow-up message templates

## API Endpoints

### Chat Room List API
- **Endpoint**: GET `/api/chat/rooms/`
- **Authentication**: Required
- **Description**: List all chat rooms where the authenticated user is a participant
- **Response**:
```json
[
  {
    "id": "integer",
    "client": {
      "id": "integer",
      "username": "string",
      "first_name": "string",
      "last_name": "string",
      "profile_image": "url|null"
    },
    "technician": {
      "id": "uuid",
      "user": {
        "username": "string",
        "first_name": "string",
        "last_name": "string"
      },
      "profile_image": "url|null"
    },
    "created_at": "datetime",
    "last_message": {
      "message": "string",
      "timestamp": "datetime",
      "sender": "string",
      "sender_name": "string",
      "sender_image": "url|null"
    }
  }
]
```
- **Frontend Notes**:
  - Call this endpoint to display the user's list of available chat rooms
  - Use the last_message data to show a preview in the chat list
  - Sort rooms by last_message timestamp for recent conversations
  - Store room IDs for navigation to specific chat interfaces
  - Display participant profile images in room list for easy identification

### Chat Room Creation API
- **Endpoint**: POST `/api/chat/rooms/create/`
- **Authentication**: Required
- **Request Body**:
```json
{
    "technician_id": "uuid or string"
}
```
- **Response**:
```json
{
    "id": "integer",
    "client": {
        "id": "integer",
        "username": "string",
        "first_name": "string",
        "last_name": "string",
        "profile_image": "url|null"
    },
    "technician": {
        "id": "uuid",
        "user": {
            "username": "string",
            "first_name": "string",
            "last_name": "string"
        },
        "profile_image": "url|null"
    },
    "created_at": "datetime",
    "last_message": null
}
```
- **Notes**:
  - Returns existing room if one already exists between client and technician
  - Creates new room if no existing room is found
  - Room ID from response should be used for WebSocket connection
  - Supports two formats for `technician_id`:
    - UUID format (standard UUID string)
    - "TECH-{id}" format (e.g., "TECH-fd68eb") where {id} is a suffix of the technician's UUID

### Chat Room Detail API
- **Endpoint**: GET `/api/chat/rooms/<room_id>/`
- **Authentication**: Required
- **Description**: Retrieve details of a specific chat room and its messages
- **Response**:
```json
{
  "room": {
    "id": "integer",
    "client": {
      "id": "integer",
      "username": "string",
      "first_name": "string", 
      "last_name": "string",
      "profile_image": "url|null"
    },
    "technician": {
      "id": "uuid",
      "user": {
        "username": "string",
        "first_name": "string",
        "last_name": "string"
      },
      "profile_image": "url|null"
    },
    "created_at": "datetime",
    "last_message": {
      "message": "string",
      "timestamp": "datetime",
    },
    "unread_count": "integer"
  },
  "messages": [
    {
      "id": "integer",
      "room": "integer",
      "sender": {
        "id": "integer",
        "username": "string",
        "first_name": "string",
        "last_name": "string",
        "profile_image": "url|null"
      },
      "message": "string",
      "file": "url",
      "timestamp": "datetime",
      "edited_at": "datetime|null",
      "read_by": [
        {
          "user": {
            "id": "integer",
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "profile_image": "url|null"
          },
          "read_at": "datetime"
        }
      ]
    }
  ]
}
```
- **Frontend Notes**:
  - Call this endpoint when opening a specific chat room
  - Use room details for displaying participant information
  - Render all messages in chronological order
  - Display read status for each message using the read_by array
  - Show unread message count in the chat list
  - After loading initial messages, establish WebSocket connection for real-time updates 
  - Display profile images next to each message to provide visual identification of participants 