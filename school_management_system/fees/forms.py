from django import forms
from .models import FeeStructure

class FeeStructureForm(forms.ModelForm):
    class Meta:
        model = FeeStructure
        fields = ['grade', 'term', 'amount', 'description']
        widgets = {
            'grade': forms.Select(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        if school:
            self.fields['grade'].queryset = self.fields['grade'].queryset.filter(school=school)
        elif hasattr(self, 'instance') and self.instance.pk:
            # If editing existing fee structure, filter by the grade's school
            if hasattr(self.instance, 'grade') and self.instance.grade:
                school = self.instance.grade.school
                self.fields['grade'].queryset = self.fields['grade'].queryset.filter(school=school)

