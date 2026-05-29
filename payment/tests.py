from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from .models import Account, Ledger

User = get_user_model()

class PaymentTests(APITestCase):
    def setUp(self):
        # Patch Celery task so registration email doesn't fail during tests
        patcher = patch('payment.tasks.send_registration_email_task.delay')
        self.mock_send_email = patcher.start()
        self.addCleanup(patcher.stop)

        self.user1 = User.objects.create_user(email='user1@test.com', password='password123', user_type='customer')
        self.user2 = User.objects.create_user(email='user2@test.com', password='password123', user_type='customer')
        self.admin_user = User.objects.create_user(email='admin@test.com', password='adminpass', user_type='admin')

        self.account1 = self.user1.account
        self.account2 = self.user2.account

        self.client.force_authenticate(user=self.user1)

        self.balance_url = reverse('balance')
        self.deposit_url = reverse('deposit')
        self.withdraw_url = reverse('withdraw')
        self.transfer_url = reverse('transfer')
        self.transactions_url = reverse('transactions')

    # --- Signal Tests ---
    def test_account_creation_signal(self):
        """Account is automatically created upon user registration with 6-digit number."""
        self.assertIsNotNone(self.account1)
        self.assertEqual(len(self.account1.account_number), 6)
        self.assertEqual(self.account1.balance, Decimal('0.00'))

    def test_registration_email_celery_task_dispatched(self):
        """Celery task is dispatched on user creation, not sent synchronously."""
        new_user = User.objects.create_user(email='newuser@test.com', password='pass1234')
        # Task should have been called for all users created (user1, user2, admin_user, new_user)
        self.assertTrue(self.mock_send_email.called)

    # --- Balance ---
    def test_get_balance(self):
        response = self.client.get(self.balance_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['balance'], '0.00')

    def test_unauthenticated_cannot_view_balance(self):
        self.client.logout()
        response = self.client.get(self.balance_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Deposit ---
    def test_deposit(self):
        response = self.client.post(self.deposit_url, {'amount': '100.50'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('100.50'))
        ledger = Ledger.objects.filter(account=self.account1, transaction_type='deposit').first()
        self.assertIsNotNone(ledger)
        self.assertEqual(ledger.balance_after, Decimal('100.50'))

    # --- Withdrawal ---
    def test_withdraw_success(self):
        self.account1.balance = Decimal('200.00')
        self.account1.save()
        response = self.client.post(self.withdraw_url, {'amount': '50.00'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('150.00'))

    def test_withdraw_insufficient_funds(self):
        response = self.client.post(self.withdraw_url, {'amount': '50.00'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Insufficient funds')

    # --- Transfer ---
    def test_transfer_success(self):
        self.account1.balance = Decimal('500.00')
        self.account1.save()
        data = {'amount': '150.00', 'destination_account': self.account2.account_number}
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account1.refresh_from_db()
        self.account2.refresh_from_db()
        self.assertEqual(self.account1.balance, Decimal('350.00'))
        self.assertEqual(self.account2.balance, Decimal('150.00'))
        self.assertEqual(Ledger.objects.filter(account=self.account1, transaction_type='transfer_sent').count(), 1)
        self.assertEqual(Ledger.objects.filter(account=self.account2, transaction_type='transfer_received').count(), 1)

    def test_transfer_insufficient_funds(self):
        data = {'amount': '150.00', 'destination_account': self.account2.account_number}
        response = self.client.post(self.transfer_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_invalid_account(self):
        self.account1.balance = Decimal('500.00')
        self.account1.save()
        response = self.client.post(self.transfer_url, {'amount': '100.00', 'destination_account': '000000'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transfer_self(self):
        self.account1.balance = Decimal('500.00')
        self.account1.save()
        response = self.client.post(self.transfer_url, {'amount': '100.00', 'destination_account': self.account1.account_number}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Transaction History: Customer Scoping ---
    def test_customer_sees_only_own_transactions(self):
        # Make a deposit for user1 and a deposit for user2
        self.client.post(self.deposit_url, {'amount': '100.00'}, format='json')

        # Now as user2, make a deposit
        self.client.force_authenticate(user=self.user2)
        self.client.post(self.deposit_url, {'amount': '200.00'}, format='json')

        # user2 should only see their 1 transaction
        response = self.client.get(self.transactions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]['amount']), '200.00')

    # --- Transaction History: Admin Scoping ---
    def test_admin_sees_all_transactions(self):
        # Create transactions for two different users
        self.client.post(self.deposit_url, {'amount': '100.00'}, format='json')
        self.client.force_authenticate(user=self.user2)
        self.client.post(self.deposit_url, {'amount': '200.00'}, format='json')

        # Admin should see both
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.transactions_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    # --- Transaction History: Filtering ---
    def test_filter_by_transaction_type(self):
        self.account1.balance = Decimal('500.00')
        self.account1.save()
        self.client.post(self.deposit_url, {'amount': '50.00'}, format='json')
        self.client.post(self.withdraw_url, {'amount': '20.00'}, format='json')

        response = self.client.get(self.transactions_url + '?transaction_type=deposit')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for entry in response.data:
            self.assertEqual(entry['transaction_type'], 'deposit')
