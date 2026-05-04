from django.db import models
from django.conf import settings
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class Grade(models.Model):
    school = models.ForeignKey('core.School', on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=20, blank=True, null=True)
    level = models.CharField(
        max_length=1,
        choices=(('P', 'Primary'), ('O','O-Level'), ('A','A-Level')),
        default='P',
    )
    class_teacher = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        limit_choices_to={'role': 'teacher'},
        related_name='classes_taught',
        help_text="Class teacher for this grade"
    )

    def __str__(self):
        return self.name

class Subject(models.Model):
    PAPER_SELECTION_CHOICES = [
        ('selective', 'Selective Papers (Students/Teachers choose which papers)'),
        ('all_compulsory', 'All Papers Compulsory (All papers automatically assigned)'),
    ]
    
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    level = models.CharField(max_length=1, choices=(('P', 'Primary'), ("O", "O-Level"), ("A", "A-Level")), default='P')
    is_compulsory = models.BooleanField(default=False, help_text="Compulsory subject for O-Level (automatically assigned)")
    has_papers = models.BooleanField(default=False, help_text="Subject has multiple papers (e.g., Literature, Mathematics)")
    has_elective_papers = models.BooleanField(default=False, help_text="Subject has elective papers that students/teachers can choose from (e.g., History, Art, French). Only these subjects appear when assigning papers.")
    paper_selection_mode = models.CharField(
        max_length=20,
        choices=PAPER_SELECTION_CHOICES,
        default='selective',
        help_text="If subject has papers, choose whether papers are selective (students/teachers choose) or all compulsory (all papers assigned automatically)"
    )

    def __str__(self):
        return self.name
    
    def get_papers(self):
        """Get all papers for this subject"""
        return self.papers.all().order_by('paper_number')
    
    def save(self, *args, **kwargs):
        """Override save to sync enrollments when compulsory status changes"""
        # Track if this is a new object or if is_compulsory/level changed
        is_new = self.pk is None
        old_is_compulsory = None
        old_level = None
        
        if not is_new:
            try:
                old_instance = Subject.objects.get(pk=self.pk)
                old_is_compulsory = old_instance.is_compulsory
                old_level = old_instance.level
            except Subject.DoesNotExist:
                pass
        
        # Save the subject first
        super().save(*args, **kwargs)
        
        # Sync enrollments for O-Level or Primary subjects
        if self.level == 'O' or self.level == 'P':
            if is_new:
                # For new subjects, sync if compulsory
                if self.is_compulsory:
                    self.sync_enrollments(None, None)
            else:
                # For existing subjects, sync if compulsory status or level changed
                compulsory_changed = (old_is_compulsory is not None and old_is_compulsory != self.is_compulsory)
                level_changed = (old_level is not None and old_level != self.level)
                
                if compulsory_changed or level_changed:
                    self.sync_enrollments(old_is_compulsory, old_level)
    
    def sync_enrollments(self, old_is_compulsory=None, old_level=None):
        """Sync subject assignments with enrollments when compulsory status or level changes"""
        from students.models import Enrollment, EnrollmentSubject
        from academics.models import StudentPaperAssignment
        
        # Handle O-Level subjects
        if self.level == 'O':
            # Get all active O-Level enrollments
            o_level_enrollments = Enrollment.objects.filter(
                grade__level='O',
                is_active=True
            ).select_related('grade', 'student')
            
            if self.is_compulsory:
                # Subject is now compulsory - add to all O-Level enrollments
                for enrollment in o_level_enrollments:
                    enrollment_subject, created = EnrollmentSubject.objects.get_or_create(
                        enrollment=enrollment,
                        subject=self,
                        defaults={'is_compulsory': True}
                    )
                    # Update is_compulsory flag if it already existed but wasn't marked as compulsory
                    if not created and not enrollment_subject.is_compulsory:
                        enrollment_subject.is_compulsory = True
                        enrollment_subject.save(update_fields=['is_compulsory'])
                    
                    # If subject has papers and is all_compulsory, auto-assign all papers
                    if self.has_papers and self.paper_selection_mode == 'all_compulsory':
                        all_papers = self.get_papers()
                        if all_papers.exists():
                            assignment, _ = StudentPaperAssignment.objects.get_or_create(
                                enrollment=enrollment,
                                subject=self,
                                defaults={}
                            )
                            assignment.papers.set(all_papers)
            else:
                # Subject is no longer compulsory - remove from O-Level enrollments
                # BUT only if it was automatically assigned (is_compulsory=True)
                # We'll keep it if it was manually assigned (is_compulsory=False) as an optional subject
                EnrollmentSubject.objects.filter(
                    enrollment__grade__level='O',
                    enrollment__is_active=True,
                    subject=self,
                    is_compulsory=True
                ).delete()
        
        # Handle Primary level subjects
        elif self.level == 'P':
            # Get all active Primary enrollments
            primary_enrollments = Enrollment.objects.filter(
                grade__level='P',
                is_active=True
            ).select_related('grade', 'student')
            
            if self.is_compulsory:
                # Subject is now compulsory - add to all Primary enrollments
                for enrollment in primary_enrollments:
                    enrollment_subject, created = EnrollmentSubject.objects.get_or_create(
                        enrollment=enrollment,
                        subject=self,
                        defaults={'is_compulsory': True}
                    )
                    # Update is_compulsory flag if it already existed but wasn't marked as compulsory
                    if not created and not enrollment_subject.is_compulsory:
                        enrollment_subject.is_compulsory = True
                        enrollment_subject.save(update_fields=['is_compulsory'])
                    
                    # If subject has papers and is all_compulsory, auto-assign all papers
                    if self.has_papers and self.paper_selection_mode == 'all_compulsory':
                        all_papers = self.get_papers()
                        if all_papers.exists():
                            assignment, _ = StudentPaperAssignment.objects.get_or_create(
                                enrollment=enrollment,
                                subject=self,
                                defaults={}
                            )
                            assignment.papers.set(all_papers)
            else:
                # Subject is no longer compulsory - remove from Primary enrollments
                EnrollmentSubject.objects.filter(
                    enrollment__grade__level='P',
                    enrollment__is_active=True,
                    subject=self,
                    is_compulsory=True
                ).delete()
        
        # Handle level changes (e.g., O-Level to A-Level)
        if old_level and old_level != self.level:
            # Remove from enrollments of the old level
            if old_level == 'O':
                EnrollmentSubject.objects.filter(
                    enrollment__grade__level='O',
                    enrollment__is_active=True,
                    subject=self,
                    is_compulsory=True
                ).delete()
            elif old_level == 'P':
                EnrollmentSubject.objects.filter(
                    enrollment__grade__level='P',
                    enrollment__is_active=True,
                    subject=self,
                    is_compulsory=True
                ).delete()
            
            # Add to enrollments of the new level if compulsory
            if self.is_compulsory and (self.level == 'O' or self.level == 'P'):
                enrollments = Enrollment.objects.filter(
                    grade__level=self.level,
                    is_active=True
                ).select_related('grade', 'student')
                
                for enrollment in enrollments:
                    enrollment_subject, created = EnrollmentSubject.objects.get_or_create(
                        enrollment=enrollment,
                        subject=self,
                        defaults={'is_compulsory': True}
                    )
                    # Update is_compulsory flag if it already existed but wasn't marked as compulsory
                    if not created and not enrollment_subject.is_compulsory:
                        enrollment_subject.is_compulsory = True
                        enrollment_subject.save(update_fields=['is_compulsory'])


class SubjectPaper(models.Model):
    """Papers within a subject (e.g., Literature Paper 1, Paper 2, Paper 3, or Pure Mathematics, Applied Mathematics)"""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='papers')
    name = models.CharField(max_length=255, help_text="Paper name (e.g., 'Paper 1', 'Paper 2', 'Pure Mathematics', 'Applied Mathematics')")
    paper_number = models.IntegerField(null=True, blank=True, help_text="Paper number for ordering (1, 2, 3, etc.)")
    code = models.CharField(max_length=50, blank=True, help_text="Paper code (e.g., LIT1, LIT2, MATH-PURE)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['subject', 'paper_number', 'name']
        unique_together = ('subject', 'name')
        verbose_name = "Subject Paper"
        verbose_name_plural = "Subject Papers"
    
    def __str__(self):
        return f"{self.subject.name} - {self.name}"


class Combination(models.Model):
    """A-Level Combinations (e.g., Science, Arts) - cut across all A-Level grades"""
    SUBSIDIARY_CHOICES = [
        ('auto', 'Auto (Based on Principals)'),
        ('sub_math', 'Subsidiary Mathematics'),
        ('sub_ict', 'Subsidiary ICT'),
    ]
    
    grade = models.ForeignKey(Grade, on_delete=models.SET_NULL, null=True, blank=True, related_name='combinations', limit_choices_to={'level': 'A'}, help_text="Optional: Leave blank to make combination available for all A-Level grades")
    name = models.CharField(max_length=64, help_text="Combination name (e.g., PCM, BAM, Literature, etc.)")
    code = models.CharField(max_length=20, blank=True, null=True, help_text="Optional code for the combination")
    subjects = models.ManyToManyField(Subject, related_name='combinations', blank=True, help_text="Subjects in this combination")
    subsidiary_choice = models.CharField(
        max_length=10,
        choices=SUBSIDIARY_CHOICES,
        default='auto',
        help_text="Which subsidiary to assign (Sub-Math or Sub-ICT). 'Auto' will determine based on principal subjects."
    )
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('grade', 'name')]
        verbose_name = "A-Level Combination"
        verbose_name_plural = "A-Level Combinations"
    
    def __str__(self):
        if self.grade:
            return f"{self.grade.name} - {self.name}"
        return f"{self.name} (All A-Level)"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Only allow combinations for A-Level grades
        if self.grade and self.grade.level != 'A':
            raise ValidationError("Combinations can only be created for A-Level classes.")


class Stream(models.Model):
    """Streams for a grade or combination (e.g., A, B, Red, Green) - created by headteachers per school"""
    school = models.ForeignKey('core.School', on_delete=models.CASCADE, related_name='streams')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='streams', null=True, blank=True)
    combination = models.ForeignKey(Combination, on_delete=models.CASCADE, related_name='streams', null=True, blank=True, help_text="A-Level combination (optional)")
    name = models.CharField(max_length=64)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('school', 'grade', 'combination', 'name')

    def __str__(self):
        if self.combination:
            if self.combination.grade:
                return f"{self.combination.grade.name} - {self.combination.name} / {self.name}"
            return f"{self.combination.name} / {self.name}"
        elif self.grade:
            return f"{self.school.name} - {self.grade.name} / {self.name}"
        return f"{self.school.name} - {self.name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Either grade or combination must be set, not both
        if not self.grade and not self.combination:
            raise ValidationError("Either grade or combination must be set.")
        if self.grade and self.combination:
            raise ValidationError("Cannot set both grade and combination. Use combination for A-Level.")


class TeacherSubject(models.Model):
    """Links teachers to subjects they teach, with optional specific papers"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'}, related_name='subjects_taught')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True)
    papers = models.ManyToManyField(SubjectPaper, blank=True, related_name='teacher_assignments', help_text="Specific papers this teacher teaches (leave empty to teach all papers)")
    
    class Meta:
        unique_together = ('teacher', 'subject', 'grade')
    
    def __str__(self):
        paper_count = self.papers.count()
        if paper_count > 0:
            return f"{self.teacher.get_full_name()} - {self.subject.name} ({paper_count} paper{'s' if paper_count > 1 else ''}) ({self.grade.name if self.grade else 'All'})"
        return f"{self.teacher.get_full_name()} - {self.subject.name} (All papers) ({self.grade.name if self.grade else 'All'})"
    
    def save(self, *args, **kwargs):
        # Ensure subject level matches grade level if both are set
        if self.grade and self.subject and self.grade.level != self.subject.level:
            from django.core.exceptions import ValidationError
            raise ValidationError("Subject level must match grade level")
        super().save(*args, **kwargs)
    
    def get_papers_display(self):
        """Get display string for assigned papers"""
        if not self.subject.has_papers:
            return "N/A (Subject has no papers)"
        if self.papers.count() == 0:
            return "All papers"
        return ", ".join([paper.name for paper in self.papers.all()])


class Exam(models.Model):
    """Exams/Assessments that can be configured per term with percentage weights"""
    school = models.ForeignKey('core.School', on_delete=models.CASCADE, related_name='exams')
    name = models.CharField(max_length=255, help_text="Exam name (e.g., CAT 1, Mid-Term, End of Term)")
    percentage_weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentage weight (e.g., 30.00 for 30%)")
    term = models.ForeignKey('core.Term', on_delete=models.CASCADE, related_name='exams')
    is_active = models.BooleanField(default=True, help_text="Active exams can be used for mark entry")
    order = models.IntegerField(default=0, help_text="Display order")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['term', 'order', 'name']
        unique_together = ('school', 'term', 'name')
        verbose_name = "Exam/Assessment"
        verbose_name_plural = "Exams/Assessments"
    
    def __str__(self):
        return f"{self.name} ({self.percentage_weight}%) - {self.term.name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.percentage_weight < 0 or self.percentage_weight > 100:
            raise ValidationError("Percentage weight must be between 0 and 100")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class MarkEntry(models.Model):
    """Student marks entered by teachers for specific exams"""
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    subject_paper = models.ForeignKey(SubjectPaper, on_delete=models.SET_NULL, null=True, blank=True, help_text="Subject paper (if subject has papers)")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='mark_entries', null=True, blank=True, help_text="The exam/assessment this mark is for")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})
    
    # Scores and grades
    score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Exam score (0-100)", default=Decimal('0.00'))
    grade = models.CharField(max_length=10, blank=True)
    points = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('0.00'), help_text="Grade Points")
    comments = models.TextField(blank=True, help_text="Teacher's comments")
    
    date_entered = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('enrollment', 'subject', 'subject_paper', 'exam')
        ordering = ['-date_entered']
        indexes = [
            models.Index(fields=['enrollment', 'subject', 'exam']),
        ]
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # If subject has papers, subject_paper must be specified
        if self.subject and self.subject.has_papers and not self.subject_paper:
            raise ValidationError(f"{self.subject.name} has papers. Please select a paper.")
        # If subject_paper is specified, it must belong to the subject
        if self.subject_paper and self.subject and self.subject_paper.subject != self.subject:
            raise ValidationError("Subject paper must belong to the selected subject.")
    
    @property
    def term(self):
        """Return term from exam"""
        if self.exam:
            return self.exam.term
        return None
    
    def save(self, *args, **kwargs):
        # Validate using clean()
        self.full_clean()
        
        # Get grade based on grading system
        school = self.enrollment.grade.school
        grade_level = self.enrollment.grade.level
        
        # Map grade level to grading system level format
        level_map = {
            'P': 'Primary',
            'O': 'O-Level',
            'A': 'A-Level'
        }
        grading_level = level_map.get(grade_level, 'Primary')
        
        grade_scale = GradingSystem.get_grade_for_score(self.score, school, grading_level)
        if grade_scale:
            self.grade = grade_scale.grade
            self.points = grade_scale.points
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.subject.name} - {self.exam.name}"


class StudentPaperAssignment(models.Model):
    """Tracks which papers each student is assigned to for subjects with multiple papers"""
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE, related_name='paper_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    papers = models.ManyToManyField(SubjectPaper, related_name='student_assignments', help_text="Papers assigned to this student for this subject")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('enrollment', 'subject')
        verbose_name = "Student Paper Assignment"
        verbose_name_plural = "Student Paper Assignments"
    
    def __str__(self):
        # Avoid accessing papers.all() if assignment is not saved yet (to prevent recursion)
        # Use a simple string representation that doesn't trigger queries
        try:
            if self.pk:
                # Use select_related to avoid N+1 queries and recursion
                paper_count = self.papers.count()
                if paper_count > 0:
                    paper_names = ", ".join([paper.name for paper in self.papers.select_related('subject').all()[:5]])
                    if paper_count > 5:
                        paper_names += f" (+{paper_count - 5} more)"
                else:
                    paper_names = "No papers"
            else:
                paper_names = "Not saved"
        except Exception:
            paper_names = "Loading..."
        
        student_name = "N/A"
        subject_name = "N/A"
        try:
            if hasattr(self, 'enrollment') and self.enrollment:
                student_name = str(self.enrollment.student)
            if hasattr(self, 'subject') and self.subject:
                subject_name = self.subject.name
        except Exception:
            pass
        
        return f"{student_name} - {subject_name}: {paper_names}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Ensure subject has papers
        if not self.subject.has_papers:
            raise ValidationError(f"{self.subject.name} does not have multiple papers. Paper assignment is not needed.")
        # Ensure all papers belong to the subject
        # Use select_related to avoid recursion issues
        papers = self.papers.select_related('subject').all()
        for paper in papers:
            if paper.subject != self.subject:
                raise ValidationError(f"Paper {paper.name} does not belong to subject {self.subject.name}.")
    
    def save(self, *args, **kwargs):
        # Skip validation if skip_validation is in kwargs (used when setting papers)
        skip_validation = kwargs.pop('skip_validation', False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)


class ReportCard(models.Model):
    """Report cards for students"""
    enrollment = models.ForeignKey('students.Enrollment', on_delete=models.CASCADE, related_name='report_cards')
    term = models.ForeignKey('core.Term', on_delete=models.CASCADE)
    
    # Academic performance
    total_marks = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    total_points = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), help_text="Total points (A-Level: sum of all subject points)")
    overall_grade = models.CharField(max_length=10, blank=True)
    position = models.IntegerField(null=True, blank=True)
    
    # Primary/O-Level/A-Level Specific Fields (Ugandan System)
    aggregate = models.IntegerField(null=True, blank=True, help_text="Sum of grades (all for Primary, best-8 for O-Level)")
    division = models.CharField(max_length=10, blank=True, help_text="Division (1-4/U) for Primary and O-Level schools")
    
    # Comments
    class_teacher_comment = models.TextField(blank=True, help_text="Comment by class teacher")
    headteacher_comment = models.TextField(blank=True, help_text="Comment by headteacher")
    
    # Attendance summary
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    
    # Status
    is_published = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_published = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('enrollment', 'term')
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.term.name} Report Card"
    
    def get_weighted_average_per_subject(self):
        """Calculate weighted average score per subject using exam weights"""
        from django.db.models import Sum, F
        
        # Get all marks for this term
        marks = MarkEntry.objects.filter(
            enrollment=self.enrollment,
            exam__term=self.term
        ).select_related('subject', 'exam')
        
        if not marks.exists():
            return {}
        
        # Group by subject and calculate weighted average
        subject_averages = {}
        
        for subject in Subject.objects.filter(
            markentry__enrollment=self.enrollment,
            markentry__exam__term=self.term
        ).distinct():
            subject_marks = marks.filter(subject=subject)
            
            total_weighted_score = Decimal('0.00')
            total_weight = Decimal('0.00')
            
            for mark_entry in subject_marks:
                weight = mark_entry.exam.percentage_weight
                total_weighted_score += Decimal(str(mark_entry.score)) * (weight / Decimal('100.00'))
                total_weight += weight
            
            if total_weight > 0:
                weighted_avg = (total_weighted_score / (total_weight / Decimal('100.00')))
                subject_averages[subject.id] = {
                    'subject': subject,
                    'weighted_average': weighted_avg,
                    'total_weight': total_weight
                }
        
        return subject_averages
    
    def calculate_aggregate(self):
        """Calculate aggregate for Ugandan Primary or O-Level system using weighted averages"""
        grade_level = self.enrollment.grade.level
        
        # Only for primary and O-Level
        if grade_level not in ['P', 'O']:
            return None
        
        # Get weighted averages per subject
        subject_averages = self.get_weighted_average_per_subject()
        
        if not subject_averages:
            return None
        
        # Calculate grades from weighted averages
        grades = []
        school = self.enrollment.grade.school
        level_map = {'P': 'Primary', 'O': 'O-Level', 'A': 'A-Level'}
        grading_level = level_map.get(grade_level, 'Primary')
        
        for subj_data in subject_averages.values():
            weighted_avg = float(subj_data['weighted_average'])
            
            # Get grade for this weighted average
            grade_scale = GradingSystem.get_grade_for_score(
                weighted_avg,
                school,
                grading_level
            )
            
            if grade_scale:
                try:
                    grade_value = int(grade_scale.grade)
                    grades.append(grade_value)
                except (ValueError, TypeError):
                    pass
        
        if not grades:
            return None
        
        # For Primary: sum all grades
        if grade_level == 'P':
            return sum(grades)
        
        # For O-Level: sum of best 8 grades (lower is better)
        elif grade_level == 'O':
            grades_sorted = sorted(grades)[:8]  # Get best 8 (lowest values)
            return sum(grades_sorted)
        
        return None
    
    def calculate_total_points(self):
        """Calculate total points for A-Level using UACE grading system"""
        if self.enrollment.grade.level != 'A':
            return Decimal('0.00')  # Not A-Level, return default
        
        # Use UACE grading system
        from academics.uace_grading import (
            assign_numerical_grade, compute_principal_letter_grade,
            compute_subsidiary_grade, calculate_uace_points
        )
        from academics.models import SubjectPaper
        
        # Get combination subjects
        if not self.enrollment.combination:
            return Decimal('0.00')
        
        combination_subjects = self.enrollment.combination.subjects.all()
        
        # Get marks for this term
        from academics.models import MarkEntry
        marks = MarkEntry.objects.filter(
            enrollment=self.enrollment,
            exam__term=self.term,
            subject__in=combination_subjects
        ).select_related('subject', 'subject_paper', 'exam')
        
        principal_grades = {}
        subsidiary_grades = {}
        
        # Group marks by subject and paper
        from collections import defaultdict
        subject_paper_marks = defaultdict(lambda: defaultdict(lambda: {'scores': []}))
        
        for mark in marks:
            subject_key = mark.subject.id
            paper_num = 1
            if mark.subject_paper:
                paper_num = mark.subject_paper.paper_number or 1
            
            # Calculate weighted average for this paper
            # Convert Decimal to float for calculations to avoid type errors
            if mark.exam and mark.exam.percentage_weight is not None:
                # percentage_weight is a DecimalField, convert to float
                exam_weight = float(mark.exam.percentage_weight)
            else:
                exam_weight = 100.0
            
            weighted_score = float(mark.score) * (exam_weight / 100.0)
            subject_paper_marks[subject_key][paper_num]['scores'].append({
                'weighted': weighted_score,
                'weight': exam_weight
            })
        
        # Process each subject
        for subject in combination_subjects:
            subject_key = subject.id
            subject_papers = SubjectPaper.objects.filter(subject=subject, is_active=True).order_by('paper_number')
            
            # Use UACE grading helper to determine if subsidiary by subject name
            from academics.uace_grading import is_subsidiary_subject
            num_papers = subject_papers.count() if subject_papers.exists() else (len(subject_paper_marks[subject_key]) if subject_key in subject_paper_marks else 0)
            is_subsidiary = is_subsidiary_subject(subject.name, num_papers)
            
            paper_numerical_grades = []
            
            if subject_papers.exists():
                for paper in subject_papers:
                    paper_num = paper.paper_number or 1
                    if subject_key in subject_paper_marks and paper_num in subject_paper_marks[subject_key]:
                        paper_data = subject_paper_marks[subject_key][paper_num]
                        weighted_scores = paper_data['scores']
                        
                        if weighted_scores:
                            total_weighted = sum(ws['weighted'] for ws in weighted_scores)
                            total_weight = sum(ws['weight'] for ws in weighted_scores)
                            avg = (total_weighted / total_weight * 100) if total_weight > 0 else 0
                            numerical_grade = assign_numerical_grade(avg)
                            paper_numerical_grades.append(numerical_grade)
            else:
                # No papers defined - check if we have marks
                if subject_key in subject_paper_marks:
                    for paper_num, paper_data in subject_paper_marks[subject_key].items():
                        weighted_scores = paper_data['scores']
                        if weighted_scores:
                            total_weighted = sum(ws['weighted'] for ws in weighted_scores)
                            total_weight = sum(ws['weight'] for ws in weighted_scores)
                            avg = (total_weighted / total_weight * 100) if total_weight > 0 else 0
                            numerical_grade = assign_numerical_grade(avg)
                            paper_numerical_grades.append(numerical_grade)
                    # Use UACE grading helper to determine if subsidiary by subject name
                    from academics.uace_grading import is_subsidiary_subject
                    is_subsidiary = is_subsidiary_subject(subject.name, len(subject_paper_marks[subject_key]))
            
            # Calculate letter grade
            if paper_numerical_grades:
                if is_subsidiary:
                    letter_grade = compute_subsidiary_grade(paper_numerical_grades[0])
                    subsidiary_grades[subject.name] = letter_grade
                else:
                    letter_grade = compute_principal_letter_grade(paper_numerical_grades, len(paper_numerical_grades))
                    principal_grades[subject.name] = letter_grade
        
        # Calculate total points using UACE system
        total_points = calculate_uace_points(principal_grades, subsidiary_grades)
        return Decimal(str(total_points))
    
    def calculate_division(self):
        """Calculate division based on aggregate for Ugandan Primary or O-Level system"""
        grade_level = self.enrollment.grade.level
        
        # A-Level has no divisions
        if grade_level == 'A':
            return ''
        
        aggregate = self.calculate_aggregate()
        
        if aggregate is None:
            return ''
        
        # Primary School Divisions (UNEB PLE spec)
        # P7 PLE uses 4 core subjects graded 1-4 each (best = 4, worst = 16)
        if grade_level == 'P':
            if 4 <= aggregate <= 12:
                return 'I'    # Division I
            elif 13 <= aggregate <= 23:
                return 'II'   # Division II
            elif 24 <= aggregate <= 29:
                return 'III'  # Division III
            elif 30 <= aggregate <= 34:
                return 'IV'   # Division IV
            else:             # aggregate >= 35
                return 'U'    # Ungraded

        # O-Level Divisions (UNEB UCE spec — best 8 subjects, points 1–9 each)
        elif grade_level == 'O':
            if 8 <= aggregate <= 11:
                return 'I'    # Division I
            elif 12 <= aggregate <= 23:
                return 'II'   # Division II
            elif 24 <= aggregate <= 29:
                return 'III'  # Division III
            elif 30 <= aggregate <= 34:
                return 'IV'   # Division IV
            else:             # aggregate >= 35
                return 'U'    # Failure / Ungraded
        
        return ''
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate weighted averages, aggregate, points, and division"""
        grade_level = self.enrollment.grade.level
        
        # Calculate weighted averages per subject
        subject_averages = self.get_weighted_average_per_subject()
        
        # Calculate total marks and average score
        if subject_averages:
            total_marks_sum = sum(subj['weighted_average'] for subj in subject_averages.values())
            self.total_marks = Decimal(str(total_marks_sum))
            self.average_score = Decimal(str(total_marks_sum / len(subject_averages)))
        
        # Calculate aggregate and division for primary and O-Level
        if grade_level in ['P', 'O']:
            self.aggregate = self.calculate_aggregate()
            self.division = self.calculate_division()
        
        # Calculate total points for A-Level (reuse existing total_points field)
        if grade_level == 'A':
            self.total_points = self.calculate_total_points()
            self.aggregate = None  # A-Level uses points, not aggregate
            self.division = ''  # A-Level has no divisions
        
        super().save(*args, **kwargs)


class GradingSystem(models.Model):
    """Grading system configuration for Uganda curriculum"""
    LEVEL_CHOICES = [
        ('Primary', 'Primary'),
        ('O-Level', 'O-Level'),
        ('A-Level', 'A-Level'),
    ]
    
    school = models.ForeignKey('core.School', on_delete=models.CASCADE, related_name='grading_systems')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    name = models.CharField(max_length=100, default="Uganda Curriculum")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('school', 'level')
        verbose_name_plural = "Grading Systems"
    
    def __str__(self):
        return f"{self.school.name} - {self.level}"
    
    @classmethod
    def get_grade_for_score(cls, score, school, level):
        """Get grade for a given score, school, and level"""
        try:
            grading_system = cls.objects.filter(school=school, level=level, is_active=True).first()
            if grading_system:
                grade_scale = GradeScale.objects.filter(
                    grading_system=grading_system,
                    min_score__lte=score,
                    max_score__gte=score
                ).first()
                return grade_scale
        except:
            pass
        return None
    
    def initialize_primary_grading_scales(self):
        """Initialize Ugandan Primary School grading scales (Grades 1-8)"""
        if self.level != 'Primary':
            return
        
        # Check if scales already exist
        if self.scales.exists():
            return
        
        from decimal import Decimal
        
        # Ugandan Primary School Grading System (UNEB spec, Grades 1–7)
        primary_scales = [
            # Grade, Min Score, Max Score, Points, Remark
            ('1', Decimal('80.00'), Decimal('100.00'), Decimal('1.00'), 'Distinction'),
            ('2', Decimal('70.00'), Decimal('79.99'), Decimal('2.00'), 'Credit'),
            ('3', Decimal('60.00'), Decimal('69.99'), Decimal('3.00'), 'Merit'),
            ('4', Decimal('50.00'), Decimal('59.99'), Decimal('4.00'), 'Pass'),
            ('5', Decimal('40.00'), Decimal('49.99'), Decimal('5.00'), 'Satisfactory'),
            ('6', Decimal('30.00'), Decimal('39.99'), Decimal('6.00'), 'Below Average'),
            ('7', Decimal('0.00'),  Decimal('29.99'), Decimal('7.00'), 'Fail'),
        ]
        
        for grade, min_score, max_score, points, remark in primary_scales:
            GradeScale.objects.get_or_create(
                grading_system=self,
                grade=grade,
                defaults={
                    'min_score': min_score,
                    'max_score': max_score,
                    'points': points,
                    'remark': remark
                }
            )
    
    def initialize_olevel_grading_scales(self):
        """Initialize Ugandan O-Level grading scales (New Lower Secondary Curriculum, UNEB NLSC spec)"""
        if self.level != 'O-Level':
            return

        # Check if scales already exist
        if self.scales.exists():
            return

        from decimal import Decimal

        # Uganda New Lower Secondary Curriculum (NLSC) O-Level Grading
        # Introduced ~2020; first UCE under new system ~2023
        # Assessment: SBA 40% (school-based) + UNEB external exam 60%
        # Grade codes D1-F9 unchanged; D1 boundary raised to 80% under NLSC
        olevel_scales = [
            # Grade, Min Score, Max Score, Points, Remark
            ('D1', Decimal('80.00'), Decimal('100.00'), Decimal('1.00'), 'Distinction 1 — Excellent'),
            ('D2', Decimal('70.00'), Decimal('79.99'),  Decimal('2.00'), 'Distinction 2 — Very Good'),
            ('C3', Decimal('65.00'), Decimal('69.99'),  Decimal('3.00'), 'Credit 3 — Good'),
            ('C4', Decimal('60.00'), Decimal('64.99'),  Decimal('4.00'), 'Credit 4 — Good'),
            ('C5', Decimal('55.00'), Decimal('59.99'),  Decimal('5.00'), 'Credit 5 — Satisfactory'),
            ('C6', Decimal('50.00'), Decimal('54.99'),  Decimal('6.00'), 'Credit 6 — Satisfactory'),
            ('P7', Decimal('45.00'), Decimal('49.99'),  Decimal('7.00'), 'Pass 7 — Pass'),
            ('P8', Decimal('40.00'), Decimal('44.99'),  Decimal('8.00'), 'Pass 8 — Marginal Pass'),
            ('F9', Decimal('0.00'),  Decimal('39.99'),  Decimal('9.00'), 'Failure 9 — Fail'),
        ]
        
        for grade, min_score, max_score, points, remark in olevel_scales:
            GradeScale.objects.get_or_create(
                grading_system=self,
                grade=grade,
                defaults={
                    'min_score': min_score,
                    'max_score': max_score,
                    'points': points,
                    'remark': remark
                }
            )
    
    def initialize_alevel_grading_scales(self):
        """Initialize Ugandan A-Level grading scales (Letter grades A-F with points)"""
        if self.level != 'A-Level':
            return
        
        # Check if scales already exist
        if self.scales.exists():
            return
        
        from decimal import Decimal
        
        # Ugandan A-Level UACE Grading System (UNEB spec)
        alevel_scales = [
            # Grade, Min Score, Max Score, Points, Remark
            ('A', Decimal('80.00'), Decimal('100.00'), Decimal('6.00'), 'A - 6 points'),
            ('B', Decimal('70.00'), Decimal('79.99'), Decimal('5.00'), 'B - 5 points'),
            ('C', Decimal('60.00'), Decimal('69.99'), Decimal('4.00'), 'C - 4 points'),
            ('D', Decimal('50.00'), Decimal('59.99'), Decimal('3.00'), 'D - 3 points'),
            ('E', Decimal('40.00'), Decimal('49.99'), Decimal('2.00'), 'E - 2 points'),
            ('O', Decimal('35.00'), Decimal('39.99'), Decimal('1.00'), 'O - 1 point (subsidiary pass)'),
            ('F', Decimal('0.00'),  Decimal('34.99'), Decimal('0.00'), 'F - 0 points (fail)'),
        ]
        
        for grade, min_score, max_score, points, remark in alevel_scales:
            GradeScale.objects.get_or_create(
                grading_system=self,
                grade=grade,
                defaults={
                    'min_score': min_score,
                    'max_score': max_score,
                    'points': points,
                    'remark': remark
                }
            )
    
    def save(self, *args, **kwargs):
        """Override save to auto-initialize grading scales based on level"""
        created = self.pk is None
        super().save(*args, **kwargs)
        
        # Auto-initialize grading scales based on level
        if created:
            if self.level == 'Primary':
                self.initialize_primary_grading_scales()
            elif self.level == 'O-Level':
                self.initialize_olevel_grading_scales()
            elif self.level == 'A-Level':
                self.initialize_alevel_grading_scales()


class GradeScale(models.Model):
    """Grade scale for Uganda curriculum"""
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.CASCADE, related_name='scales')
    grade = models.CharField(max_length=10, help_text="Grade letter (e.g., A, B, C, D, E, F)")
    min_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Minimum percentage score")
    max_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Maximum percentage score")
    points = models.DecimalField(max_digits=5, decimal_places=2, help_text="Points value (e.g., 9 for A*, 8 for A)")
    remark = models.CharField(max_length=100, help_text="Remark (e.g., Excellent, Very Good, Good, Pass, Fail)")
    
    class Meta:
        ordering = ['-min_score']
        unique_together = ('grading_system', 'grade')
    
    def __str__(self):
        return f"{self.grade} ({self.min_score}-{self.max_score}%) - {self.remark}"


class PromotionCriteria(models.Model):
    """Promotion criteria for students based on performance"""
    grading_system = models.ForeignKey(GradingSystem, on_delete=models.CASCADE, related_name='promotion_criteria')
    min_average_score = models.DecimalField(max_digits=5, decimal_places=2, help_text="Minimum average score to promote")
    min_subjects_passed = models.IntegerField(default=5, help_text="Minimum number of subjects that must be passed")
    required_core_subjects = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Comma-separated list of required core subjects (e.g., 'Mathematics,English,Science')"
    )
    max_failures_allowed = models.IntegerField(default=2, help_text="Maximum number of subjects that can be failed")
    
    class Meta:
        verbose_name_plural = "Promotion Criteria"
    
    def __str__(self):
        return f"{self.grading_system.level} - Min Average: {self.min_average_score}%"


class UACEGradingConfig(models.Model):
    """Editable UACE Grading Configuration per school"""
    school = models.ForeignKey('core.School', on_delete=models.CASCADE, related_name='uace_grading_configs')
    
    # Numerical Grade Ranges (1-9)
    grade_1_min = models.DecimalField(max_digits=5, decimal_places=2, default=80.0, help_text="Minimum mark for D1 (Grade 1)")
    grade_1_max = models.DecimalField(max_digits=5, decimal_places=2, default=100.0, help_text="Maximum mark for D1 (Grade 1)")
    
    grade_2_min = models.DecimalField(max_digits=5, decimal_places=2, default=75.0)
    grade_2_max = models.DecimalField(max_digits=5, decimal_places=2, default=79.9)
    
    grade_3_min = models.DecimalField(max_digits=5, decimal_places=2, default=66.0)
    grade_3_max = models.DecimalField(max_digits=5, decimal_places=2, default=74.9)
    
    grade_4_min = models.DecimalField(max_digits=5, decimal_places=2, default=60.0)
    grade_4_max = models.DecimalField(max_digits=5, decimal_places=2, default=65.9)
    
    grade_5_min = models.DecimalField(max_digits=5, decimal_places=2, default=55.0)
    grade_5_max = models.DecimalField(max_digits=5, decimal_places=2, default=59.9)
    
    grade_6_min = models.DecimalField(max_digits=5, decimal_places=2, default=50.0)
    grade_6_max = models.DecimalField(max_digits=5, decimal_places=2, default=54.9)
    
    grade_7_min = models.DecimalField(max_digits=5, decimal_places=2, default=45.0)
    grade_7_max = models.DecimalField(max_digits=5, decimal_places=2, default=49.9)
    
    grade_8_min = models.DecimalField(max_digits=5, decimal_places=2, default=40.0)
    grade_8_max = models.DecimalField(max_digits=5, decimal_places=2, default=44.9)
    
    grade_9_min = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    grade_9_max = models.DecimalField(max_digits=5, decimal_places=2, default=39.9)
    
    # Points System
    points_a = models.IntegerField(default=6, help_text="Points for grade A")
    points_b = models.IntegerField(default=5)
    points_c = models.IntegerField(default=4)
    points_d = models.IntegerField(default=3)
    points_e = models.IntegerField(default=2)
    points_o = models.IntegerField(default=1)
    points_f = models.IntegerField(default=0)
    points_subsidiary_pass = models.IntegerField(default=1, help_text="Points for subsidiary Pass")
    points_subsidiary_fail = models.IntegerField(default=0, help_text="Points for subsidiary Fail")
    
    # Subsidiary Pass Threshold
    subsidiary_pass_max_grade = models.IntegerField(default=6, help_text="Maximum numerical grade (1-6) for subsidiary Pass")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('school',)
        verbose_name = "UACE Grading Configuration"
        verbose_name_plural = "UACE Grading Configurations"
    
    def __str__(self):
        return f"UACE Grading Config - {self.school.name}"
    
    def get_grade_range(self, grade_num):
        """Get min/max for a numerical grade (1-9)"""
        attr_min = f'grade_{grade_num}_min'
        attr_max = f'grade_{grade_num}_max'
        return (getattr(self, attr_min), getattr(self, attr_max))
    
    def get_points_for_letter(self, letter_grade):
        """Get points for a letter grade"""
        attr = f'points_{letter_grade.lower()}'
        return getattr(self, attr, 0)
