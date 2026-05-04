from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.conf import settings

def handler403(request, exception):
    """Custom 403 handler that returns JSON for AJAX requests or shows modal-friendly response"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Content-Type') == 'application/json':
        # Return JSON for AJAX requests
        return JsonResponse({
            'success': False,
            'error': 'Permission Denied',
            'message': 'You don\'t have the required permissions to access this feature. Please contact your administrator if you believe this is an error.',
            'status': 403,
            'show_modal': True
        }, status=403)
    
    # For regular requests, return a page that will trigger the modal via JavaScript
    context = {
        'exception': exception,
        'show_permission_modal': True
    }
    return render(request, 'core/403.html', context, status=403)

