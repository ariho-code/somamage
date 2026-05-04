"""
Management command to create initial users and clear existing data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import School
from students.models import Student, Guardian, Enrollment
from academics.models import Grade, Subject
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Create initial users and setup system - clears existing parent/bursar data and creates new users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing users (except superadmin)',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting user setup...'))
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            
            # Delete parents, bursars, teachers, headteachers (but keep superadmin)
            User.objects.exclude(is_superuser=True).filter(
                role__in=['parent', 'bursar', 'teacher', 'headteacher']
            ).delete()
            
            # Delete students and guardians
            Student.objects.all().delete()
            Guardian.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('Existing data cleared!'))

        # Create or get schools
        primary_school, _ = School.objects.get_or_create(
            name="Kampala Primary School",
            defaults={
                'code': 'KPS',
                'address': 'Kampala, Uganda',
                'email': 'info@kps.ug',
                'phone': '+256-700-000-001',
                'motto': 'Excellence in Education'
            }
        )
        
        high_school, _ = School.objects.get_or_create(
            name="Kampala High School",
            defaults={
                'code': 'KHS',
                'address': 'Kampala, Uganda',
                'email': 'info@khs.ug',
                'phone': '+256-700-000-002',
                'motto': 'Knowledge is Power'
            }
        )
        
        self.stdout.write(self.style.SUCCESS(f'Schools created/verified: {primary_school.name}, {high_school.name}'))

        # Create Superadmin (if doesn't exist)
        superadmin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@schoolmanagement.ug',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': 'superadmin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            superadmin.set_password('admin123')
            superadmin.save()
            self.stdout.write(self.style.SUCCESS('[OK] Superadmin created: username=admin, password=admin123'))
        else:
            superadmin.set_password('admin123')
            superadmin.save()
            self.stdout.write(self.style.SUCCESS('[OK] Superadmin password reset: username=admin, password=admin123'))

        # Create Headteachers
        # Primary School Headteacher
        headteacher_primary, created = User.objects.get_or_create(
            username='headteacher_primary',
            defaults={
                'email': 'headteacher.primary@kps.ug',
                'first_name': 'Jane',
                'last_name': 'Nakato',
                'role': 'headteacher',
                'school': primary_school,
            }
        )
        if created:
            headteacher_primary.set_password('headteacher123')
            headteacher_primary.save()
            self.stdout.write(self.style.SUCCESS('[OK] Primary Headteacher created: username=headteacher_primary, password=headteacher123'))
        else:
            headteacher_primary.set_password('headteacher123')
            headteacher_primary.school = primary_school
            headteacher_primary.save()
            self.stdout.write(self.style.SUCCESS('[OK] Primary Headteacher updated: username=headteacher_primary, password=headteacher123'))

        # High School Headteacher
        headteacher_high, created = User.objects.get_or_create(
            username='headteacher_high',
            defaults={
                'email': 'headteacher.high@khs.ug',
                'first_name': 'John',
                'last_name': 'Mukasa',
                'role': 'headteacher',
                'school': high_school,
            }
        )
        if created:
            headteacher_high.set_password('headteacher123')
            headteacher_high.save()
            self.stdout.write(self.style.SUCCESS('[OK] High School Headteacher created: username=headteacher_high, password=headteacher123'))
        else:
            headteacher_high.set_password('headteacher123')
            headteacher_high.school = high_school
            headteacher_high.save()
            self.stdout.write(self.style.SUCCESS('[OK] High School Headteacher updated: username=headteacher_high, password=headteacher123'))

        # Create Teachers
        teachers_data = [
            {'username': 'teacher1', 'first_name': 'Mary', 'last_name': 'Nalubega', 'email': 'teacher1@school.ug', 'school': primary_school},
            {'username': 'teacher2', 'first_name': 'Peter', 'last_name': 'Ssemwogerere', 'email': 'teacher2@school.ug', 'school': primary_school},
            {'username': 'teacher3', 'first_name': 'Sarah', 'last_name': 'Kigozi', 'email': 'teacher3@school.ug', 'school': high_school},
            {'username': 'teacher4', 'first_name': 'David', 'last_name': 'Lubega', 'email': 'teacher4@school.ug', 'school': high_school},
        ]
        
        for teacher_data in teachers_data:
            teacher, created = User.objects.get_or_create(
                username=teacher_data['username'],
                defaults={
                    'email': teacher_data['email'],
                    'first_name': teacher_data['first_name'],
                    'last_name': teacher_data['last_name'],
                    'role': 'teacher',
                    'school': teacher_data['school'],
                }
            )
            if created:
                teacher.set_password('teacher123')
                teacher.save()
                self.stdout.write(self.style.SUCCESS(f"[OK] Teacher created: username={teacher_data['username']}, password=teacher123"))
            else:
                teacher.set_password('teacher123')
                teacher.school = teacher_data['school']
                teacher.save()
                self.stdout.write(self.style.SUCCESS(f"[OK] Teacher updated: username={teacher_data['username']}, password=teacher123"))

        # Create Bursar
        bursar, created = User.objects.get_or_create(
            username='bursar',
            defaults={
                'email': 'bursar@school.ug',
                'first_name': 'Grace',
                'last_name': 'Namukasa',
                'role': 'bursar',
                'school': primary_school,  # Can be assigned to any school
            }
        )
        if created:
            bursar.set_password('bursar123')
            bursar.save()
            self.stdout.write(self.style.SUCCESS('[OK] Bursar created: username=bursar, password=bursar123'))
        else:
            bursar.set_password('bursar123')
            bursar.save()
            self.stdout.write(self.style.SUCCESS('[OK] Bursar password reset: username=bursar, password=bursar123'))

        # Create Director of Studies
        director, created = User.objects.get_or_create(
            username='director',
            defaults={
                'email': 'director@school.ug',
                'first_name': 'Robert',
                'last_name': 'Wasswa',
                'role': 'director_of_studies',
                'school': high_school,
            }
        )
        if created:
            director.set_password('director123')
            director.save()
            self.stdout.write(self.style.SUCCESS('[OK] Director of Studies created: username=director, password=director123'))
        else:
            director.set_password('director123')
            director.save()
            self.stdout.write(self.style.SUCCESS('[OK] Director password reset: username=director, password=director123'))

        self.stdout.write(self.style.SUCCESS('\n[OK] User setup completed!'))
        self.stdout.write(self.style.SUCCESS('\nLogin Credentials:'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('Admin Panel: username=admin, password=admin123'))
        self.stdout.write(self.style.SUCCESS('Primary Headteacher: username=headteacher_primary, password=headteacher123'))
        self.stdout.write(self.style.SUCCESS('High School Headteacher: username=headteacher_high, password=headteacher123'))
        self.stdout.write(self.style.SUCCESS('Teachers: username=teacher1-4, password=teacher123'))
        self.stdout.write(self.style.SUCCESS('Bursar: username=bursar, password=bursar123'))
        self.stdout.write(self.style.SUCCESS('Director: username=director, password=director123'))

