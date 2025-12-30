# Account API Documentation

## Table of Contents
- [Authentication Endpoints](#authentication-endpoints)
  - [Generate CAPTCHA](#generate-captcha)
  - [Register User](#1-register-user)
  - [Verify Email OTP](#2-verify-phone-otp)
  - [Resend OTP](#3-resend-otp)
  - [Login](#4-login)
  - [Refresh Token](#5-refresh-token)
  - [Logout](#6-logout)
- [Account Management](#account-management)
  - [Password Reset Request](#1-password-reset-request)
  - [Forgot Password](#2-forgot-password)
  - [Password Reset Confirm](#3-password-reset-confirm)
- [Profile Management](#profile-management)
  - [Technician Profile](#1-technician-profile)
  - [Client Profile](#2-client-profile)
  - [Dealership Profile](#dealership-profile)
  - [Technician Profile Completion Check](#technician-profile-completion-check)
- [Image Management](#image-management)
  - [Upload Technician Image](#1-upload-technician-image)
  - [Update/Delete Technician Image](#2-updatedelete-technician-image)
  - [Update/Delete Skill Set](#3-updateskill-set)
- [Profile Completion Requirements](#profile-completion-requirements)
  - [Overview](#overview)
  - [Client Profile Completion Requirements](#client-profile-completion-requirements)
  - [Technician Profile Completion Requirements](#technician-profile-completion-requirements)
  - [Dealership Profile Completion Requirements](#dealership-profile-completion-requirements)
  - [Completion Status](#completion-status)
  - [Error Messages](#error-messages)
  - [Frontend Implementation](#frontend-implementation)
  - [Rate Limiting and Security](#rate-limiting-and-security)
- [Data Privacy and Security](#data-privacy-and-security)
  - [Sensitive Personal Information](#sensitive-personal-information)
  - [Public Information](#public-information)
  - [Access Control](#access-control)
  - [Implementation Guidelines](#implementation-guidelines)
  - [Regulatory Compliance](#regulatory-compliance)
- [Frontend Implementation Notes](#frontend-implementation-notes)
  - [Governorate Selection](#governorate-selection)
  - [Profile Forms](#profile-forms)
  - [Gender Selection](#gender-selection)
  - [Date of Birth](#date-of-birth)
  - [Access to Technician List for Clients](#access-to-technician-list-for-clients)
- [Technician Approval System](#technician-approval-system)
  - [Overview](#technician-approval-overview)
  - [List Technicians for Approval](#list-technicians-for-approval)
  - [Approve/Reject Technician](#approvereject-technician)
  - [Technician Approval Statistics](#technician-approval-statistics)
  - [Approval System Permissions](#approval-system-permissions)
- [Admin Accounts](#admin-accounts)
  - [Overview](#admin-accounts-overview)
  - [Administrator Roles](#administrator-roles)
  - [Admin Profile Completion Requirements](#admin-profile-completion-requirements)
  - [Administrator Creation](#administrator-creation)
  - [Administrator API Endpoints](#administrator-api-endpoints)
  - [Administrator Permissions](#administrator-permissions)
  - [Administrator Features](#administrator-features)
  - [API Permissions](#api-permissions)
  - [Admin Interface](#admin-interface)

## Authentication Endpoints

### CAPTCHA

### Generate CAPTCHA
- **URL**: `/api/accounts/generate-captcha/`
- **Method**: `GET`
- **Description**: Generate new CAPTCHA for registration
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
{
    "captcha_key": "string",
    "image_url": "string"
}
``` 
- **Frontend Notes**:
  - Use this endpoint to load a new CAPTCHA before showing the registration form
  - Store the `captcha_key` for submission with the registration form
  - Display the image from `image_url` in your registration form
  - Implement a refresh button to get a new CAPTCHA if user can't read it

### 1. Register User
- **URL**: `/api/accounts/register/`
- **Method**: `POST`
- **Description**: Register a new user account
- **Authentication**: Not required
- **Request Body**:
```json
{
    "username": "string",
    "password": "string",
    "password2": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "user_type": "client|technician|dealership",
    "phone_number": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "governorate": "string",
    "captcha_0": "string (captcha key)",
    "captcha_1": "string (captcha value)"
}
```
- **Response**:
  - Success (201):
```json
{
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "verification_id": "string"
}
```
  - Error (400):
```json
{
    "field_name": [
        "error message"
    ]
}
```

**Notes**:
- The `user_type` field determines what kind of profile is created:
  - `client`: For users looking for technical services
  - `technician`: For users offering technical services
  - `dealership`: For payment service providers
- All users must verify their email address before the account is activated
- Password must be at least 8 characters long and meet complexity requirements
- Date of birth is required and user must be at least 18 years old
- CAPTCHA verification is required to prevent automated registrations

### 2. Verify Phone OTP
- **URL**: `/api/accounts/verify-otp/`
- **Method**: `POST`
- **Description**: Verify email using OTP
- **Authentication**: Not required
- **Rate Limiting**: Maximum 5 attempts per email address in 10 minutes
- **Request Body**:
```json
{
    "email": "string",
    "verification_id": "string",
    "otp_code": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "Email verified successfully."
}
```
  - Error (400/404):
```json
{
    "error": "Email, verification ID and OTP code are required."
}
```
```json
{
    "error": "No pending verification found for this email."
}
```
```json
{
    "error": "Invalid OTP code or verification ID."
}
```
```json
{
    "error": "OTP code has expired. Please request a new one."
}
```
```json
{
    "error": "Too many verification attempts. Please wait for 10 minutes."
}
```
- **Frontend Notes**:
  - Create a 6-digit OTP input with proper formatting
  - Add countdown timer to indicate OTP expiration (10 minutes)
  - Provide link/button to request new OTP if expired
  - After successful verification, redirect to login page
  - Display clear message about successful verification
  - Handle all error cases with appropriate user feedback
  - Show remaining attempts count to user
  - Implement exponential backoff for retry attempts

### 3. Resend OTP
- **URL**: `/api/accounts/resend-otp/`
- **Method**: `POST`
- **Description**: Resend OTP code for account activation
- **Authentication**: Not required
- **Rate Limiting**: Maximum 3 resend requests per email address in 30 minutes
- **Request Body**:
```json
{
    "email": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "New OTP sent to your email.",
    "verification_id": "string"
}
```
  - Error (400/404):
```json
{
    "error": "Email is required."
}
```
```json
{
    "error": "No pending account verification found for this email."
}
```
```json
{
    "error": "Too many resend attempts. Please try again in 30 minutes."
}
```
- **Frontend Notes**:
  - Implement rate limiting in UI (allow only one request every 30 seconds)
  - Show loading state while request is processing
  - Update the verification_id in the OTP form with the new one received
  - Display clear message to check email for new OTP
  - Reset the countdown timer after getting a new OTP
  - Show remaining resend attempts to user
  - Display countdown timer for rate limit cooldown

### 4. Login
- **URL**: `/api/accounts/login/`
- **Method**: `POST`
- **Description**: Obtain JWT token pair and user information
- **Authentication**: Not required
- **Rate Limiting**: Maximum 5 attempts per IP address in 5 minutes
- **Request Body**:
```json
{
    "username": "string",
    "password": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "access": "string",
    "refresh": "string",
    "public_id": "TECH-123abc|CLIENT-123abc",
    "first_name": "string",
    "last_name": "string",
    "profile_image": "url|null",
    "user_type": "technician|client",
    "email": "string",
    "username": "string"
}
```
  - Error (401):
```json
{
    "detail": "No active account found with the given credentials",
    "attempts_remaining": 4
}
```
  - Error (400):
```json
{
    "username": ["This field is required."]
}
```
```json
{
    "password": ["This field is required."]
}
```
  - Error (403):
```json
{
    "detail": "User account is disabled."
}
```
  - Error (429):
```json
{
    "detail": "Too many login attempts. Please try again in 5 minutes.",
    "remaining_timeout": 240
}
```
- **Frontend Notes**:
  - Store tokens securely (HTTP-only cookies or secure localStorage)
  - Implement automatic token refresh mechanism using the refresh token
  - Store user information in application state for immediate use
  - Use the public_id and user_type to determine appropriate dashboard/views
  - Show appropriate error messages for invalid credentials
  - Handle account verification status:
    - Redirect unverified users to verification page
    - Show clear message for disabled accounts
  - Implement "Remember me" functionality if desired
  - Add rate limiting UI feedback:
    - Show remaining attempts on failed login
    - Display countdown timer when rate limit is exceeded
  - Consider implementing progressive delays between login attempts

### 5. Refresh Token
- **URL**: `/api/accounts/login/refresh/`
- **Method**: `POST`
- **Description**: Refresh access token
- **Authentication**: Not required
- **Request Body**:
```json
{
    "refresh": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "access": "string"
}
```
- **Frontend Notes**:
  - Set up automatic token refresh before access token expires
  - Implement interceptors to handle 401 responses by refreshing token
  - If refresh fails, log user out and redirect to login page
  - Set up refresh processes to happen in the background without disrupting user

### 6. Logout
- **URL**: `/api/accounts/logout/`
- **Method**: `POST`
- **Description**: Blacklist refresh token
- **Authentication**: Required
- **Request Body**:
```json
{
    "refresh": "string"
}
```
- **Response**:
  - Success (205): Empty response
- **Frontend Notes**:
  - Clear all stored tokens and user data on logout
  - Redirect to login page after successful logout
  - Handle edge cases like logout request failures gracefully
  - Consider implementing silent logout if token refresh fails

## Account Management

### 1. Password Reset Request
- **URL**: `/api/accounts/password-reset/`
- **Method**: `POST`
- **Description**: Request password reset OTP
- **Authentication**: Not required
- **Request Body**:
```json
{
    "email": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "OTP sent to your email.",
    "verification_id": "string"
}
```
  - Error (404):
```json
{
    "error": "No user found with this email."
}
```
- **Frontend Notes**:
  - Implement email validation before submission
  - Show success message even if email doesn't exist (security best practice)
  - Save the verification_id for the next step
  - Provide clear instructions to check email for OTP
  - Add rate limiting in UI to prevent abuse (one request per minute)

### 2. Forgot Password
- **URL**: `/api/accounts/forgot-password/`
- **Method**: `POST`
- **Description**: Reset password through email verification (alternative flow)
- **Authentication**: Not required
- **Request Body**:
```json
{
    "email": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "If your email is registered, you will receive password reset instructions.",
    "verification_id": "string"
}
```
  - Error (400):
```json
{
    "error": "Email is required."
}
```
- **Frontend Notes**:
  - Similar to password reset but with enhanced security measures
  - Never reveals if an email exists in the system
  - Always shows a positive message for both existing and non-existing emails
  - Store the verification_id for the password reset confirmation step
  - Implement client-side rate limiting to prevent abuse
  - Display clear instructions for users to check their email

### 3. Password Reset Confirm
- **URL**: `/api/accounts/password-reset-confirm/`
- **Method**: `POST`
- **Description**: Reset password with OTP verification
- **Authentication**: Not required
- **Request Body**:
```json
{
    "email": "string",
    "verification_id": "string",
    "otp_code": "string",
    "password": "string",
    "password2": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "message": "Password has been reset successfully."
}
```
  - Error (400):
```json
{
    "error": "All fields are required.|Passwords do not match.|Invalid OTP."
}
```
- **Frontend Notes**:
  - Implement strong password requirements with visual indicators
  - Validate passwords match before submission
  - Display clear instructions for password requirements
  - After successful reset, redirect to login page
  - Provide option to resend OTP if needed

## Profile Management

### 1. Technician Profile

#### List Technicians
- **URL**: `/api/accounts/technicians/`
- **Method**: `GET`
- **Description**: Get list of all technicians
- **Authentication**: Not required
- **Request**: No body required
- **Response**:
  - Success (200):
```json
[
    {
        "public_id": "TECH-123abc",
        "profile_image": "url|null",
        "user": {
            "first_name": "string",
            "last_name": "string"
        },
        "job_title": "string",
        "rate": "decimal",
        "governorate": {
            "key": "string",
            "display_name": "string"
        },
        "skills": ["string"],
        "years_of_expertise": "integer",
        "rating": {
            "average": "decimal",
            "count": "integer"
        },
        "is_online": "boolean",
        "created_at": "YYYY-MM-DD",
        "approved": "boolean"
    }
]
```

**Frontend Implementation Notes**:

1. **Search & Filtering**
   - Implement a search bar for technician name and skills
   - Add a "Filters" button that opens the filter panel
   - Filter panel should include:
     * Skills categories (checkboxes)
     * Location selection (governorate)
     * Minimum rating filter (slider)
     * Online status toggle
     * Approval status filter (show only approved technicians by default)

2. **Technician Cards**
   - Display technician information in a card format with:
     * Profile image (use placeholder for null)
     * Full name from first_name and last_name
     * Job title
     * Rating stars with review count (e.g., "4.9 (47 reviews)")
     * Location (governorate display_name)
     * Years of expertise
     * Relevant skills as tags
     * Online status indicator (green dot for online)
     * Member since date (format: "Member since May 2023")
     * "View Profile" button linking to `/technicians/{public_id}`

3. **Governorate (Location) Implementation**
   - The API returns both the key (English) and display_name (Arabic)
   - Available governorates:
     ```json
     [
       {"key": "Baghdad", "display_name": "بغداد"},
       {"key": "Basra", "display_name": "البصرة"},
       {"key": "Nineveh", "display_name": "نينوى"},
       {"key": "Erbil", "display_name": "أربيل"},
       {"key": "Sulaymaniyah", "display_name": "السليمانية"},
       {"key": "Kirkuk", "display_name": "كركوك"},
       {"key": "Duhok", "display_name": "دهوك"},
       {"key": "Najaf", "display_name": "النجف"},
       {"key": "Karbala", "display_name": "كربلاء"},
       {"key": "Anbar", "display_name": "الأنبار"},
       {"key": "Babil", "display_name": "بابل"},
       {"key": "Maysan", "display_name": "ميسان"},
       {"key": "Wasit", "display_name": "واسط"},
       {"key": "Dhi Qar", "display_name": "ذي قار"},
       {"key": "Muthanna", "display_name": "المثنى"},
       {"key": "Qadisiyyah", "display_name": "القادسية"},
       {"key": "Salah al-Din", "display_name": "صلاح الدين"},
       {"key": "Diyala", "display_name": "ديالى"}
     ]
     ```
   - Always display the Arabic name (display_name) in the UI
   - Use the English key when making API calls

4. **Technical Notes**
   - Only completed profiles are returned (`is_complete=true`)
   - Only approved technicians are returned (`approved=true`)
   - The `public_id` should be used for URLs and display
   - Online status is true if active within last 5 minutes
   - The `approved` field can be used for filtering technicians by approval status
   - Implement infinite scroll or pagination for large lists
   - Cache governorate list for better performance
   - Use proper error handling for failed API calls
   - Rating average is rounded to 1 decimal place
   - Rating count shows total number of reviews
   - Created date is returned in YYYY-MM-DD format
   - Format member since date in a user-friendly way (e.g., "Member since May 2023")

#### Get Technician Profile
- **URL**: `/api/accounts/technician/<uuid:pk>/` or `/api/accounts/technician/<public_id>/`
- **Method**: `GET`
- **Description**: Get technician profile details
- **Authentication**: Not required (but some fields are only visible to authenticated owners)
- **Request**: No body required
- **Response**:
  - Success (200) for public/non-owner view:
```json
{
    "public_id": "TECH-123abc",
    "user": {
        "first_name": "string",
        "last_name": "string"
    },
    "profile_image": "url|null",
    "job_title": "string",
    "about": "string",
    "rate": "decimal",
    "skills": ["string"],
    "images": [
        {
            "id": "integer",
            "image": "url",
            "description": "string"
        }
    ],
    "reviews": [
        {
            "id": "integer",
            "client": {
                "id": "uuid",
                "full_name": "string",
                "profile_image": "url|null"
            },
            "rating": "integer",
            "review_text": "string",
            "created_at": "datetime"
        }
    ],
    "governorate": "string",
    "gender": "male|female",
    "years_of_expertise": "integer",
    "is_available": "boolean",
    "created_at": "YYYY-MM-DD"
}
```
  - Success (200) for authenticated owner or admin:
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
    "profile_image": "url|null",
    "identification_documents": "url|null",
    "job_title": "string",
    "about": "string",
    "rate": "decimal",
    "skills": ["string"],
    "images": [
        {
            "id": "integer",
            "image": "url",
            "description": "string"
        }
    ],
    "reviews": [
        {
            "id": "integer",
            "client": {
                "id": "uuid",
                "full_name": "string",
                "profile_image": "url|null"
            },
            "rating": "integer",
            "review_text": "string",
            "created_at": "datetime"
        }
    ],
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    },
    "governorate": "string",
    "phone_number": "string",
    "is_available": "boolean",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "age": "integer",
    "years_of_expertise": "integer",
    "is_complete": "boolean",
    "is_profile_complete": "boolean",
    "created_at": "YYYY-MM-DD"
}
```
- **Frontend Notes**:
  - Create detailed profile view with sections for different information
  - Display portfolio images in a gallery/carousel
  - The `skills` field provides a simple list of all technician's skills for easy display and filtering
  - Create UI for reviews with ratings
  - Display location info using governorate
  - For owner view:
    - Show wallet balance with USD equivalent
    - Display sensitive information in a secure section
    - Show profile completion status with guidance on missing fields
    - Provide edit options for all fields
  - For public view:
    - Hide sensitive information (ID, phone, email, address, wallet, etc.)
    - Show only public fields with a masked public_id instead of the actual ID
    - Display availability status
  - Use proper date formatting for created_at timestamps
  - Handle null values gracefully with appropriate placeholders

#### Update Technician Profile
- **URL**: `/api/accounts/technician/<uuid:pk>/` or `/api/accounts/technician/<public_id>/`
- **Method**: `PUT`
- **Description**: Update technician profile (supports partial updates)
- **Authentication**: Required (owner only)
- **Request Body** (all fields are optional - send only what you want to update):
```json
{
    "phone_number": "string",
    "profile_image": "file|null",
    "job_title": "string",
    "about": "string",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "years_of_expertise": "integer",
    "is_available": "boolean",
    "identification_documents": "file|null",
    "url1": "string|null",
    "url2": "string|null",
    "skill_sets": [
        {
            "categories": ["uuid"],
            "main_skills": ["uuid"],
            "sub_skills": ["uuid"]
        }
    ]
}
```

**Note**: The `rate` field is **auto-calculated** from client reviews and cannot be manually set. It represents the average rating (1-5 stars) from all client reviews.

**Important Notes:**
- **Partial Updates**: This endpoint uses `partial=True`, so only send the fields you want to update
- **Skill Sets**: You can use either `main_skills` or `skills` as the field name. Both are accepted by the API
- **File Uploads**: For `profile_image` and `identification_documents`, use `multipart/form-data` content type
- **Data Preservation**: Fields not included in the request will remain unchanged

- **Response**:
  - Success (200): Updated profile data
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```

## Technician Profile Update Instructions

### Overview
The technician profile update system supports **partial updates**, meaning you only need to send the fields you want to change. This prevents data loss and makes updates more efficient.

### 1. Basic Profile Information Updates

#### Update Personal Information
```javascript
// Update phone number only
const updatePhone = async (phoneNumber) => {
    const formData = new FormData();
    formData.append('phone_number', phoneNumber);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};

// Update location information
const updateLocation = async (governorate, address) => {
    const formData = new FormData();
    formData.append('governorate', governorate);
    formData.append('address', address);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};

// Update professional information
const updateProfessional = async (jobTitle, about, yearsOfExpertise) => {
    const formData = new FormData();
    formData.append('job_title', jobTitle);
    formData.append('about', about);
    formData.append('years_of_expertise', yearsOfExpertise);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};
```

#### Update Profile Image
```javascript
// Update profile image
const updateProfileImage = async (imageFile) => {
    const formData = new FormData();
    formData.append('profile_image', imageFile);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

#### Update Identification Documents
```javascript
// Update identification documents
const updateDocuments = async (documentFile) => {
    const formData = new FormData();
    formData.append('identification_documents', documentFile);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

### 2. Skill Set Management

#### Adding New Skill Sets
```javascript
// Add new skill sets to profile
const addSkillSets = async (skillSets) => {
    const formData = new FormData();
    formData.append('skill_sets', JSON.stringify(skillSets));
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};

// Example skill sets data
const newSkillSets = [
    {
        "categories": ["uuid1", "uuid2"],
        "main_skills": ["uuid3", "uuid4"],
        "sub_skills": ["uuid5", "uuid6"]
    }
];
```

#### Updating Existing Skill Sets
```javascript
// Update specific skill set (use dedicated endpoint)
const updateSkillSet = async (skillSetId, updatedData) => {
    await api.put(`/api/accounts/technician/skill-set/${skillSetId}/`, updatedData);
};

// Example: Update categories and skills for a skill set
const updateSkillSetExample = async () => {
    const updatedData = {
        "categories": ["new-uuid1", "new-uuid2"],
        "main_skills": ["new-uuid3", "new-uuid4"],
        "sub_skills": ["new-uuid5", "new-uuid6"]
    };
    
    await updateSkillSet(123, updatedData);
};
```

#### Deleting Skill Sets
```javascript
// Delete a skill set (use dedicated endpoint)
const deleteSkillSet = async (skillSetId) => {
    await api.delete(`/api/accounts/technician/skill-set/${skillSetId}/`);
};
```

### 3. Portfolio Image Management

#### Upload New Portfolio Image
```javascript
// Upload new portfolio image
const uploadPortfolioImage = async (imageFile, description) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('description', description);
    
    await api.post('/api/accounts/technician/TECH-123abc/upload-image/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

#### Update Portfolio Image
```javascript
// Update portfolio image description
const updatePortfolioImage = async (imageId, description) => {
    await api.put(`/api/accounts/technician/image/${imageId}/`, {
        description: description
    });
};

// Update portfolio image file
const updatePortfolioImageFile = async (imageId, imageFile, description) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('description', description);
    
    await api.put(`/api/accounts/technician/image/${imageId}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

#### Delete Portfolio Image
```javascript
// Delete portfolio image
const deletePortfolioImage = async (imageId) => {
    await api.delete(`/api/accounts/technician/image/${imageId}/`);
};
```

### 4. Complete Update Examples

#### Update Multiple Fields at Once
```javascript
// Update multiple profile fields
const updateMultipleFields = async (updates) => {
    const formData = new FormData();
    
    // Add text fields
    if (updates.phone_number) formData.append('phone_number', updates.phone_number);
    if (updates.job_title) formData.append('job_title', updates.job_title);
    if (updates.about) formData.append('about', updates.about);
    if (updates.governorate) formData.append('governorate', updates.governorate);
    if (updates.address) formData.append('address', updates.address);
    if (updates.gender) formData.append('gender', updates.gender);
    if (updates.date_of_birth) formData.append('date_of_birth', updates.date_of_birth);
    if (updates.years_of_expertise) formData.append('years_of_expertise', updates.years_of_expertise);
    if (updates.is_available !== undefined) formData.append('is_available', updates.is_available);
    if (updates.url1) formData.append('url1', updates.url1);
    if (updates.url2) formData.append('url2', updates.url2);
    
    // Add files
    if (updates.profile_image) formData.append('profile_image', updates.profile_image);
    if (updates.identification_documents) formData.append('identification_documents', updates.identification_documents);
    
    // Add skill sets (as JSON string)
    if (updates.skill_sets) formData.append('skill_sets', JSON.stringify(updates.skill_sets));
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

### 5. Frontend Implementation Best Practices

#### Form Handling
```javascript
// React Hook Form example
import { useForm } from 'react-hook-form';

const TechnicianProfileForm = ({ currentProfile }) => {
    const { handleSubmit, register, formState: { dirtyFields } } = useForm({
        defaultValues: currentProfile
    });
    
    const onSubmit = async (data) => {
        // Only send fields that were actually modified
        const changedData = {};
        
        Object.keys(dirtyFields).forEach(field => {
            if (data[field] !== null && data[field] !== undefined && data[field] !== '') {
                changedData[field] = data[field];
            }
        });
        
        if (Object.keys(changedData).length > 0) {
            await updateMultipleFields(changedData);
        }
    };
    
    return (
        <form onSubmit={handleSubmit(onSubmit)}>
            {/* Form fields */}
        </form>
    );
};
```

#### File Upload Handling
```javascript
// Handle file uploads with validation
const handleFileUpload = async (file, fieldName) => {
    // Validate file
    if (file.size > 5 * 1024 * 1024) { // 5MB limit
        throw new Error('File too large. Maximum size is 5MB.');
    }
    
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        throw new Error('Invalid file type. Allowed: JPG, PNG, WebP');
    }
    
    // Upload file
    const formData = new FormData();
    formData.append(fieldName, file);
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};
```

#### Error Handling
```javascript
// Comprehensive error handling
const updateProfile = async (updates) => {
    try {
        await updateMultipleFields(updates);
        showSuccessMessage('Profile updated successfully');
    } catch (error) {
        if (error.response?.status === 400) {
            // Validation errors
            const errors = error.response.data;
            Object.keys(errors).forEach(field => {
                showFieldError(field, errors[field][0]);
            });
        } else if (error.response?.status === 403) {
            showErrorMessage('You do not have permission to update this profile');
        } else if (error.response?.status === 413) {
            showErrorMessage('File too large. Please choose a smaller file.');
        } else {
            showErrorMessage('An error occurred while updating your profile');
        }
    }
};
```

### 6. Available Fields Reference

| Field | Type | Description | Required for Completion |
|-------|------|-------------|------------------------|
| `phone_number` | string | Phone number (Iraqi format) | ✅ Yes |
| `profile_image` | file | Profile picture | ✅ Yes |
| `job_title` | string | Professional title | ✅ Yes |
| `about` | text | Professional description | ✅ Yes |
| `governorate` | string | Location (province) | ✅ Yes |
| `address` | string | Detailed address | ✅ Yes |
| `gender` | string | "male" or "female" | ✅ Yes |
| `date_of_birth` | date | Birth date (YYYY-MM-DD) | ✅ Yes |
| `years_of_expertise` | integer | Years of experience | ✅ Yes |
| `identification_documents` | file | ID documents (ZIP) | ✅ Yes |
| `rate` | decimal | **Auto-calculated** average rating from reviews | ❌ No |
| `is_available` | boolean | Availability status | ❌ No |
| `url1` | string | Portfolio URL 1 | ✅ Yes |
| `url2` | string | Portfolio URL 2 | ✅ Yes |
| `skill_sets` | array | Professional skills | ✅ Yes |

### 7. Skill Set Structure

```json
{
    "skill_sets": [
        {
            "categories": ["uuid1", "uuid2"],
            "main_skills": ["uuid3", "uuid4"],
            "sub_skills": ["uuid5", "uuid6"]
        }
    ]
}
```

**Note**: You can use either `main_skills` or `skills` as the field name. Both are accepted by the API.

### 9. Rate System (Auto-Calculated)

The technician's `rate` field is **automatically calculated** from client reviews and cannot be manually set by users.

#### How the Rate is Calculated
- **Source**: Average rating from all client reviews (1-5 stars)
- **Calculation**: `rate = average(rating1, rating2, rating3, ...)`
- **Precision**: Rounded to 2 decimal places
- **Default**: 0.00 if no reviews exist

#### When Rate is Updated
- **New Review**: Rate is recalculated whenever a client submits a new review
- **Review Update**: Rate is recalculated if an existing review is modified
- **Review Deletion**: Rate is recalculated if a review is deleted

#### Rate in API Responses
```json
{
    "rate": 4.75,  // Average rating from all client reviews
    "reviews": [
        {
            "rating": 5,
            "review_text": "Excellent work!",
            "created_at": "2024-01-15T10:30:00Z"
        },
        {
            "rating": 4,
            "review_text": "Good service",
            "created_at": "2024-01-10T14:20:00Z"
        }
    ]
}
```

#### Frontend Implementation Notes
- **Display**: Show rate as stars or numerical value (e.g., "4.8 ★")
- **Read-only**: Never allow users to edit the rate field
- **Updates**: Rate updates automatically when new reviews are added
- **Validation**: No validation needed - rate is always valid when calculated

### 10. Retrieving Available Skills for UI

```javascript
// Get all categories
const getCategories = async () => {
    const response = await api.get('/api/categories/');
    return response.data;
};

// Get skills for a specific category
const getSkillsForCategory = async (categoryId) => {
    const response = await api.get(`/api/categories/${categoryId}/skills/`);
    return response.data;
};

// Get sub-skills for a specific skill
const getSubSkillsForSkill = async (skillId) => {
    const response = await api.get(`/api/categories/skills/${skillId}/sub-skills/`);
    return response.data;
};
```

### 11. Profile Completion Check

```javascript
// Check profile completion status
const checkProfileCompletion = async () => {
    const response = await api.get('/api/accounts/technician/profile-completion/');
    return response.data;
};

// Example response
{
    "is_profile_complete": false,
    "is_profile_approved": false,
    "incomplete_fields": ["profile_image", "job_title", "skill_sets"],
    "completion_guidance": [
        {
            "field": "profile_image",
            "label": "Profile Image",
            "message": "Please complete the Profile Image field."
        }
    ],
    "completion_percentage": 72.73
}
```

### 12. Critical: Partial Update Guidelines

**⚠️ IMPORTANT**: This endpoint uses `partial=True`, which means you should **ONLY** send the fields you want to update. Sending null/empty values for unchanged fields will **CLEAR** existing data.

#### ❌ WRONG Implementation (Causes Data Loss)
```javascript
// DON'T DO THIS - sends null/empty values that will clear existing data
const updateProfile = async (newJobTitle) => {
    const formData = {
        phone_number: '',           // ← Will clear existing phone number!
        profile_image: null,        // ← Will clear existing image!
        job_title: newJobTitle,     // ← Only field we want to update
        about: '',                  // ← Will clear existing about!
        governorate: null,          // ← Will clear existing governorate!
        address: '',                // ← Will clear existing address!
        gender: null,               // ← Will clear existing gender!
        date_of_birth: null,        // ← Will clear existing date!
        years_of_expertise: 0,      // ← Will clear existing experience!
        is_available: null,         // ← Will clear existing availability!
        url1: '',                   // ← Will clear existing URL!
        url2: '',                   // ← Will clear existing URL!
        identification_documents: null, // ← Will clear existing documents!
        skill_sets: []              // ← Will clear existing skills!
    };
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};
```

#### ✅ CORRECT Implementation (Preserves Existing Data)
```javascript
// CORRECT - only send the field being updated
const updateProfile = async (newJobTitle) => {
    const formData = new FormData();
    formData.append('job_title', newJobTitle);  // ← Only the field we're changing
    
    await api.put('/api/accounts/technician/TECH-123abc/', formData);
};
```

**For more detailed partial update guidelines, see the [Partial Update Guidelines](#partial-update-guidelines-critical-for-clienttechnician-profiles) section above.**

### 2. Client Profile

#### Get Own Profile
- **URL**: `/api/accounts/client/me/`
- **Method**: `GET`
- **Description**: Get the authenticated client's own profile details
- **Authentication**: Required (client only)
- **Request**: No body required
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "user": {
        "username": "string",
        "email": "string",
        "first_name": "string",
        "last_name": "string"
    },
    "phone_number": "string",
    "profile_image": "url|null",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "age": "integer",
    "is_complete": "boolean",
    "is_delete": "boolean",
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    }
}
```
  - Error (403):
```json
{
    "error": "User is not a client"
}
```
- **Frontend Notes**:
  - Use this endpoint to populate client dashboard
  - Show profile completion status with visual indicator
  - Provide quick links to edit profile if incomplete
  - Display wallet balance prominently if available
  - Handle permission errors appropriately
  - **For Technicians**: This endpoint works regardless of admin approval status - technicians can always access their own profile

#### Update Own Profile
- **URL**: `/api/accounts/client/me/`
- **Method**: `PUT`
- **Description**: Partially update the authenticated client's profile. Send only the fields that need to change; all validation rules are identical to the general client-update endpoint.
- **Authentication**: Required (client only)
- **Request Body**:
```json
{
    "phone_number": "string",
    "profile_image": "file|null",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD"
}
```
- **Response**:
  - Success (200): Updated profile data (same schema as *Get Own Profile*)
  - Error (400): Validation errors (field-specific messages)
  - Error (403): `{ "error": "User is not a client" }`
- **Frontend Notes**:
  - Use this for the "Edit Profile" page; no need to include unchanged fields.
  - Upon success, refresh the cached profile and progress indicators.
  - **Critical**: Only send fields that are actually being changed to avoid data loss (see Partial Update Guidelines below)

#### List Clients (Admin Only)
- **URL**: `/api/accounts/clients/`
- **Method**: `GET`
- **Description**: Get list of all clients (admin only)
- **Authentication**: Required (Admin)
- **Request**: No body required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "user": {
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string"
        },
        "phone_number": "string",
        "profile_image": "url|null",
        "governorate": "string",
        "address": "string",
        "gender": "male|female",
        "date_of_birth": "YYYY-MM-DD",
        "age": "integer",
        "is_complete": "boolean",
        "is_delete": "boolean",
        "wallet": {
            "transaction_id": "string",
            "balance": "decimal"
        }
    }
]
```
- **Frontend Notes**:
  - This endpoint may be primarily for admin interfaces
  - Implement filtering and search functionality
  - Display clients in table or card format
  - Use pagination for large datasets
  - Note: Currently this endpoint allows public access in the implementation, but should be restricted to admins for security

#### Get Client Profile
- **URL**: `/api/accounts/client/<uuid:pk>/`
- **Method**: `GET`
- **Description**: Get client profile details
- **Authentication**: Not required, but sensitive data is only shown to the profile owner
- **Request**: No body required
- **Response**:
  - Success (200) for non-owners:
```json
{
    "id": "uuid",
    "user": {
        "first_name": "string",
        "last_name": "string"
    },
    "profile_image": "url|null",
    "governorate": "string",
    "gender": "male|female"
}
```
  - Success (200) for authenticated owner:
```json
{
    "id": "uuid",
    "user": {
        "username": "string",
        "email": "string",
        "first_name": "string",
        "last_name": "string"
    },
    "phone_number": "string",
    "profile_image": "url|null",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "age": "integer",
    "is_complete": "boolean",
    "is_delete": "boolean",
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    }
}
```

#### Update Client Profile
- **URL**: `/api/accounts/client/<uuid:pk>/`
- **Method**: `PUT`
- **Description**: Update client profile
- **Authentication**: Required (Own profile only)
- **Request Body**:
```json
{
    "phone_number": "string",
    "profile_image": "file",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD"
}
```
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "user": {
        "username": "string",
        "email": "string",
        "first_name": "string",
        "last_name": "string"
    },
    "phone_number": "string",
    "profile_image": "url|null",
    "governorate": "string",
    "address": "string",
    "gender": "male|female",
    "date_of_birth": "YYYY-MM-DD",
    "age": "integer",
    "is_complete": "boolean",
    "is_delete": "boolean",
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    }
}
```
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```
  - Error (404):
```json
{
    "detail": "Not found."
}
```
- **Frontend Notes**:
  - Create form with file upload for profile image
  - Implement address input with validation
  - Show real-time validation for phone number
  - Display success message after update
  - Create simple and intuitive profile edit interface
  - **Critical**: Follow Partial Update Guidelines above to avoid data loss during profile updates

## Partial Update Guidelines (Critical for Client/Technician Profiles)

### Overview
All profile update endpoints (`PUT /api/accounts/client/me/`, `PUT /api/accounts/client/<id>/`, `PUT /api/accounts/technician/<id>/`) use **partial updates** with `partial=True`. This means you should only send the fields that are actually being changed.

### ❌ WRONG Implementation (Causes Data Loss)
```javascript
// DON'T DO THIS - sends null/empty values that will clear existing data
const updateProfile = async (newGovernorate) => {
    const formData = {
        phone_number: '',           // ← Will clear existing phone number!
        profile_image: null,        // ← Will clear existing image!
        governorate: newGovernorate, // ← Only field we want to update
        address: '',                // ← Will clear existing address!
        gender: null,               // ← Will clear existing gender!
        date_of_birth: null         // ← Will clear existing date!
    };
    
    await api.put('/api/accounts/client/me/', formData);
};
```

### ✅ CORRECT Implementation (Preserves Existing Data)
```javascript
// CORRECT - only send the field being updated
const updateProfile = async (newGovernorate) => {
    const updateData = {
        governorate: newGovernorate  // ← Only the field we're changing
    };
    
    await api.put('/api/accounts/client/me/', updateData);
};
```

### Frontend Implementation Strategies

#### 1. **Field-Specific Updates**
```javascript
// Update individual fields separately
const updatePhoneNumber = async (phoneNumber) => {
    await api.put('/api/accounts/client/me/', { phone_number: phoneNumber });
};

const updateLocation = async (governorate) => {
    await api.put('/api/accounts/client/me/', { governorate });
};

const updateAddress = async (address) => {
    await api.put('/api/accounts/client/me/', { address });
};
```

#### 2. **Clean Form Data Before Sending**
```javascript
function cleanUpdateData(formData) {
    const cleanData = {};
    
    // Only include fields that have actual values
    Object.keys(formData).forEach(key => {
        const value = formData[key];
        
        // Include field if it has a meaningful value
        if (value !== null && 
            value !== undefined && 
            value !== '' && 
            !(value instanceof File && value.size === 0)) {
            cleanData[key] = value;
        }
    });
    
    return cleanData;
}

// Usage in form submission
const handleSubmit = async (formData) => {
    const updateData = cleanUpdateData(formData);
    
    // Only make API call if there are fields to update
    if (Object.keys(updateData).length > 0) {
        await api.put('/api/accounts/client/me/', updateData);
    }
};
```

#### 3. **Diff-Based Updates (Recommended)**
```javascript
// Compare with current profile and only send changed fields
const updateProfile = async (currentProfile, newFormData) => {
    const changes = {};
    
    // Compare each field
    const fieldsToCheck = [
        'phone_number', 'governorate', 'address', 
        'gender', 'date_of_birth'
    ];
    
    fieldsToCheck.forEach(field => {
        if (newFormData[field] !== currentProfile[field] && 
            newFormData[field] !== null && 
            newFormData[field] !== undefined && 
            newFormData[field] !== '') {
            changes[field] = newFormData[field];
        }
    });
    
    // Handle file uploads separately
    if (newFormData.profile_image instanceof File) {
        changes.profile_image = newFormData.profile_image;
    }
    
    // Only update if there are actual changes
    if (Object.keys(changes).length > 0) {
        await api.put('/api/accounts/client/me/', changes);
    }
};
```

### File Upload Considerations
```javascript
// For file uploads, use FormData and only include the file if selected
const updateProfileImage = async (imageFile) => {
    if (imageFile && imageFile instanceof File) {
        const formData = new FormData();
        formData.append('profile_image', imageFile);
        
        await api.put('/api/accounts/client/me/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
    }
};
```

### Form Library Implementations

#### React Hook Form Example
```javascript
import { useForm } from 'react-hook-form';

const ProfileForm = ({ currentProfile }) => {
    const { handleSubmit, register, formState: { dirtyFields } } = useForm({
        defaultValues: currentProfile
    });
    
    const onSubmit = async (data) => {
        // Only send fields that were actually modified
        const changedData = {};
        
        Object.keys(dirtyFields).forEach(field => {
            if (data[field] !== null && data[field] !== undefined && data[field] !== '') {
                changedData[field] = data[field];
            }
        });
        
        if (Object.keys(changedData).length > 0) {
            await api.put('/api/accounts/client/me/', changedData);
        }
    };
    
    // Form JSX...
};
```

#### Formik Example
```javascript
import { Formik } from 'formik';

const ProfileForm = ({ currentProfile }) => {
    return (
        <Formik
            initialValues={currentProfile}
            onSubmit={async (values, { setSubmitting }) => {
                // Compare with initial values
                const changes = {};
                
                Object.keys(values).forEach(key => {
                    if (values[key] !== currentProfile[key] && 
                        values[key] !== null && 
                        values[key] !== undefined && 
                        values[key] !== '') {
                        changes[key] = values[key];
                    }
                });
                
                if (Object.keys(changes).length > 0) {
                    await api.put('/api/accounts/client/me/', changes);
                }
                
                setSubmitting(false);
            }}
        >
            {/* Form JSX... */}
        </Formik>
    );
};
```

### Common Pitfalls to Avoid

1. **Form Reset Issues**: Don't send empty form values after clearing/resetting forms
2. **Null/Undefined Values**: These will clear existing data in the database
3. **Empty Strings**: Treat as null - don't send unless intentionally clearing a field
4. **File Inputs**: Only send file objects when user actually selects a new file
5. **Default Values**: Don't send default form values that weren't actually filled by user

### Testing Partial Updates

```javascript
// Test scenario: User updates only phone number
const testPartialUpdate = async () => {
    // 1. Get current profile
    const currentProfile = await api.get('/api/accounts/client/me/');
    console.log('Before:', currentProfile.data);
    
    // 2. Update only phone number
    await api.put('/api/accounts/client/me/', {
        phone_number: '07711111111'
    });
    
    // 3. Verify other fields are preserved
    const updatedProfile = await api.get('/api/accounts/client/me/');
    console.log('After:', updatedProfile.data);
    
    // All other fields should remain unchanged
    console.assert(
        updatedProfile.data.governorate === currentProfile.data.governorate,
        'Governorate should be preserved'
    );
    console.assert(
        updatedProfile.data.address === currentProfile.data.address,
        'Address should be preserved'
    );
};
```

### Sequential Updates Example

```javascript
// Example: User updates phone number, then later updates location
const demonstrateSequentialUpdates = async () => {
    // Update 1: Phone number only
    console.log('Updating phone number...');
    await api.put('/api/accounts/client/me/', {
        phone_number: '07722222222'
    });
    
    // Update 2: Location only (phone number should be preserved)
    console.log('Updating location...');
    await api.put('/api/accounts/client/me/', {
        governorate: 'Baghdad'
    });
    
    // Final profile should have both updates
    const finalProfile = await api.get('/api/accounts/client/me/');
    console.log('Final profile:', finalProfile.data);
    // Should show: phone_number: '07722222222', governorate: 'Baghdad'
};
```

### Debugging Update Issues

If you're experiencing data loss during updates:

1. **Check Network Tab**: Verify you're only sending the intended fields
2. **Log Request Data**: Console.log the data being sent before API call
3. **Compare Before/After**: Get profile before and after update to verify
4. **Test with Simple Updates**: Start with single-field updates to isolate the issue

### Dealership Profile

#### List Dealerships
- **URL**: `/api/accounts/dealerships/`
- **Method**: `GET`
- **Description**: Get list of all dealerships
- **Authentication**: Not required
- **Request**: No body required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "user": {
            "first_name": "string",
            "last_name": "string"
        },
        "company_name": "string",
        "profile_image": "url|null",
        "governorate": "string",
        "about": "string"
    }
]
```

#### Get Dealership Profile
- **URL**: `/api/accounts/dealership/<uuid:pk>/`
- **Method**: `GET`
- **Description**: Get dealership profile details
- **Authentication**: Not required (but some fields are only visible to authenticated owners)
- **Request**: No body required
- **Response**:
  - Success (200) for public/non-owner view:
```json
{
    "id": "uuid",
    "user": {
        "first_name": "string",
        "last_name": "string"
    },
    "company_name": "string",
    "profile_image": "url|null",
    "governorate": "string",
    "about": "string"
}
```
  - Success (200) for authenticated owner or admin:
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
    "company_name": "string",
    "company_registration_number": "string",
    "profile_image": "url|null",
    "phone_number": "string",
    "address": "string",
    "governorate": "string",
    "about": "string",
    "is_complete": "boolean",
    "is_delete": "boolean",
    "wallet": {
        "transaction_id": "string",
        "balance": "decimal"
    },
    "is_profile_complete": "boolean",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

#### Update Dealership Profile
- **URL**: `/api/accounts/dealership/<uuid:pk>/`
- **Method**: `PUT`
- **Description**: Update dealership profile
- **Authentication**: Required (owner only)
- **Request Body**:
```json
{
    "company_name": "string",
    "company_registration_number": "string",
    "profile_image": "file|null",
    "phone_number": "string",
    "address": "string",
    "governorate": "string",
    "about": "string"
}
```
- **Response**:
  - Success (200): Updated profile data
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```

## Image Management

### 1. Upload Technician Image
- **URL**: `/api/accounts/technician/<uuid:technician_id>/upload-image/` or `/api/accounts/technician/<public_id>/upload-image/` or `/api/accounts/technician/<uuid_suffix>/upload-image/`
- **Method**: `POST`
- **Description**: Upload technician portfolio image (supports full UUID, public_id format like "TECH-123abc", or UUID suffix like "fd68eb")
- **Authentication**: Required (owner only)
- **File Validation**:
  - Maximum file size: 5MB
  - Allowed formats: JPG, JPEG, PNG, WebP
  - Minimum dimensions: 200x200 pixels
  - Maximum dimensions: 2000x2000 pixels
- **Request Body**: Form data with fields:
```json
{
    "image": "file",
    "description": "string"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "integer",
    "image": "url",
    "description": "string"
}
```
  - Error (400):
```json
{
    "image": ["File size too large. Maximum size is 5MB."]
}
```
```json
{
    "image": ["Invalid image format. Allowed formats are JPG, JPEG, PNG, WebP."]
}
```
```json
{
    "image": ["Image dimensions must be between 200x200 and 2000x2000 pixels."]
}
```
  - Error (403):
```json
{
    "detail": "You do not have permission to upload images for this technician."
}
```
  - Error (413):
```json
{
    "detail": "Request Entity Too Large"
}
```

### 2. Update/Delete Technician Image
- **URL**: `/api/accounts/technician/image/<int:image_id>/`
- **Methods**: `PUT`, `DELETE`
- **Description**: Update or delete technician portfolio image
- **Authentication**: Required (owner only)
- **Request Body** (PUT):
```json
{
    "description": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "id": "integer",
    "image": "url",
    "description": "string"
}
```
  - Success (204): No content (DELETE)
  - Error (403):
```json
{
    "detail": "You do not have permission to edit/delete this image."
}
```

### Portfolio Image Management

Technician portfolio images (work samples, credentials, etc.) are managed through dedicated endpoints separate from the main profile endpoint. This separation allows for more efficient handling of multiple images and keeps the main profile update lightweight.

#### Adding Portfolio Images
1. **Upload a new portfolio image**:
   - **Endpoint**: `POST /api/accounts/technician/<technician_id>/upload-image/` 
   - **ID Formats**: The endpoint supports these formats:
     - Full UUID: `f423472e-341e-4c29-8cf6-aed471fd68eb`
     - Public ID: `TECH-fd68eb`
     - UUID Suffix: `fd68eb`
   - **Request**: Form data with `image` file and optional `description`
   - **Response**: Returns the created image object with ID, URL, and description
   - **Example**:
   ```
   curl -X POST \
     -H "Authorization: Bearer {your_token}" \
     -F "image=@/path/to/image.jpg" \
     -F "description=Project screenshot" \
     http://example.com/api/accounts/technician/fd68eb/upload-image/
   ```

### 3. Update/Delete Skill Set
- **URL**: `/api/accounts/technician/skill-set/<int:skill_set_id>/`
- **Methods**: `PUT`, `DELETE`
- **Description**: Update or delete a technician's skill set
- **Authentication**: Required (owner only)
- **Request Body** (PUT):
```json
{
    "categories": ["uuid"],
    "main_skills": ["uuid"],
    "sub_skills": ["uuid"]
}
```
- **Response**:
  - Success (200):
```json
{
    "id": "integer",
    "categories": ["uuid"],
    "main_skills": ["uuid"],
    "sub_skills": ["uuid"]
}
```
  - Success (204): No content (DELETE)
  - Error (403):
```json
{
    "detail": "You do not have permission to edit/delete this skill set."
}
```
  - Error (400) when trying to delete last skill set:
```json
{
    "detail": "Cannot delete the last skill set. Technicians must have at least one skill set."
}
```

**Frontend Notes**:
- For image updates:
  - Create form with file upload for image
  - Allow updating description without changing image
  - Show preview of current and new image
  - Implement proper file validation
  - Show loading state during upload
  - Handle errors appropriately

- For skill set updates:
  - Create dynamic form for selecting categories, skills, and sub-skills
  - Allow updating individual fields (categories, main skills, or sub-skills)
  - Show current selections
  - Validate that at least one skill set remains after deletion
  - Update profile completion status after changes
  - Show appropriate success/error messages

## Profile Completion Requirements

### Overview
To use most features of the platform (contracts, payments, chat), users must complete their profiles with required information. The system automatically checks if a profile is complete before allowing access to these features.

### Client Profile Completion Requirements
For a Client profile to be considered complete, **all** of the following fields must be filled:
- Phone number
- Profile image (avatar)
- Governorate (province)
- **Address** (street / city detail)
- Gender (male or female)
- Date of birth (user must be at least 18 years old)

If any of these are missing, `is_profile_complete` and `is_complete` will both be `false`, and the API will deny access to certain endpoints (e.g. technician list, contract creation).

### Technician Profile Completion Requirements
For a Technician profile to be considered complete, the following fields must be filled:
- Phone number
- Profile image
- Governorate (province)
- About (description)
- Job title (professional title or role)
- Address
- Gender (male or female)
- Date of birth (user must be at least 18 years old)
- Years of expertise (must be greater than 0)
- Identification documents (ZIP file containing required identification documents)
- Portfolio URL 1 (url1)
- Portfolio URL 2 (url2)
- At least one skill set must be added

### Dealership Profile Completion Requirements
For a Dealership profile to be considered complete, the following fields must be filled:
- Company name
- Company registration number
- Profile image
- Phone number
- Address
- Governorate
- About description

The `is_complete` flag will be automatically updated when all required fields are filled, but final verification by an administrator is required before the dealership can process payments.

### Completion Status
The profile completion status is represented in two ways:
1. `is_complete` field: Boolean flag that is officially set by administrators after verifying identification documents
2. `is_profile_complete` field: Boolean that indicates if all required fields are filled

`is_complete` for clients now mirrors `is_profile_complete` — it is automatically recalculated on every profile update and **cannot** be manually set to `true` while required fields are still missing. Administrators no longer need to toggle this for clients.

When a client updates their profile via `/client/me/` or `/client/<id>/`, the backend reevaluates completion; once all required data is present `is_complete` flips to `true` and the user can immediately access technician-related features.

When updating a profile through the API, the system will automatically check if all required fields are completed and update the `is_profile_complete` flag accordingly. The `is_complete` flag can only be set by administrators after verifying the submitted identification documents.

### Error Messages
If a user tries to access a protected feature without a complete profile, they will receive a 403 Forbidden response:
```json
{
    "error": "You must complete your profile before accessing this feature.",
    "profile_status": "incomplete"
}
```

### Frontend Implementation
Frontend applications should:
1. Check profile completion status when a user logs in
2. Direct users to complete their profiles if needed before accessing protected features
3. Show clear indicators of which fields are missing
4. Implement progressive profile completion interfaces
5. Show helpful error messages explaining why certain features are restricted

### Rate Limiting and Security
1. **Profile Update Rate Limiting**:
   - Maximum 10 profile updates per hour
   - Maximum 3 profile image updates per day
   - Maximum 5 failed update attempts before temporary lockout (1 hour)

2. **File Upload Security**:
   - Profile Images:
     * Maximum size: 5MB
     * Allowed formats: JPG, JPEG, PNG, WebP
     * Dimensions: 200x200 to 2000x2000 pixels
   - Identification Documents:
     * Maximum size: 10MB
     * Allowed formats: ZIP
     * Maximum files in ZIP: 10
     * Allowed file types in ZIP: PDF, JPG, JPEG, PNG
     * Maximum individual file size in ZIP: 2MB

3. **Input Validation**:
   - Phone number: Must match Iraqi format (077/078/075 + 8 digits)
   - Email: Valid format and domain verification
   - Password: Minimum 8 characters, must include uppercase, lowercase, number, special character
   - Text fields: Maximum lengths
     * About: 1000 characters
     * Address: 255 characters
     * Description: 255 characters
     * URLs: 255 characters

4. **Error Handling**:
   - Validation Errors (400):
```json
{
    "field_name": ["Specific validation error message"]
}
```
   - Rate Limit Errors (429):
```json
{
    "error": "Too many requests. Please try again in X minutes.",
    "retry_after": "timestamp"
}
```
   - File Upload Errors (413):
```json
{
    "error": "File too large. Maximum size is XMB."
}
```
   - Permission Errors (403):
```json
{
    "error": "You do not have permission to perform this action."
}
```

## Data Privacy and Security

### Sensitive Personal Information
The following fields are considered sensitive personal information and should be protected:
- Technician/Client ID (UUID)
- Email address
- Phone number
- Full address
- Identification documents
- Date of birth
- Wallet information and balance

### Public Information
The following profile fields are considered public and visible to all users:
- Public ID (masked version of the actual ID)
- First name and last name
- Profile image
- Governorate (province/city)
- Gender
- For technicians: About description, skills, rate, reviews, years of expertise, availability status

### Access Control
- **Public access**: Only public information is displayed in public views or search results
- **Owner access**: Users should only see their own sensitive information
- **Admin access**: System administrators have access to sensitive information for moderation and support purposes

### Implementation Guidelines
1. **API Serializers**: The backend implements context-aware serializers that filter sensitive fields based on the viewer's role
2. **Frontend Security**: The frontend must respect these privacy boundaries and never display sensitive information to unauthorized users
3. **Data Transmission**: All API calls handling sensitive data must use HTTPS
4. **Data Storage**: Client-side storage should encrypt any cached sensitive user information
5. **Error Handling**: Error messages should not expose sensitive information

### Regulatory Compliance
These privacy measures ensure compliance with data protection regulations that require appropriate safeguards for personal information.

## Frontend Implementation Notes

### Governorate Selection
The governorate field for both Client and Technician profiles should be implemented as a dropdown list with the following available options:
```
Baghdad (بغداد)
Basra (البصرة)
Nineveh (نينوى)
Erbil (أربيل)
Sulaymaniyah (السليمانية)
Kirkuk (كركوك)
Duhok (دهوك)
Najaf (النجف)
Karbala (كربلاء)
Anbar (الأنبار)
Babil (بابل)
Maysan (ميسان)
Wasit (واسط)
Dhi Qar (ذي قار)
Muthanna (المثنى)
Qadisiyyah (القادسية)
Salah al-Din (صلاح الدين)
Diyala (ديالى)
```

**Implementation Notes**:
- The backend stores the English name (e.g., "Baghdad") as the value
- The frontend should display the Arabic name (e.g., "بغداد") to the user
- When submitting forms, use the English name as the value
- The governorate field is required during registration for both client and technician users
- In API responses, the governorate is returned with both the English key and Arabic display value

**Example API Usage**:
```javascript
// When registering a user
const formData = {
  // other fields...
  governorate: "Baghdad" // Use English name as value
};

// When displaying a profile
// The API returns both formats
const displayName = profile.governorate; // "بغداد" (Arabic display name)
```

### Profile Forms
For both Client and Technician profile forms:
- Implement full address as a text field for detailed location information
- Use the governorate dropdown for province selection
- Consider adding map integration for precise location selection
- Show appropriate validation for phone number (must be 11 digits starting with 075, 077, or 078)

### Gender Selection
The gender field for both Client and Technician profiles should be implemented as a dropdown/radio button selection with the following options:
- Male (male)
- Female (female)

**Important Privacy Note**: Gender is considered public information and can be displayed to all users.

### Date of Birth
The date of birth field should be implemented with the following considerations:
- Use a date picker component that allows selecting dates from a calendar
- Validate that the user is at least 18 years old
- Format the date as YYYY-MM-DD when sending to the API
- Display the calculated age (if needed) based on the date of birth

**Important Privacy Note**: Date of birth and age are considered sensitive personal information and should only be displayed to the profile owner and administrators. They should not be shown in public profile views. Unlike date of birth and age, gender is considered public information and can be shown in all profile views.

### Access to Technician List for Clients

### Contact-Technician Guard (Clients)

Clients can browse the marketplace (technician list) even if their profile is incomplete, **but** they cannot initiate contact with a technician until the required profile fields are provided.  
`POST /api/chat/rooms/create/` will return **403** for an incomplete client profile (see Chat docs for the exact payload).

Recommended frontend UX:
1. On login fetch `/api/accounts/client/me/` and cache `is_complete`.  
2. If **false**, show a persistent banner (or profile-completion page) prompting the user to finish their profile before they can book or chat.  
3. Keep the marketplace routes accessible; when the user taps "Contact Technician" handle the 403 response by opening the same completion prompt.

---

## How to Update a Client Profile (step-by-step)

Endpoint: `PUT /api/accounts/client/me/` (partial update)  
Auth: `Bearer <access_token>`

Required fields for completion:
| Field | Notes |
|-------|-------|
| `phone_number` | Iraqi format: 11 digits starting with 075 / 077 / 078 |
| `profile_image` | JPG / PNG / WebP ≤ 5 MB, 200-2000 px |
| `governorate` | **English key** from list (e.g. `"Baghdad"`) |
| `address` | Free-text street / city detail |
| `gender` | `"male"` or `"female"` |
| `date_of_birth` | `YYYY-MM-DD`, must be ≥ 18 years old |

Example request (cURL, JSON-only fields):
```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "phone_number": "07712345678",
        "governorate": "Baghdad",
        "address": "Al-Karrada, St. 62, House 10",
        "gender": "male",
        "date_of_birth": "1990-05-14"
      }' \
  https://api.example.com/api/accounts/client/me/
```

Uploading / changing the avatar:
```bash
curl -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -F profile_image=@/path/to/avatar.jpg \
  https://api.example.com/api/accounts/client/me/
```

Response: **200** with the updated profile (same schema as *Get Own Profile*).  
If any validation fails you'll receive **400** with field-specific error messages.

Once all required fields are present the backend automatically sets both `is_profile_complete` and `is_complete` to **true**. The next attempt to open "Contact Technician" will succeed.

## Technician Approval System

### Overview {#technician-approval-overview}
The technician approval system ensures quality control by requiring administrator approval before technicians appear in public listings. Only technicians with complete profiles and administrator approval are visible to clients.

**Approval Workflow:**
1. Technician completes registration and profile
2. Profile appears in admin approval queue with `approved=false`
3. Administrator reviews profile and documents
4. Administrator approves or rejects the technician
5. System automatically sends notification to technician about the decision
6. Approved technicians (`approved=true`) become visible in public listings

**Important Notes:**
- **Profile Access**: Technicians can always access and edit their own profile regardless of approval status
- **Public Visibility**: Only approved technicians appear in public listings and search results
- **Approval Persistence**: Once approved by an admin, the approval status is protected from accidental changes during profile updates

**Permission Requirements:**
- Only **System Administrators** and **Account Managers** can approve/reject technicians
- All admin roles can view approval statistics
- Technician listings are automatically filtered based on approval status

### List Technicians for Approval
- **URL**: `/api/accounts/admin/technicians/approval/`
- **Method**: `GET`
- **Description**: List all technicians with their approval status for admin review
- **Authentication**: Required (System Admin or Account Manager only)
- **Permission**: Only System Administrators and Account Managers can access this endpoint

**Query Parameters:**
- `approval_status` (optional): Filter by approval status
  - Values: `all`, `pending`, `approved`, `rejected`
  - Default: `all`
- `completion_status` (optional): Filter by profile completion
  - Values: `all`, `complete`, `incomplete` 
  - Default: `all`

**Response:**
- Success (200):
```json
{
    "count": 15,
    "technicians": [
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "public_id": "TECH-a1b2c3d4e5f6",
            "user": {
                "id": 42,
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "is_active": true,
                "date_joined": "2024-01-15T10:30:00Z"
            },
            "approved": false,
            "is_complete": true,
            "is_available": true,
            "phone_number": "07712345678",
            "job_title": "Full Stack Developer",
            "governorate": "Baghdad",
            "years_of_expertise": 5,
            "profile_url": "/media/technicians/profile_images/aed471fd68eb.png",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-20T14:45:00Z",
            "last_active": "2024-01-25T09:15:00Z",
            "profile_completion_status": {
                "is_complete": true,
                "missing_fields": [],
                "completion_percentage": 100.0
            },
            "identification_documents_url": "/media/technicians/identification_docs/a1b2c3d4e5f6_identification.zip"
        }
    ]
}
```
- Error (403):
```json
{
    "detail": "Your admin role does not have permission to manage technician approvals."
}
```

**Frontend Implementation Notes:**
- **Approval Queue Interface**: Create a dedicated approval management interface
- **Filter Controls**: Implement filter dropdowns for approval and completion status
- **Profile Completion**: Display completion percentage with visual indicators:
  - Green (90-100%): Ready for approval
  - Yellow (70-89%): Nearly complete
  - Red (0-69%): Needs completion
- **Document Access**: Provide "Download Documents" button for verification
- **Action Buttons**: Include "Approve" and "Reject" buttons for eligible profiles
- **Status Indicators**: Use color-coded badges for approval status
- **Bulk Actions**: Consider implementing bulk approval for efficiency

### Approve/Reject Technician
- **URL**: `/api/accounts/admin/technicians/<technician_id>/approval/`
- **Method**: `POST`
- **Description**: Approve or reject a technician for public listings. Automatically sends notification to technician via email, push, and in-app channels.
- **Authentication**: Required (System Admin or Account Manager only)
- **Permission**: Only System Administrators and Account Managers can perform this action

**Request Body:**
```json
{
    "action": "approve|reject"
}
```

**Response:**
- Success (200):
```json
{
    "message": "Technician John Doe has been approved.",
    "technician": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "public_id": "TECH-a1b2c3d4e5f6",
        "user": {
            "username": "johndoe",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "is_active": true
        },
        "approved": true,
        "is_complete": true,
        "updated_at": "2024-01-25T15:30:00Z"
    },
    "notification_sent": true
}
```

**Note**: The system automatically sends a notification to the technician via email, push notification, and in-app notification informing them of the approval/rejection decision.
- Error (400):
```json
{
    "detail": "Technician profile is incomplete. Only complete profiles can be approved."
}
```
- Error (403):
```json
{
    "detail": "Your admin role does not have permission to manage technician approvals."
}
```
- Error (404):
```json
{
    "detail": "Technician not found."
}
```

**Frontend Implementation Notes:**
- **Confirmation Dialogs**: Show confirmation before approve/reject actions
- **Reason for Rejection**: Consider adding optional rejection reason field
- **Instant Feedback**: Display success/error messages immediately
- **Status Updates**: Refresh the technician list after actions
- **Audit Trail**: Log approval actions for accountability
- **Automatic Notifications**: System automatically sends multi-channel notifications to technicians:
  - **Approval**: Congratulatory email/push/in-app notification with next steps
  - **Rejection**: Guidance email/push/in-app notification with improvement suggestions
  - **Channels**: Email, push notifications, and in-app notifications
  - **Action URLs**: Direct links to profile view (approval) or edit page (rejection)

### Technician Approval Statistics
- **URL**: `/api/accounts/admin/technicians/approval/stats/`
- **Method**: `GET`
- **Description**: Get statistics about technician approvals for dashboard
- **Authentication**: Required (Admin only)
- **Permission**: All admin roles can view statistics

**Response:**
- Success (200):
```json
{
    "total_technicians": 45,
    "complete_technicians": 38,
    "approved_technicians": 32,
    "pending_approval": 6,
    "incomplete_technicians": 7,
    "approval_rate": 84.2,
    "recent_activity": {
        "new_registrations_30_days": 8,
        "approvals_30_days": 5
    }
}
```

**Frontend Implementation Notes:**
- **Dashboard Cards**: Display key metrics as dashboard cards
- **Progress Indicators**: Show approval rate with progress bars
- **Trend Charts**: Visualize registration and approval trends
- **Quick Actions**: Provide shortcuts to approval queue from stats
- **Real-time Updates**: Refresh statistics periodically
- **Export Options**: Allow exporting statistics for reporting

### Approval System Permissions
The technician approval system implements role-based access control:

| Action | System Admin | Account Manager | Content Moderator | Finance Admin |
|--------|-------------|----------------|------------------|---------------|
| View Approval Queue | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Approve Technicians | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| Reject Technicians | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| View Statistics | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| Download Documents | ✅ Yes | ✅ Yes | ❌ No | ❌ No |

**Implementation Security Notes:**
- All approval endpoints verify admin authentication
- Role-based permissions are enforced server-side
- Approval actions are logged for audit purposes
- Only complete profiles can be approved
- Document access is restricted to authorized roles

## Admin Accounts

### Overview
Administrator accounts in the Tiqani platform are Django staff/superuser accounts with elevated privileges to manage the system. Administrators primarily use the Django admin interface rather than the regular frontend application.

### Administrator Roles
The platform supports different administrator roles with varying levels of permission:
1. **System Administrator**: Full system access and control
2. **Content Moderator**: Focused on content review and moderation
3. **Account Manager**: Focused on user account management
4. **Financial Administrator**: Focused on financial operations

### Admin Profile Completion Requirements
For an Admin profile to be considered complete, the following fields must be filled:
- Profile image
- Phone number
- Governorate (location)

While other profile fields like address, gender, and date of birth are optional for admins, completing the required fields helps maintain consistency across the platform and ensures admins have proper contact information available.

The `is_profile_complete` flag will be automatically updated when all required fields are filled. Admin users can check their profile completion status through the profile completion API endpoint.

### Administrator Creation
Administrators can be created through:
1. **Django Command Line**:
```bash
python manage.py createsuperuser
```

2. **Django Admin Panel**:
   - Navigate to Users section and create a new user with "Staff status" checked
   - Edit the user to add an Admin Profile with the appropriate role
   - Alternatively, go to the Admin Profiles section and create a new profile for an existing staff user

3. **Admin API (Superuser Only)**:
- **URL**: `/api/accounts/admins/create/`
- **Method**: `POST`
- **Description**: Create a new admin user
- **Authentication**: Required (Superuser only)
- **Request Body**:
```json
{
    "username": "string",
    "email": "string",
    "password": "string",
    "confirm_password": "string",
    "first_name": "string",
    "last_name": "string",
    "role": "system_admin|content_moderator|account_manager|finance_admin",
    "is_superuser": boolean,
    "profile_image": "file|null",
    "phone_number": "string|null",
    "governorate": "string|null",
    "address": "string|null",
    "gender": "male|female|null",
    "date_of_birth": "YYYY-MM-DD|null",
    "notes": "string|null"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "uuid",
    "user": {
        "id": "integer",
        "username": "string",
        "email": "string",
        "first_name": "string",
        "last_name": "string",
        "is_staff": true,
        "is_superuser": boolean,
        "date_joined": "datetime",
        "last_login": "datetime"
    },
    "role": "string",
    "role_display": "string",
    "profile_image": "url|null",
    "phone_number": "string|null",
    "governorate": "string|null",
    "governorate_display": "string|null",
    "address": "string|null",
    "gender": "male|female|null",
    "date_of_birth": "YYYY-MM-DD|null",
    "age": "integer|null",
    "is_profile_complete": "boolean",
    "notes": "string|null",
    "last_login_ip": "string|null",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

### Administrator API Endpoints

#### List Administrators
- **URL**: `/api/accounts/admins/`
- **Method**: `GET`
- **Description**: List all admin profiles
- **Authentication**: Required (System Administrator role only)
- **Permission**: Only users with the System Administrator role can access this endpoint
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "user": {
            "id": "integer",
            "username": "string",
            "email": "string",
            "first_name": "string",
            "last_name": "string",
            "is_staff": true,
            "is_superuser": boolean,
            "date_joined": "datetime",
            "last_login": "datetime"
        },
        "role": "string",
        "role_display": "string",
        "profile_image": "url|null",
        "phone_number": "string|null",
        "governorate": "string|null",
        "governorate_display": "string|null",
        "address": "string|null",
        "gender": "male|female|null",
        "date_of_birth": "YYYY-MM-DD|null",
        "age": "integer|null",
        "is_profile_complete": "boolean",
        "notes": "string|null",
        "last_login_ip": "string|null",
        "created_at": "datetime",
        "updated_at": "datetime"
    }
]
```
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```

#### Get Current Admin Profile
- **URL**: `/api/accounts/admins/me/`
- **Method**: `GET`
- **Description**: Get the current admin's profile
- **Authentication**: Required (Admin only)
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
        "last_name": "string",
        "is_staff": true,
        "is_superuser": boolean,
        "date_joined": "datetime",
        "last_login": "datetime"
    },
    "role": "string",
    "role_display": "string",
    "profile_image": "url|null",
    "phone_number": "string|null",
    "governorate": "string|null",
    "governorate_display": "string|null",
    "address": "string|null",
    "gender": "male|female|null",
    "date_of_birth": "YYYY-MM-DD|null",
    "age": "integer|null",
    "is_profile_complete": "boolean",
    "notes": "string|null",
    "last_login_ip": "string|null",
    "created_at": "datetime",
    "updated_at": "datetime"
}
```

#### Get/Update/Delete Admin Profile
- **URL**: `/api/accounts/admins/<uuid:pk>/`
- **Methods**: `GET`, `PUT`, `PATCH`, `DELETE`
- **Description**: Retrieve, update or delete an admin profile
- **Authentication**: Required (System Administrator role only)
- **Permission**: Only users with the System Administrator role can access this endpoint
- **Request Body** (PUT/PATCH):
```json
{
    "role": "system_admin|content_moderator|account_manager|finance_admin",
    "profile_image": "file|null",
    "phone_number": "string|null",
    "governorate": "string|null",
    "address": "string|null",
    "gender": "male|female|null",
    "date_of_birth": "YYYY-MM-DD|null",
    "notes": "string|null"
}
```
- **Response**:
  - Success (200 for GET/PUT/PATCH, 204 for DELETE)
  - Error (403):
```json
{
    "detail": "You do not have permission to perform this action."
}
```

#### Admin Profile Completion Check
- **URL**: `/api/accounts/admins/profile-completion/`
- **Method**: `GET`
- **Description**: Get detailed guidance on what fields need to be completed for the admin profile
- **Authentication**: Required (admin only)
- **Request**: No body required
- **Response**:
  - Success (200):
```json
{
    "is_profile_complete": false,
    "incomplete_fields": ["profile_image", "phone_number", "governorate"],
    "completion_guidance": [
        {
            "field": "profile_image",
            "label": "Profile Image",
            "message": "Please complete the Profile Image field."
        },
        {
            "field": "phone_number",
            "label": "Phone Number",
            "message": "Please complete the Phone Number field."
        },
        {
            "field": "governorate",
            "label": "Governorate (Location)",
            "message": "Please complete the Governorate (Location) field."
        }
    ],
    "completion_percentage": 0.0
}
```
  - Error (403):
```json
{
    "error": "User is not an admin"
}
```
- **Frontend Notes**:
  - Use this endpoint to provide a profile completion dashboard for admin users
  - Display a progress bar using the `completion_percentage` value
  - Show a checklist of fields to complete with the messages from `completion_guidance`
  - Provide direct links to edit each incomplete field
  - Reset and check completion status after each profile update
  - The completion percentage is calculated based on 3 required fields for profile completion

### Administrator Permissions
Administrator accounts are identified by the following flags on the Django User model:
- `is_staff=True`: Grants access to the admin interface
- `is_superuser=True`: Grants all permissions in the system

### Administrator Features
Administrators have access to specialized functionality:
1. **User Management**:
   - Approve or reject technician profiles by setting the `is_complete` flag
   - Activate/deactivate user accounts by modifying the `is_active` flag
   - Review user profiles and content

2. **Content Management**:
   - Manage categories, skills, and sub-skills
   - Monitor and moderate reviews
   - Review technician portfolios

3. **System Management**:
   - Access to all models through the admin interface
   - Configuration of system settings
   - Monitoring of logs and system health

4. **Financial Oversight**:
   - View all wallet transactions
   - Resolve payment disputes
   - Monitor contract status

### API Permissions
Many API endpoints have permission checks that only allow admin users to access certain functionality:

```python
if not request.user.is_staff:
    return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
```

### Admin Interface
Administrators have a customized Django admin interface with specialized views for:
- User management
- Content review
- Transaction monitoring
- System configuration

The Django admin interface provides comprehensive management for all profile types:

1. **User Management**:
   - Create and manage users with different profile types (Client, Technician, Admin, Dealership)
   - When editing a user, the appropriate profile inline editor will be shown based on user type
   - Staff users will see the Admin Profile inline editor

2. **Profile Management**:
   - Each profile type has its own dedicated section in the admin:
     * Client Profiles - manage client user details and account status
     * Technician Profiles - manage technician details, skills, and portfolio images
     * Admin Profiles - manage administrator roles and permissions
     * Dealership Profiles - manage payment service provider details

3. **Financial Management**:
   - Exchange Rates - set and monitor currency exchange rates
   - Wallet Management - view and adjust user wallet balances
   - Transaction History - review all financial transactions in the system
   - System Configuration - adjust platform and payment processing fees

### Technician Profile Completion Check
- **URL**: `/api/accounts/technician/profile-completion/`
- **Method**: `GET`
- **Description**: Get detailed guidance on what fields need to be completed for the technician profile
- **Authentication**: Required (technician only)
- **Request**: No body required
- **Response**:
  - Success (200):
```json
{
    "is_profile_complete": false,
    "is_profile_approved": false,
    "incomplete_fields": ["profile_image", "job_title", "skill_sets"],
    "completion_guidance": [
        {
            "field": "profile_image",
            "label": "Profile Image",
            "message": "Please complete the Profile Image field."
        },
        {
            "field": "job_title",
            "label": "Job Title/Professional Role",
            "message": "Please complete the Job Title/Professional Role field."
        },
        {
            "field": "skill_sets",
            "label": "Professional Skills",
            "message": "Add at least one skill set with categories, skills, and sub-skills."
        }
    ],
    "completion_percentage": 72.73
}
```
  - Error (403):
```json
{
    "error": "User is not a technician"
}
```
- **Frontend Notes**:
  - Use this endpoint to provide a profile completion dashboard for technicians
  - Display a progress bar using the `completion_percentage` value
  - Show a checklist of fields to complete with the messages from `completion_guidance`
  - Provide direct links to edit each incomplete field
  - Display a prominent message when the profile is complete but waiting for admin approval (`is_profile_complete=true` but `is_profile_approved=false`)
  - Reset and check completion status after each profile update
  - The completion percentage is calculated based on the 11 required fields for profile completion

Note: Dashboard-related functionality (Currency Exchange System, Exchange Rate Management, Fee Structure, Admin Dashboard, and User Management API) has been moved to the dashboard app.

## Notification System Integration

The technician approval system includes comprehensive notification functionality to keep technicians informed about their profile status.

### Notification Types

#### Profile Approved (`technician_approved`)
- **Trigger**: When an admin approves a technician profile
- **Channels**: Email, Push, In-App
- **Content**: Congratulatory message with next steps
- **Action URL**: `/profile/technician` (technician's profile page)

#### Profile Rejected (`technician_rejected`)
- **Trigger**: When an admin rejects a technician profile
- **Channels**: Email, Push, In-App  
- **Content**: Guidance on required updates
- **Action URL**: `/profile/edit` (profile editing page)

### Notification Content Templates

**Approval Notification:**
```
Subject: Congratulations! Your Profile Has Been Approved
Body: Great news! Your technician profile has been approved by our admin team. 
      You are now visible to clients and can start receiving project requests.

What you can do now:
- Your profile is now publicly visible
- Clients can contact you for projects
- You can receive and accept contract offers

Thank you for being part of the Tiqani community!
```

**Rejection Notification:**
```
Subject: Profile Review Update Required
Body: Thank you for submitting your technician profile. After reviewing your 
      application, we need you to make some updates before we can approve your profile.

Next steps:
- Review your profile information for accuracy
- Ensure all required fields are completed
- Upload clear identification documents if needed
- Contact our support team if you need assistance

Once you've made the necessary updates, our team will review your profile again.
```

### Notification Context Data

When notifications are sent, they include the following context data:
- **user**: Technician's user object (name, email, etc.)
- **admin_name**: Name of the admin who performed the action
- **profile_completion_percentage**: Current completion percentage of the profile

### Notification Preferences

- **Default Settings**: All channels (Email, Push, In-App) are enabled by default for approval notifications
- **User Customization**: Technicians can modify their notification preferences through their account settings
- **Quiet Hours**: System respects user's quiet hours for push/email notifications
- **Failure Handling**: Notification failures don't affect the approval process - the approval/rejection will still be processed

### Integration with Frontend

**Notification Display:**
- In-app notifications appear in the user's notification center
- Push notifications are sent to registered devices
- Email notifications are sent to the user's registered email address

**Action Handling:**
- Approval notifications link to the technician's profile page
- Rejection notifications link to the profile editing page
- Notifications include direct action URLs for seamless user experience

### Error Handling

- Notification failures are logged but don't block the approval process
- Failed notifications are recorded in the delivery logs for debugging
- Retry mechanisms can be implemented for failed notifications

### Security Considerations

- **Permission-based access control**: Only authorized admin roles can approve/reject technicians
- **Audit logging**: All approval actions are logged for accountability
- **Profile validation**: System checks completion percentage to guide decision making
- **Status filtering**: Non-admin users only see approved technicians in public listings
- **Notification security**: Notifications include user-specific context and proper authentication
- **Privacy protection**: Notification content does not expose sensitive user data

