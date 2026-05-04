from .models import AcademicYear, Term


def global_school_context(request):
    """Provide school, academic years and terms to all templates.

    - school: request.user.school if available
    - academic_years: list of AcademicYear for the school (or all if no school)
    - selected_academic_year: from session or the active academic year
    - terms_for_selected_year: terms for the selected academic year
    - selected_term: from session or first term of the selected year
    """
    user = getattr(request, 'user', None)
    school = None
    if user and hasattr(user, 'school'):
        school = user.school

    # Academic years scoped to school if available, otherwise global
    if school:
        academic_years = AcademicYear.objects.filter(school=school).order_by('-start_date')
    else:
        academic_years = AcademicYear.objects.all().order_by('-start_date')

    # Determine selected academic year from session or active flag
    selected_academic_year = None
    selected_academic_year_id = request.session.get('selected_academic_year_id')
    if selected_academic_year_id:
        try:
            selected_academic_year = academic_years.filter(id=selected_academic_year_id).first()
        except Exception:
            selected_academic_year = None

    if not selected_academic_year:
        # fallback to active academic year for the school, or first in the list
        selected_academic_year = academic_years.filter(is_active=True).first() or (academic_years.first() if academic_years.exists() else None)

    # Terms for selected year
    terms_for_selected_year = Term.objects.filter(academic_year=selected_academic_year).order_by('start_date') if selected_academic_year else Term.objects.none()

    # Selected term from session or first term
    selected_term = None
    selected_term_id = request.session.get('selected_term_id')
    if selected_term_id:
        try:
            selected_term = terms_for_selected_year.filter(id=selected_term_id).first()
        except Exception:
            selected_term = None

    if not selected_term and terms_for_selected_year.exists():
        selected_term = terms_for_selected_year.first()

    return {
        'school': school,
        'academic_years': academic_years,
        'selected_academic_year': selected_academic_year,
        'terms_for_selected_year': terms_for_selected_year,
        'selected_term': selected_term,
    }
