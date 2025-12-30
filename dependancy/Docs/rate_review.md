# Rate & Review API Documentation

## Table of Contents
- [Overview](#overview)
- [Endpoints](#endpoints)
  - [Create Review](#create-review)
- [Review Data in Technician Profile](#review-data-in-technician-profile)
- [Features](#features)
- [Frontend Implementation Guidelines](#frontend-implementation-guidelines)
  - [Implementation Status](#implementation-status)
  - [Integration Points](#integration-points)
  - [UI/UX Best Practices](#uiux-best-practices)

## Overview
The Rate & Review system allows clients to rate and review technicians they've worked with. Each review includes a rating (1-5 stars) and optional review text. The technician's overall rating is automatically calculated as the average of all their reviews.

## Endpoints

### Create Review
- **URL**: `/api/technician/<uuid:pk>/review/`
- **Method**: `POST`
- **Description**: Create a new review for a technician
- **Authentication**: Required (Client only)
- **Request Body**:
```json
{
    "rating": "integer(1-5)",
    "review_text": "string|null"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "integer",
    "client": {
        "id": "uuid",
        "full_name": "string",
        "profile_image": "url|null"
    },
    "technician": "uuid",
    "rating": "integer",
    "review_text": "string|null",
    "created_at": "datetime"
}
```
  - Error (400): Invalid rating value
  - Error (403): Not authorized to review this technician

## Review Data in Technician Profile

Reviews are included in the technician's profile data when fetching technician details through these endpoints:
- `/api/accounts/technician/<uuid:pk>/` (GET)
- `/api/technicians/` (GET - only for listing)

Example response showing review data in a technician profile:

```json
{
    "id": "uuid",
    "user": {
        "username": "string",
        "first_name": "string",
        "last_name": "string"
    },
    "rate": "decimal",  // Average rating (1-5)
    "reviews": [
        {
            "id": "integer",
            "client": {
                "id": "uuid",
                "full_name": "string",
                "profile_image": "url|null"
            },
            "rating": "integer",
            "review_text": "string|null",
            "created_at": "datetime"
        }
    ]
}
```

## Features

1. **Rating System**:
   - Scale: 1 to 5 stars
   - Automatically calculates average rating for technician
   - Updates technician's rate field after each new review

2. **Review Text**:
   - Optional text feedback
   - Allows clients to provide detailed feedback

3. **Automatic Updates**:
   - Technician's average rating is updated automatically when:
     - New review is created
     - Review is modified (not currently implemented)
     - Review is deleted (not currently implemented)

4. **Access Control**:
   - Only authenticated clients can create reviews
   - Clients can only review technicians they've worked with on completed contracts
   - Reviews are publicly visible in technician profiles 

## Frontend Implementation Guidelines

### Implementation Status
1. **Client-Technician Relationship Validation**: ✅ Implemented
   - The backend validates that clients can only review technicians they've worked with on completed contracts
   - The API returns a 403 error if a client tries to review a technician they haven't worked with
   - Frontend should only show review options for technicians with completed contracts

2. **Rating Validation**: ✅ Implemented
   - The backend validates that rating values are between 1-5
   - Frontend should enforce this range in the UI before submission

3. **Review Response Structure**: ✅ Confirmed
   - The API response includes client details with profile_image
   - The response format matches the documentation

4. **Review Modification/Deletion**: ❌ Not Implemented
   - Currently no endpoints exist for updating or deleting reviews
   - If needed, frontend should request these endpoints to be added to the API

### Integration Points
1. **Technician Profile**: 
   - Reviews appear in serializers through the following paths:
     - `TechnicianProfileSerializer`: Access via `reviewed_technicians` related name
     - `TechnicianInfoForClientSerializer`: Similar access pattern
   - The review data is consistent across different endpoints

2. **Rating Display**: 
   - Technician's average rating is stored in the `rate` field (decimal, max 3 digits with 2 decimal places)
   - The rate field is automatically updated whenever a new review is created
   - Frontend should display this value prominently in technician profiles and listings

3. **Review Form Implementation**:
   - Implement a form with a star rating component (1-5) and optional text input
   - POST to `/api/technician/<uuid:pk>/review/` endpoint with the technician's UUID
   - Handle both success and error responses appropriately
   - Show relevant error messages for 403 errors (not worked with technician) and 400 errors (invalid rating)

### UI/UX Best Practices
1. **Rating Display**:
   - Use visual star representations for ratings (filled/empty stars)
   - Display average rating prominently on technician profile cards
   - Consider showing total number of reviews alongside average rating
   - Use consistent color-coding for ratings (e.g., green for high ratings)

2. **Review Listing**:
   - Sort reviews chronologically (newest first)
   - Paginate reviews if there are many
   - Display review date in a human-readable format
   - Highlight client names and profile images for better recognition

3. **Review Form**:
   - Implement interactive star selection (hover effects, clear selection)
   - Add character counter for review text
   - Provide clear submission feedback (success/error messages)
   - Consider adding placeholder text for the review input

4. **Conditional UI Elements**:
   - Only show "Add Review" button for completed contracts
   - Display appropriate messages when user cannot review (not a client, no completed contract)
   - Consider showing previous review if the client has already reviewed the technician 