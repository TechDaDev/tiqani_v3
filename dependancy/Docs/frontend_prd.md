# Tiqani Platform - Frontend Product Requirements Document

## Table of Contents
- [Overview](#overview)
- [User Types & Authentication](#user-types--authentication)
- [Core Features](#core-features)
- [Technical Requirements](#technical-requirements)
- [UX/UI Guidelines](#uxui-guidelines)
- [Module Requirements](#module-requirements)
  - [Authentication & User Management](#authentication--user-management)
  - [Technician Marketplace](#technician-marketplace)
  - [Chat & Communication](#chat--communication)
  - [Contracts & Projects](#contracts--projects)
  - [Payments & Wallet](#payments--wallet)
  - [Dealership Management](#dealership-management)
  - [Rating & Reviews](#rating--reviews)
  - [Notification System](#notification-system)
- [API Integration](#api-integration)
- [Testing Requirements](#testing-requirements)
- [Deployment](#deployment)

## Overview

Tiqani (which means 'IT Technician' in Arabic) is an Iraqi platform connecting clients with IT technical service providers (IT technicians) for project-based work. The platform facilitates the entire workflow from discovery to payment, with integrated chat, contracting, and financial tools.

### Project Goals
1. Create a user-friendly marketplace for IT technical services
2. Provide secure and reliable communication between clients and IT technicians
3. Facilitate contract creation, management, and payment processing
4. Build trust through transparent ratings and reviews
5. Support both Arabic and English interfaces, Arabic is the defaut.
6. Implement comprehensive notification system for user engagement
7. Provide secure cash withdrawal options through verified dealerships

## User Types & Authentication

### User Types
1. **Clients** - Users seeking IT technical services
2. **IT Technicians** - Service providers with IT technical skills
3. **Dealerships** - Exchange office owners who facilitate withdrawals for users
4. **Administrators** - Platform managers with elevated privileges

### User Data Privacy
The frontend must implement strict privacy controls to protect user data:

1. **Public Data**: 
   - Basic profile information (name, profile image, governorate)
   - Gender (considered public for both client and technician profiles)
   - For technicians: Skills, about description, portfolio samples, rates, reviews

2. **Private Data** (only visible to profile owner and administrators):
   - Date of birth and age
   - Contact information (phone number, email address)
   - Detailed address information
   - Financial information (wallet details, transaction history)

3. **Privacy UI Components**:
   - Clear visual indicators showing which profile fields are public vs. private
   - Privacy settings panel allowing users to understand what information is shared
   - Appropriate information masking in public views

### Administrator Role
Administrators are system managers with privileged access who maintain and oversee the platform. Unlike clients and technicians who use the main application frontend, administrators primarily interact with the system through a dedicated admin interface.

#### Administrator Responsibilities
1. **User Management**:
   - Approving/rejecting technician profiles
   - Managing account verification status
   - Handling user complaints and reports
   - Activating/deactivating user accounts
   - Approving/rejecting dealership registrations

2. **Content Moderation**:
   - Reviewing technician portfolios
   - Monitoring reviews for policy violations
   - Moderating reported content

3. **System Administration**:
   - Managing skill categories and subcategories
   - Configuring system settings
   - Monitoring platform performance
   - Setting business rules

4. **Financial Oversight**:
   - Monitoring transaction flows
   - Managing dispute resolution
   - Reviewing payment issues
   - Generating financial reports
   - Managing dealership operations and verification
   - Monitoring withdrawal processes

#### Administrator Interface
The administrator interface is separate from the main client/technician frontend and will be implemented using Django's built-in admin interface with customizations:

1. **Dashboard**:
   - Key metrics overview
   - Recent activity feed
   - System alerts and notifications

2. **User Management**:
   - User search and filtering
   - Profile approval workflows
   - Account status controls

3. **Content Management**:
   - Category/skills management
   - Content moderation tools
   - Review management

4. **Financial Tools**:
   - Transaction monitoring
   - Payment dispute resolution
   - Financial reporting

#### Technical Implementation
- Based on Django's built-in admin interface
- Role-based on Django's `is_staff` and `is_superuser` flags
- Custom admin views for specialized workflows
- Styled to match platform branding

### Authentication
- JWT-based authentication system
- Refresh token mechanism for extended sessions
- Profile-based authorization for different user types
- User registration and profile completion workflows

## Core Features

### 1. User Profiles
- **Client Profiles**: Basic information, payment methods, project history
- **IT Technician Profiles**: IT skills, portfolio, availability, rates, reviews, years of expertise

### 2. Marketplace
- Search/filtering of IT technicians by skills, ratings, location
- IT technician discovery and comparison tools
- IT category-based browsing

### 3. Communication
- Real-time chat with message history
- File sharing capabilities
- Notification system

### 4. Contracts
- Contract creation and negotiation
- Milestone/stage-based project structure
- Status tracking and updates

### 5. Payments
- Secure payment processing via Stripe
- Wallet system for managing funds
- Escrow functionality for milestone payments
- Wallet-to-wallet transfers
- Physical withdrawal through verified dealerships

### 6. Ratings & Reviews
- Post-project review system
- Star ratings with text reviews
- Aggregated ratings for technicians

### 7. Notifications
- Multi-channel notification delivery (in-app, email, push)
- User-configurable notification preferences
- Categorized notification types
- Real-time notification delivery

## Technical Requirements

### Frontend Stack
- React.js with TypeScript
- State management with Redux or Context API
- Responsive design with CSS frameworks (Material UI or similar)
- WebSocket integration for real-time features
- Stripe Elements for payment processing
- Push notification integration for mobile and web

### Browser Support
- Latest 2 versions of Chrome, Firefox, Safari, Edge
- Mobile browser support for responsive layouts

### Performance Targets
- Initial load < 3 seconds on broadband
- Time to interactive < 5 seconds
- Smooth scrolling and transitions (60fps)
- Notification delivery < 500ms after event

## UX/UI Guidelines

### Design System
- Consistent color scheme based on brand guidelines
- Typography hierarchy with legible fonts for both Arabic and English
- Component library with reusable UI elements
- Responsive breakpoints for mobile, tablet, and desktop

### Localization
- Bidirectional (RTL/LTR) layout support
- Language switcher for Arabic/English
- Date/time/currency formatting based on locale

### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Sufficient color contrast

### Privacy Guidelines
- **Public Profile Information**: Display only approved public fields (first name, last name, profile image, governorate, gender) on public-facing views
- **Private Information Protection**: Do not display sensitive information (date of birth, age, phone number, full address, email) on public views
- **Owner View**: Show complete profile data only to the profile owner
- **Administrative View**: Allow administrators to see all profile information through the admin interface
- **Data Display Patterns**: Implement consistent patterns for displaying/hiding information based on the viewer's relationship to the profile

## Module Requirements

### Authentication & User Management

#### Registration Flow
- Step-by-step user registration with role selection
- Email verification
- Profile completion guidance

#### Login Features
- Username/password authentication
- Password reset functionality
- Remember-me option
- Account recovery process

#### Profile Management
- Profile editing interface
- Profile completion indicator
- Profile image upload
- Settings management
- Privacy controls with clear indicators of which information is public vs. private

### Technician Marketplace

#### Search & Discovery
- Advanced filtering by:
  - IT Skills and categories
  - Location/governorate
  - Rating
  - Availability
- Search results with card-based layout
- Quick view of key IT technician information

#### IT Technician Profiles
- Visual portfolio display
- IT Skills visualization
- Review section with pagination
- Contact/hire action buttons
- Rate information
- Gender information (public)
- Years of expertise display (public)
- Private information properly hidden in public views

### Chat & Communication

#### Chat Interface
- Thread-based conversation list
- Real-time message delivery
- Typing indicators
- Read receipts
- Profile picture and online status
- Message timestamps
- File attachment support
- URL previews

#### Notifications
- Real-time notification system
- Notification center with read/unread state
- Email notifications for important events
- Push notification integration (future)

### Contracts & Projects

#### Contract Creation
- Contract template with customizable fields
- Milestone/stage definition
- Pricing and timeline configuration
- Terms and conditions

#### Contract Management
- Status tracking (pending, active, completed, etc.)
- Milestone completion workflow
- Change request handling
- Document attachment

#### Project Dashboard
- Overview of active and completed projects
- Timeline visualization
- Payment status tracking
- Action items and next steps

### Payments & Wallet

#### Wallet Interface
- Current balance display
- Transaction history with filtering
- Wallet ID for transfers (partially masked for security)
- Withdrawal options including dealership withdrawal
- Display of balance in IQD with USD equivalent in parentheses
- Current exchange rate display
- Transaction history showing both IQD and USD amounts

#### Payment Processing
- Stripe Elements integration for card payments
- Payment confirmation flow
- Receipt generation
- Currency conversion display (USD to IQD) with current exchange rate

#### Fund Transfers
- Transfer form with recipient ID validation
- Transfer confirmation step
- Transfer receipt
- Amount input in IQD with real-time USD equivalent display

#### Withdrawal System
- Withdrawal request form
- Dealership selection by location
- Withdrawal status tracking
- Receipt generation
- IQD amount display with USD equivalent for reference

#### Exchange Rate Display
- Current exchange rate prominently displayed in wallet dashboard
- Exchange rate used at transaction time shown in transaction history
- Exchange rate history chart (for admin users)
- Last updated timestamp for exchange rate

### Dealership Management

#### Dealership Registration
- Registration application with required verification data:
  - Office name (business name)
  - Registration/commercial license number
  - Tax identification number
  - Owner information (name, ID number)
  - Governorate and detailed address
  - Contact information (phone numbers, email)
  - Operating hours
  - Banking information for settlements
  - Document uploads (business license, owner ID, tax registration, commercial lease agreement)
  - Background check consent
  - Anti-money laundering compliance agreement
  - Security deposit requirement information
- Multi-step registration form with validation
- Uploading multiple document types with description
- Clear explanation of verification process and requirements

#### Dealership Dashboard
- Active withdrawal requests list
- Transaction history and reporting
- Financial reconciliation interface
- Commission tracking
- Performance metrics
- Risk assessment indicators
- Compliance status monitoring
- Suspicious activity alerts
- Daily transaction limits display
- Success rate and rating visualization
- Document verification status tracking

#### Dealership Verification
- Two-factor authentication for dealership operators
- Biometric verification options (future enhancement)
- Fraud prevention controls
- Approval workflows for large transactions
- IP address logging and location verification
- Device fingerprinting for authorized devices
- Periodic re-verification requirements
- Transaction anomaly detection
- Real-time video verification for high-value transactions
- QR code scanner integration for withdrawal verification
- Enhanced verification for transactions above certain thresholds

#### Dealership Public Profile
- Name and location information
- Operating hours
- User ratings and reviews
- Verification status badge
- Years in operation
- Service level indicators
- Photos of physical location
- Maximum withdrawal limits
- Success rate display
- Weekend days display
- Governorate and address information

#### Withdrawal Process
- QR code generation for in-person verification
- Transaction verification flow
- Receipt generation and digital signatures
- Dispute resolution process
- Transaction logging with timestamps and geolocation
- Customer satisfaction confirmation
- Cooling-off period for large transactions
- Tiered verification based on transaction amount
- Multi-level approval for high-value withdrawals
- Withdrawal status tracking with clear visual indicators
- Verification type selection based on amount
- Digital signature capture capability

#### Security and Compliance
- Real-time transaction monitoring
- Fraud detection algorithms
- Daily transaction limits and thresholds
- AML/KYC compliance tools
- Automated suspicious activity reporting
- Secure communication channels
- Regular security audits
- Staff verification and access management
- Insurance requirements for dealerships
- Emergency transaction freeze capabilities
- Comprehensive verification logging
- IP address tracking for all transactions
- Device fingerprinting

### Rating & Reviews

#### Review Submission
- Star rating input (1-5 stars)
- Text review with character counter
- Submission confirmation

#### Review Display
- Star visualization
- Review listing with client information
- Date formatting
- Sorting options

### Notification System

#### Notification Center
- Centralized notification hub accessible from all pages
- Unread count badge with real-time updates
- Categorized notification list with visual indicators
- Mark as read functionality (individual and batch)
- Clear notification option
- Infinite scroll for notification history

#### Notification Types Display
- Category-based visual styling (different icons/colors)
- Time-based sorting with relative timestamps
- Action buttons based on notification type
- Rich notification content with relevant context

#### Notification Preferences
- Comprehensive preference management interface
- Channel-based toggles (in-app, email, push) for each notification type
- Category grouping of notification types
- Quiet hours configuration with time picker
- Default vs. custom preference indication
- Bulk preference update options

#### Push Notification Setup
- Browser permission request with clear explanation
- Device management interface
- Multiple device support with friendly names
- Test notification option
- Token refresh handling
- Service worker installation for web push

#### Real-time Notification Delivery
- WebSocket integration for instant delivery
- Fallback mechanisms for connection issues
- Offline notification queuing
- Notification sound options (configurable)
- Visual notification animations

#### Notification Templates
- Consistent visual design across notification types
- Action URL integration for direct navigation
- Related object preview when applicable
- Contextual information display

## API Integration

### API Endpoints
- Comprehensive integration with backend API endpoints
- Error handling for all API calls
- Loading states during API requests
- Retry logic for failed requests

### Real-time Features
- WebSocket connection for chat and notifications
- Reconnection handling for dropped connections
- Event-based updates for real-time data

#### WebSocket Implementation
- Connection to WebSocket endpoints using secure protocol (wss://)
- JWT token authentication via URL query parameters
- Connection format: `wss://your-app-name.herokuapp.com/ws/chat/<room_id>/?token=<jwt_token>`
- Automatic reconnection with exponential backoff strategy
- Connection state management and error handling
- Support for synchronous WebSocket consumers on the backend
- Handling of various message types (text messages, file transfers, typing indicators)
- Graceful handling of connection errors and server restarts

## Testing Requirements

### Unit Testing
- Component-level unit tests
- Form validation testing
- Utility function testing

### Integration Testing
- User flow testing
- API integration testing
- Authentication flow testing

### UI Testing
- Responsive design testing across devices
- Browser compatibility testing
- Accessibility testing

### Privacy and Security Testing
- Verify that sensitive information is not displayed in public views
- Test that gender information is displayed correctly while date of birth and age remain private
- Confirm that only profile owners and administrators can see private information
- Validate that API requests do not expose sensitive data to unauthorized users
- Test privacy controls and settings functionality

## Deployment

### Build Process
- Optimized production builds
- Asset minification and bundling
- Code splitting for improved performance

### Environment Configuration
- Environment-specific configuration management
- Feature flags for gradual rollout
- API endpoint configuration

### Monitoring
- Error tracking integration
- Performance monitoring
- Usage analytics

---

## Appendix A: User Flows

### Client User Flow
1. Registration and profile completion
2. Browse and search for technicians
3. View technician profiles and reviews
4. Initiate contact through chat
5. Negotiate and create contract
6. Fund wallet and make payment (in IQD)
7. Track project progress
8. Close project and leave review

### Technician User Flow
1. Registration and profile completion
2. Configure skills and portfolio
3. Set availability and rates (in IQD)
4. Respond to client inquiries
5. Negotiate contract terms
6. Execute project stages
7. Receive payments upon milestone completion (in IQD)
8. Build rating through successful projects

### Dealership User Flow
1. Registration application submission
2. Document verification process
3. Administrator approval
4. Dashboard access and configuration
5. Receive withdrawal requests from users
6. Verify user identity via QR code/ID
7. Process physical cash payments
8. Record completed transactions
9. Financial reconciliation and reporting
10. Manage ratings and respond to feedback

### Notification User Flow
1. Receive notification (in-app, email, or push)
2. View notification details in notification center
3. Take action based on notification content
4. Mark notification as read
5. Configure notification preferences
6. Manage notification channels
7. Set up quiet hours for notifications

## Appendix B: API Endpoints Reference

Refer to the following documentation for detailed API specifications:
- [Authentication API](./auth.md)
- [Accounts API](./account.md)
- [Chat API](./chat.md)
- [Contract API](./contract.md)
- [Payment API](./payment.md)
- [Dealership API](./dealership.md)
- [Rate & Review API](./rate_review.md)
- [Notification API](./notification.md)

For development and testing specifics, refer to:
- [Payment Development Guide](./payment_dev.md)
- [Dealership Integration Guide](./dealership_dev.md)

### Technician Additional Information
For IT technicians, the platform should collect and display additional professional information:
1. **Years of Expertise**: Numeric input for years of professional IT experience
   - Display prominently on profile
   - Used for filtering/sorting in search results
   - Required for profile completion
   - Shown as part of expertise indicators

2. **Portfolio Management**:
   - Multiple image upload capability
   - Portfolio description fields
   - Portfolio categorization options

3. **IT Skill Set Management**:
   - Multi-level IT skill selection (category → skills → sub-skills)
   - Skill endorsement visualization
   - Primary vs. secondary IT skills designation

## Appendix C: Notification Types

The following notification types must be supported by the frontend:

### Authentication Notifications
- **Welcome**: Sent when a user creates a new account
- **Password Reset**: Sent when a user requests a password reset

### Contract Notifications
- **New Contract**: Sent when a new contract is created
- **Contract Accepted**: Sent when a contract is accepted
- **Contract Rejected**: Sent when a contract is rejected
- **Milestone Completed**: Sent when a milestone is completed

### Payment Notifications
- **Payment Received**: Sent when a payment is received
- **Payment Sent**: Sent when a payment is sent
- **Withdrawal Ready**: Sent when a withdrawal is ready for pickup

### Chat Notifications
- **New Message**: Sent when a new chat message is received

### Rating Notifications
- **New Rating**: Sent when a new rating is received

### System Notifications
- **System Announcement**: Sent for system-wide announcements 