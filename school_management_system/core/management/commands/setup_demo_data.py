from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import School, AcademicYear, Term
from datetime import date

User = get_user_model()

class Command(BaseCommand):
    help = 'Create initial demo data with different user roles and school structure'

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create Platform (if not exists)
            from tenants.models import Platform
            platform, created = Platform.objects.get_or_create(
                id=Platform.objects.first().id if Platform.objects.exists() else None,
                defaults={'name': 'SomaMange', 'contact_email': 'admin@somamage.com'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created Platform'))

            # Create Demo Schools (both Primary and Secondary)
            demo_schools = [
                {
                    'name': 'SomaMange Primary School',
                    'school_type': 'primary',
                    'address': '123 Kampala Road, Kampala, Uganda',
                    'phone': '+256 760 730 254',
                    'email': 'primary@somamage.com',
                    'motto': 'Foundation for Excellence'
                },
                {
                    'name': 'SomaMange Secondary School',
                    'school_type': 'high',
                    'address': '456 Jinja Road, Kampala, Uganda',
                    'phone': '+256 760 730 255',
                    'email': 'secondary@somamage.com',
                    'motto': 'Excellence in Education'
                }
            ]
            
            created_schools = []
            for school_data in demo_schools:
                school, created = School.objects.get_or_create(
                    name=school_data['name'],
                    defaults={
                        'school_type': school_data['school_type'],
                        'address': school_data['address'],
                        'phone': school_data['phone'],
                        'email': school_data['email'],
                        'motto': school_data['motto']
                    }
                )
                created_schools.append(school)
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created {school.name} ({school.get_school_type_display()})'))
            
            # Use the first school for demo data setup
            school = created_schools[0]

            # Create Academic Year
            academic_year, created = AcademicYear.objects.get_or_create(
                school=school,
                name='2025',
                defaults={
                    'start_date': date(2025, 1, 1),
                    'end_date': date(2025, 12, 31),
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created Academic Year 2025'))

            # Create Terms
            terms_data = [
                {'name': 'Term 1', 'start_date': date(2025, 2, 3), 'end_date': date(2025, 5, 2)},
                {'name': 'Term 2', 'start_date': date(2025, 5, 26), 'end_date': date(2025, 8, 22)},
                {'name': 'Term 3', 'start_date': date(2025, 9, 14), 'end_date': date(2025, 12, 4)},
            ]
            
            for term_data in terms_data:
                term, created = Term.objects.get_or_create(
                    academic_year=academic_year,
                    name=term_data['name'],
                    defaults={
                        'start_date': term_data['start_date'],
                        'end_date': term_data['end_date'],
                        'is_active': term_data['name'] == 'Term 1'  # Term 1 is active
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created {term.name}'))

            # Create Demo Users with Different Roles for Both Schools
            demo_users = [
                # Primary School Users
                {
                    'username': 'primary_headteacher',
                    'email': 'primary.headteacher@somamage.com',
                    'password': 'headteacher123',
                    'first_name': 'Sarah',
                    'last_name': 'Nakato',
                    'role': 'headteacher',
                    'phone': '+256 760 730 255',
                    'school': created_schools[0]  # Primary School
                },
                {
                    'username': 'primary_teacher',
                    'email': 'primary.teacher@somamage.com',
                    'password': 'teacher123',
                    'first_name': 'John',
                    'last_name': 'Mugisha',
                    'role': 'teacher',
                    'phone': '+256 760 730 256',
                    'school': created_schools[0]  # Primary School
                },
                # Secondary School Users
                {
                    'username': 'secondary_headteacher',
                    'email': 'secondary.headteacher@somamage.com',
                    'password': 'headteacher123',
                    'first_name': 'Peter',
                    'last_name': 'Ssekandi',
                    'role': 'headteacher',
                    'phone': '+256 760 730 260',
                    'school': created_schools[1]  # Secondary School
                },
                {
                    'username': 'secondary_teacher',
                    'email': 'secondary.teacher@somamage.com',
                    'password': 'teacher123',
                    'first_name': 'Grace',
                    'last_name': 'Nankya',
                    'role': 'teacher',
                    'phone': '+256 760 730 261',
                    'school': created_schools[1]  # Secondary School
                },
                # Shared Users (can access both schools)
                {
                    'username': 'bursar',
                    'email': 'bursar@somamage.com',
                    'password': 'bursar123',
                    'first_name': 'Joseph',
                    'last_name': 'Lubega',
                    'role': 'bursar',
                    'phone': '+256 760 730 257',
                    'school': created_schools[0]  # Primary School
                },
                {
                    'username': 'dos',
                    'email': 'dos@somamage.com',
                    'password': 'dos123',
                    'first_name': 'Michael',
                    'last_name': 'Kato',
                    'role': 'director_of_studies',
                    'phone': '+256 760 730 258',
                    'school': created_schools[1]  # Secondary School
                },
                {
                    'username': 'parent',
                    'email': 'parent@somamage.com',
                    'password': 'parent123',
                    'first_name': 'Faith',
                    'last_name': 'Nakimera',
                    'role': 'parent',
                    'phone': '+256 760 730 259',
                    'school': created_schools[0]  # Primary School
                }
            ]

            for user_data in demo_users:
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        'email': user_data['email'],
                        'first_name': user_data['first_name'],
                        'last_name': user_data['last_name'],
                        'role': user_data['role'],
                        'school': user_data['school'],
                        'phone_number': user_data['phone'],
                        'is_active': True
                    }
                )
                
                if created:
                    user.set_password(user_data['password'])
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Created {user.role}: {user.email} / {user_data["password"]}')
                    )
                else:
                    # Update password for existing users
                    user.set_password(user_data['password'])
                    user.school = school
                    user.save()
                    self.stdout.write(
                        self.style.WARNING(f'Updated {user.role}: {user.email} / {user_data["password"]}')
                    )

            self.stdout.write(self.style.SUCCESS('\n✅ Demo data setup complete!'))
            self.stdout.write(self.style.SUCCESS('\n🏫 Schools Created:'))
            self.stdout.write(self.style.SUCCESS('• SomaMange Primary School (P1-P7)'))
            self.stdout.write(self.style.SUCCESS('• SomaMange Secondary School (S1-S6)'))
            
            self.stdout.write(self.style.SUCCESS('\n🔑 Login Credentials:'))
            self.stdout.write(self.style.SUCCESS('\n📚 PRIMARY SCHOOL:'))
            self.stdout.write(self.style.SUCCESS('Headteacher: primary.headteacher@somamage.com / headteacher123'))
            self.stdout.write(self.style.SUCCESS('Teacher: primary.teacher@somamage.com / teacher123'))
            self.stdout.write(self.style.SUCCESS('Parent: parent@somamage.com / parent123'))
            
            self.stdout.write(self.style.SUCCESS('\n🎓 SECONDARY SCHOOL:'))
            self.stdout.write(self.style.SUCCESS('Headteacher: secondary.headteacher@somamage.com / headteacher123'))
            self.stdout.write(self.style.SUCCESS('Teacher: secondary.teacher@somamage.com / teacher123'))
            self.stdout.write(self.style.SUCCESS('Director of Studies: dos@somamage.com / dos123'))
            
            self.stdout.write(self.style.SUCCESS('\n💼 SHARED STAFF:'))
            self.stdout.write(self.style.SUCCESS('Bursar: bursar@somamage.com / bursar123'))
            
            self.stdout.write(self.style.SUCCESS('\n👑 Super Admin: admin@somamage.com / admin123'))
            self.stdout.write(self.style.SUCCESS('\n🎯 System supports both Primary (P1-P7) and Secondary (S1-S6) schools!'))
