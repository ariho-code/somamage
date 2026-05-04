from django.core.management.base import BaseCommand
from academics.models import GradingSystem, GradeScale, PromotionCriteria
from core.models import School

class Command(BaseCommand):
    help = 'Sets up Uganda education system grading scales for Primary, O-Level, and A-Level'

    def handle(self, *args, **options):
        # Get all schools
        schools = School.objects.all()
        
        for school in schools:
            # Primary School Grading (Scale 1-9)
            primary_grading, _ = GradingSystem.objects.get_or_create(
                school=school,
                level='Primary',
                defaults={
                    'name': 'Uganda Primary Curriculum',
                    'is_active': True
                }
            )
            
            primary_scales = [
                ('D1', 85, 100, 1, 'Distinction 1'),
                ('D2', 80, 84, 2, 'Distinction 2'),
                ('C3', 75, 79, 3, 'Credit 3'),
                ('C4', 70, 74, 4, 'Credit 4'),
                ('C5', 65, 69, 5, 'Credit 5'),
                ('C6', 60, 64, 6, 'Credit 6'),
                ('P7', 55, 59, 7, 'Pass 7'),
                ('P8', 50, 54, 8, 'Pass 8'),
                ('F9', 0, 49, 9, 'Fail'),
            ]
            
            for grade, min_score, max_score, points, remark in primary_scales:
                GradeScale.objects.update_or_create(
                    grading_system=primary_grading,
                    grade=grade,
                    defaults={
                        'min_score': min_score,
                        'max_score': max_score,
                        'points': points,
                        'remark': remark
                    }
                )
            
            # O-Level Grading (A to E)
            olevel_grading, _ = GradingSystem.objects.get_or_create(
                school=school,
                level='O-Level',
                defaults={
                    'name': 'Uganda O-Level Curriculum',
                    'is_active': True
                }
            )
            
            olevel_scales = [
                ('A', 80, 100, 1, 'Excellent'),
                ('B', 70, 79, 2, 'Very Good'),
                ('C', 60, 69, 3, 'Good'),
                ('D', 50, 59, 4, 'Pass'),
                ('E', 40, 49, 5, 'Poor'),
                ('F', 0, 39, 6, 'Fail'),
            ]
            
            for grade, min_score, max_score, points, remark in olevel_scales:
                GradeScale.objects.update_or_create(
                    grading_system=olevel_grading,
                    grade=grade,
                    defaults={
                        'min_score': min_score,
                        'max_score': max_score,
                        'points': points,
                        'remark': remark
                    }
                )
            
            # A-Level Grading (A to F)
            alevel_grading, _ = GradingSystem.objects.get_or_create(
                school=school,
                level='A-Level',
                defaults={
                    'name': 'Uganda A-Level Curriculum',
                    'is_active': True
                }
            )
            
            alevel_scales = [
                ('A', 80, 100, 6, 'Excellent'),
                ('B', 70, 79, 5, 'Very Good'),
                ('C', 60, 69, 4, 'Good'),
                ('D', 50, 59, 3, 'Fair'),
                ('E', 40, 49, 2, 'Pass'),
                ('F', 0, 39, 1, 'Fail'),
            ]
            
            for grade, min_score, max_score, points, remark in alevel_scales:
                GradeScale.objects.update_or_create(
                    grading_system=alevel_grading,
                    grade=grade,
                    defaults={
                        'min_score': min_score,
                        'max_score': max_score,
                        'points': points,
                        'remark': remark
                    }
                )
            
            # Set up promotion criteria for each level
            PromotionCriteria.objects.update_or_create(
                grading_system=primary_grading,
                defaults={
                    'min_average_score': 50,  # Pass mark for primary
                    'min_subjects_passed': 4,  # Must pass at least 4 subjects
                    'required_core_subjects': 'Mathematics,English,Science,Social Studies',
                    'max_failures_allowed': 2
                }
            )
            
            PromotionCriteria.objects.update_or_create(
                grading_system=olevel_grading,
                defaults={
                    'min_average_score': 40,  # Pass mark for O-Level
                    'min_subjects_passed': 6,  # Must pass at least 6 subjects
                    'required_core_subjects': 'Mathematics,English,Science',
                    'max_failures_allowed': 2
                }
            )
            
            PromotionCriteria.objects.update_or_create(
                grading_system=alevel_grading,
                defaults={
                    'min_average_score': 40,  # Pass mark for A-Level
                    'min_subjects_passed': 2,  # Must pass at least 2 principal subjects
                    'required_core_subjects': 'General Paper',
                    'max_failures_allowed': 1
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully set up grading scales for {school.name}')
            )