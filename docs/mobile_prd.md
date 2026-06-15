# Tiqani Platform - Mobile Applications Product Requirements Document

## Table of Contents
- [Overview](#overview)
- [Platform Specifications](#platform-specifications)
- [Core Features](#core-features)
- [Technical Requirements](#technical-requirements)
- [UX/UI Guidelines](#uxui-guidelines)
- [Mobile-Specific Features](#mobile-specific-features)
- [Security Requirements](#security-requirements)
- [Testing Requirements](#testing-requirements)
- [Deployment](#deployment)
- [Backend API Integration](#backend-api-integration)

## Overview

Tiqani's mobile applications provide a native experience for both Android and iOS users, enabling them to access the platform's IT technician marketplace on the go. The apps maintain feature parity with the web platform while leveraging mobile-specific capabilities for enhanced user experience.

### Project Goals
1. Deliver native mobile experiences for Android and iOS users
2. Ensure seamless synchronization with the existing REST and WebSocket APIs
3. Leverage mobile-specific features for enhanced functionality
4. Maintain consistent user experience across platforms
5. Support offline capabilities for essential features
6. Optimize performance for mobile networks
7. Implement secure mobile authentication with biometrics

## Platform Specifications

### Android Requirements
- Minimum SDK Version: Android 8.0 (API Level 26)
- Target SDK Version: Latest stable Android version (Android 14, API Level 34)
- Screen Support: All standard Android screen sizes and densities
- Device Support: Smartphones and tablets
- Architecture: MVVM with Clean Architecture
- Language: Kotlin
- Build System: Gradle

### iOS Requirements
- Minimum iOS Version: iOS 14.0
- Target iOS Version: Latest stable iOS version (iOS 17)
- Device Support: iPhone and iPad
- Architecture: MVVM with Clean Architecture
- Language: Swift
- Build System: Xcode

## Core Features

### 1. Authentication
- Biometric authentication (Face ID/Touch ID)
- JWT token management with refresh token handling
- Secure credential storage
- Auto-login functionality
- Session management
- Two-factor authentication support via OTP
- Integration with existing authentication endpoints:
  - Registration with CAPTCHA support
  - OTP verification for email
  - Login/logout
  - Password reset

### 2. User Profiles
- Profile creation and editing for all user types (Client, Technician, Dealership)
- Profile image upload with camera/gallery access
- Skills and portfolio management for technicians
- Availability settings
- Rate configuration
- Profile completion progress tracking using existing profile completion APIs
- Support for multi-role profiles

### 3. Marketplace
- Advanced search with filters (using existing API filters)
- Location-based technician discovery using mobile location services
- Category browsing
- Save favorite technicians
- Recent searches
- Offline access to saved profiles
- Integration with governorate-based location system

### 4. Chat & Communication
- Real-time messaging using WebSocket integration (Channels)
- Push notifications for new messages
- Media sharing (images, documents)
- Typing indicators
- Read receipts
- Message history
- Offline message queueing
- Integration with existing chat module

### 5. Contracts & Projects
- Contract creation and management
- Milestone tracking
- Document signing
- Status updates
- Project timeline view
- Offline contract viewing
- Integration with existing contract API endpoints

### 6. Payments & Wallet
- Secure payment processing
- Wallet management
- Transaction history
- Payment notifications
- QR code generation for withdrawals
- Biometric authentication for transactions
- Multi-currency support (IQD/USD)
- Integration with existing payment APIs

### 7. Ratings & Reviews
- Post-project review submission
- Rating visualization
- Review management
- Review notifications
- Integration with existing RateReview module

### 8. Notifications
- Push notification support
- In-app notification center
- Notification preferences
- Action-based notifications
- Quiet hours configuration
- Integration with existing notification module

## Technical Requirements

### Performance Targets
- App launch time < 2 seconds
- Screen transition time < 300ms
- Offline functionality for core features
- Background sync for data updates
- Efficient battery usage
- Memory optimization

### Network Handling
- Offline-first architecture
- Efficient data synchronization
- Background data updates
- Network state monitoring
- Automatic retry mechanisms
- Data compression
- Support for intermittent connectivity common in target regions

### Storage
- Secure local storage
- Efficient caching strategy
- Data persistence
- Storage optimization
- Cache management

## UX/UI Guidelines

### Design System
- Platform-specific design patterns
- Consistent branding with web platform
- Responsive layouts
- Dark mode support
- Accessibility compliance
- Gesture support
- Support for Arabic localization

### Navigation
- Bottom navigation (Android)
- Tab bar (iOS)
- Gesture-based navigation
- Deep linking support
- Back navigation handling
- Screen transitions

### Forms & Input
- Platform-specific input patterns
- Form validation
- Auto-complete support
- Input masking
- Error handling
- Loading states
- Support for both English and Arabic input

## Mobile-Specific Features

### Location Services
- GPS integration
- Location-based search
- Map view for technicians
- Location sharing
- Geofencing support
- Background location updates
- Integration with existing governorate system

### Camera Integration
- Profile picture capture
- Document scanning
- Portfolio image upload
- QR code scanning
- Image compression
- Gallery access
- Integration with existing file upload APIs

### Push Notifications
- Firebase Cloud Messaging (Android)
- Apple Push Notification Service (iOS)
- Rich notifications
- Action buttons
- Notification grouping
- Priority levels
- Integration with existing notification system

### Offline Capabilities
- Offline data access
- Background sync
- Conflict resolution
- Data versioning
- Sync status indicators
- Offline mode indicators

## Security Requirements

### Data Protection
- End-to-end encryption for sensitive communications
- Secure storage
- Network security
- Certificate pinning
- Data encryption at rest
- Secure key storage
- Compliance with existing backend security measures

### Authentication
- Biometric authentication
- Secure token storage
- Session management
- Auto-logout
- Device binding
- Security logging
- Integration with JWT-based authentication system

### Compliance
- GDPR compliance
- Data privacy
- User consent management
- Data retention policies
- Privacy policy integration
- Terms of service

## Testing Requirements

### Unit Testing
- Component testing
- View model testing
- Repository testing
- Utility testing
- Mock testing
- Test coverage requirements

### Integration Testing
- API integration
- Database integration
- Third-party service integration
- Payment integration
- Push notification testing
- Deep link testing

### UI Testing
- Screen testing
- Navigation testing
- Gesture testing
- Accessibility testing
- Dark mode testing
- Orientation testing
- RTL layout testing for Arabic support

### Performance Testing
- Load testing
- Memory leak testing
- Battery usage testing
- Network performance
- Storage performance
- Launch time testing

## Deployment

### App Store Requirements
- App Store Connect setup
- Play Console setup
- App signing
- Release management
- Version control
- Beta testing

### CI/CD
- Automated builds
- Test automation
- Code signing
- Release automation
- Environment management
- Version management

### Monitoring
- Crash reporting
- Analytics
- Performance monitoring
- User feedback
- Error tracking
- Usage statistics
- Integration with backend monitoring systems

## Backend API Integration

### REST API Integration
- Base URL configuration for production and staging environments
- API versioning compatibility
- Error handling
- Response caching
- Request retry logic
- Authentication headers
- JWT token refresh mechanism
- Integration with all existing API endpoints:
  - Accounts module (user authentication, profiles)
  - Dashboard module (admin functions)
  - Contract module (project management)
  - Payment module (wallet, transactions)
  - Chat module (messaging)
  - Notification module (alerts, preferences)
  - RateReview module (ratings system)
  - Category module (skills, services)

### WebSocket Integration
- Connection management using Channels
- Reconnection strategy
- Message handling
- Event subscription
- Error recovery
- Connection monitoring
- Real-time chat synchronization

### Backward Compatibility
- Support for API versioning
- Graceful handling of backend changes
- Feature flags for new functionality
- App update prompts for critical API changes

## Appendix A: Mobile-Specific User Flows

### Client User Flow
1. App installation and onboarding
2. Account creation/authentication
3. Profile completion
4. Technician search and discovery
5. Chat initiation
6. Contract creation
7. Payment processing
8. Project tracking
9. Review submission

### IT Technician User Flow
1. App installation and onboarding
2. Account creation/authentication
3. Profile and portfolio setup
4. Availability management
5. Chat response
6. Contract management
7. Project execution
8. Payment receipt
9. Review management

### Dealership User Flow
1. App installation and onboarding
2. Account creation/authentication
3. Profile setup
4. Transaction processing
5. Financial management
6. Service integration

## Appendix B: Mobile-Specific Notifications

### Push Notification Types
- New message notifications
- Contract updates
- Payment notifications
- System announcements
- Profile updates
- Security alerts

### In-App Notifications
- Chat messages
- Contract status
- Payment status
- Review notifications
- System messages
- Profile updates

## Appendix C: Offline Behavior Strategy

The mobile app will implement the following offline behavior strategy:

1. **Critical Data Caching**:
   - User profile information
   - Active contracts and projects
   - Recent messages
   - Saved technician profiles

2. **Background Synchronization**:
   - Queue outgoing messages and actions when offline
   - Automatic retry when connection is restored
   - Conflict resolution for concurrent changes

3. **User Experience**:
   - Clear indicators for offline status
   - Preview of cached content with freshness timestamps
   - Guidance on actions available offline 