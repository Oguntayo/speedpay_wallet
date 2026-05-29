from rest_framework.permissions import BasePermission

class IsAdminUserType(BasePermission):
    """
    Allows access only to authenticated users with user_type set to 'admin'.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'admin'
        )
