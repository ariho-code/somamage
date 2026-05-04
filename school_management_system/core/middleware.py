"""
Middleware for tracking login history
"""
import re
from django.utils import timezone
from .models import LoginHistory

class LoginHistoryMiddleware:
    """Track user login history with device and IP information"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Track login if user is authenticated
        if request.user.is_authenticated:
            # Only track on login (when session is new)
            if not hasattr(request.session, 'login_tracked'):
                ip_address = self.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                device, browser = self.parse_user_agent(user_agent)
                
                LoginHistory.objects.create(
                    user=request.user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device=device,
                    browser=browser,
                    is_successful=True
                )
                request.session['login_tracked'] = True
        
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def parse_user_agent(self, user_agent):
        """Parse user agent to extract device and browser info"""
        device = "Unknown"
        browser = "Unknown"
        
        # Detect device
        if 'Mobile' in user_agent or 'Android' in user_agent:
            device = "Mobile"
        elif 'Tablet' in user_agent or 'iPad' in user_agent:
            device = "Tablet"
        elif 'Windows' in user_agent:
            device = "Windows PC"
        elif 'Mac' in user_agent or 'Macintosh' in user_agent:
            device = "Mac"
        elif 'Linux' in user_agent:
            device = "Linux PC"
        
        # Detect browser
        if 'Chrome' in user_agent and 'Edg' not in user_agent:
            browser = "Chrome"
        elif 'Firefox' in user_agent:
            browser = "Firefox"
        elif 'Safari' in user_agent and 'Chrome' not in user_agent:
            browser = "Safari"
        elif 'Edg' in user_agent:
            browser = "Edge"
        elif 'Opera' in user_agent or 'OPR' in user_agent:
            browser = "Opera"
        
        return device, browser

