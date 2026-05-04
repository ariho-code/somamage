from django.core.management.base import BaseCommand
from academics.models import Subject, Grade, GradingSystem
from core.models import School

PRIMARY_GRADES = [f'P{i}' for i in range(1,8)]  # P1-P7
SECONDARY_GRADES = [f'S{i}' for i in range(1,7)]  # S1-S6

# A reasonably comprehensive list of common subjects across Ugandan primary and secondary curriculum
UGANDA_SUBJECTS = [
    # Primary (P1-P7)
    ('English', 'ENG', 'P'),
    ('Mathematics', 'MAT', 'P'),
    ('Science', 'SCI', 'P'),
    ('Social Studies', 'SST', 'P'),
    ('Religious Education', 'RE', 'P'),
    ('Music and Dance', 'MUS', 'P'),
    ('Physical Education', 'PHE', 'P'),
    ('Handwriting and Art', 'ART', 'P'),
    ('Local Languages', 'LL', 'P'),
    # Lower Secondary / O-Level (S1-S4)
    ('English Language', 'ENG', 'O'),
    ('Mathematics', 'MAT', 'O'),
    ('Biology', 'BIO', 'O'),
    ('Chemistry', 'CHEM', 'O'),
    ('Physics', 'PHY', 'O'),
    ('Geography', 'GEO', 'O'),
    ('History', 'HIS', 'O'),
    ('Commerce', 'COM', 'O'),
    ('Economics', 'ECO', 'O'),
    ('Computer Studies / ICT', 'ICT', 'O'),
    ('Agriculture', 'AGR', 'O'),
    ('Technical Drawing', 'TD', 'O'),
    ('Fine Art', 'FA', 'O'),
    ('French', 'FRE', 'O'),
    ('Christian Religious Education', 'CRE', 'O'),
    ('Islamic Religious Education', 'IRE', 'O'),
    ('Home Economics', 'HEC', 'O'),
    ('Music', 'MUS', 'O'),
    ('Physical Education', 'PHE', 'O'),
    # A-Level / Senior (S5-S6)
    ('Mathematics', 'MAT', 'A'),
    ('Further Mathematics', 'FM', 'A'),
    ('Physics', 'PHY', 'A'),
    ('Chemistry', 'CHEM', 'A'),
    ('Biology', 'BIO', 'A'),
    ('Economics', 'ECO', 'A'),
    ('History', 'HIS', 'A'),
    ('Geography', 'GEO', 'A'),
    ('Divinity', 'DIV', 'A'),
    ('Agriculture', 'AGR', 'A'),
    ('Computer Studies / ICT', 'ICT', 'A'),
    ('Commerce', 'COM', 'A'),
    ('Entrepreneurship', 'ENT', 'A'),
    ('Literature in English', 'LIT', 'A'),
]

class Command(BaseCommand):
    help = 'Initialize Uganda curriculum subjects and create standard grades (P1-P7, S1-S6) for each school or globally.'

    def add_arguments(self, parser):
        parser.add_argument('--school-id', type=int, help='If provided, create grades for the given school only')

    def handle(self, *args, **options):
        school_id = options.get('school_id')

        # Create subjects
        created_subjects = 0
        for name, code, level in UGANDA_SUBJECTS:
            level_code = level
            if level_code == 'P':
                level_code = 'P'
            # Subject.level expects 'P','O','A'
            subj, created = Subject.objects.get_or_create(name=name, defaults={'code': code, 'level': level_code})
            if created:
                created_subjects += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created_subjects} new subjects (or they already existed).'))

        # Create grades for schools based on school type
        schools = School.objects.all() if not school_id else School.objects.filter(id=school_id)
        created_grades = 0
        for school in schools:
            # Only create grades appropriate for the school type
            if school.is_primary():
                # Primary school: only create P1-P7
                for g in PRIMARY_GRADES:
                    name = g.replace('P', 'P')  # keep P1 format
                    grade, created = Grade.objects.get_or_create(school=school, name=name, defaults={'level': 'P'})
                    if created:
                        created_grades += 1
                
                # Only create primary grading system with scales
                gs, created = GradingSystem.objects.get_or_create(school=school, level='Primary', defaults={'name': 'Uganda Curriculum', 'is_active': True})
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created grading system for {school.name} - Primary'))
                    # Initialize primary grading scales (Grades 1-8)
                    gs.initialize_primary_grading_scales()
                    self.stdout.write(self.style.SUCCESS(f'Initialized primary grading scales (Grades 1-8) for {school.name}'))
                    
            elif school.is_high_school():
                # High school: only create S1-S6
                for s in SECONDARY_GRADES:
                    name = s.replace('S', 'S')
                    # Map S1-S4 to O-Level (O) and S5-S6 to A-Level (A)
                    level = 'O' if int(s[1:]) <= 4 else 'A'
                    grade, created = Grade.objects.get_or_create(school=school, name=name, defaults={'level': level})
                    if created:
                        created_grades += 1
                
                # Create O-Level and A-Level grading systems with scales
                for lvl in ['O-Level', 'A-Level']:
                    gs, created = GradingSystem.objects.get_or_create(school=school, level=lvl, defaults={'name': 'Uganda Curriculum', 'is_active': True})
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Created grading system for {school.name} - {lvl}'))
                        # Initialize grading scales
                        if lvl == 'O-Level':
                            gs.initialize_olevel_grading_scales()
                            self.stdout.write(self.style.SUCCESS(f'Initialized O-Level grading scales (Grades 1-9) for {school.name}'))
                        elif lvl == 'A-Level':
                            gs.initialize_alevel_grading_scales()
                            self.stdout.write(self.style.SUCCESS(f'Initialized A-Level grading scales (Letter grades A-F) for {school.name}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_grades} new grade entries for {schools.count()} school(s).'))
        self.stdout.write(self.style.SUCCESS('Initialization complete.'))
