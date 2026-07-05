# Technician Multi-Skill Selection

## Existing Bug

Technician skills were stored in a `TechnicianSkillSet` with many-to-many relations for categories, skills, and sub-skills, but profile completion and admin approval did not treat skills as required. API responses also returned flat skill names without category context, which made it easy for clients to behave like a single category or single skill selector.

## Expected Behavior

Technicians can save multiple skills and sub-skills across multiple categories. A valid technician profile must have at least one selected skill or sub-skill. The skills endpoint accepts arrays in the existing fields:

```json
{
  "categories": ["category-uuid"],
  "skills": ["skill-uuid-1", "skill-uuid-2"],
  "sub_skills": ["sub-skill-uuid"]
}
```

The backend derives category membership from selected skills and sub-skills, deduplicates submitted IDs, and returns all selections with category context. Admin technician detail and approval checklist read the same multi-selection state.

## Compatibility

No category, skill, or sub-skill data is removed. The existing `TechnicianSkillSet` many-to-many schema remains in place, so existing selected skills/sub-skills continue to work without a migration.
