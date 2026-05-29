from django.urls import path
from .views import (
    BalanceView,
    DepositView,
    WithdrawView,
    AccountNameView,
    TransferFundsView,
    TransactionHistoryView
)

urlpatterns = [
    path('balance/', BalanceView.as_view(), name='balance'),
    path('deposit/', DepositView.as_view(), name='deposit'),
    path('withdraw/', WithdrawView.as_view(), name='withdraw'),
    path('account-name/', AccountNameView.as_view(), name='account_name'),
    path('transfer-funds/', TransferFundsView.as_view(), name='transfer_funds'),
    path('transactions/', TransactionHistoryView.as_view(), name='transaction_history'),
]
