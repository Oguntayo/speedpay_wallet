from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .serializers import (
    UserRegisterSerializer, UserDetailSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    UserWithAccountSerializer
)
from .permissions import IsAdminUserType
from .tasks import send_password_reset_email_task
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.views import APIView

User = get_user_model()


class SpeedpayTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT serializer that appends user profile data to the login response."""

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
        }
        return data


class LoginView(TokenObtainPairView):
    """Login with email and password. Returns JWT tokens and user profile info."""
    serializer_class = SpeedpayTokenObtainPairSerializer

    @extend_schema(
        summary="Login",
        description="Authenticate with email and password. Returns access token, refresh token, and user profile including user_type.",
        responses={
            200: OpenApiResponse(description="Login successful. Returns tokens and user profile."),
            401: OpenApiResponse(description="Invalid credentials.")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class UserRegisterView(generics.CreateAPIView):
    """
    Register a new user in the Speedpay application.
    Automatically generates and returns JWT access and refresh tokens upon successful registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Register User",
        description="Register a new user with email and password. Returns user data along with initial access and refresh tokens.",
        responses={
            201: OpenApiResponse(
                description="User successfully registered",
            ),
            400: OpenApiResponse(description="Validation error (e.g. email already exists)")
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserDetailSerializer(user, context=self.get_serializer_context()).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of the currently authenticated user.
    Requires a valid JWT token in the Authorization header (e.g. 'Bearer <token>').
    """
    serializer_class = UserDetailSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get Current User Profile",
        description="Retrieves the detailed profile information of the currently authenticated user.",
        responses={
            200: UserDetailSerializer,
            401: OpenApiResponse(description="Unauthorized or invalid token")
        }
    )
    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """
    List all registered users with full profile and account details.
    Only accessible by admin users.
    """
    serializer_class = UserWithAccountSerializer
    permission_classes = (IsAdminUserType,)

    def get_queryset(self):
        # select_related avoids N+1 queries when loading account data
        return User.objects.select_related('account').all().order_by('-date_joined')

    @extend_schema(
        summary="List All Users with Account Details (Admin Only)",
        description="Returns all users including their account number and balance. Admin access required.",
        responses={
            200: UserWithAccountSerializer(many=True),
            401: OpenApiResponse(description="Unauthorized"),
            403: OpenApiResponse(description="Forbidden - Admin access required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Change Password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password updated successfully."),
            400: OpenApiResponse(description="Wrong old password."),
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"error": "Wrong old password."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"message": "Password updated successfully."})


class ForgotPasswordView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Forgot Password",
        request=ForgotPasswordSerializer,
        responses={200: OpenApiResponse(description="Reset link sent if account exists.")}
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()
        if user:
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"http://localhost:8000/api/auth/reset-password/?uid={uid}&token={token}"
            send_password_reset_email_task.delay(email, reset_link)
        return Response({"message": "If an account with this email exists, a password reset link has been sent."})


class ResetPasswordView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="Reset Password",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully."),
            400: OpenApiResponse(description="Invalid or expired token."),
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and PasswordResetTokenGenerator().check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successfully."})
        return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
