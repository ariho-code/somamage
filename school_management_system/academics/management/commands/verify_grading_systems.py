from django.core.management.base import BaseCommand
from academics.models import GradingSystem, GradeScale


class Command(BaseCommand):
    help = 'Verify that grading systems are set up correctly with the Ugandan grading scales'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('VERIFYING GRADING SYSTEMS'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))
        
        # Check Primary grading systems
        primary_systems = GradingSystem.objects.filter(level='Primary')
        if primary_systems.exists():
            for gs in primary_systems:
                self.stdout.write(self.style.SUCCESS(f'\n✓ Primary Grading System: {gs.school.name}'))
                scales = GradeScale.objects.filter(grading_system=gs).order_by('-min_score')
                self.stdout.write(f'  Scales ({scales.count()}):')
                for scale in scales:
                    self.stdout.write(f'    Grade {scale.grade}: {scale.min_score}-{scale.max_score}%, Points: {scale.points}, Remark: {scale.remark}')
        else:
            self.stdout.write(self.style.WARNING('✗ No Primary grading systems found'))
        
        # Check O-Level grading systems
        olevel_systems = GradingSystem.objects.filter(level='O-Level')
        if olevel_systems.exists():
            for gs in olevel_systems:
                self.stdout.write(self.style.SUCCESS(f'\n✓ O-Level Grading System: {gs.school.name}'))
                scales = GradeScale.objects.filter(grading_system=gs).order_by('-min_score')
                self.stdout.write(f'  Scales ({scales.count()}):')
                for scale in scales:
                    self.stdout.write(f'    Grade {scale.grade}: {scale.min_score}-{scale.max_score}%, Points: {scale.points}, Remark: {scale.remark}')
        else:
            self.stdout.write(self.style.WARNING('✗ No O-Level grading systems found'))
        
        # Check A-Level grading systems
        alevel_systems = GradingSystem.objects.filter(level='A-Level')
        if alevel_systems.exists():
            for gs in alevel_systems:
                self.stdout.write(self.style.SUCCESS(f'\n✓ A-Level Grading System: {gs.school.name}'))
                scales = GradeScale.objects.filter(grading_system=gs).order_by('-min_score')
                self.stdout.write(f'  Scales ({scales.count()}):')
                for scale in scales:
                    self.stdout.write(f'    Grade {scale.grade}: {scale.min_score}-{scale.max_score}%, Points: {scale.points}, Remark: {scale.remark}')
                
                # Verify A-Level points
                self.stdout.write(self.style.SUCCESS('\n  A-Level Points Verification:'))
                expected_points = {'A': 6, 'B': 5, 'C': 4, 'D': 3, 'E': 2, 'O': 1, 'F': 0}
                all_correct = True
                for scale in scales:
                    expected = expected_points.get(scale.grade, None)
                    if expected is not None:
                        if float(scale.points) == expected:
                            self.stdout.write(self.style.SUCCESS(f'    ✓ Grade {scale.grade}: Points {scale.points} (Correct)'))
                        else:
                            self.stdout.write(self.style.ERROR(f'    ✗ Grade {scale.grade}: Points {scale.points} (Expected {expected})'))
                            all_correct = False
                
                if all_correct:
                    self.stdout.write(self.style.SUCCESS('\n  ✓ All A-Level points are correct!'))
        else:
            self.stdout.write(self.style.WARNING('✗ No A-Level grading systems found'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70 + '\n'))

