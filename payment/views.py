from django.db import transaction
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django_filters.rest_framework import DjangoFilterBackend
import django_filters
from .models import Account, Ledger
from .serializers import (
    AccountBalanceSerializer,
    DepositSerializer,
    WithdrawalSerializer,
    TransferSerializer,
    TransferFundsSerializer,
    LedgerSerializer,
    AccountNameSerializer,
)


class LedgerFilter(django_filters.FilterSet):
    transaction_type = django_filters.CharFilter(field_name='transaction_type', lookup_expr='exact')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Ledger
        fields = ['transaction_type', 'date_from', 'date_to']


class BalanceView(generics.RetrieveAPIView):
    serializer_class = AccountBalanceSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(summary="Get Account Balance")
    def get_object(self):
        return self.request.user.account

class DepositView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Deposit Funds",
        request=DepositSerializer,
        responses={200: OpenApiResponse(description="Deposit successful")}
    )
    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        with transaction.atomic():
            account = Account.objects.select_for_update().get(user=request.user)
            account.balance += amount
            account.save()

            Ledger.objects.create(
                account=account,
                transaction_type='deposit',
                amount=amount,
                balance_after=account.balance,
                description=f"Deposited {amount}"
            )

        return Response({"message": "Deposit successful", "balance": account.balance})

class WithdrawView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Withdraw Funds",
        request=WithdrawalSerializer,
        responses={
            200: OpenApiResponse(description="Withdrawal successful"),
            400: OpenApiResponse(description="Insufficient funds")
        }
    )
    def post(self, request):
        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        with transaction.atomic():
            account = Account.objects.select_for_update().get(user=request.user)
            
            if account.balance < amount:
                return Response({"error": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)

            account.balance -= amount
            account.save()

            Ledger.objects.create(
                account=account,
                transaction_type='withdrawal',
                amount=amount,
                balance_after=account.balance,
                description=f"Withdrew {amount}"
            )

        return Response({"message": "Withdrawal successful", "balance": account.balance})

class AccountNameView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = AccountNameSerializer

    @extend_schema(
        summary="Get Account Holder Name",
        request=AccountNameSerializer,
        responses={200: OpenApiResponse(description="Account name lookup successful")},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_number = serializer.validated_data['account_number']
        account = Account.objects.get(account_number=account_number)
        full_name = f"{account.user.first_name} {account.user.last_name}".strip()
        return Response({"account_number": account_number, "name": full_name})


class TransferFundsView(APIView):
    """Transfer funds requiring recipient name, account number and amount."""
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Transfer Funds with Recipient Name",
        request=TransferFundsSerializer,
        responses={
            200: OpenApiResponse(description="Transfer successful"),
            400: OpenApiResponse(description="Invalid request or insufficient funds")
        }
    )
    def post(self, request):
        serializer = TransferFundsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        dest_account_obj = serializer.validated_data['destination_account']
        dest_name = serializer.validated_data['destination_name']
        # Validate name matches account holder
        expected_name = f"{dest_account_obj.user.first_name} {dest_account_obj.user.last_name}".strip()
        if dest_name.strip() != expected_name:
            return Response({
                'error': f'Destination name does not match account holder. Expected: {expected_name}'
            }, status=status.HTTP_400_BAD_REQUEST)

        source_account = request.user.account
        if source_account.id == dest_account_obj.id:
            return Response({"error": "Cannot transfer to your own account."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            accounts = Account.objects.select_for_update().filter(
                id__in=[source_account.id, dest_account_obj.id]
            ).order_by('id')
            account_dict = {acc.id: acc for acc in accounts}
            locked_source = account_dict[source_account.id]
            locked_dest = account_dict[dest_account_obj.id]
            if locked_source.balance < amount:
                return Response({"error": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)
            locked_source.balance -= amount
            locked_source.save()
            locked_dest.balance += amount
            locked_dest.save()
            Ledger.objects.create(
                account=locked_source,
                transaction_type='transfer_sent',
                amount=amount,
                balance_after=locked_source.balance,
                description=f"Transferred to {locked_dest.account_number}"
            )
            Ledger.objects.create(
                account=locked_dest,
                transaction_type='transfer_received',
                amount=amount,
                balance_after=locked_dest.balance,
                description=f"Received from {locked_source.account_number}"
            )
        return Response({"message": "Transfer successful", "balance": locked_source.balance})


class TransferView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Transfer Funds",
        request=TransferSerializer,
        responses={
            200: OpenApiResponse(description="Transfer successful"),
            400: OpenApiResponse(description="Invalid request or insufficient funds")
        }
    )
    def post(self, request):
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']
        dest_account_obj = serializer.validated_data['destination_account']

        source_account = request.user.account

        # Validate optional destination name if provided
        dest_name = serializer.validated_data.get('destination_name')
        if dest_name:
            expected_name = f"{dest_account_obj.user.first_name} {dest_account_obj.user.last_name}".strip()
            if dest_name.strip() != expected_name:
                return Response({
                    'error': f'Destination name does not match account holder. Expected: {expected_name}'
                }, status=status.HTTP_400_BAD_REQUEST)


        with transaction.atomic():
            # Lock accounts in consistent order to prevent deadlocks
            accounts = Account.objects.select_for_update().filter(
                id__in=[source_account.id, dest_account_obj.id]
            ).order_by('id')
            
            # Fetch locked objects
            account_dict = {acc.id: acc for acc in accounts}
            locked_source = account_dict[source_account.id]
            locked_dest = account_dict[dest_account_obj.id]

            if locked_source.balance < amount:
                return Response({"error": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)

            locked_source.balance -= amount
            locked_source.save()

            locked_dest.balance += amount
            locked_dest.save()

            # Ledger for sender
            Ledger.objects.create(
                account=locked_source,
                transaction_type='transfer_sent',
                amount=amount,
                balance_after=locked_source.balance,
                description=f"Transferred to {locked_dest.account_number}"
            )

            # Ledger for recipient
            Ledger.objects.create(
                account=locked_dest,
                transaction_type='transfer_received',
                amount=amount,
                balance_after=locked_dest.balance,
                description=f"Received from {locked_source.account_number}"
            )

        return Response({"message": "Transfer successful", "balance": locked_source.balance})

class TransactionHistoryView(generics.ListAPIView):
    """
    Returns transaction history.
    - Admin users see ALL transactions across all accounts.
    - Customer users only see their own account's transactions.

    Supports filtering via query params:
    - `transaction_type` (deposit | withdrawal | transfer_sent | transfer_received)
    - `date_from` (ISO 8601 datetime, e.g. 2025-01-01T00:00:00)
    - `date_to` (ISO 8601 datetime)
    """
    serializer_class = LedgerSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = LedgerFilter

    @extend_schema(
        summary="Get Transaction History",
        parameters=[
            OpenApiParameter('transaction_type', OpenApiTypes.STR, description='Filter by type: deposit, withdrawal, transfer_sent, transfer_received'),
            OpenApiParameter('date_from', OpenApiTypes.DATETIME, description='Filter from this datetime (ISO 8601)'),
            OpenApiParameter('date_to', OpenApiTypes.DATETIME, description='Filter up to this datetime (ISO 8601)'),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        # Guard for drf-spectacular schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Ledger.objects.none()
        user = self.request.user
        if user.user_type == 'admin':
            return Ledger.objects.all().order_by('-created_at')
        return Ledger.objects.filter(account=user.account).order_by('-created_at')
