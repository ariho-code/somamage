from django.core.management.base import BaseCommand
from core.models import School, AcademicYear, Term
from django.utils import timezone

class Command(BaseCommand):
    help = "Seed initial data for School, AcademicYear, and Term"

    def handle(self, *args, **kwargs):
        school, _ = School.objects.get_or_create(
            name="Sample School",
            code="SAMP001",
            address="123 School Road, Kampala",
            email="info@sampleschool.com",
            phone="+256123456789",
            motto="Education for Excellence",
        )
        academic_year, _ = AcademicYear.objects.get_or_create(
            school=school,
            start_year=2025,
            end_year=2026,
            is_active=True,
        )
        Term.objects.get_or_create(
            academic_year=academic_year,
            name="Term 1",
            start_date=timezone.datetime(2025, 2, 1),
            end_date=timezone.datetime(2025, 4, 30),
        )
        Term.objects.get_or_create(
            academic_year=academic_year,
            name="Term 2",
            start_date=timezone.datetime(2025, 5, 1),
            end_date=timezone.datetime(2025, 8, 31),
        )
        Term.objects.get_or_create(
            academic_year=academic_year,
            name="Term 3",
            start_date=timezone.datetime(2025, 9, 1),
            end_date=timezone.datetime(2025, 12, 15),
        )
        self.stdout.write(self.style.SUCCESS("Successfully seeded initial data"))
