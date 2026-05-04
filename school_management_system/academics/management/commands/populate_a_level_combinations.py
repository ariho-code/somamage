from django.core.management.base import BaseCommand
from academics.models import Subject, Combination
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate common A-Level combinations from Ugandan UACE curriculum'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to populate A-Level combinations...'))
        
        # Get or create superadmin user for created_by field
        admin_user = User.objects.filter(is_superuser=True).first()
        
        # Combination data - Sciences Stream
        sciences_combinations = [
            {
                'name': 'PCB',
                'code': 'PCB',
                'description': 'Physics, Chemistry, Biology - Medicine, Pharmacy, Veterinary Science',
                'subjects': ['Physics', 'Chemistry', 'Biology']
            },
            {
                'name': 'PCM',
                'code': 'PCM',
                'description': 'Physics, Chemistry, Principal Mathematics - Engineering, Actuarial Science',
                'subjects': ['Physics', 'Chemistry', 'Principal Mathematics']
            },
            {
                'name': 'PEM',
                'code': 'PEM',
                'description': 'Physics, Economics, Principal Mathematics - Engineering, Economics, Data Science',
                'subjects': ['Physics', 'Economics', 'Principal Mathematics']
            },
            {
                'name': 'BCM',
                'code': 'BCM',
                'description': 'Biology, Chemistry, Principal Mathematics - Biochemistry, Biotechnology',
                'subjects': ['Biology', 'Chemistry', 'Principal Mathematics']
            },
            {
                'name': 'PCA',
                'code': 'PCA',
                'description': 'Physics, Chemistry, Agriculture - Agricultural Engineering, Food Science',
                'subjects': ['Physics', 'Chemistry', 'Agriculture Principles & Practices']
            },
            {
                'name': 'BCA',
                'code': 'BCA',
                'description': 'Biology, Chemistry, Agriculture - Agriculture, Nutrition, Agribusiness',
                'subjects': ['Biology', 'Chemistry', 'Agriculture Principles & Practices']
            },
            {
                'name': 'MEA',
                'code': 'MEA',
                'description': 'Principal Mathematics, Economics, Agriculture - Agricultural Economics',
                'subjects': ['Principal Mathematics', 'Economics', 'Agriculture Principles & Practices']
            },
        ]
        
        # Combination data - Arts Stream
        arts_combinations = [
            {
                'name': 'HEG',
                'code': 'HEG',
                'description': 'History, Economics, Geography - Law, International Relations, Urban Planning',
                'subjects': ['History', 'Economics', 'Geography']
            },
            {
                'name': 'HEL',
                'code': 'HEL',
                'description': 'History, Economics, Literature in English - Law, Journalism, Teaching',
                'subjects': ['History', 'Economics', 'Literature in English']
            },
            {
                'name': 'HEA',
                'code': 'HEA',
                'description': 'History, Economics, Art - Graphic Design, Architecture, Cultural Studies',
                'subjects': ['History', 'Economics', 'Art']
            },
            {
                'name': 'DEG',
                'code': 'DEG',
                'description': 'Divinity/CRE, Economics, Geography - Theology, Social Work, Education',
                'subjects': ['Christian Religious Education (CRE)', 'Economics', 'Geography']
            },
            {
                'name': 'DEL',
                'code': 'DEL',
                'description': 'Divinity/CRE, Economics, Literature in English - Law, Counseling, Media',
                'subjects': ['Christian Religious Education (CRE)', 'Economics', 'Literature in English']
            },
            {
                'name': 'HLD',
                'code': 'HLD',
                'description': 'History, Literature in English, Divinity/CRE - Teaching, Journalism, Religious Studies',
                'subjects': ['History', 'Literature in English', 'Christian Religious Education (CRE)']
            },
            {
                'name': 'LEG',
                'code': 'LEG',
                'description': 'Literature in English, Economics, Geography - Business, Tourism, Environmental Policy',
                'subjects': ['Literature in English', 'Economics', 'Geography']
            },
            {
                'name': 'HFA',
                'code': 'HFA',
                'description': 'History, Fine Art, French - Arts Management, Design, International Affairs',
                'subjects': ['History', 'Art', 'French']
            },
        ]
        
        # Mixed/Vocational Combinations
        mixed_combinations = [
            {
                'name': 'EGA',
                'code': 'EGA',
                'description': 'Economics, Geography, Agriculture - Agricultural Economics',
                'subjects': ['Economics', 'Geography', 'Agriculture Principles & Practices']
            },
            {
                'name': 'HEM',
                'code': 'HEM',
                'description': 'History, Economics, Principal Mathematics - Economics with History',
                'subjects': ['History', 'Economics', 'Principal Mathematics']
            },
        ]
        
        all_combinations = sciences_combinations + arts_combinations + mixed_combinations
        
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for combo_data in all_combinations:
            try:
                # Get subjects by name
                subject_objects = []
                for subject_name in combo_data['subjects']:
                    subject = Subject.objects.filter(name=subject_name, level='A').first()
                    if not subject:
                        # Try alternative names
                        if subject_name == 'Agriculture Principles & Practices':
                            subject = Subject.objects.filter(name__icontains='Agriculture', level='A').first()
                        elif subject_name == 'Christian Religious Education (CRE)':
                            subject = Subject.objects.filter(name__icontains='Christian Religious', level='A').first()
                        elif subject_name == 'Principal Mathematics':
                            subject = Subject.objects.filter(name__icontains='Principal Mathematics', level='A').first()
                        
                        if not subject:
                            self.stdout.write(self.style.WARNING(f'  Warning: Subject "{subject_name}" not found'))
                            continue
                    
                    subject_objects.append(subject)
                
                if not subject_objects:
                    self.stdout.write(self.style.ERROR(f'  Error: No valid subjects found for combination "{combo_data["name"]}"'))
                    error_count += 1
                    continue
                
                # Determine subsidiary choice based on combination subjects
                # Rules: If Math is principal → Sub-ICT; If Economics but no Math → Sub-Math; Science → Sub-Math
                subsidiary_choice = 'auto'
                subject_names_lower = [s.lower() for s in combo_data['subjects']]
                has_math = any('math' in s or 'mathematics' in s for s in subject_names_lower)
                has_economics = any('economics' in s or 'econ' in s for s in subject_names_lower)
                is_science = any(subj in s for s in subject_names_lower for subj in ['physics', 'chemistry', 'biology', 'agriculture'])
                
                if has_math:
                    subsidiary_choice = 'sub_ict'
                elif has_economics and not has_math:
                    subsidiary_choice = 'sub_math'
                elif is_science and not has_math:
                    subsidiary_choice = 'sub_math'
                else:
                    subsidiary_choice = 'auto'  # Default to auto
                
                # Create or get combination
                combination, created = Combination.objects.get_or_create(
                    name=combo_data['name'],
                    grade=None,  # All A-Level combinations cut across all grades
                    defaults={
                        'code': combo_data.get('code', ''),
                        'subsidiary_choice': subsidiary_choice,
                        'created_by': admin_user
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created combination: {combination.name}'))
                else:
                    # Update existing
                    combination.code = combo_data.get('code', '')
                    combination.subsidiary_choice = subsidiary_choice
                    combination.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'Updated combination: {combination.name}'))
                
                # Add subjects to combination
                combination.subjects.set(subject_objects)
                self.stdout.write(self.style.SUCCESS(f'  Added {len(subject_objects)} subject(s)'))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating combination "{combo_data.get("name", "Unknown")}": {str(e)}'))
                error_count += 1
        
        # Summary
        total_combinations = Combination.objects.filter(grade__isnull=True).count()
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(self.style.SUCCESS(f'  Combinations created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Combinations updated: {updated_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Errors: {error_count}'))
        self.stdout.write(self.style.SUCCESS(f'  Total A-Level combinations: {total_combinations}'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('\nA-Level combinations have been populated successfully!'))
