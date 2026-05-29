from decimal import Decimal
from rest_framework import serializers
from .models import Account, Ledger


def validate_positive_amount(value):
    """Ensures amount is a positive decimal."""
    if value <= Decimal('0'):
        raise serializers.ValidationError("Amount must be greater than zero.")
    return value


class AccountBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('account_number', 'balance')
        read_only_fields = ('account_number', 'balance')


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        validators=[validate_positive_amount]
    )

    def validate_amount(self, value):
        if value > Decimal('1000000'):
            raise serializers.ValidationError("Single deposit cannot exceed 1,000,000.")
        return value


class WithdrawalSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        validators=[validate_positive_amount]
    )

    def validate_amount(self, value):
        if value > Decimal('1000000'):
            raise serializers.ValidationError("Single withdrawal cannot exceed 1,000,000.")
        return value


class AccountNameSerializer(serializers.Serializer):
    account_number = serializers.CharField(max_length=6, min_length=6, required=True, help_text='6-digit account number')

    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        validators=[validate_positive_amount]
    )
    destination_account = serializers.CharField(
        max_length=6,
        min_length=6,
    )
    destination_name = serializers.CharField(required=False, write_only=True, help_text='Full name of recipient (First Last)')

    def validate_destination_account(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Account number must be exactly 6 digits.")
        try:
            account = Account.objects.get(account_number=value)
            return account
        except Account.DoesNotExist:
            raise serializers.ValidationError("No account found with this account number.")

    def validate_amount(self, value):
        if value > Decimal('1000000'):
            raise serializers.ValidationError("Single transfer cannot exceed 1,000,000.")
        return value


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ledger
        fields = ('id', 'transaction_type', 'amount', 'balance_after', 'description', 'created_at')
        read_only_fields = fields
