# Category API Documentation

## Table of Contents
- [Overview](#overview)
- [Permission Structure](#permission-structure)
- [API Endpoints](#api-endpoints)
  - [Categories](#categories)
    - [List Categories](#list-categories)
    - [Create Category](#create-category)
    - [Get Category Detail](#get-category-detail)
    - [Update Category](#update-category)
    - [Delete Category](#delete-category)
  - [Skills](#skills)
    - [List Skills for Category](#list-skills-for-category)
    - [Create Skill](#create-skill)
  - [SubSkills](#subskills)
    - [List SubSkills for Skill](#list-subskills-for-skill)
    - [Create SubSkill](#create-subskill)
    - [Get SubSkill Detail](#get-subskill-detail)
    - [Update SubSkill](#update-subskill)
    - [Delete SubSkill](#delete-subskill)
  - [Helper API Endpoints](#helper-api-endpoints)
    - [Check Skill Category Membership](#check-skill-category-membership)
    - [Check SubSkill Skill Membership](#check-subskill-skill-membership)
- [Management Commands](#management-commands)
  - [Load Data from JSON](#load-data-from-json)
- [Data Models](#data-models)
  - [Category Model](#category-model)
  - [Skill Model](#skill-model)
  - [SubSkill Model](#subskill-model)
- [Frontend Implementation Notes](#frontend-implementation-notes)

## Overview
The Category API manages the skill hierarchy system in the platform, consisting of Categories, Skills, and SubSkills. This hierarchical structure is used to organize and classify technician capabilities.

## Permission Structure
The API implements a tiered permission system:

1. **Public Access (No Authentication Required)**:
   - View categories
   - View skills within categories
   - View subskills within skills

2. **Admin Only Operations** (Requires `is_staff=True`):
   - Create new categories, skills, or subskills
   - Update existing categories, skills, or subskills
   - Delete categories, skills, or subskills

## API Endpoints

### Categories

#### List Categories
- **URL**: `/api/categories/`
- **Method**: `GET`
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "name": "string",
        "skills": [
            {
                "id": "uuid",
                "name": "string",
                "sub_skills": [
    {
        "id": "uuid",
        "name": "string"
                    }
                ]
            }
        ]
    }
]
```
  - Error (500): Internal Server Error

#### Create Category
- **URL**: `/api/categories/`
- **Method**: `POST`
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "name": "string"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "uuid",
    "name": "string"
}
```
  - Error (400): {"name": ["This field is required."]}
  - Error (403): "You do not have permission to perform this action."
  - Error (400): {"name": ["Category with this name already exists."]}

#### Get Category Detail
- **URL**: `/api/categories/<uuid:pk>/`
- **Method**: `GET`
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "name": "string",
    "skills": [
        {
            "id": "uuid",
            "name": "string",
            "sub_skills": [
{
    "id": "uuid",
    "name": "string"
                }
            ]
        }
    ]
}
```
  - Error (404): "Not found."

#### Update Category
- **URL**: `/api/categories/<uuid:pk>/`
- **Method**: `PUT`
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "name": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "name": "string"
}
```
  - Error (400): {"name": ["This field is required."]}
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Not found."
  - Error (400): {"name": ["Category with this name already exists."]}

#### Delete Category
- **URL**: `/api/categories/<uuid:pk>/`
- **Method**: `DELETE`
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (204): No content
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Not found."

### Skills

#### List Skills for Category
- **URL**: `/api/categories/<uuid:category_id>/skills/`
- **Method**: `GET`
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "name": "string",
        "sub_skills": [
            {
                "id": "uuid",
                "name": "string"
            }
        ]
    }
]
```
  - Error (404): "Category not found."

#### Create Skill
- **URL**: `/api/categories/<uuid:category_id>/skills/`
- **Method**: `POST`
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "name": "string"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "uuid",
    "name": "string",
    "category": "uuid"
}
```
  - Error (400): {"name": ["This field is required."]}
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Category not found."

### SubSkills

#### List SubSkills for Skill
- **URL**: `/api/categories/skills/<uuid:skill_id>/sub-skills/`
- **Method**: `GET`
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
[
    {
        "id": "uuid",
        "name": "string"
    }
]
```
  - Error (404): "Skill not found."

#### Create SubSkill
- **URL**: `/api/categories/skills/<uuid:skill_id>/sub-skills/`
- **Method**: `POST`
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "name": "string"
}
```
- **Response**:
  - Success (201):
```json
{
    "id": "uuid",
    "name": "string"
}
```
  - Error (400): {"name": ["This field is required."]}
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Skill not found."

#### Get SubSkill Detail
- **URL**: `/api/categories/skills/<uuid:skill_id>/sub-skills/<uuid:pk>/`
- **Method**: `GET`
- **Authentication**: Not required
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "name": "string"
}
```
  - Error (404): "Not found."

#### Update SubSkill
- **URL**: `/api/categories/skills/<uuid:skill_id>/sub-skills/<uuid:pk>/`
- **Method**: `PUT`
- **Authentication**: Required (Admin only)
- **Request Body**:
```json
{
    "name": "string"
}
```
- **Response**:
  - Success (200):
```json
{
    "id": "uuid",
    "name": "string"
}
```
  - Error (400): {"name": ["This field is required."]}
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Not found."

#### Delete SubSkill
- **URL**: `/api/categories/skills/<uuid:skill_id>/sub-skills/<uuid:pk>/`
- **Method**: `DELETE`
- **Authentication**: Required (Admin only)
- **Response**:
  - Success (204): No content
  - Error (403): "You do not have permission to perform this action."
  - Error (404): "Not found."

### Helper API Endpoints

#### Check Skill Category Membership
- **URL**: `/api/categories/skills-by-category/`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `skill_id`: UUID of the skill to check
  - `categories`: Comma-separated list of category IDs to check against
- **Response**:
  - Success (200):
```json
{
    "belongs_to_category": true
}
```
  - Error (400): `{"error": "Missing required parameters"}`
  - Error (404): `{"error": "Skill not found"}`
- **Frontend Notes**:
  - Use this endpoint to validate skill-category relationships
  - Useful for filtering and validation in forms
  - Handle errors appropriately in the UI

#### Check SubSkill Skill Membership
- **URL**: `/api/categories/subskills-by-skill/`
- **Method**: `GET`
- **Authentication**: Required
- **Query Parameters**:
  - `subskill_id`: UUID of the subskill to check
  - `skills`: Comma-separated list of skill IDs to check against
- **Response**:
  - Success (200):
```json
{
    "belongs_to_skill": true
}
```
  - Error (400): `{"error": "Missing required parameters"}`
  - Error (404): `{"error": "SubSkill not found"}`
- **Frontend Notes**:
  - Use this endpoint to validate subskill-skill relationships
  - Helpful for dynamic form validation
  - Consider caching results for better performance

## Management Commands

### Load Data from JSON
- **Command**: `python manage.py load_data_from_json <json_file>`
- **Description**: Loads categories, skills, and subskills from a JSON file into the database
- **Arguments**:
  - `json_file`: Path to the JSON file containing the data structure
- **JSON Format**:
```json
{
    "categories": [
        {
            "name": "Category Name",
            "skills": [
                {
                    "name": "Skill Name",
                    "sub_skills": [
                        {
                            "name": "SubSkill Name"
                        }
                    ]
                }
            ]
        }
    ]
}
```
- **Usage Example**:
```bash
python manage.py load_data_from_json data_skills.json
```
- **Notes**:
  - Existing data with the same names will be updated
  - New data will be created
  - Relationships are maintained automatically
  - Use this command for initial data setup or bulk updates

## Data Models

### Category Model
```python
class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
```

### Skill Model
```python
class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, related_name='skills', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
```

### SubSkill Model
```python
class SubSkill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, related_name='sub_skills', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
```

## Frontend Implementation Notes

1. **Permission Handling**:
   - Implement role-based UI elements (show edit/delete buttons only to admins)
   - Handle 403 errors appropriately with user-friendly messages
   - Redirect unauthorized users to appropriate pages
   - Check user's admin status before showing admin-only actions

2. **Category Management**:
   - Create hierarchical display of categories → skills → subskills
   - Implement search and filter functionality
   - Add confirmation dialogs for delete operations
   - Show loading states during API calls
   - Handle cascading deletes (deleting a category will delete all related skills and subskills)

3. **Form Implementation**:
   - Validate unique names for categories
   - Implement proper error handling
   - Show success messages after operations
   - Add auto-complete for existing names to prevent duplicates
   - Add client-side validation matching server requirements

4. **Admin Interface**:
   - Create dedicated admin section for category management
   - Implement batch operations where possible
   - Add audit logging for admin operations
   - Provide data export functionality
   - Show relationships between categories, skills, and subskills
   - Add search and filter capabilities for large datasets

5. **Error Handling**:
   - Display user-friendly error messages
   - Handle network errors gracefully
   - Provide retry options for failed operations
   - Show validation errors inline with form fields
   - Implement proper error boundaries

6. **Performance Considerations**:
   - Cache frequently accessed category data
   - Implement pagination for large lists
   - Use optimistic updates for better UX
   - Lazy load subskills when needed
   - Consider implementing a search index for large datasets 