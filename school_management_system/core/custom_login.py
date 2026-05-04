"""
Custom login view with school selection for multi-school support
Supports parent login via student admission number
"""
from django.contrib.auth.views import LoginView
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import School
from students.models import Student

class SchoolLoginView(LoginView):
    """Custom login view with school selection and parent login via student number"""
    template_name = 'registration/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        admission_number = request.POST.get('admission_number', None)
        login_type = request.POST.get('login_type', 'regular')  # regular or parent
        
        # Parent login using student admission number
        if login_type == 'parent' and admission_number:
            student = Student.objects.filter(admission_number=admission_number).first()
            if student and student.guardian:
                # Create or get parent user for this guardian
                parent_phone = student.guardian.phone.replace(' ', '').replace('-', '')
                
                # Try to find existing parent user or create one
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                # Try to find parent by phone (as username)
                parent_user = User.objects.filter(
                    username=parent_phone,
                    role='parent'
                ).first()
                
                if not parent_user:
                    # Create parent user
                    parent_user = User.objects.create_user(
                        username=parent_phone,
                        password=f"parent{admission_number}",  # Default password
                        email=student.guardian.email if student.guardian.email else '',
                        first_name=student.guardian.name.split()[0] if student.guardian.name else '',
                        last_name=' '.join(student.guardian.name.split()[1:]) if len(student.guardian.name.split()) > 1 else '',
                        role='parent',
                        school=student.enrollments.first().grade.school if student.enrollments.exists() else None
                    )
                
                # Login the parent user
                login(request, parent_user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Welcome! Viewing records for student: {student.admission_number}')
                request.session['viewing_student_id'] = student.id
                request.session['admission_number'] = admission_number
                return redirect('home')
            else:
                messages.error(request, 'Student admission number not found or no guardian linked!')
                return render(request, self.template_name, {
                    'login_type': 'parent'
                })
        
        # Regular user login
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Prevent student login - redirect them to parent login
            if user.is_student():
                messages.error(request, 'Students cannot login directly. Parents should use student admission number to access records.')
                return render(request, self.template_name, {
                    'login_type': 'parent'
                })
            
            # Automatically use the user's school - no selection needed
            if user.school or user.is_superadmin():
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Welcome, {user.get_full_name()}!')
                return redirect('home')
            else:
                messages.error(request, 'Your account is not associated with any school. Please contact the administrator.')
                return render(request, self.template_name, {
                    'username': username
                })
        else:
            messages.error(request, 'Invalid username or password!')
            return render(request, self.template_name, {})
        
        return super().post(request, *args, **kwargs)

