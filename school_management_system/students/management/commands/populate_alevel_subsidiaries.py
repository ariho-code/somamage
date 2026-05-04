"""
Management command to populate subsidiaries for existing A-Level students.
This command will:
1. Find all A-Level students with combinations assigned
2. Automatically assign required subsidiaries (GP + Sub-Math/Sub-ICT)
3. Update existing enrollments to include subsidiaries
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from students.models import Enrollment, EnrollmentSubject
from academics.models import Subject
from academics.uace_grading import get_required_subsidiaries, is_subsidiary_subject
from django.db import models


class Command(BaseCommand):
    help = 'Populate subsidiaries for existing A-Level students based on their combinations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes (preview only)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get all active A-Level enrollments with combinations
        enrollments = Enrollment.objects.filter(
            grade__level='A',
            combination__isnull=False,
            is_active=True
        ).select_related('grade', 'combination', 'student')
        
        total_enrollments = enrollments.count()
        self.stdout.write(f'Found {total_enrollments} A-Level enrollments with combinations')
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        with transaction.atomic():
            for enrollment in enrollments:
                try:
                    # Get principal subjects from combination
                    combination_subjects = enrollment.combination.subjects.all()
                    principal_subject_names = [subj.name for subj in combination_subjects]
                    
                    # Get required subsidiaries (respect combination's subsidiary_choice)
                    subsidiary_choice = getattr(enrollment.combination, 'subsidiary_choice', 'auto')
                    required_subsidiary_names = get_required_subsidiaries(principal_subject_names, subsidiary_choice)
                    
                    # Check which subsidiaries are already assigned
                    existing_subsidiaries = EnrollmentSubject.objects.filter(
                        enrollment=enrollment,
                        subject__level='A'
                    ).select_related('subject')
                    
                    existing_subsidiary_names = [
                        es.subject.name for es in existing_subsidiaries 
                        if is_subsidiary_subject(es.subject.name)
                    ]
                    
                    # Find and assign missing subsidiaries
                    subsidiaries_assigned = []
                    
                    # Assign GP (General Paper) - always required
                    if any('General Paper' in name or 'GP' in name for name in required_subsidiary_names):
                        gp_subjects = Subject.objects.filter(level='A').filter(
                            models.Q(name__icontains='General Paper') |
                            models.Q(name__icontains='GP') |
                            models.Q(name__icontains='General Studies')
                        )
                        
                        gp_assigned = False
                        for gp_subject in gp_subjects:
                            if is_subsidiary_subject(gp_subject.name):
                                # Check if already assigned
                                if any(gp_subject.name.lower() in name.lower() or name.lower() in gp_subject.name.lower() 
                                       for name in existing_subsidiary_names):
                                    gp_assigned = True
                                    break
                                
                                if not dry_run:
                                    EnrollmentSubject.objects.get_or_create(
                                        enrollment=enrollment,
                                        subject=gp_subject,
                                        defaults={'is_compulsory': True}
                                    )
                                subsidiaries_assigned.append(gp_subject.name)
                                gp_assigned = True
                                break
                        
                        if not gp_assigned:
                            self.stdout.write(
                                self.style.WARNING(f'  Warning: GP not found for {enrollment.student.get_full_name()}')
                            )
                    
                    # Assign second subsidiary (Sub-Math or Sub-ICT)
                    for req_subsidiary_name in required_subsidiary_names:
                        if req_subsidiary_name == "General Paper":
                            continue  # Already handled
                        
                        # Check if already assigned
                        if any(req_subsidiary_name.lower() in name.lower() or name.lower() in req_subsidiary_name.lower() 
                               for name in existing_subsidiary_names):
                            continue
                        
                        if "Mathematics" in req_subsidiary_name:
                            # Look for Sub-Math
                            sub_math_subjects = Subject.objects.filter(level='A').filter(
                                models.Q(name__icontains='Subsidiary Mathematics') |
                                models.Q(name__icontains='Sub-Math') |
                                models.Q(name__icontains='Sub Math') |
                                models.Q(name__icontains='Subsidiary Math')
                            )
                            
                            for sub_math_subject in sub_math_subjects:
                                if is_subsidiary_subject(sub_math_subject.name):
                                    if not dry_run:
                                        EnrollmentSubject.objects.get_or_create(
                                            enrollment=enrollment,
                                            subject=sub_math_subject,
                                            defaults={'is_compulsory': True}
                                        )
                                    subsidiaries_assigned.append(sub_math_subject.name)
                                    break
                        
                        elif "ICT" in req_subsidiary_name or "Computer" in req_subsidiary_name:
                            # Look for Sub-ICT/Sub-Computer
                            sub_ict_subjects = Subject.objects.filter(level='A').filter(
                                models.Q(name__icontains='Subsidiary ICT') |
                                models.Q(name__icontains='Subsidiary Computer') |
                                models.Q(name__icontains='Sub-ICT') |
                                models.Q(name__icontains='Sub ICT') |
                                models.Q(name__icontains='Sub-Computer') |
                                models.Q(name__icontains='Sub Computer')
                            )
                            
                            for sub_ict_subject in sub_ict_subjects:
                                if is_subsidiary_subject(sub_ict_subject.name):
                                    if not dry_run:
                                        EnrollmentSubject.objects.get_or_create(
                                            enrollment=enrollment,
                                            subject=sub_ict_subject,
                                            defaults={'is_compulsory': True}
                                        )
                                    subsidiaries_assigned.append(sub_ict_subject.name)
                                    break
                    
                    if subsidiaries_assigned:
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  [OK] {enrollment.student.get_full_name()} ({enrollment.combination.name}): '
                                f'Assigned {", ".join(subsidiaries_assigned)}'
                            )
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            f'  [-] {enrollment.student.get_full_name()}: Already has subsidiaries'
                        )
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'  [ERROR] Error processing {enrollment.student.get_full_name()}: {str(e)}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('SUMMARY:'))
        self.stdout.write(f'  Total enrollments: {total_enrollments}')
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Skipped (already have subsidiaries): {skipped_count}')
        self.stdout.write(f'  Errors: {error_count}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN - no changes were made'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Subsidiaries populated successfully!'))

