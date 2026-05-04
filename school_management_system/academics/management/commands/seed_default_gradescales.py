from django.core.management.base import BaseCommand
from academics.models import GradingSystem, GradeScale

# Default grade scales (example bands) based on common Uganda patterns
DEFAULT_SCALES = {
    'Primary': [
        ('A', 80, 100, 6, 'Excellent'),
        ('B', 70, 79.99, 5, 'Very Good'),
        ('C', 60, 69.99, 4, 'Good'),
        ('D', 50, 59.99, 3, 'Credit'),
        ('E', 40, 49.99, 2, 'Pass'),
        ('F', 0, 39.99, 0, 'Fail'),
    ],
    'O-Level': [
        # new curriculum bands (example) — headteachers can adjust per school
        ('A', 85, 100, 10, 'Excellent'),
        ('B', 70, 84.99, 8, 'Very Good'),
        ('C', 55, 69.99, 6, 'Good'),
        ('D', 45, 54.99, 4, 'Credit'),
        ('E', 35, 44.99, 2, 'Pass'),
        ('F', 0, 34.99, 0, 'Fail'),
    ],
    'A-Level': [
        ('A', 80, 100, 6, 'Excellent'),
        ('B', 70, 79.99, 5, 'Very Good'),
        ('C', 60, 69.99, 4, 'Good'),
        ('D', 50, 59.99, 3, 'Credit'),
        ('E', 40, 49.99, 2, 'Pass'),
        ('F', 0, 39.99, 0, 'Fail'),
    ]
}

class Command(BaseCommand):
    help = 'Seed default GradeScale entries for existing GradingSystem records (Primary, O-Level, A-Level)'

    def handle(self, *args, **options):
        created = 0
        for gs in GradingSystem.objects.all():
            band_key = gs.level
            bands = DEFAULT_SCALES.get(band_key)
            if not bands:
                self.stdout.write(self.style.WARNING(f'No default bands defined for level: {gs.level}'))
                continue

            for grade_letter, min_score, max_score, points, remark in bands:
                obj, was_created = GradeScale.objects.get_or_create(
                    grading_system=gs,
                    grade=grade_letter,
                    defaults={
                        'min_score': min_score,
                        'max_score': max_score,
                        'points': points,
                        'remark': remark,
                    }
                )
                if was_created:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} GradeScale entries (or they already existed).'))
