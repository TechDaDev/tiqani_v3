# Category API Documentation

**Last Updated:** December 31, 2025

This document covers the public category endpoints, data shapes, admin behaviors, and data-loading utilities for the `category` app.

---

## Table of Contents
1. [Base Path](#base-path)
2. [Endpoints](#endpoints)
  - [List Categories](#list-categories)
  - [Category Detail](#category-detail)
  - [Skills](#skills)
  - [Sub-Skills](#sub-skills)
3. [Data Model Quick Reference](#data-model-quick-reference)
4. [Admin Panel](#admin-panel)
5. [Management Commands](#management-commands)
6. [Error Handling](#error-handling)
7. [Future Additions](#future-additions)

---

## Base Path
All category endpoints are served under `/api/category/`.

---

## Endpoints

### List Categories
**Endpoint**
```
GET /api/category/categories/
```

**Auth**: Public

**Description**: Returns active categories (excluding soft-deleted) ordered by `order`, then `name`, with nested skills and sub-skills. Use `?fields=basic` to omit sub_skills for lighter payloads.

**Query Params**
- `q`: search in name/description
- `parent`: filter by parent UUID
- `is_featured`, `is_active`: boolean filters (`true/false/1/0`)
- `ordering`: comma list, allowed `order,name,created_at,updated_at` (prefix with `-` for descending)
- `page`, `page_size` (max 100)
- `fields=basic`: use slim serializer (no sub_skills nesting)

**Success Response (200 OK)**
```json
[
  {
    "id": "c8c2f43e-1e8e-4e31-9f7a-40a2bb9f9b4c",
    "name": "Data",
    "description": "Data related services",
    "icon": null,
    "parent": null,
    "is_active": true,
    "is_featured": false,
    "is_delete": false,
    "order": 0,
    "skill_count": 14,
    "technician_count": 0,
    "created_at": "2025-12-31T12:00:00Z",
    "updated_at": "2025-12-31T12:00:00Z",
    "skills": [
      {
        "id": "0c32c3e0-6b36-4ab9-9e9a-3c8d7c6ad6f0",
        "category": "c8c2f43e-1e8e-4e31-9f7a-40a2bb9f9b4c",
        "name": "Databases",
        "description": "Databases services",
        "is_active": true,
        "is_delete": false,
        "order": 4,
        "technician_count": 0,
        "created_at": "2025-12-31T12:00:00Z",
        "updated_at": "2025-12-31T12:00:00Z",
        "sub_skills": [
          {
            "id": "c2d1d5d1-3e9c-4a2f-9c2b-8a1d6a7f8b9c",
            "skill": "0c32c3e0-6b36-4ab9-9e9a-3c8d7c6ad6f0",
            "name": "Database Administration (DBA)",
            "description": "Database Administration (DBA) specialization",
            "difficulty_level": "intermediate",
            "is_active": true,
            "is_delete": false,
            "order": 1,
            "full_path": "Data -> Databases -> Database Administration (DBA)",
            "created_at": "2025-12-31T12:00:00Z",
            "updated_at": "2025-12-31T12:00:00Z"
          }
        ]
      }
    ]
  }
]
```

**Notes**
- Filters out `is_delete=True` records.
- Uses nested serializers for `skills` and `sub_skills` (read-only in this public API).
- Ordering: `order` asc, then `name` asc.
 - Staff can create/update/delete; public is read-only.

---

### Category Detail
**Endpoint**
```
GET /api/category/categories/<uuid:id>/
```

**Auth**: Public

**Description**: Retrieve a single category by UUID with nested skills and sub-skills. Soft-deleted records are excluded.

**Success Response (200 OK)**
```json
{
  "id": "c8c2f43e-1e8e-4e31-9f7a-40a2bb9f9b4c",
  "name": "Data",
  "description": "Data related services",
  "icon": null,
  "parent": null,
  "is_active": true,
  "is_featured": false,
  "is_delete": false,
  "order": 0,
  "skill_count": 14,
  "technician_count": 0,
  "created_at": "2025-12-31T12:00:00Z",
  "updated_at": "2025-12-31T12:00:00Z",
  "skills": [
    {
      "id": "0c32c3e0-6b36-4ab9-9e9a-3c8d7c6ad6f0",
      "category": "c8c2f43e-1e8e-4e31-9f7a-40a2bb9f9b4c",
      "name": "Databases",
      "description": "Databases services",
      "is_active": true,
      "is_delete": false,
      "order": 4,
      "technician_count": 0,
      "created_at": "2025-12-31T12:00:00Z",
      "updated_at": "2025-12-31T12:00:00Z",
      "sub_skills": [
        {
          "id": "c2d1d5d1-3e9c-4a2f-9c2b-8a1d6a7f8b9c",
          "skill": "0c32c3e0-6b36-4ab9-9e9a-3c8d7c6ad6f0",
          "name": "Database Administration (DBA)",
          "description": "Database Administration (DBA) specialization",
          "difficulty_level": "intermediate",
          "is_active": true,
          "is_delete": false,
          "order": 1,
          "full_path": "Data -> Databases -> Database Administration (DBA)",
          "created_at": "2025-12-31T12:00:00Z",
          "updated_at": "2025-12-31T12:00:00Z"
        }
      ]
    }
  ]
}
```

**Error Responses**
- 404 Not Found when the UUID does not exist or is soft-deleted.

---

### Skills
**Endpoints**
```
GET /api/category/skills/
GET /api/category/skills/<uuid:pk>/
POST /api/category/skills/
PATCH /api/category/skills/<uuid:pk>/
DELETE /api/category/skills/<uuid:pk>/
```

**Auth**: Public read; staff write.

**Query Params (list)**
- `q`: search name/description
- `category_id`: filter by parent category UUID
- `is_active`: boolean
- `ordering`: `order,name,created_at,updated_at` (comma, `-` for desc)
- `page`, `page_size` (max 100)
- `fields=basic`: omit nested sub_skills

**Behavior**
- Soft-deletes on DELETE (sets `is_delete=True`).
- Public list excludes soft-deleted/inactive skills and inactive/soft-deleted parent categories.

---

### Sub-Skills
**Endpoints**
```
GET /api/category/sub-skills/
GET /api/category/sub-skills/<uuid:pk>/
POST /api/category/sub-skills/
PATCH /api/category/sub-skills/<uuid:pk>/
DELETE /api/category/sub-skills/<uuid:pk>/
```

**Auth**: Public read; staff write.

**Query Params (list)**
- `q`: search name/description
- `skill_id`: filter by parent skill UUID
- `difficulty_level`: one of `beginner|intermediate|advanced|expert`
- `is_active`: boolean
- `ordering`: `order,name,created_at,updated_at`
- `page`, `page_size` (max 100)

**Behavior**
- Soft-deletes on DELETE (sets `is_delete=True`).
- Public list excludes soft-deleted/inactive sub-skills and inactive/soft-deleted parents.

---

## Data Model Quick Reference
- **Category**: `id (UUID)`, `name`, `description`, `icon`, `parent`, `is_active`, `is_featured`, `is_delete`, `order`, timestamps; computed `skill_count`, `technician_count`.
- **Skill**: `id (UUID)`, `category` FK, `name`, `description`, `is_active`, `is_delete`, `order`, `technician_count`, timestamps; nested `sub_skills` read-only here.
- **SubSkill**: `id (UUID)`, `skill` FK, `name`, `description`, `difficulty_level`, `is_active`, `is_delete`, `order`, timestamps; computed `full_path` and `technician_count`.
- All models inherit `TimestampedModel` (UUID primary key, `is_delete`, `created_at`, `updated_at`).

---

## Admin Panel
- Soft delete surfaced on Category, Skill, and SubSkill list displays and filters.
- Bulk actions: activate/deactivate and soft-delete/restore for each model.
- Inlines: Category shows Skills inline; Skill shows SubSkills inline.
- Read-only: `id`, `created_at`, `updated_at`, counters (`skill_count`, `technician_count`, `full_path`).

---

## Management Commands
- Load seed data from JSON files (aligned with the structure in `dependancy/skills_files`).

Run examples:
```
python manage.py load_skills --file dependancy/skills_files/data_skills.json
python manage.py load_skills --file dependancy/skills_files/graphics_design_skills.json
python manage.py load_skills --file dependancy/skills_files/programming_tech_skills.json
```
- Command behavior: get-or-create semantics for Category/Skill/SubSkill; sets `description`, `is_active=True`, and sequential `order` based on file order.

---

## Error Handling
- Standard DRF error payloads (e.g., `{"detail": "Not found."}` for 404).
- Soft-deleted records are excluded from public queries.

---

## Future Additions
- Expose OpenAPI schema entries for category, skill, and sub-skill endpoints (document soft-delete semantics and query params).
- Add optional caching headers + ETags once traffic patterns are known.
- Add bulk import/export endpoints (admin-only) for CSV/JSON skill trees.
- Add optional tree-structured response for categories (`?view=tree`) with nested children categories if hierarchy is used.
- Add audit logging for staff writes (who/when for create/update/delete/restore).
