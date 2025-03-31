"""
Exception handling middleware.
"""
import logging
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

from . import (
    InventoryException, 
    InsufficientStockError, 
    AuthorizationError, 
    ResourceNotFoundError, 
    InventoryValidationError,
    InventoryBusinessError
)

logger = logging.getLogger(__name__)

class ExceptionMiddleware(MiddlewareMixin):
    """Middleware to handle common exceptions."""
    
    def process_exception(self, request, exception):
        """Process exceptions raised during request processing."""
        if isinstance(exception, InventoryException):
            # Log the exception
            logger.error(
                f"InventoryException: {exception.message}",
                exc_info=True,
                extra={
                    'request': request,
                    'code': exception.code,
                    'extra': exception.extra
                }
            )
            
            # For API requests, return JSON response
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'success': False,
                    'message': exception.message,
                    'code': exception.code,
                    'errors': exception.extra.get('errors', {})
                }, status=self._get_status_code(exception))
            
            # For normal requests, add message and redirect
            messages.error(request, exception.message)
            
            if isinstance(exception, InsufficientStockError):
                return HttpResponseRedirect(reverse('inventory_list'))
            
            if isinstance(exception, AuthorizationError):
                return HttpResponseRedirect(reverse('index'))
            
            if isinstance(exception, ResourceNotFoundError):
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('index')))
            
            # Default redirect to previous page or home
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('index')))
        
        # If it's not our exception, let Django handle it
        return None
    
    def _get_status_code(self, exception):
        """Get HTTP status code based on exception type."""
        if isinstance(exception, InsufficientStockError):
            return 400
        if isinstance(exception, AuthorizationError):
            return 403
        if isinstance(exception, ResourceNotFoundError):
            return 404
        if isinstance(exception, InventoryValidationError):
            return 400
        if isinstance(exception, InventoryBusinessError):
            return 400
        return 500 