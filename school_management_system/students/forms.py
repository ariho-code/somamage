from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Student, Guardian, Enrollment

User = get_user_model()

class UserForm(UserCreationForm):
    phone_number = forms.CharField(max_length=20, required=False, label="Phone Number")
    date_of_birth = forms.DateField(required=False, label="Date of Birth", widget=forms.DateInput(attrs={'type': 'date'}))
    qualifications = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label="Qualifications")
    bio = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}), label="Biography")
    
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2", 
                  "phone_number", "date_of_birth", "qualifications", "bio")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Manually save the extra fields since UserCreationForm doesn't handle them
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.qualifications = self.cleaned_data.get('qualifications', '')
        user.bio = self.cleaned_data.get('bio', '')
        if commit:
            user.save()
        return user

class GuardianForm(forms.ModelForm):
    class Meta:
        model = Guardian
        fields = ("name", "phone", "email", "address")
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        # exclude user/guardian since they are created/assigned in the view
        exclude = ("user", "guardian")
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'index_number': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            # Medical fields
            'has_disabilities': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'disabilities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe any disabilities'}),
            'has_chronic_diseases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'chronic_diseases': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List chronic diseases (e.g., HIV, diabetes, asthma)'}),
            'has_special_care_needs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'special_care_needs': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe special care requirements'}),
            'medical_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional medical information'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact person name'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency contact phone number'}),
            'blood_group': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., A+, O-'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List any allergies'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make medical detail fields conditional based on checkboxes
        if self.instance and self.instance.pk:
            if not self.instance.has_disabilities:
                self.fields['disabilities'].widget.attrs['disabled'] = True
            if not self.instance.has_chronic_diseases:
                self.fields['chronic_diseases'].widget.attrs['disabled'] = True
            if not self.instance.has_special_care_needs:
                self.fields['special_care_needs'].widget.attrs['disabled'] = True

class EnrollmentForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        exclude = ("student",)
        widgets = {
            'grade': forms.Select(attrs={'class': 'form-control', 'id': 'id_grade'}),
            'combination': forms.Select(attrs={'class': 'form-control', 'id': 'id_combination'}),
            'academic_year': forms.Select(attrs={'class': 'form-control'}),
            'date_joined': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_left': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'stream': forms.Select(attrs={'class': 'form-control', 'id': 'id_stream'}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Check if user is a class teacher
        from academics.models import Grade
        class_teacher_grades = None
        is_class_teacher = False
        
        if user and not (hasattr(user, 'is_superadmin') and user.is_superadmin()) and not (hasattr(user, 'is_headteacher') and user.is_headteacher()):
            class_teacher_grades = Grade.objects.filter(class_teacher=user)
            if class_teacher_grades.exists():
                is_class_teacher = True
                # Class teacher - auto-select and lock their assigned class(es)
                if class_teacher_grades.count() == 1:
                    # Single class - auto-select and make read-only
                    self.fields['grade'].queryset = class_teacher_grades
                    self.fields['grade'].initial = class_teacher_grades.first().id
                    self.fields['grade'].widget.attrs['readonly'] = True
                    self.fields['grade'].widget.attrs['disabled'] = True
                    self.fields['grade'].help_text = f"Class Teacher of {class_teacher_grades.first().name} (Locked)"
                else:
                    # Multiple classes - allow selection but only from their classes
                    self.fields['grade'].queryset = class_teacher_grades
                    self.fields['grade'].help_text = "Select one of your assigned classes"
                # Set academic years based on class teacher's school
                from core.models import AcademicYear
                if class_teacher_grades.exists():
                    teacher_school = class_teacher_grades.first().school
                    self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=teacher_school)
        
        # Filter grades by school and school type (if not class teacher or editing existing enrollment)
        if not is_class_teacher:
            # Check if editing existing enrollment first
            if hasattr(self.instance, 'pk') and self.instance.pk and hasattr(self.instance, 'grade') and self.instance.grade:
                # If editing existing enrollment, filter by the enrollment's grade's school
                edit_school = self.instance.grade.school
                if edit_school.is_primary():
                    self.fields['grade'].queryset = Grade.objects.filter(school=edit_school, level='P')
                elif edit_school.is_high_school():
                    self.fields['grade'].queryset = Grade.objects.filter(school=edit_school, level__in=['O', 'A'])
                else:
                    self.fields['grade'].queryset = Grade.objects.filter(school=edit_school)
                from core.models import AcademicYear
                self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=edit_school)
            elif school:
                # Filter by school - Primary schools only see Primary grades, High schools only see O-Level/A-Level
                if hasattr(school, 'is_primary') and school.is_primary():
                    self.fields['grade'].queryset = Grade.objects.filter(school=school, level='P')
                elif hasattr(school, 'is_high_school') and school.is_high_school():
                    self.fields['grade'].queryset = Grade.objects.filter(school=school, level__in=['O', 'A'])
                else:
                    self.fields['grade'].queryset = Grade.objects.filter(school=school)
                
                # Filter academic years by school
                from core.models import AcademicYear
                self.fields['academic_year'].queryset = AcademicYear.objects.filter(school=school)
            else:
                # Superadmin or no school - show all grades
                self.fields['grade'].queryset = Grade.objects.all().order_by('school__name', 'level', 'name')
                from core.models import AcademicYear
                self.fields['academic_year'].queryset = AcademicYear.objects.all().order_by('-name')
        
        # Add combination field for A-Level students (populated dynamically via JavaScript)
        from academics.models import Combination
        if 'combination' not in self.fields:
            self.fields['combination'] = forms.ModelChoiceField(
                queryset=Combination.objects.none(),
                required=False,
                widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_combination'}),
                help_text="Select combination for A-Level students (required for A-Level)"
            )
        
        # Make combination required if grade is A-Level
        if hasattr(self, 'initial') and self.initial.get('grade'):
            from academics.models import Grade
            try:
                grade = Grade.objects.get(id=self.initial['grade'])
                if grade.level == 'A':
                    self.fields['combination'].required = True
                    self.fields['combination'].queryset = Combination.objects.filter(grade=grade)
            except:
                pass
        
        # If editing and enrollment has a grade, populate combinations for that grade
        if hasattr(self.instance, 'pk') and self.instance.pk and self.instance.grade and self.instance.grade.level == 'A':
            self.fields['combination'].queryset = Combination.objects.filter(grade=self.instance.grade)
        
        # Make stream a Select field - populated by JavaScript
        self.fields['stream'].required = False
        self.fields['stream'].widget = forms.Select(attrs={'class': 'form-control', 'id': 'id_stream'})
        self.fields['stream'].choices = [('', '-- Select Grade First --')]
        self.fields['stream'].help_text = "Streams will appear after selecting a grade"
        
        # Allow past dates for enrollment
        self.fields['date_joined'].required = True
        if not self.instance.pk:
            # For new enrollments, default to today but allow past dates
            from django.utils import timezone
            self.fields['date_joined'].initial = timezone.now().date()