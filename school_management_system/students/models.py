from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Guardian(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Student(models.Model):
    GENDER_CHOICES = (('M','Male'), ('F','Female'), ('O','Other'))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    admission_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    index_number = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    guardian = models.ForeignKey(Guardian, null=True, blank=True, on_delete=models.SET_NULL)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    
    # Medical Records Fields
    has_disabilities = models.BooleanField(default=False, help_text="Check if student has any disabilities")
    disabilities = models.TextField(blank=True, null=True, help_text="Describe any disabilities the student has")
    has_chronic_diseases = models.BooleanField(default=False, help_text="Check if student has chronic diseases")
    chronic_diseases = models.TextField(blank=True, null=True, help_text="List any chronic diseases (e.g., HIV, diabetes, asthma)")
    has_special_care_needs = models.BooleanField(default=False, help_text="Check if student requires special care")
    special_care_needs = models.TextField(blank=True, null=True, help_text="Describe special care requirements")
    medical_notes = models.TextField(blank=True, null=True, help_text="Additional medical information or notes")
    emergency_contact_name = models.CharField(max_length=255, blank=True, null=True, help_text="Emergency contact person name")
    emergency_contact_phone = models.CharField(max_length=32, blank=True, null=True, help_text="Emergency contact phone number")
    blood_group = models.CharField(max_length=10, blank=True, null=True, help_text="Student's blood group (e.g., A+, O-, etc.)")
    allergies = models.TextField(blank=True, null=True, help_text="List any allergies the student has")

    def save(self, *args, **kwargs):
        # Auto-generate admission number if not provided
        if not self.admission_number:
            from django.utils import timezone
            year = timezone.now().year
            # Get the last admission number for this year
            last_student = Student.objects.filter(
                admission_number__startswith=str(year)
            ).order_by('-admission_number').first()
            
            if last_student and last_student.admission_number:
                try:
                    last_num = int(last_student.admission_number[-4:])
                    new_num = last_num + 1
                except ValueError:
                    new_num = 1
            else:
                new_num = 1
            
            self.admission_number = f"{year}{new_num:04d}"
        
        super().save(*args, **kwargs)

    def get_full_name(self):
        """Get the student's full name"""
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        elif self.user:
            full = getattr(self.user, "get_full_name", None)
            if callable(full):
                return self.user.get_full_name()
            else:
                return str(self.user)
        return f"Student {self.admission_number or self.id}"
    
    def __str__(self):
        return self.get_full_name()


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    grade = models.ForeignKey('academics.Grade', on_delete=models.PROTECT)
    combination = models.ForeignKey('academics.Combination', on_delete=models.SET_NULL, null=True, blank=True, help_text="A-Level combination (only for A-Level students)")
    stream = models.CharField(max_length=10, blank=True, null=True)
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.PROTECT)
    date_joined = models.DateField()  # Allow manual entry, including past dates
    date_left = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'academic_year')

    def __str__(self):
        return f"{self.student} - {self.grade} ({self.academic_year})"
    
    def save(self, *args, **kwargs):
        """Auto-assign subjects based on grade level and combination"""
        super().save(*args, **kwargs)
        
        # Auto-assign subjects after enrollment is saved
        if self.is_active:
            self.auto_assign_subjects()
    
    def auto_assign_subjects(self):
        """Automatically assign subjects based on grade level and combination (Ugandan curriculum)"""
        from academics.models import Subject
        from academics.uace_grading import get_required_subsidiaries, is_subsidiary_subject
        from django.db import models
        
        # A-Level: Assign subjects based on combination + required subsidiaries
        if self.grade.level == 'A' and self.combination:
            # Get principal subjects from combination
            combination_subjects = self.combination.subjects.all()
            principal_subject_names = [subj.name for subj in combination_subjects]
            
            # Get required subsidiaries based on principals and combination's subsidiary_choice
            subsidiary_choice = getattr(self.combination, 'subsidiary_choice', 'auto')
            required_subsidiary_names = get_required_subsidiaries(principal_subject_names, subsidiary_choice)
            
            # Assign principal subjects
            for subject in combination_subjects:
                EnrollmentSubject.objects.get_or_create(
                    enrollment=self,
                    subject=subject,
                    defaults={'is_compulsory': True}
                )
            
            # Assign required subsidiaries
            # First, find or create GP (General Paper) - always required
            gp_subjects = Subject.objects.filter(
                level='A'
            ).filter(
                models.Q(name__icontains='General Paper') |
                models.Q(name__icontains='GP') |
                models.Q(name__icontains='General Studies')
            )
            
            for gp_subject in gp_subjects:
                if is_subsidiary_subject(gp_subject.name):
                    EnrollmentSubject.objects.get_or_create(
                        enrollment=self,
                        subject=gp_subject,
                        defaults={'is_compulsory': True}
                    )
                    break
            
            # Find and assign the second required subsidiary (Sub-Math OR Sub-ICT, not both)
            # Only ONE subsidiary should be assigned (GP + one other)
            for req_subsidiary_name in required_subsidiary_names:
                if req_subsidiary_name == "General Paper":
                    continue  # Already handled above
                
                # Remove any existing Sub-Math or Sub-ICT before assigning new one
                # This ensures only ONE subsidiary is assigned
                existing_subsidiaries = EnrollmentSubject.objects.filter(
                    enrollment=self,
                    subject__level='A'
                ).select_related('subject')
                
                for es in existing_subsidiaries:
                    if is_subsidiary_subject(es.subject.name):
                        subj_name_upper = es.subject.name.upper()
                        # Remove if it's Sub-Math or Sub-ICT (but not GP)
                        if ('MATHEMATICS' in subj_name_upper or 'MATH' in subj_name_upper or 'MATHS' in subj_name_upper) and 'SUBSIDIARY' in subj_name_upper:
                            if req_subsidiary_name != "Subsidiary Mathematics":
                                es.delete()  # Remove Sub-Math if we're assigning Sub-ICT
                        elif ('ICT' in subj_name_upper or 'COMPUTER' in subj_name_upper) and 'SUBSIDIARY' in subj_name_upper:
                            if req_subsidiary_name != "Subsidiary ICT":
                                es.delete()  # Remove Sub-ICT if we're assigning Sub-Math
                
                # Search for the subsidiary subject
                if "Mathematics" in req_subsidiary_name:
                    # Look for Sub-Math
                    sub_math_subjects = Subject.objects.filter(
                        level='A'
                    ).filter(
                        models.Q(name__icontains='Subsidiary Mathematics') |
                        models.Q(name__icontains='Sub-Math') |
                        models.Q(name__icontains='Sub Math') |
                        models.Q(name__icontains='Subsidiary Math')
                    )
                    for sub_math_subject in sub_math_subjects:
                        if is_subsidiary_subject(sub_math_subject.name):
                            EnrollmentSubject.objects.get_or_create(
                                enrollment=self,
                                subject=sub_math_subject,
                                defaults={'is_compulsory': True}
                            )
                            break
                elif "ICT" in req_subsidiary_name or "Computer" in req_subsidiary_name:
                    # Look for Sub-ICT/Sub-Computer
                    sub_ict_subjects = Subject.objects.filter(
                        level='A'
                    ).filter(
                        models.Q(name__icontains='Subsidiary ICT') |
                        models.Q(name__icontains='Subsidiary Computer') |
                        models.Q(name__icontains='Sub-ICT') |
                        models.Q(name__icontains='Sub ICT') |
                        models.Q(name__icontains='Sub-Computer') |
                        models.Q(name__icontains='Sub Computer')
                    )
                    for sub_ict_subject in sub_ict_subjects:
                        if is_subsidiary_subject(sub_ict_subject.name):
                            EnrollmentSubject.objects.get_or_create(
                                enrollment=self,
                                subject=sub_ict_subject,
                                defaults={'is_compulsory': True}
                            )
                            break
                break  # Only assign one subsidiary (GP + one other)
        
        # O-Level: Assign compulsory subjects
        elif self.grade.level == 'O':
            from academics.models import StudentPaperAssignment
            # Only get subjects that are actually marked as compulsory in the Subject model
            # This ensures we only assign subjects that are truly compulsory
            compulsory_subjects = Subject.objects.filter(level='O', is_compulsory=True)
            
            # Also clean up any incorrectly marked compulsory subjects for this enrollment
            # Get all EnrollmentSubject records marked as compulsory
            existing_compulsory = EnrollmentSubject.objects.filter(
                enrollment=self,
                is_compulsory=True
            ).select_related('subject')
            
            actual_compulsory_subject_ids = set(compulsory_subjects.values_list('id', flat=True))
            
            # Remove any EnrollmentSubject that is marked as compulsory but the subject is not actually compulsory
            for enrollment_subject in existing_compulsory:
                if enrollment_subject.subject.id not in actual_compulsory_subject_ids:
                    enrollment_subject.delete()
            
            # Assign actual compulsory subjects
            for subject in compulsory_subjects:
                enrollment_subject, _ = EnrollmentSubject.objects.get_or_create(
                    enrollment=self,
                    subject=subject,
                    defaults={'is_compulsory': True}
                )
                # Ensure is_compulsory is set correctly
                if not enrollment_subject.is_compulsory:
                    enrollment_subject.is_compulsory = True
                    enrollment_subject.save(update_fields=['is_compulsory'])
                
                # If subject has papers and is all_compulsory, auto-assign all papers
                if subject.has_papers and subject.paper_selection_mode == 'all_compulsory':
                    all_papers = subject.get_papers()
                    if all_papers.exists():
                        assignment, _ = StudentPaperAssignment.objects.get_or_create(
                            enrollment=self,
                            subject=subject,
                            defaults={}
                        )
                        assignment.papers.set(all_papers)
        
        # Primary: Assign primary subjects (if needed)
        elif self.grade.level == 'P':
            from academics.models import StudentPaperAssignment
            primary_subjects = Subject.objects.filter(level='P', is_compulsory=True)
            for subject in primary_subjects:
                enrollment_subject, _ = EnrollmentSubject.objects.get_or_create(
                    enrollment=self,
                    subject=subject,
                    defaults={'is_compulsory': True}
                )
                # If subject has papers and is all_compulsory, auto-assign all papers
                if subject.has_papers and subject.paper_selection_mode == 'all_compulsory':
                    all_papers = subject.get_papers()
                    if all_papers.exists():
                        assignment, _ = StudentPaperAssignment.objects.get_or_create(
                            enrollment=self,
                            subject=subject,
                            defaults={}
                        )
                        assignment.papers.set(all_papers)
    
    def get_combination_subjects(self):
        """Get subjects for A-Level combination (Ugandan curriculum)"""
        from academics.models import Subject
        
        if not self.combination:
            return []
        
        # Return subjects from combination's many-to-many relationship
        return self.combination.subjects.all()
    
    def get_o_level_compulsory_subjects(self):
        """Get compulsory O-Level subjects (Ugandan curriculum)"""
        from academics.models import Subject
        
        # Ugandan O-Level compulsory subjects
        compulsory_subject_names = [
            'English', 'Mathematics', 'Physics', 'Chemistry', 'Biology',
            'Geography', 'History', 'Religious Education', 'Divinity'
        ]
        
        subjects = []
        for subject_name in compulsory_subject_names:
            subject = Subject.objects.filter(
                name__icontains=subject_name,
                level='O'
            ).first()
            if subject:
                subjects.append(subject)
        
        return subjects
    
    def get_primary_subjects(self):
        """Get primary level subjects (Ugandan curriculum)"""
        from academics.models import Subject
        
        # Primary level subjects
        primary_subject_names = [
            'English', 'Mathematics', 'Science', 'Social Studies',
            'Religious Education', 'Art', 'Physical Education'
        ]
        
        subjects = []
        for subject_name in primary_subject_names:
            subject = Subject.objects.filter(
                name__icontains=subject_name,
                level='P'
            ).first()
            if subject:
                subjects.append(subject)
        
        return subjects


class EnrollmentSubject(models.Model):
    """Track which subjects are assigned to a student enrollment"""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='enrollment_subjects')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    is_compulsory = models.BooleanField(default=True, help_text="Whether this subject is compulsory for this enrollment")
    assigned_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('enrollment', 'subject')
        verbose_name = "Enrollment Subject"
        verbose_name_plural = "Enrollment Subjects"
        ordering = ['subject__name']
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.subject.name} ({'Compulsory' if self.is_compulsory else 'Optional'})"
