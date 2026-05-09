from django.db.utils import IntegrityError
from django.test import TestCase

from accounts.models import User


class UserManagerCreateUserTests(TestCase):
    """Tests for UserManager.create_user method."""

    def test_missing_email_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(email="", username="testuser", password="testpass")
        self.assertIn("Email", str(ctx.exception))

    def test_none_email_raises_value_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, username="testuser", password="testpass")

    def test_missing_username_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(email="test@example.com", username="", password="testpass")
        self.assertIn("Username", str(ctx.exception))

    def test_creates_user_with_valid_fields(self):
        user = User.objects.create_user(email="test@example.com", username="testuser", password="testpass")
        self.assertIsNotNone(user.pk)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")

    def test_email_is_normalized(self):
        user = User.objects.create_user(email="Test@Example.COM", username="normalized", password="testpass")
        self.assertEqual(user.email, "Test@example.com")

    def test_password_is_hashed_not_plaintext(self):
        user = User.objects.create_user(email="pw@example.com", username="hashed", password="testpass")
        self.assertNotEqual(user.password, "testpass")
        self.assertTrue(user.check_password("testpass"))

    def test_password_none_is_allowed(self):
        user = User.objects.create_user(email="nopw@example.com", username="nopassword", password=None)
        self.assertIsNotNone(user.pk)
        self.assertFalse(user.check_password("testpass"))

    def test_default_is_staff_is_false(self):
        user = User.objects.create_user(email="staff@example.com", username="staffcheck", password="testpass")
        self.assertFalse(user.is_staff)

    def test_default_is_active_is_true(self):
        user = User.objects.create_user(email="active@example.com", username="activecheck", password="testpass")
        self.assertTrue(user.is_active)

    def test_default_is_superuser_is_false(self):
        user = User.objects.create_user(email="super@example.com", username="supercheck", password="testpass")
        self.assertFalse(user.is_superuser)

    def test_extra_fields_are_passed_through(self):
        user = User.objects.create_user(
            email="extra@example.com",
            username="extrauser",
            password="testpass",
            full_name="John Doe",
        )
        self.assertEqual(user.full_name, "John Doe")

    def test_is_staff_can_be_set_true_via_extra_fields(self):
        user = User.objects.create_user(
            email="stafftrue@example.com",
            username="stafftrue",
            password="testpass",
            is_staff=True,
        )
        self.assertTrue(user.is_staff)

    def test_username_must_be_unique(self):
        User.objects.create_user(email="a@example.com", username="dupe", password="testpass")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="b@example.com", username="dupe", password="testpass")

    def test_email_must_be_unique(self):
        User.objects.create_user(email="dupe@example.com", username="user1", password="testpass")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dupe@example.com", username="user2", password="testpass")

    def test_dunder_str_returns_username(self):
        user = User.objects.create_user(email="str@example.com", username="struser", password="testpass")
        self.assertEqual(str(user), "struser")


class UserManagerCreateSuperuserTests(TestCase):
    """Tests for UserManager.create_superuser method."""

    def test_creates_superuser_with_defaults(self):
        user = User.objects.create_superuser(email="admin@example.com", username="admin", password="adminpass")
        self.assertIsNotNone(user.pk)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_email_is_normalized(self):
        user = User.objects.create_superuser(email="Admin@Example.COM", username="admin2", password="adminpass")
        self.assertEqual(user.email, "Admin@example.com")

    def test_password_is_hashed(self):
        user = User.objects.create_superuser(email="hash@example.com", username="hashadmin", password="adminpass")
        self.assertNotEqual(user.password, "adminpass")
        self.assertTrue(user.check_password("adminpass"))

    def test_is_staff_false_explicitly_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_superuser(
                email="bad@example.com",
                username="badadmin",
                password="adminpass",
                is_staff=False,
            )
        self.assertIn("is_staff", str(ctx.exception))

    def test_is_superuser_false_explicitly_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_superuser(
                email="bad2@example.com",
                username="badadmin2",
                password="adminpass",
                is_superuser=False,
            )
        self.assertIn("is_superuser", str(ctx.exception))

    def test_extra_fields_are_passed_through(self):
        user = User.objects.create_superuser(
            email="extra@example.com",
            username="extrasuper",
            password="adminpass",
            full_name="Admin User",
        )
        self.assertEqual(user.full_name, "Admin User")

    def test_username_must_be_unique(self):
        User.objects.create_superuser(email="a1@example.com", username="superdupe", password="adminpass")
        with self.assertRaises(IntegrityError):
            User.objects.create_superuser(email="a2@example.com", username="superdupe", password="adminpass")

    def test_email_must_be_unique(self):
        User.objects.create_superuser(email="dupe@example.com", username="sd1", password="adminpass")
        with self.assertRaises(IntegrityError):
            User.objects.create_superuser(email="dupe@example.com", username="sd2", password="adminpass")

    def test_dunder_str_returns_username(self):
        user = User.objects.create_superuser(email="str@example.com", username="strsuper", password="adminpass")
        self.assertEqual(str(user), "strsuper")

    def test_is_active_defaults_true(self):
        user = User.objects.create_superuser(email="active@example.com", username="activesuper", password="adminpass")
        self.assertTrue(user.is_active)

    def test_is_active_false_is_still_allowed(self):
        """create_superuser only enforces is_staff and is_superuser, not is_active."""
        user = User.objects.create_superuser(
            email="inactive@example.com",
            username="inactivesuper",
            password="adminpass",
            is_active=False,
        )
        self.assertFalse(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
