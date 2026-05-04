from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def number_to_words_ugx(value):
    """Convert number to words for UGX currency"""
    try:
        # Convert to int if it's a Decimal or float
        if isinstance(value, Decimal):
            number = int(value)
        elif isinstance(value, float):
            number = int(value)
        else:
            number = int(float(value))
    except (ValueError, TypeError):
        return "Invalid Amount"
    
    if number == 0:
        return "Zero Shillings Only"
    
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']
    
    def convert_hundreds(n):
        result = ''
        if n >= 100:
            result += ones[n // 100] + ' Hundred '
            n %= 100
        if n >= 20:
            result += tens[n // 10] + ' '
            n %= 10
        if n > 0:
            result += ones[n] + ' '
        return result.strip()
    
    result = ''
    if number >= 1000000000:
        result += convert_hundreds(number // 1000000000) + ' Billion '
        number %= 1000000000
    if number >= 1000000:
        result += convert_hundreds(number // 1000000) + ' Million '
        number %= 1000000
    if number >= 1000:
        result += convert_hundreds(number // 1000) + ' Thousand '
        number %= 1000
    if number > 0:
        result += convert_hundreds(number)
    
    return (result.strip() + ' Shillings Only').strip()

@register.filter
def student_or_pupil(school):
    """Return 'Student' for high schools, 'Pupil' for primary schools"""
    if not school:
        return 'Student'
    if school.is_primary():
        return 'Pupil'
    return 'Student'

@register.filter
def students_or_pupils(school):
    """Return 'Students' for high schools, 'Pupils' for primary schools"""
    if not school:
        return 'Students'
    if school.is_primary():
        return 'Pupils'
    return 'Students'

