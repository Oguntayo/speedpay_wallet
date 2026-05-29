from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

User = get_user_model()

class UserRoleAndPasswordTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass1234', user_type='admin'
        )
        self.customer = User.objects.create_user(
            email='customer@test.com', password='pass1234', user_type='customer'
        )
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.me_url = reverse('user_detail')
        self.users_url = reverse('user_list')
        self.change_pw_url = reverse('change_password')
        self.forgot_pw_url = reverse('forgot_password')
        self.reset_pw_url = reverse('reset_password')

    # --- Login ---
    def test_login_success(self):
        data = {'email': 'customer@test.com', 'password': 'pass1234'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_invalid_credentials(self):
        data = {'email': 'customer@test.com', 'password': 'wrongpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- User list (admin-only) ---
    def test_admin_can_list_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_customer_cannot_list_users(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_can_view_own_profile(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'customer@test.com')

    # --- Change Password ---
    def test_change_password_success(self):
        self.client.force_authenticate(user=self.customer)
        data = {'old_password': 'pass1234', 'new_password': 'NewPass@5678'}
        response = self.client.post(self.change_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('NewPass@5678'))

    def test_change_password_wrong_old(self):
        self.client.force_authenticate(user=self.customer)
        data = {'old_password': 'wrongoldpass', 'new_password': 'newpass5678'}
        response = self.client.post(self.change_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Forgot Password ---
    @patch('user.tasks.send_password_reset_email_task.delay')
    def test_forgot_password_valid_email(self, mock_task):
        data = {'email': 'customer@test.com'}
        response = self.client.post(self.forgot_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_task.assert_called_once()

    @patch('user.tasks.send_password_reset_email_task.delay')
    def test_forgot_password_unknown_email(self, mock_task):
        """Should always return 200 to avoid email enumeration."""
        data = {'email': 'doesnotexist@test.com'}
        response = self.client.post(self.forgot_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_task.assert_not_called()

    # --- Reset Password ---
    def test_reset_password_invalid_token(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        data = {'uid': uid, 'token': 'badtoken', 'new_password': 'newpass1234'}
        response = self.client.post(self.reset_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_full_flow(self):
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = PasswordResetTokenGenerator().make_token(self.customer)
        data = {'uid': uid, 'token': token, 'new_password': 'ResetPass@1234'}
        response = self.client.post(self.reset_pw_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('ResetPass@1234'))
