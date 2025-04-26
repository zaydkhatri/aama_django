# core/middleware.py
import threading

# Thread local storage
_thread_locals = threading.local()

def get_current_request():
    """
    Returns the request object for the current thread.
    """
    return getattr(_thread_locals, 'request', None)

class RequestMiddleware:
    """
    Middleware that stores the request object in thread local storage.
    This allows models to access the request (and session) to get the current currency.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Store request in thread local storage
        _thread_locals.request = request
        
        # Process the request
        response = self.get_response(request)
        
        # Clear thread local storage
        del _thread_locals.request
        
        return response