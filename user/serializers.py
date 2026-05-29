import re
from decimal import Decimal
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


def validate_strong_password(value):
    """
    Enforces:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Runs Django's built-in password validators (CommonPassword, UserAttribute, etc.)
    """
    if len(value) < 8:
        raise serializers.ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r'\d', value):
        raise serializers.ValidationError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]\/\\]', value):
        raise serializers.ValidationError("Password must contain at least one special character.")
    try:
        validate_password(value)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return value


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_strong_password]
    )
    first_name = serializers.CharField(required=False, allow_blank=True, default='', max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, default='', max_length=150)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'user_type')
        extra_kwargs = {
            'email': {'required': True},
            'user_type': {'required': False},
        }

    def validate_email(self, value):
        """Normalize and check email uniqueness."""
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_user_type(self, value):
        allowed = [choice[0] for choice in User.USER_TYPE_CHOICES]
        if value not in allowed:
            raise serializers.ValidationError(f"Invalid user type. Choose from: {', '.join(allowed)}.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            user_type=validated_data.get('user_type', 'customer')
        )


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'user_type', 'date_joined')
        read_only_fields = ('id', 'email', 'date_joined')


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        validators=[validate_strong_password]
    )

    def validate(self, attrs):
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from the old password."}
            )
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        validators=[validate_strong_password]
    )


class UserWithAccountSerializer(serializers.ModelSerializer):
    """Full user profile + account details for admin use."""
    account_number = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'user_type', 'date_joined', 'account_number', 'balance')
        read_only_fields = fields

    def get_account_number(self, obj):
        try:
            return obj.account.account_number
        except Exception:
            return None

    def get_balance(self, obj):
        try:
            return str(obj.account.balance)
        except Exception:
            return None
