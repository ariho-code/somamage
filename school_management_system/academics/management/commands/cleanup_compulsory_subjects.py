"""
Management command to clean up incorrectly marked compulsory subjects
This ensures that only subjects marked as compulsory in the Subject model
are marked as compulsory in EnrollmentSubject records
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from academics.models import Subject
from students.models import EnrollmentSubject, Enrollment


class Command(BaseCommand):
    help = 'Clean up incorrectly marked compulsory subjects to match Subject model settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all O-Level subjects that are actually compulsory
        actual_compulsory_subjects = Subject.objects.filter(
            level='O',
            is_compulsory=True
        )
        actual_compulsory_subject_ids = set(actual_compulsory_subjects.values_list('id', flat=True))
        
        self.stdout.write(self.style.SUCCESS(f'Found {len(actual_compulsory_subject_ids)} actual compulsory O-Level subjects'))
        
        # Get all O-Level enrollments
        o_level_enrollments = Enrollment.objects.filter(
            grade__level='O',
            is_active=True
        )
        
        total_enrollments = o_level_enrollments.count()
        self.stdout.write(self.style.SUCCESS(f'Processing {total_enrollments} O-Level enrollments'))
        
        # Process each enrollment
        cleaned_count = 0
        removed_count = 0
        updated_count = 0
        
        for enrollment in o_level_enrollments:
            # Get all EnrollmentSubject records for this enrollment
            enrollment_subjects = EnrollmentSubject.objects.filter(
                enrollment=enrollment
            ).select_related('subject')
            
            for enrollment_subject in enrollment_subjects:
                subject = enrollment_subject.subject
                subject_id = subject.id
                
                # Check if subject is actually compulsory
                is_actually_compulsory = subject_id in actual_compulsory_subject_ids
                
                # If EnrollmentSubject says it's compulsory but Subject says it's not
                if enrollment_subject.is_compulsory and not is_actually_compulsory:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would remove: {subject.name} from {enrollment.student.get_full_name()} '
                                f'(marked compulsory but subject is not compulsory)'
                            )
                        )
                    else:
                        # Remove the EnrollmentSubject if it was auto-assigned (compulsory=True)
                        # This means it was added automatically, so we can safely remove it
                        enrollment_subject.delete()
                        removed_count += 1
                
                # If EnrollmentSubject says it's not compulsory but Subject says it is
                elif not enrollment_subject.is_compulsory and is_actually_compulsory:
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(
                                f'Would update: {subject.name} for {enrollment.student.get_full_name()} '
                                f'(subject is compulsory but not marked as such)'
                            )
                        )
                    else:
                        # Update to mark as compulsory
                        enrollment_subject.is_compulsory = True
                        enrollment_subject.save(update_fields=['is_compulsory'])
                        updated_count += 1
                
                # If both match, no action needed
                else:
                    cleaned_count += 1
        
        # Summary
        if dry_run:
            self.stdout.write(self.style.SUCCESS('\n=== DRY RUN SUMMARY ==='))
            self.stdout.write(self.style.SUCCESS(f'Would remove: {removed_count} incorrectly marked compulsory subjects'))
            self.stdout.write(self.style.SUCCESS(f'Would update: {updated_count} subjects to mark as compulsory'))
            self.stdout.write(self.style.SUCCESS(f'Correctly configured: {cleaned_count} subjects'))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== CLEANUP SUMMARY ==='))
            self.stdout.write(self.style.SUCCESS(f'Removed: {removed_count} incorrectly marked compulsory subjects'))
            self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count} subjects to mark as compulsory'))
            self.stdout.write(self.style.SUCCESS(f'Already correct: {cleaned_count} subjects'))
            self.stdout.write(self.style.SUCCESS('Cleanup completed successfully!'))

