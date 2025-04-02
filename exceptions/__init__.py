"""
Custom exception classes for the inventory system.
"""

class InventoryException(Exception):
    """Base exception class for inventory system."""
    def __init__(self, message, code=None, extra=None):
        self.message = message
        self.code = code
        self.extra = extra or {}
        super().__init__(self.message)

class InventoryValidationError(InventoryException):
    """Raised when validation fails."""
    pass

class InventoryBusinessError(InventoryException):
    """Raised when a business rule is violated."""
    pass

class InsufficientStockError(InventoryBusinessError):
    """Raised when there is insufficient stock for a transaction."""
    pass

class AuthorizationError(InventoryException):
    """Raised when a user is not authorized to perform an action."""
    pass

class ResourceNotFoundError(InventoryException):
    """Raised when a requested resource is not found."""
    pass 