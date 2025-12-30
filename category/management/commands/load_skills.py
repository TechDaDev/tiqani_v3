import json
import os
from django.core.management.base import BaseCommand
from category.models import Category, Skill, SubSkill


class Command(BaseCommand):
    help = 'Load categories, skills, and sub-skills from JSON file into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data_skills.json',
            help='Path to JSON file (default: data_skills.json in project root)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # If relative path, make it absolute from project root
        if not os.path.isabs(file_path):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            file_path = os.path.join(project_root, file_path)
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Loading data from: {file_path}'))
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'Invalid JSON: {str(e)}'))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {str(e)}'))
            return
        
        # Get or create category
        category_name = data.get('category')
        if not category_name:
            self.stdout.write(self.style.ERROR('No category found in JSON'))
            return
        
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'{category_name} related services',
                'is_active': True,
                'order': 0
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created category: {category_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'→ Category already exists: {category_name}'))
        
        # Process skills
        skills_data = data.get('skills', [])
        skills_count = 0
        subskills_count = 0
        
        for idx, skill_data in enumerate(skills_data):
            skill_name = skill_data.get('skill')
            if not skill_name:
                continue
            
            # Get or create skill
            skill, skill_created = Skill.objects.get_or_create(
                category=category,
                name=skill_name,
                defaults={
                    'description': f'{skill_name} services',
                    'is_active': True,
                    'order': idx
                }
            )
            
            if skill_created:
                skills_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created skill: {skill_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  → Skill already exists: {skill_name}'))
            
            # Process sub-skills
            sub_skills_data = skill_data.get('sub_skills', [])
            for sub_idx, sub_skill_name in enumerate(sub_skills_data):
                if not sub_skill_name:
                    continue
                
                # Get or create sub-skill
                sub_skill, sub_skill_created = SubSkill.objects.get_or_create(
                    skill=skill,
                    name=sub_skill_name,
                    defaults={
                        'description': f'{sub_skill_name} specialization',
                        'is_active': True,
                        'difficulty_level': 'intermediate',
                        'order': sub_idx
                    }
                )
                
                if sub_skill_created:
                    subskills_count += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✓ Created sub-skill: {sub_skill_name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'    → Sub-skill already exists: {sub_skill_name}'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'Category: {category_name}'))
        self.stdout.write(self.style.SUCCESS(f'New skills created: {skills_count}'))
        self.stdout.write(self.style.SUCCESS(f'New sub-skills created: {subskills_count}'))
        self.stdout.write(self.style.SUCCESS(f'Total skills processed: {len(skills_data)}'))
        self.stdout.write(self.style.SUCCESS('='*60))
