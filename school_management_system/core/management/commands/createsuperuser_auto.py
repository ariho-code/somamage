from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class Command(BaseCommand):
    help = 'Create superuser automatically from environment variables'

    def handle(self, *args, **options):
        import os
        
        email = os.environ.get('SUPERUSER_EMAIL', 'admin@somamage.com')
        password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
        
        if not User.objects.filter(email=email).exists():
            try:
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name='Super',
                    last_name='Admin'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {email}')
                )
            except ValidationError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating superuser: {e}')
                )
        else:
            self.stdout.write(
                self.style.WARNING(f'Superuser {email} already exists')
            )
