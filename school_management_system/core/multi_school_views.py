"""
Multi-school management views for superadmin
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count
from .models import School, User
from django.contrib.auth import get_user_model

User = get_user_model()

def superadmin_required(user):
    return user.is_authenticated and user.is_superadmin()

@login_required
@user_passes_test(superadmin_required)
def school_list(request):
    """List all schools (superadmin only)"""
    schools = School.objects.annotate(
        user_count=Count('users'),
        grade_count=Count('academics__grade', distinct=True),
    ).all()
    
    context = {
        'schools': schools,
        'title': 'Manage Schools'
    }
    return render(request, 'core/school_list.html', context)

@login_required
@user_passes_test(superadmin_required)
def school_create(request):
    """Create a new school"""
    from .forms import SchoolForm
    
    if request.method == 'POST':
        form = SchoolForm(request.POST, request.FILES)
        if form.is_valid():
            school = form.save()
            messages.success(request, f'School "{school.name}" created successfully!')
            return redirect('school_list')
    else:
        form = SchoolForm()
    
    context = {
        'form': form,
        'title': 'Create School'
    }
    return render(request, 'core/school_form.html', context)

@login_required
@user_passes_test(superadmin_required)
def school_edit(request, school_id):
    """Edit a school"""
    from .forms import SchoolForm
    school = get_object_or_404(School, id=school_id)
    
    if request.method == 'POST':
        form = SchoolForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, f'School "{school.name}" updated successfully!')
            return redirect('school_list')
    else:
        form = SchoolForm(instance=school)
    
    context = {
        'form': form,
        'school': school,
        'title': f'Edit {school.name}'
    }
    return render(request, 'core/school_form.html', context)

@login_required
@user_passes_test(superadmin_required)
def school_admin_create(request, school_id):
    """Create a headteacher/admin for a school"""
    school = get_object_or_404(School, id=school_id)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        role = request.POST.get('role', 'headteacher')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('school_admin_create', school_id=school_id)
        
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            school=school
        )
        
        messages.success(request, f'{role.title()} "{user.get_full_name()}" created for {school.name}!')
        return redirect('school_list')
    
    context = {
        'school': school,
        'title': f'Create Admin for {school.name}'
    }
    return render(request, 'core/school_admin_form.html', context)

@login_required
@user_passes_test(superadmin_required)
def school_delete(request, school_id):
    """Delete a school"""
    school = get_object_or_404(School, id=school_id)
    
    if request.method == 'POST':
        school_name = school.name
        school.delete()
        messages.success(request, f'School "{school_name}" deleted successfully!')
        return redirect('school_list')
    
    context = {
        'school': school,
        'title': f'Delete {school.name}'
    }
    return render(request, 'core/school_delete_confirm.html', context)

