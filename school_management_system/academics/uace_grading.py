"""
Uganda Advanced Certificate of Education (UACE) Grading System
Implements the official UACE grading logic for A-Level students.
"""


def is_subsidiary_subject(subject_name: str, num_papers: int = None) -> bool:
    """
    Determine if a subject is a subsidiary subject based on its name.
    
    Subsidiary subjects are:
    - General Paper (GP) - compulsory
    - Subsidiary Mathematics (Sub-Math) - if Math is not a principal
    - Subsidiary Computer/ICT - if ICT/Computer is not a principal
    
    All other A-Level subjects are principal subjects.
    
    Args:
        subject_name: Name of the subject
        num_papers: Number of papers (optional, for validation)
    
    Returns:
        True if the subject is a subsidiary, False if it's a principal
    """
    if not subject_name:
        return False
    
    subject_name_upper = subject_name.upper().strip()
    
    # Subsidiary subject patterns
    subsidiary_patterns = [
        # General Paper variations
        "GENERAL PAPER",
        "GP",
        "GENERAL STUDIES",
        
        # Subsidiary Mathematics variations
        "SUBSIDIARY MATHEMATICS",
        "SUBSIDIARY MATH",
        "SUB-MATHEMATICS",
        "SUB-MATH",
        "SUB MATHEMATICS",
        "SUB MATH",
        "SUBSIDIARY MATHS",
        "SUB-MATHS",
        "SUB MATHS",
        
        # Subsidiary Computer/ICT variations
        "SUBSIDIARY COMPUTER",
        "SUBSIDIARY COMPUTING",
        "SUBSIDIARY ICT",
        "SUBSIDIARY INFORMATION TECHNOLOGY",
        "SUB-COMPUTER",
        "SUB-COMPUTING",
        "SUB-ICT",
        "SUB COMPUTER",
        "SUB COMPUTING",
        "SUB ICT",
        "SUBSIDIARY COMPUTER STUDIES",
        "SUB-COMPUTER STUDIES",
        "SUB COMPUTER STUDIES",
    ]
    
    # Check if subject name matches any subsidiary pattern
    for pattern in subsidiary_patterns:
        if pattern in subject_name_upper:
            return True
    
    # If it doesn't match subsidiary patterns, it's a principal subject
    # Even if it has only 1 paper, if it's not explicitly a subsidiary by name, it's principal
    return False


def assign_numerical_grade(raw_mark: float, config=None) -> int:
    """
    Convert raw mark (0-100%) to numerical grade (1-9) using UACE ranges.
    
    Args:
        raw_mark: Raw percentage mark (0-100)
        config: Optional UACEGradingConfig instance. If None, uses default ranges.
    
    Returns:
        Numerical grade (1-9) where:
        1 = D1, 2 = D2, 3 = C3, 4 = C4, 5 = C5, 6 = C6, 7 = P7, 8 = P8, 9 = F9
    """
    if raw_mark < 0:
        raw_mark = 0
    if raw_mark > 100:
        raw_mark = 100
    
    # Use config if provided, otherwise use defaults
    if config:
        # Check each grade range from config
        for grade_num in range(1, 10):
            min_val, max_val = config.get_grade_range(grade_num)
            if float(min_val) <= raw_mark <= float(max_val):
                return grade_num
        return 9  # Default to F9 if no match
    else:
        # Default ranges — UNEB UCE spec
        if raw_mark >= 75.0:
            return 1  # D1
        elif raw_mark >= 70.0:
            return 2  # D2
        elif raw_mark >= 65.0:
            return 3  # C3
        elif raw_mark >= 60.0:
            return 4  # C4
        elif raw_mark >= 55.0:
            return 5  # C5
        elif raw_mark >= 50.0:
            return 6  # C6
        elif raw_mark >= 45.0:
            return 7  # P7
        elif raw_mark >= 40.0:
            return 8  # P8
        else:
            return 9  # F9


def get_numerical_grade_label(grade: int) -> str:
    """
    Get the label for a numerical grade.
    
    Args:
        grade: Numerical grade (1-9)
    
    Returns:
        Grade label (e.g., "D1", "C3", "F9")
    """
    grade_labels = {
        1: "D1",
        2: "D2",
        3: "C3",
        4: "C4",
        5: "C5",
        6: "C6",
        7: "P7",
        8: "P8",
        9: "F9"
    }
    return grade_labels.get(grade, "F9")


def compute_principal_letter_grade(paper_grades: list[int], num_papers: int = None) -> str:
    """
    Convert numerical paper grades to principal subject letter grade (A-E, O, F).
    
    For Principal Subjects with multiple papers:
    - A-E: Principal passes (qualifying for full credit)
    - O: Subsidiary pass (lower level)
    - F: Fail
    
    Args:
        paper_grades: List of numerical grades (1-9) for each paper
        num_papers: Expected number of papers (optional, for validation)
    
    Returns:
        Letter grade (A, B, C, D, E, O, or F)
    """
    if not paper_grades:
        return "F"
    
    # Validate paper count
    if num_papers and len(paper_grades) != num_papers:
        # If mismatch, use actual count
        num_papers = len(paper_grades)
    
    if not num_papers:
        num_papers = len(paper_grades)
    
    # Sort grades ascending (worst first) for easier checking
    sorted_grades = sorted(paper_grades)
    
    # Two-Paper Subjects
    if num_papers == 2:
        g1, g2 = sorted_grades
        
        # A: Both distinctions: e.g., (1,1), (1,2), (2,2)
        if g1 <= 2 and g2 <= 2:
            return "A"
        
        # B: At worst one C3, with the other better or equal: e.g., (1,3), (2,3), (3,3)
        elif g1 <= 3 and g2 <= 3:
            return "B"
        
        # C: At worst one C4, with the other better or equal: e.g., (1,4), (3,4), (4,4)
        elif g1 <= 4 and g2 <= 4:
            return "C"
        
        # D: At worst one C5, with the other better or equal: e.g., (1,5), (4,5), (5,5)
        elif g1 <= 5 and g2 <= 5:
            return "D"
        
        # E: At worst one P7, with the other a credit or better: e.g., (1,7), (6,7), but not (7,7)
        elif g1 <= 6 and g2 == 7:
            return "E"
        elif g1 == 7 and g2 <= 6:
            return "E"
        
        # O: Combinations like (7,7), (7,8), (8,8) – passes but not qualifying for E
        elif g1 >= 7 and g2 >= 7 and g1 <= 8 and g2 <= 8:
            return "O"
        
        # F: At least one F9 with the other P8 or worse: e.g., (8,9), (9,9)
        else:
            return "F"
    
    # Three-Paper Subjects
    elif num_papers == 3:
        g1, g2, g3 = sorted_grades
        
        # A: At worst one C3, with the other two distinctions: e.g., (1,1,3), (1,2,3), (2,2,3)
        if g1 <= 2 and g2 <= 2 and g3 <= 3:
            return "A"
        
        # B: At worst one C4, with the other two better: e.g., (1,1,4), (2,3,4), (3,3,4)
        elif g1 <= 3 and g2 <= 3 and g3 <= 4:
            return "B"
        
        # C: At worst one C5, with the other two better: e.g., (1,1,5), (3,4,5), (4,4,5)
        elif g1 <= 4 and g2 <= 4 and g3 <= 5:
            return "C"
        
        # D: At worst one C6, with the other two better: e.g., (1,1,6), (4,5,6), (5,5,6)
        elif g1 <= 5 and g2 <= 5 and g3 <= 6:
            return "D"
        
        # E: At worst one P7, with the other two credits or better: e.g., (1,1,7), (5,6,7), (6,6,7)
        elif g1 <= 6 and g2 <= 6 and g3 == 7:
            return "E"
        elif g1 <= 6 and g2 == 7 and g3 <= 6:
            return "E"
        elif g1 == 7 and g2 <= 6 and g3 <= 6:
            return "E"
        
        # O: Combinations like (6,7,8), (7,7,7) – moderate passes not qualifying for E
        elif g1 >= 6 and g2 >= 7 and g3 >= 7 and g1 <= 8 and g2 <= 8 and g3 <= 8:
            return "O"
        
        # F: Severe failures: e.g., (9,9,9), or two F9s with one P8
        else:
            return "F"
    
    # Four-Paper Subjects
    elif num_papers == 4:
        g1, g2, g3, g4 = sorted_grades
        
        # A: At worst one C3, with the other three distinctions: e.g., (1,1,1,3), (1,1,2,3)
        if g1 <= 2 and g2 <= 2 and g3 <= 2 and g4 <= 3:
            return "A"
        
        # B: At worst one C4, with the other three better: e.g., (1,1,1,4), (2,2,3,4)
        elif g1 <= 3 and g2 <= 3 and g3 <= 3 and g4 <= 4:
            return "B"
        
        # C: At worst one C5, with the other three better: e.g., (1,1,1,5), (3,3,4,5)
        elif g1 <= 4 and g2 <= 4 and g3 <= 4 and g4 <= 5:
            return "C"
        
        # D: At worst one C6, with the other three better: e.g., (1,1,1,6), (4,4,5,6)
        elif g1 <= 5 and g2 <= 5 and g3 <= 5 and g4 <= 6:
            return "D"
        
        # E: At worst one P7, with the other three credits or better: e.g., (1,1,1,7), (5,5,6,7)
        elif g1 <= 6 and g2 <= 6 and g3 <= 6 and g4 == 7:
            return "E"
        elif g1 <= 6 and g2 <= 6 and g3 == 7 and g4 <= 6:
            return "E"
        elif g1 <= 6 and g2 == 7 and g3 <= 6 and g4 <= 6:
            return "E"
        elif g1 == 7 and g2 <= 6 and g3 <= 6 and g4 <= 6:
            return "E"
        
        # O: Combinations like (6,6,7,8), (7,7,7,7) – passes not qualifying for E
        elif g1 >= 6 and g2 >= 6 and g3 >= 7 and g4 >= 7 and all(g <= 8 for g in sorted_grades):
            return "O"
        
        # F: Severe failures: e.g., (9,9,9,9), or at least two F9s with others P8 or worse
        else:
            return "F"
    
    # Default: Single paper or invalid count - treat as worst case
    else:
        # For single paper, use subsidiary logic (shouldn't happen for principals)
        if len(paper_grades) == 1:
            grade = paper_grades[0]
            if grade <= 6:
                return "E"  # Best possible for single paper
            else:
                return "F"
        else:
            # Unknown paper count - use worst grade
            return "F"


def compute_subsidiary_grade(paper_grade: int, config=None) -> str:
    """
    Convert numerical paper grade to subsidiary subject grade (Pass/Fail).
    
    For Subsidiary Subjects (single paper):
    - Pass: Numerical grades up to threshold (configurable, default 1-6)
    - Fail: Numerical grades above threshold (default 7-9)
    
    Args:
        paper_grade: Numerical grade (1-9) for the single paper
        config: Optional UACEGradingConfig instance. If None, uses default threshold (6).
    
    Returns:
        "Pass" or "Fail"
    """
    if config:
        threshold = config.subsidiary_pass_max_grade
        if 1 <= paper_grade <= threshold:
            return "Pass"
        else:
            return "Fail"
    else:
        # Default: 1-6 = Pass, 7-9 = Fail
        if 1 <= paper_grade <= 6:
            return "Pass"
        else:
            return "Fail"


def calculate_uace_points(principal_grades: dict[str, str], subsidiary_grades: dict[str, str] = None, config=None) -> int:
    """
    Calculate total UACE points for internal tracking/simulation.
    
    Principal subjects:
    - A = configurable points (default 6)
    - B = configurable points (default 5)
    - C = configurable points (default 4)
    - D = configurable points (default 3)
    - E = configurable points (default 2)
    - O = configurable points (default 1)
    - F = configurable points (default 0)
    
    Subsidiary subjects:
    - Pass = configurable points (default 1)
    - Fail = configurable points (default 0)
    
    Args:
        principal_grades: Dict mapping subject names to letter grades (A-E, O, F)
        subsidiary_grades: Dict mapping subject names to Pass/Fail (optional)
        config: Optional UACEGradingConfig instance. If None, uses default points.
    
    Returns:
        Total points (sum of up to 3 best principal subjects + all subsidiaries)
    """
    if config:
        principal_points_map = {
            "A": config.points_a,
            "B": config.points_b,
            "C": config.points_c,
            "D": config.points_d,
            "E": config.points_e,
            "O": config.points_o,
            "F": config.points_f
        }
        subsidiary_pass_points = config.points_subsidiary_pass
        subsidiary_fail_points = config.points_subsidiary_fail
    else:
        # Default points
        principal_points_map = {
            "A": 6,
            "B": 5,
            "C": 4,
            "D": 3,
            "E": 2,
            "O": 1,
            "F": 0
        }
        subsidiary_pass_points = 1
        subsidiary_fail_points = 0
    
    # Calculate points for principal subjects
    principal_points = []
    for subject, grade in principal_grades.items():
        points = principal_points_map.get(grade.upper(), 0)
        principal_points.append(points)
    
    # Sort and take best 3
    principal_points.sort(reverse=True)
    best_3_principals = sum(principal_points[:3])
    
    # Calculate points for subsidiary subjects
    # Note: Subsidiaries now use "O" instead of "Pass" (changed in views.py)
    subsidiary_points = 0
    if subsidiary_grades:
        for subject, grade in subsidiary_grades.items():
            # Check for both "Pass" (old format) and "O" (new format) for backwards compatibility
            if grade == "O" or grade == "Pass":
                subsidiary_points += subsidiary_pass_points
            else:
                subsidiary_points += subsidiary_fail_points
    
    return best_3_principals + subsidiary_points


def get_grade_category(letter_grade: str) -> str:
    """
    Get the category for a letter grade.
    
    Args:
        letter_grade: Letter grade (A-E, O, F)
    
    Returns:
        Category: "Distinction", "Credit", "Pass", or "Fail"
    """
    if letter_grade in ["A", "B"]:
        return "Distinction"
    elif letter_grade in ["C", "D", "E"]:
        return "Credit"
    elif letter_grade == "O":
        return "Pass"
    else:  # F
        return "Fail"


def get_required_subsidiaries(principal_subjects: list[str], subsidiary_choice: str = 'auto') -> list[str]:
    """
    Determine required subsidiary subjects based on principal subjects and combination choice.
    
    Rules:
    - General Paper (GP) is ALWAYS required (for all A-Level students)
    - If subsidiary_choice is 'auto':
      - If Mathematics is a principal → Sub-ICT required
      - If Economics is a principal but NOT Mathematics → Sub-Math required
      - If science combination without Mathematics → Sub-Math required
      - Other combinations → default to Sub-Math
    - If subsidiary_choice is 'sub_math' → Sub-Math required
    - If subsidiary_choice is 'sub_ict' → Sub-ICT required
    
    Args:
        principal_subjects: List of principal subject names
        subsidiary_choice: 'auto', 'sub_math', or 'sub_ict' (default: 'auto')
    
    Returns:
        List of required subsidiary subject names (e.g., ["General Paper", "Subsidiary Mathematics"])
        NOTE: Returns only ONE subsidiary (GP + one other), not both Sub-Math and Sub-ICT
    """
    required_subsidiaries = ["General Paper"]  # GP is always required
    
    # If explicit choice is made, use it
    if subsidiary_choice == 'sub_math':
        required_subsidiaries.append("Subsidiary Mathematics")
        return required_subsidiaries
    elif subsidiary_choice == 'sub_ict':
        required_subsidiaries.append("Subsidiary ICT")
        return required_subsidiaries
    
    # Auto-determine based on principals
    # Normalize principal subject names for comparison
    principals_upper = [p.upper().strip() for p in principal_subjects]
    
    # Check if Mathematics is a principal
    math_variations = ["MATHEMATICS", "MATH", "MATHS", "PURE MATHEMATICS", "APPLIED MATHEMATICS"]
    has_math = any(any(math_var in p for math_var in math_variations) for p in principals_upper)
    
    # Check if Economics is a principal
    economics_variations = ["ECONOMICS", "ECON"]
    has_economics = any(any(econ_var in p for econ_var in economics_variations) for p in principals_upper)
    
    # Check if it's a science combination (Physics, Chemistry, Biology, Agriculture, etc.)
    science_subjects = ["PHYSICS", "CHEMISTRY", "BIOLOGY", "AGRICULTURE", "COMPUTER STUDIES", 
                       "COMPUTER SCIENCE", "ICT", "INFORMATION TECHNOLOGY"]
    is_science_combo = any(any(science in p for science in science_subjects) for p in principals_upper)
    
    # Determine second subsidiary based on rules
    if has_math:
        # If Math is principal → Sub-ICT required
        required_subsidiaries.append("Subsidiary ICT")
    elif has_economics and not has_math:
        # If Economics but no Math → Sub-Math required
        required_subsidiaries.append("Subsidiary Mathematics")
    elif is_science_combo and not has_math:
        # If science combination without Math → Sub-Math required
        required_subsidiaries.append("Subsidiary Mathematics")
    else:
        # Other combinations → default to Sub-Math
        required_subsidiaries.append("Subsidiary Mathematics")
    
    return required_subsidiaries


def validate_combination(principals: list[str], subsidiaries: list[str]) -> tuple[bool, str]:
    """
    Validate that a combination meets UACE requirements.
    
    Requirements:
    - Exactly 3 principal subjects
    - General Paper (GP) always included
    - Appropriate subsidiary based on principals
    
    Args:
        principals: List of principal subject names
        subsidiaries: List of subsidiary subject names
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(principals) != 3:
        return False, f"Must have exactly 3 principal subjects, found {len(principals)}"
    
    # Check for General Paper
    gp_variations = ["General Paper", "GP", "General Studies"]
    has_gp = any(any(gp in sub.upper() for gp in gp_variations) for sub in subsidiaries)
    if not has_gp:
        return False, "General Paper (GP) is mandatory for all students"
    
    # Get required subsidiaries based on principals
    required_subsidiaries = get_required_subsidiaries(principals)
    
    # Check if required subsidiaries are present
    subsidiaries_upper = [s.upper().strip() for s in subsidiaries]
    
    # Check for Sub-Math requirement
    if "Subsidiary Mathematics" in required_subsidiaries:
        sub_math_variations = ["SUBSIDIARY MATHEMATICS", "SUBSIDIARY MATH", "SUB-MATH", "SUB MATH", 
                              "SUBSIDIARY MATHS", "SUB-MATHS", "SUB MATHS"]
        has_sub_math = any(any(sub_math in sub for sub_math in sub_math_variations) for sub in subsidiaries_upper)
        if not has_sub_math:
            return False, "Subsidiary Mathematics is required for this combination"
    
    # Check for Sub-ICT requirement
    if "Subsidiary ICT" in required_subsidiaries:
        sub_ict_variations = ["SUBSIDIARY ICT", "SUBSIDIARY COMPUTER", "SUBSIDIARY COMPUTING",
                             "SUB-ICT", "SUB ICT", "SUB-COMPUTER", "SUB COMPUTER"]
        has_sub_ict = any(any(sub_ict in sub for sub_ict in sub_ict_variations) for sub in subsidiaries_upper)
        if not has_sub_ict:
            return False, "Subsidiary ICT is required for this combination"

    return True, ""


# ── UNEB Canonical Grading Functions ─────────────────────────────────────────
# These are the authoritative, spec-correct implementations used by the API
# and unit tests. The older helpers above remain for backwards-compatibility
# with the existing template-based views.

def get_olevel_grade(mark: float) -> dict:
    """
    Return UCE grade, points, and classification for an O-Level mark.
    UNEB UCE spec: D1(75-100)=1pt … F9(0-39)=9pts
    """
    thresholds = [
        (75, 'D1', 1, 'Distinction'),
        (70, 'D2', 2, 'Distinction'),
        (65, 'C3', 3, 'Credit'),
        (60, 'C4', 4, 'Credit'),
        (55, 'C5', 5, 'Credit'),
        (50, 'C6', 6, 'Credit'),
        (45, 'P7', 7, 'Pass'),
        (40, 'P8', 8, 'Pass'),
        (0,  'F9', 9, 'Failure'),
    ]
    for min_mark, grade, points, classification in thresholds:
        if mark >= min_mark:
            return {'grade': grade, 'points': points, 'classification': classification}
    return {'grade': 'F9', 'points': 9, 'classification': 'Failure'}


def calculate_uce_division(subject_grades: list) -> dict:
    """
    Calculate UCE division from a list of grade points (1–9).
    Takes best 8 subjects (lowest point values = best).
    UNEB spec: I=8-11, II=12-23, III=24-29, IV=30-34, F=35+
    """
    best_8 = sorted(subject_grades)[:8]
    aggregate = sum(best_8)
    if 8 <= aggregate <= 11:
        division = 'I'
    elif 12 <= aggregate <= 23:
        division = 'II'
    elif 24 <= aggregate <= 29:
        division = 'III'
    elif 30 <= aggregate <= 34:
        division = 'IV'
    else:
        division = 'F'
    return {'aggregate': aggregate, 'division': division, 'subjects_used': best_8}


def get_alevel_principal_grade(mark: float) -> dict:
    """
    Return UACE principal subject grade and points.
    UNEB UACE spec: A(80-100)=6 … F(0-34)=0
    """
    thresholds = [
        (80, 'A', 6), (70, 'B', 5), (60, 'C', 4),
        (50, 'D', 3), (40, 'E', 2), (35, 'O', 1), (0, 'F', 0),
    ]
    for min_mark, grade, points in thresholds:
        if mark >= min_mark:
            return {'grade': grade, 'points': points}
    return {'grade': 'F', 'points': 0}


def get_alevel_subsidiary_grade(mark: float) -> str:
    """Return UACE subsidiary subject grade (a-f)."""
    if mark >= 70:
        return 'a'
    elif mark >= 55:
        return 'b'
    elif mark >= 40:
        return 'c'
    elif mark >= 30:
        return 'd'
    return 'f'


def calculate_uace_summary(principal_marks: list) -> dict:
    """
    Calculate UACE total points from up to 3 principal subject marks.
    Returns total points and classification.
    """
    results = [get_alevel_principal_grade(m) for m in principal_marks[:3]]
    total_points = sum(r['points'] for r in results)
    if total_points >= 15:
        classification = 'Excellent'
    elif total_points >= 12:
        classification = 'Very Good'
    elif total_points >= 9:
        classification = 'Good'
    elif total_points >= 6:
        classification = 'Average'
    elif total_points >= 3:
        classification = 'Below Average'
    else:
        classification = 'Fail'
    return {
        'total_points': total_points,
        'grades': [r['grade'] for r in results],
        'classification': classification,
    }


def calculate_ple_aggregate(english: int, maths: int, science: int, sst_re: int) -> dict:
    """
    Calculate P7 PLE aggregate and division.
    Each param is a subject grade (1–4 where 1 is best, matching Primary Grade 1-4).
    UNEB PLE spec: I=4-12, II=13-23, III=24-29, IV=30-34, U=35+
    """
    aggregate = english + maths + science + sst_re
    if 4 <= aggregate <= 12:
        division = 'I'
    elif 13 <= aggregate <= 23:
        division = 'II'
    elif 24 <= aggregate <= 29:
        division = 'III'
    elif 30 <= aggregate <= 34:
        division = 'IV'
    else:
        division = 'U'
    return {'aggregate': aggregate, 'division': division}

