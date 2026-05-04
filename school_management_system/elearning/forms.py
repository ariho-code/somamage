"""
E-Learning Forms
"""
from django import forms
from .models import Assignment, QuizQuestion, QuizOption, AssignmentSubmission, SubmissionAttachment

class QuizQuestionForm(forms.ModelForm):
    """Form for creating/editing quiz questions"""
    class Meta:
        model = QuizQuestion
        fields = ['question_text', 'question_type', 'points', 'order']
        widgets = {
            'question_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your question...'
            }),
            'question_type': forms.Select(attrs={'class': 'form-control'}),
            'points': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
        }


class QuizOptionForm(forms.ModelForm):
    """Form for quiz answer options"""
    class Meta:
        model = QuizOption
        fields = ['option_text', 'is_correct', 'order']
        widgets = {
            'option_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter option text...'
            }),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'})
        }


class ExamSubmissionForm(forms.ModelForm):
    """Form for exam submissions"""
    # Note: For multiple file uploads, we'll handle it in the view
    # Django forms don't natively support multiple file uploads in a single field
    
    class Meta:
        model = AssignmentSubmission
        fields = ['submission_text', 'submission_file']
        widgets = {
            'submission_text': forms.Textarea(attrs={
                'class': 'form-control exam-text-editor',
                'rows': 15,
                'placeholder': 'Type your answers here...',
                'id': 'examTextEditor'
            }),
            'submission_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            })
        }


class QuizSubmissionForm(forms.Form):
    """Form for quiz submissions - dynamically generated from questions"""
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super().__init__(*args, **kwargs)
        
        for question in questions:
            if question.question_type == 'multiple_choice':
                choices = [(opt.id, opt.option_text) for opt in question.options.all()]
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    choices=choices,
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    required=True
                )
            elif question.question_type == 'true_false':
                self.fields[f'question_{question.id}'] = forms.ChoiceField(
                    choices=[(True, 'True'), (False, 'False')],
                    widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                    required=True
                )
            elif question.question_type == 'short_answer':
                self.fields[f'question_{question.id}'] = forms.CharField(
                    widget=forms.Textarea(attrs={
                        'class': 'form-control',
                        'rows': 3,
                        'placeholder': 'Enter your answer...'
                    }),
                    required=True
                )

