from django.core.management.base import BaseCommand
from academics.models import GradingSystem, GradeScale
from core.models import School


class Command(BaseCommand):
    help = 'Delete all existing grading systems and scales, then reinitialize with correct Ugandan grading systems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        if not force:
            self.stdout.write(self.style.WARNING(
                'This will delete ALL existing grading systems and scales!'
            ))
            confirm = input('Are you sure you want to continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return
        
        # Delete all existing grade scales first (due to foreign key constraint)
        scale_count = GradeScale.objects.count()
        GradeScale.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {scale_count} grade scales.'))
        
        # Delete all existing grading systems
        system_count = GradingSystem.objects.count()
        GradingSystem.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {system_count} grading systems.'))
        
        # Reinitialize grading systems for each school
        schools = School.objects.all()
        primary_systems = 0
        olevel_systems = 0
        alevel_systems = 0
        
        for school in schools:
            if school.is_primary():
                # Create Primary grading system
                gs, created = GradingSystem.objects.get_or_create(
                    school=school,
                    level='Primary',
                    defaults={
                        'name': 'Uganda Primary Curriculum',
                        'is_active': True
                    }
                )
                if created:
                    gs.initialize_primary_grading_scales()
                    primary_systems += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Created Primary grading system for {school.name}'
                    ))
                else:
                    # Reinitialize scales even if system exists
                    gs.scales.all().delete()
                    gs.initialize_primary_grading_scales()
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Reinitialized Primary grading scales for {school.name}'
                    ))
            
            elif school.is_high_school():
                # Create O-Level grading system
                gs_olevel, created = GradingSystem.objects.get_or_create(
                    school=school,
                    level='O-Level',
                    defaults={
                        'name': 'Uganda O-Level Curriculum',
                        'is_active': True
                    }
                )
                if created:
                    gs_olevel.initialize_olevel_grading_scales()
                    olevel_systems += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Created O-Level grading system for {school.name}'
                    ))
                else:
                    gs_olevel.scales.all().delete()
                    gs_olevel.initialize_olevel_grading_scales()
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Reinitialized O-Level grading scales for {school.name}'
                    ))
                
                # Create A-Level grading system
                gs_alevel, created = GradingSystem.objects.get_or_create(
                    school=school,
                    level='A-Level',
                    defaults={
                        'name': 'Uganda A-Level Curriculum',
                        'is_active': True
                    }
                )
                if created:
                    gs_alevel.initialize_alevel_grading_scales()
                    alevel_systems += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Created A-Level grading system for {school.name}'
                    ))
                else:
                    gs_alevel.scales.all().delete()
                    gs_alevel.initialize_alevel_grading_scales()
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Reinitialized A-Level grading scales for {school.name}'
                    ))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(self.style.SUCCESS(f'Primary grading systems: {primary_systems}'))
        self.stdout.write(self.style.SUCCESS(f'O-Level grading systems: {olevel_systems}'))
        self.stdout.write(self.style.SUCCESS(f'A-Level grading systems: {alevel_systems}'))
        self.stdout.write(self.style.SUCCESS('\nAll grading systems have been reset and reinitialized!'))
        self.stdout.write(self.style.SUCCESS('='*60))

