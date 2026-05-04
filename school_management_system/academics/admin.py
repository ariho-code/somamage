from django.contrib import admin
from .models import Grade, Subject, SubjectPaper, TeacherSubject, Exam, MarkEntry, ReportCard, Stream, Combination, StudentPaperAssignment
# Old GradingSystem models removed - using UACE grading system now
# from .models import GradingSystem, GradeScale, PromotionCriteria

class StreamInline(admin.TabularInline):
    """Inline admin for Streams under a Grade"""
    model = Stream
    extra = 1
    fields = ('name', 'created_by', 'created_at')

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'level', 'class_teacher')
    list_filter = ('school', 'level')
    search_fields = ('name', 'code')
    # Allow managing Streams (streams are specific to a Grade) inline in the Grade admin
    inlines = [StreamInline]

class SubjectPaperInline(admin.TabularInline):
    """Inline admin for Subject Papers"""
    model = SubjectPaper
    extra = 1
    fields = ('name', 'paper_number', 'code', 'description', 'is_active')

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level', 'is_compulsory', 'has_papers')
    list_filter = ('level', 'is_compulsory', 'has_papers')
    search_fields = ('name', 'code')
    inlines = [SubjectPaperInline]

@admin.register(SubjectPaper)
class SubjectPaperAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'paper_number', 'code', 'is_active')
    list_filter = ('subject', 'is_active')
    search_fields = ('subject__name', 'name', 'code')
    ordering = ('subject', 'paper_number', 'name')

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'subject', 'grade', 'get_papers_display')
    list_filter = ('subject', 'grade')
    search_fields = ('teacher__username', 'subject__name')
    filter_horizontal = ('papers',)
    
    def get_papers_display(self, obj):
        return obj.get_papers_display()
    get_papers_display.short_description = 'Papers'

@admin.register(StudentPaperAssignment)
class StudentPaperAssignmentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'subject', 'get_papers_display', 'created_at')
    list_filter = ('subject', 'created_at')
    search_fields = ('enrollment__student__admission_number', 'subject__name')
    filter_horizontal = ('papers',)
    
    def get_papers_display(self, obj):
        return ", ".join([p.name for p in obj.papers.all()])
    get_papers_display.short_description = 'Papers'

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'term', 'percentage_weight', 'is_active', 'order')
    list_filter = ('school', 'term', 'is_active')
    search_fields = ('name', 'school__name')
    ordering = ('term', 'order', 'name')

@admin.register(MarkEntry)
class MarkEntryAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'subject', 'subject_paper', 'exam', 'score', 'grade', 'teacher', 'date_entered')
    list_filter = ('exam__term', 'subject', 'subject_paper', 'teacher', 'exam')
    search_fields = ('enrollment__student__admission_number', 'subject__name', 'subject_paper__name', 'exam__name')

@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'term', 'average_score', 'total_points', 'position', 'is_published')
    list_filter = ('term', 'is_published')
    search_fields = ('enrollment__student__admission_number',)


# Old GradingSystem inlines - removed (using UACE grading system now)
# class GradeScaleInline(admin.TabularInline):
#     """Inline admin for GradeScale"""
#     model = GradeScale
#     extra = 1
#     fields = ('grade', 'min_score', 'max_score', 'points', 'remark')
# 
# 
# class PromotionCriteriaInline(admin.TabularInline):
#     """Inline admin for PromotionCriteria"""
#     model = PromotionCriteria
#     extra = 0
#     max_num = 1


# OLD GRADING SYSTEM - REMOVED - Using UACE grading system now
# A-Level uses UACE grading system (see academics/uace_grading.py)
# O-Level and Primary use their respective grading systems
# @admin.register(GradingSystem)
# class GradingSystemAdmin(admin.ModelAdmin):
#     """Admin interface for Grading System"""
#     list_display = ('school', 'level', 'name', 'is_active')
#     list_filter = ('school', 'level', 'is_active')
#     search_fields = ('school__name', 'level', 'name')
#     inlines = [GradeScaleInline, PromotionCriteriaInline]
#     
#     fieldsets = (
#         ('Basic Information', {
#             'fields': ('school', 'level', 'name', 'is_active')
#         }),
#     )


# @admin.register(GradeScale)
# class GradeScaleAdmin(admin.ModelAdmin):
#     """Admin interface for Grade Scale"""
#     list_display = ('grading_system', 'grade', 'min_score', 'max_score', 'points', 'remark')
#     list_filter = ('grading_system', 'grade')
#     search_fields = ('grade', 'remark')
#     ordering = ('grading_system', '-min_score')


# @admin.register(PromotionCriteria)
# class PromotionCriteriaAdmin(admin.ModelAdmin):
#     """Admin interface for Promotion Criteria"""
#     list_display = ('grading_system', 'min_average_score', 'min_subjects_passed', 'max_failures_allowed')
#     list_filter = ('grading_system',)
#     search_fields = ('grading_system__school__name',)


@admin.register(Combination)
class CombinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'grade', 'created_by', 'created_at')
    list_filter = ('grade',)
    search_fields = ('name', 'code', 'grade__name')
    readonly_fields = ('created_by', 'created_at')
    filter_horizontal = ('subjects',)

@admin.register(Stream)
class StreamAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'grade', 'combination', 'created_by', 'created_at')
    list_filter = ('school', 'grade', 'combination')
    search_fields = ('name', 'school__name')
