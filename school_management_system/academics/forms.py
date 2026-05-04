from django import forms
from academics.models import Grade, Subject, SubjectPaper, Combination, UACEGradingConfig
from academics.models import Stream, GradingSystem
from django.contrib.auth import get_user_model

User = get_user_model()

class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ["school", "name", "code", "level", "class_teacher"]
        widgets = {
            "level": forms.Select(),
            "class_teacher": forms.Select(),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter level choices based on school type
        # First check if school was passed as parameter
        if school is None:
            if self.instance and self.instance.pk and self.instance.school:
                # Editing existing grade
                school = self.instance.school
            elif 'school' in self.data:
                # Form has been submitted with school data
                try:
                    from core.models import School
                    school_id = self.data.get('school')
                    if school_id:
                        school = School.objects.get(pk=school_id)
                    else:
                        school = None
                except (School.DoesNotExist, ValueError):
                    school = None
            elif 'school' in self.initial:
                # School is set in initial data (from view)
                try:
                    from core.models import School
                    school = self.initial['school']
                except (AttributeError, ValueError):
                    school = None
        
        # Set level choices based on school type
        if school:
            if school.is_primary():
                self.fields['level'].choices = [('P', 'Primary')]
            elif school.is_high_school():
                self.fields['level'].choices = [('O', 'O-Level'), ('A', 'A-Level')]
            else:
                self.fields['level'].choices = [('P', 'Primary'), ('O','O-Level'), ('A','A-Level')]
        else:
            # Default to all choices if no school selected
            self.fields['level'].choices = [('P', 'Primary'), ('O','O-Level'), ('A','A-Level')]
        
        # Filter class_teacher queryset by school
        if school:
            self.fields['class_teacher'].queryset = User.objects.filter(role='teacher', school=school)
        else:
            self.fields['class_teacher'].queryset = User.objects.filter(role='teacher')

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "code", "level", "is_compulsory", "has_papers", "has_elective_papers", "paper_selection_mode"]
        widgets = {
            "level": forms.Select(attrs={'onchange': 'toggleCompulsoryField()'}),
            "is_compulsory": forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_compulsory'}),
            "has_papers": forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'togglePaperSelectionMode()'}),
            "has_elective_papers": forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            "paper_selection_mode": forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter level choices based on school type
        if school:
            if school.is_primary():
                self.fields['level'].choices = [('P', 'Primary')]
            elif school.is_high_school():
                self.fields['level'].choices = [('O', 'O-Level'), ('A', 'A-Level')]
            else:
                self.fields['level'].choices = [('P', 'Primary'), ('O','O-Level'), ('A','A-Level')]
        else:
            # Default to all choices if no school selected
            self.fields['level'].choices = [('P', 'Primary'), ('O','O-Level'), ('A','A-Level')]
        
        # Only show is_compulsory for O-Level subjects
        if self.instance.pk and self.instance.level != 'O':
            self.fields['is_compulsory'].widget = forms.HiddenInput()
        elif 'level' in self.initial and self.initial['level'] != 'O':
            self.fields['is_compulsory'].widget = forms.HiddenInput()


class SubjectPaperForm(forms.ModelForm):
    class Meta:
        model = SubjectPaper
        fields = ["subject", "name", "paper_number", "code", "description", "is_active"]
        widgets = {
            "subject": forms.Select(attrs={'class': 'form-control'}),
            "name": forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Paper 1, Pure Mathematics'}),
            "paper_number": forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            "code": forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., LIT1, MATH-PURE'}),
            "description": forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            "is_active": forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter subjects to only those that have_papers=True and are high school level
        if school:
            subjects = Subject.objects.filter(
                level__in=['O', 'A'],
                has_papers=True
            )
        else:
            subjects = Subject.objects.filter(
                level__in=['O', 'A'],
                has_papers=True
            )
        
        self.fields['subject'].queryset = subjects


class CombinationForm(forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.none(), # Will be filtered in __init__
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select 3 principal subjects for this combination (only A-Level subjects)"
    )

    class Meta:
        model = Combination
        fields = ['name', 'code', 'subjects', 'subsidiary_choice']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'subsidiary_choice': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter subjects to A-Level only (exclude subsidiaries)
        from academics.uace_grading import is_subsidiary_subject
        all_a_level = Subject.objects.filter(level='A')
        # Only show principal subjects (not subsidiaries)
        principal_subjects = [s for s in all_a_level if not is_subsidiary_subject(s.name)]
        
        if school:
            self.fields['subjects'].queryset = Subject.objects.filter(id__in=[s.id for s in principal_subjects])
        else:
            # Superadmin can see all A-Level principal subjects
            self.fields['subjects'].queryset = Subject.objects.filter(id__in=[s.id for s in principal_subjects])
        
        # Add help text for subsidiary choice
        self.fields['subsidiary_choice'].help_text = (
            "Auto: Determines based on principals (Math → Sub-ICT, Economics → Sub-Math, Science → Sub-Math). "
            "Or choose Sub-Math or Sub-ICT explicitly."
        )


class GradingSystemForm(forms.ModelForm):
    class Meta:
        model = GradingSystem
        fields = ['level', 'name', 'is_active']
        widgets = {
            'level': forms.Select(),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Uganda Curriculum'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        # Filter level choices based on school type
        if school:
            if school.is_primary():
                self.fields['level'].choices = [('Primary', 'Primary')]
            elif school.is_high_school():
                self.fields['level'].choices = [('O-Level', 'O-Level'), ('A-Level', 'A-Level')]
            else:
                self.fields['level'].choices = GradingSystem.LEVEL_CHOICES
        else:
            self.fields['level'].choices = GradingSystem.LEVEL_CHOICES


class StreamForm(forms.ModelForm):
    class Meta:
        model = Stream
        fields = ['school', 'grade', 'name']


class AssignRoleForm(forms.Form):
    role = forms.ChoiceField(choices=[('teacher','Teacher'), ('director_of_studies','Director of Studies'), ('bursar','Bursar')])


class GradeScaleForm(forms.ModelForm):
    class Meta:
        model = __import__('academics.models', fromlist=['GradeScale']).GradeScale
        fields = ['grading_system', 'grade', 'min_score', 'max_score', 'points', 'remark']
        widgets = {
            'grading_system': forms.HiddenInput(),
        }


from core.models import Term

class ExamForm(forms.ModelForm):
    class Meta:
        model = __import__('academics.models', fromlist=['Exam']).Exam
        fields = ['name', 'percentage_weight', 'term', 'is_active', 'order']

    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)

        # Add class to each field
        self.fields['name'].widget.attrs['class'] = 'form-control'
        self.fields['name'].widget.attrs['placeholder'] = 'e.g., CAT 1, Mid-Term, End of Term'
        
        self.fields['percentage_weight'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'max': '100'
        })
        
        self.fields['order'].widget.attrs.update({
            'class': 'form-control',
            'min': '0'
        })
        
        self.fields['is_active'].widget.attrs['class'] = 'form-check-input'
        
        # Get available terms for the school
        if school:
            # Use direct query to avoid related name issues - NEVER use school.academic_years or school.academicyear_set
            from core.models import AcademicYear
            try:
                current_year = AcademicYear.objects.filter(school=school, is_active=True).first()
                if not current_year:
                    # If no active year, get most recent year
                    current_year = AcademicYear.objects.filter(school=school).order_by('-start_date').first()
            except AttributeError:
                # Fallback: direct query if anything goes wrong
                current_year = AcademicYear.objects.filter(school=school, is_active=True).first() or \
                              AcademicYear.objects.filter(school=school).order_by('-start_date').first()
            
            if current_year:
                # Get terms for the current academic year
                terms = Term.objects.filter(
                    academic_year=current_year
                ).select_related('academic_year').order_by('start_date')
                
                # Debug print
                print(f"School: {school.name}")
                print(f"Current Year: {current_year.name}")
                print(f"Terms found: {terms.count()}")
                for term in terms:
                    print(f"- {term.name} ({term.academic_year.name})")
            else:
                terms = Term.objects.none()
                print(f"No academic year found for school: {school.name}")
        else:
            # For superadmin, show all terms
            terms = Term.objects.all().select_related('academic_year').order_by('-academic_year__name', 'name')
            print("Superadmin: showing all terms")
            print(f"Terms found: {terms.count()}")
            for term in terms:
                print(f"- {term.name} ({term.academic_year.name})")
        
        # Set up the term field
        self.fields['term'] = forms.ModelChoiceField(
            queryset=terms,
            widget=forms.Select(attrs={'class': 'form-control'}),
            empty_label='-- No terms configured --' if not terms.exists() else None
        )
        
        # Don't override choices for ModelChoiceField - it will use __str__ method
        # But ensure we're using a Select widget
        self.fields['term'].widget = forms.Select(attrs={'class': 'form-control'})
    
    def save(self, commit=True):
        exam = super().save(commit=False)
        # School will be set in the view if not already set
        if commit:
            exam.save()
        return exam


class UACEGradingConfigForm(forms.ModelForm):
    """Form for editing UACE Grading Configuration"""
    class Meta:
        model = UACEGradingConfig
        fields = [
            # Numerical Grade Ranges (1-9)
            'grade_1_min', 'grade_1_max',
            'grade_2_min', 'grade_2_max',
            'grade_3_min', 'grade_3_max',
            'grade_4_min', 'grade_4_max',
            'grade_5_min', 'grade_5_max',
            'grade_6_min', 'grade_6_max',
            'grade_7_min', 'grade_7_max',
            'grade_8_min', 'grade_8_max',
            'grade_9_min', 'grade_9_max',
            # Points System
            'points_a', 'points_b', 'points_c', 'points_d', 'points_e', 'points_o', 'points_f',
            'points_subsidiary_pass', 'points_subsidiary_fail',
            # Subsidiary Pass Threshold
            'subsidiary_pass_max_grade',
        ]
        widgets = {
            'grade_1_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_1_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_2_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_2_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_3_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_3_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_4_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_4_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_5_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_5_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_6_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_6_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_7_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_7_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_8_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_8_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_9_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'grade_9_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'}),
            'points_a': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_b': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_c': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_d': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_e': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_o': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_f': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_subsidiary_pass': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'points_subsidiary_fail': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'subsidiary_pass_max_grade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '9'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate grade ranges are in order (1 should be highest, 9 should be lowest)
        for grade_num in range(1, 10):
            min_attr = f'grade_{grade_num}_min'
            max_attr = f'grade_{grade_num}_max'
            min_val = cleaned_data.get(min_attr)
            max_val = cleaned_data.get(max_attr)
            
            if min_val and max_val:
                if min_val > max_val:
                    raise forms.ValidationError(f'Grade {grade_num}: Minimum value cannot be greater than maximum value.')
        
        # Validate ranges don't overlap (basic check)
        for grade_num in range(1, 9):
            current_max = cleaned_data.get(f'grade_{grade_num}_max')
            next_min = cleaned_data.get(f'grade_{grade_num + 1}_min')
            
            if current_max and next_min and current_max >= next_min:
                # Allow slight overlap (0.1) but warn if significant
                if current_max > next_min + 0.1:
                    raise forms.ValidationError(f'Grade {grade_num} and Grade {grade_num + 1} ranges overlap significantly.')
        
        return cleaned_data
