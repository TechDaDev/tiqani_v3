# Product Requirements Document (PRD)
## Project: Tiqani API

### 1. Overview
Tiqani API is a Django REST–based backend platform designed to support freelancing and contracting services. It provides secure user management, service categorization, payments, contracts, reviews, and notifications, serving as the core backend for web and mobile clients.

### 2. Objectives
- Provide a scalable backend for freelancing and contracting workflows  
- Enable secure authentication and role-based access  
- Support service discovery, contracting, payments, and reviews  
- Offer extensible APIs for future mobile and web applications  

### 3. Target Users
- Freelancers / Service Providers  
- Clients / Customers  
- Platform Administrators  

### 4. Functional Requirements

#### 4.1 Authentication & User Management
- JWT-based authentication  
- User registration, login, and profile management  
- Role-based permissions  

#### 4.2 Category Management
- Create, update, delete, and list service categories  
- Hierarchical category support  

#### 4.3 Contract Management
- Create and manage service contracts between users  
- Track contract status (pending, active, completed, canceled)  

#### 4.4 Payment Processing
- Stripe integration for payments  
- Transaction tracking and validation  

#### 4.5 Rating & Review System
- Users can rate and review completed contracts  
- Average ratings calculated per service/provider  

#### 4.6 Dealership Management
- Support intermediary or agency-style accounts  
- Manage associations between dealers and service providers  

#### 4.7 Notification System
- In-app notifications for key events  
- Persistent storage of notifications  

### 5. Non-Functional Requirements
- Secure API endpoints (JWT, permissions)  
- Scalable architecture  
- Clean RESTful design  
- Maintainable and modular Django apps  

### 6. Technology Stack
- Backend: Django, Django REST Framework  
- Authentication: Django Simple JWT  
- Payments: Stripe  
- Database: SQLite (development), PostgreSQL (production)  
- Async Support: Django Channels (excluding chat features)  

### 7. API Structure
- /api/accounts/ – User management  
- /api/category/ – Categories  
- /api/payment/ – Payments  
- /api/contract/ – Contracts  
- /api/ratereview/ – Ratings & reviews  
- /api/dealership/ – Dealership management  
- /api/notification/ – Notifications  

### 8. Deployment
- Supports traditional Linux server deployment  
- Environment-based configuration using .env files  
- Production-ready with Nginx, Gunicorn, Redis, PostgreSQL  

### 9. Out of Scope
- Real-time chat or messaging system  
- Frontend UI implementation  

### 10. Future Enhancements
- Mobile application integration  
- Advanced analytics and reporting  
- Multi-currency and regional payment support  
