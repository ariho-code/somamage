from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Grade, Stream, Combination

def headteacher_required(user):
    return user.is_authenticated and (user.is_superadmin() or user.is_headteacher() or user.is_director_of_studies())

# Stream Management Views
@login_required
@user_passes_test(headteacher_required)
def manage_streams(request, grade_id):
    grade = get_object_or_404(Grade, pk=grade_id)
    
    # Only allow managing streams for own school
    if not request.user.is_superadmin() and grade.school != request.user.school:
        messages.error(request, "You don't have permission to manage streams for this class.")
        return redirect('grade_list')
    
    # Get streams - either direct to grade or via combinations
    direct_streams = Stream.objects.filter(grade=grade, combination__isnull=True)
    combinations = Combination.objects.filter(grade=grade) if grade.level == 'A' else []
    
    return render(request, "academics/manage_streams.html", {
        "grade": grade,
        "direct_streams": direct_streams,
        "combinations": combinations,
    })

@login_required
@user_passes_test(headteacher_required)
def add_stream(request, grade_id):
    grade = get_object_or_404(Grade, pk=grade_id)
    
    # Security check
    if not request.user.is_superadmin() and grade.school != request.user.school:
        messages.error(request, "You don't have permission to add streams to this class.")
        return redirect('grade_list')
    
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            Stream.objects.create(
                school=grade.school,
                grade=grade,
                name=name,
                created_by=request.user
            )
            messages.success(request, f"Stream '{name}' was successfully added.")
        else:
            messages.error(request, "Stream name is required.")
    
    return redirect('manage_streams', grade_id=grade.id)

@login_required
@user_passes_test(headteacher_required)
def edit_stream(request, stream_id):
    stream = get_object_or_404(Stream, pk=stream_id)
    
    # Security check
    if not request.user.is_superadmin() and stream.school != request.user.school:
        messages.error(request, "You don't have permission to edit this stream.")
        return redirect('grade_list')
    
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            stream.name = name
            stream.save()
            messages.success(request, f"Stream was successfully updated.")
        else:
            messages.error(request, "Stream name is required.")
    
    return redirect('manage_streams', grade_id=stream.grade.id)

@login_required
@user_passes_test(headteacher_required)
def delete_stream(request, stream_id):
    stream = get_object_or_404(Stream, pk=stream_id)
    
    # Security check
    if not request.user.is_superadmin() and stream.school != request.user.school:
        messages.error(request, "You don't have permission to delete this stream.")
        return redirect('grade_list')
    
    grade_id = stream.grade.id if stream.grade else stream.combination.grade.id
    stream.delete()
    messages.success(request, "Stream was successfully deleted.")
    
    return redirect('manage_streams', grade_id=grade_id)

# Combination Management Views (for A-Level)
@login_required
@user_passes_test(headteacher_required)
def add_combination(request, grade_id):
    grade = get_object_or_404(Grade, pk=grade_id)
    
    # Security check
    if not request.user.is_superadmin() and grade.school != request.user.school:
        messages.error(request, "You don't have permission to add combinations to this class.")
        return redirect('grade_list')
    
    # Only allow for A-Level
    if grade.level != 'A':
        messages.error(request, "Combinations are only for A-Level classes.")
        return redirect('manage_streams', grade_id=grade.id)
    
    if request.method == "POST":
        name = request.POST.get('name')
        code = request.POST.get('code', '').strip()
        if name:
            Combination.objects.create(
                grade=grade,
                name=name,
                code=code if code else None,
                created_by=request.user
            )
            messages.success(request, f"Combination '{name}' was successfully added.")
        else:
            messages.error(request, "Combination name is required.")
    
    return redirect('manage_streams', grade_id=grade.id)

@login_required
@user_passes_test(headteacher_required)
def edit_combination(request, combination_id):
    combination = get_object_or_404(Combination, pk=combination_id)
    
    # Security check
    if not request.user.is_superadmin() and combination.grade.school != request.user.school:
        messages.error(request, "You don't have permission to edit this combination.")
        return redirect('grade_list')
    
    if request.method == "POST":
        name = request.POST.get('name')
        code = request.POST.get('code', '').strip()
        if name:
            combination.name = name
            combination.code = code if code else None
            combination.save()
            messages.success(request, f"Combination was successfully updated.")
        else:
            messages.error(request, "Combination name is required.")
    
    return redirect('manage_streams', grade_id=combination.grade.id)

@login_required
@user_passes_test(headteacher_required)
def delete_combination(request, combination_id):
    combination = get_object_or_404(Combination, pk=combination_id)
    
    # Security check
    if not request.user.is_superadmin() and combination.grade.school != request.user.school:
        messages.error(request, "You don't have permission to delete this combination.")
        return redirect('grade_list')
    
    grade_id = combination.grade.id
    combination.delete()
    messages.success(request, "Combination was successfully deleted.")
    
    return redirect('manage_streams', grade_id=grade_id)

# Stream management for combinations
@login_required
@user_passes_test(headteacher_required)
def add_stream_to_combination(request, combination_id):
    combination = get_object_or_404(Combination, pk=combination_id)
    
    # Security check
    if not request.user.is_superadmin() and combination.grade.school != request.user.school:
        messages.error(request, "You don't have permission to add streams to this combination.")
        return redirect('grade_list')
    
    if request.method == "POST":
        name = request.POST.get('name')
        if name:
            Stream.objects.create(
                school=combination.grade.school,
                combination=combination,
                name=name,
                created_by=request.user
            )
            messages.success(request, f"Stream '{name}' was successfully added to {combination.name}.")
        else:
            messages.error(request, "Stream name is required.")
    
    return redirect('manage_streams', grade_id=combination.grade.id)