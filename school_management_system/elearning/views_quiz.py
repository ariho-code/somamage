"""
Quiz Management Views for Teachers
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Assignment, QuizQuestion, QuizOption
from .forms import QuizQuestionForm, QuizOptionForm

@login_required
def add_quiz_questions(request, assignment_id):
    """Add questions to a quiz"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check permission
    if assignment.course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to edit this quiz.')
        return redirect('teacher_class_detail', grade_id=assignment.course.grade.id)
    
    questions = assignment.questions.all().prefetch_related('options')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_question':
            question_text = request.POST.get('question_text')
            question_type = request.POST.get('question_type', 'multiple_choice')
            points = request.POST.get('points', 1)
            order = request.POST.get('order', questions.count())
            
            question = QuizQuestion.objects.create(
                assignment=assignment,
                question_text=question_text,
                question_type=question_type,
                points=float(points),
                order=int(order)
            )
            
            # Add options for multiple choice or true/false
            if question_type in ['multiple_choice', 'true_false']:
                options_data = request.POST.getlist('options[]')
                is_correct_data = request.POST.getlist('is_correct[]')
                
                for idx, option_text in enumerate(options_data):
                    if option_text.strip():
                        QuizOption.objects.create(
                            question=question,
                            option_text=option_text,
                            is_correct=str(idx) in is_correct_data,
                            order=idx
                        )
            
            messages.success(request, 'Question added successfully!')
            return redirect('add_quiz_questions', assignment_id=assignment_id)
        
        elif action == 'delete_question':
            question_id = request.POST.get('question_id')
            try:
                question = QuizQuestion.objects.get(id=question_id, assignment=assignment)
                question.delete()
                messages.success(request, 'Question deleted!')
            except:
                messages.error(request, 'Question not found.')
            return redirect('add_quiz_questions', assignment_id=assignment_id)
    
    context = {
        'assignment': assignment,
        'questions': questions,
        'title': f'Add Questions - {assignment.title}'
    }
    
    return render(request, 'elearning/add_quiz_questions.html', context)


@login_required
def edit_quiz_question(request, question_id):
    """Edit a quiz question"""
    question = get_object_or_404(QuizQuestion, id=question_id)
    assignment = question.assignment
    
    # Check permission
    if assignment.course.instructor != request.user and not (request.user.is_headteacher() or request.user.is_director_of_studies()):
        messages.error(request, 'You do not have permission to edit this question.')
        return redirect('add_quiz_questions', assignment_id=assignment.id)
    
    if request.method == 'POST':
        question.question_text = request.POST.get('question_text')
        question.question_type = request.POST.get('question_type')
        question.points = float(request.POST.get('points', 1))
        question.save()
        
        # Update options
        if question.question_type in ['multiple_choice', 'true_false']:
            # Delete old options
            question.options.all().delete()
            
            # Add new options
            options_data = request.POST.getlist('options[]')
            is_correct_data = request.POST.getlist('is_correct[]')
            
            for idx, option_text in enumerate(options_data):
                if option_text.strip():
                    QuizOption.objects.create(
                        question=question,
                        option_text=option_text,
                        is_correct=str(idx) in is_correct_data,
                        order=idx
                    )
        
        messages.success(request, 'Question updated!')
        return redirect('add_quiz_questions', assignment_id=assignment.id)
    
    context = {
        'question': question,
        'assignment': assignment,
        'title': f'Edit Question - {assignment.title}'
    }
    
    return render(request, 'elearning/edit_quiz_question.html', context)

