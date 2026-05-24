from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.forms import SignUpForm
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


class SignUpFormTests(TestCase):
    """Tests for accounts/forms.py: SignUpForm validation."""

    def test_valid_form_creates_user(self):
        """Form with all required fields is valid."""
        form = SignUpForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_form_saves_user(self):
        """Form.save() creates a User with correct fields."""
        form = SignUpForm(
            data={
                "username": "newuser",
                "email": "new@example.com",
                "full_name": "Jane Doe",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, "newuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.full_name, "Jane Doe")
        self.assertTrue(user.check_password("SecureP4ss!"))

    def test_missing_username_is_invalid(self):
        """Blank username fails validation."""
        form = SignUpForm(
            data={
                "username": "",
                "email": "test@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_missing_email_is_invalid(self):
        """Blank email fails validation (email is required)."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_password_is_invalid(self):
        """Missing password1 fails validation."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password1": "",
                "password2": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_password_mismatch_is_invalid(self):
        """Mismatched password1 and password2 fails validation."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password1": "SecureP4ss!",
                "password2": "DifferentP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_password_too_short_is_invalid(self):
        """Password shorter than 8 chars fails validation."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password1": "short",
                "password2": "short",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_full_name_is_optional(self):
        """Form is valid without full_name."""
        form = SignUpForm(
            data={
                "username": "noname",
                "email": "noname@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.full_name, "")

    def test_duplicate_username_is_invalid(self):
        """Existing username makes form invalid."""
        User.objects.create_user(email="existing@example.com", username="existing", password="pw")
        form = SignUpForm(
            data={
                "username": "existing",
                "email": "another@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_duplicate_email_is_invalid(self):
        """Existing email makes form invalid."""
        User.objects.create_user(email="dup@example.com", username="user1", password="pw")
        form = SignUpForm(
            data={
                "username": "user2",
                "email": "dup@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_invalid_email_format_is_rejected(self):
        """Malformed email fails validation."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "not-an-email",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_too_common_is_rejected(self):
        """Common passwords like 'password' or '12345678' are rejected."""
        form = SignUpForm(
            data={
                "username": "testuser",
                "email": "test@example.com",
                "password1": "password",
                "password2": "password",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_widget_attrs_are_applied(self):
        """All fields get Tailwind widget classes."""
        form = SignUpForm()
        css_class = (
            "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
        )
        for field in form.fields.values():
            self.assertIn(css_class, field.widget.attrs.get("class", ""))


class SignUpViewTests(TestCase):
    """Tests for accounts/views.py: SignUpView."""

    def test_get_returns_200(self):
        """GET /accounts/signup/ returns 200."""
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/signup.html")

    def test_get_contains_signup_form(self):
        """GET response includes a SignUpForm in context."""
        response = self.client.get(reverse("signup"))
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], SignUpForm)

    def test_post_with_valid_data_creates_user(self):
        """POST with valid data creates a new user."""
        self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        self.assertEqual(User.objects.filter(username="newuser").count(), 1)

    def test_post_with_valid_data_redirects_to_dashboard(self):
        """POST with valid data redirects to dashboard after signup."""
        response = self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        self.assertRedirects(response, reverse("dashboard"))

    def test_post_with_valid_data_logs_user_in(self):
        """POST with valid data logs the user in automatically."""
        self.client.post(
            reverse("signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        response = self.client.get(reverse("dashboard"))
        # If logged in, dashboard should be accessible
        self.assertEqual(response.status_code, 200)

    def test_post_with_invalid_data_returns_200(self):
        """POST with invalid data re-renders form (200, not redirect)."""
        response = self.client.post(
            reverse("signup"),
            {
                "username": "",
                "email": "invalid",
                "password1": "short",
                "password2": "mismatch",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/signup.html")

    def test_post_with_invalid_data_does_not_create_user(self):
        """POST with invalid data does not create a user."""
        initial_count = User.objects.count()
        self.client.post(
            reverse("signup"),
            {
                "username": "",
                "email": "",
                "password1": "",
                "password2": "",
            },
        )
        self.assertEqual(User.objects.count(), initial_count)

    def test_post_with_password_mismatch_shows_error(self):
        """POST with mismatched passwords shows error in form."""
        response = self.client.post(
            reverse("signup"),
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "SecureP4ss!",
                "password2": "DifferentP4ss!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)

    def test_post_with_duplicate_username_shows_error(self):
        """POST with existing username shows error in form."""
        User.objects.create_user(email="existing@example.com", username="existing", password="pw")
        response = self.client.post(
            reverse("signup"),
            {
                "username": "existing",
                "email": "another@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)

    def test_post_with_duplicate_email_shows_error(self):
        """POST with existing email shows error in form."""
        User.objects.create_user(email="dup@example.com", username="user1", password="pw")
        response = self.client.post(
            reverse("signup"),
            {
                "username": "user2",
                "email": "dup@example.com",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)

    def test_post_with_full_name_sets_field(self):
        """POST with full_name sets it on the created user."""
        self.client.post(
            reverse("signup"),
            {
                "username": "nameduser",
                "email": "named@example.com",
                "full_name": "John Smith",
                "password1": "SecureP4ss!",
                "password2": "SecureP4ss!",
            },
        )
        user = User.objects.get(username="nameduser")
        self.assertEqual(user.full_name, "John Smith")
