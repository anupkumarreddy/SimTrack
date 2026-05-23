"""Tests for milestones/models.py and milestones/views.py: Milestone CRUD and MilestoneUpdate creation."""

from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from common.choices import MilestoneStatus, Priority
from milestones.models import Milestone, MilestoneUpdate
from projects.models import Project


class MilestoneModelTests(TestCase):
    """Tests for Milestone model: __str__, defaults, ordering."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")

    def test_str_returns_title(self):
        """__str__ returns the milestone title."""
        m = Milestone.objects.create(project=self.project, title="Phase 1 Complete")
        self.assertEqual(str(m), "Phase 1 Complete")

    def test_default_status_is_planned(self):
        """New milestones default to PLANNED status."""
        m = Milestone.objects.create(project=self.project, title="Test")
        self.assertEqual(m.status, MilestoneStatus.PLANNED)

    def test_default_priority_is_medium(self):
        """New milestones default to MEDIUM priority."""
        m = Milestone.objects.create(project=self.project, title="Test")
        self.assertEqual(m.priority, Priority.MEDIUM)

    def test_default_completion_percentage_is_zero(self):
        """New milestones default to 0% completion."""
        m = Milestone.objects.create(project=self.project, title="Test")
        self.assertEqual(m.completion_percentage, 0)

    def test_owner_is_optional(self):
        """Milestone can be created without an owner."""
        m = Milestone.objects.create(project=self.project, title="Ownerless")
        self.assertIsNone(m.owner)

    def test_target_date_is_optional(self):
        """Milestone can be created without a target date."""
        m = Milestone.objects.create(project=self.project, title="No Date")
        self.assertIsNone(m.target_date)

    def test_description_is_optional(self):
        """Milestone can be created with blank description."""
        m = Milestone.objects.create(project=self.project, title="No Desc", description="")
        self.assertEqual(m.description, "")

    def test_full_creation_with_all_fields(self):
        """Milestone can be created with all fields populated."""
        user = User.objects.create_user(email="owner@example.com", username="owner", password="pw")
        m = Milestone.objects.create(
            project=self.project,
            title="Full Milestone",
            description="A detailed description",
            status=MilestoneStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            owner=user,
            target_date=date(2026, 12, 31),
            completion_percentage=50,
        )
        self.assertEqual(m.project, self.project)
        self.assertEqual(m.title, "Full Milestone")
        self.assertEqual(m.description, "A detailed description")
        self.assertEqual(m.status, MilestoneStatus.IN_PROGRESS)
        self.assertEqual(m.priority, Priority.HIGH)
        self.assertEqual(m.owner, user)
        self.assertEqual(m.target_date, date(2026, 12, 31))
        self.assertEqual(m.completion_percentage, 50)


class MilestoneUpdateModelTests(TestCase):
    """Tests for MilestoneUpdate model: __str__, creation, defaults."""

    def test_str_returns_update_on_milestone(self):
        """__str__ returns 'Update on <milestone title>'."""
        project = Project.objects.create(name="Test Project")
        m = Milestone.objects.create(project=project, title="Test Milestone")
        u = MilestoneUpdate.objects.create(milestone=m, comment="Progress update")
        self.assertEqual(str(u), "Update on Test Milestone")

    def test_updated_by_is_optional(self):
        """MilestoneUpdate can be created without an updated_by user."""
        project = Project.objects.create(name="Test Project")
        m = Milestone.objects.create(project=project, title="Test Milestone")
        u = MilestoneUpdate.objects.create(milestone=m, comment="Anonymous update")
        self.assertIsNone(u.updated_by)

    def test_comment_blank_string_is_allowed_by_model(self):
        """MilestoneUpdate allows empty string for comment at model level (TextField blank=False but stores '' at DB)."""
        project = Project.objects.create(name="Test Project")
        m = Milestone.objects.create(project=project, title="Test Milestone")
        u = MilestoneUpdate.objects.create(milestone=m, comment="")
        self.assertEqual(u.comment, "")

    def test_multiple_updates_ordered_by_created_at_desc(self):
        """Updates are ordered by -created_at (newest first)."""
        project = Project.objects.create(name="Test Project")
        m = Milestone.objects.create(project=project, title="Test Milestone")
        MilestoneUpdate.objects.create(milestone=m, comment="First")
        u2 = MilestoneUpdate.objects.create(milestone=m, comment="Second")
        self.assertEqual(MilestoneUpdate.objects.first(), u2)

    def test_related_name_updates_on_milestone(self):
        """Milestone.updates returns all related updates."""
        project = Project.objects.create(name="Test Project")
        m = Milestone.objects.create(project=project, title="Test Milestone")
        MilestoneUpdate.objects.create(milestone=m, comment="Update 1")
        MilestoneUpdate.objects.create(milestone=m, comment="Update 2")
        self.assertEqual(m.updates.count(), 2)


class MilestoneListViewTests(TestCase):
    """Tests for MilestoneListView: filtering, pagination, context."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(email="viewer@example.com", username="viewer", password="pw")
        cls.project1 = Project.objects.create(name="Project Alpha")
        cls.project2 = Project.objects.create(name="Project Beta")

        cls.m1 = Milestone.objects.create(
            project=cls.project1,
            title="Alpha M1",
            status=MilestoneStatus.PLANNED,
            priority=Priority.HIGH,
        )
        cls.m2 = Milestone.objects.create(
            project=cls.project1,
            title="Alpha M2",
            status=MilestoneStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
        )
        cls.m3 = Milestone.objects.create(
            project=cls.project2,
            title="Beta M1",
            status=MilestoneStatus.COMPLETED,
            priority=Priority.LOW,
        )
        cls.m4 = Milestone.objects.create(
            project=cls.project2,
            title="Beta M2",
            status=MilestoneStatus.BLOCKED,
            priority=Priority.CRITICAL,
        )

    def setUp(self):
        self.client.login(username="viewer", password="pw")

    def test_returns_all_milestones_without_filters(self):
        """Unfiltered list returns all milestones."""
        response = self.client.get(reverse("milestone-list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "milestones/milestone_list.html")
        self.assertEqual(len(response.context["milestones"]), 4)

    def test_filter_by_project(self):
        """project=ID returns only milestones for that project."""
        response = self.client.get(reverse("milestone-list"), {"project": self.project1.pk})
        milestones = list(response.context["milestones"])
        self.assertEqual(len(milestones), 2)
        self.assertIn(self.m1, milestones)
        self.assertIn(self.m2, milestones)

    def test_filter_by_status(self):
        """status=planned returns only planned milestones."""
        response = self.client.get(reverse("milestone-list"), {"status": MilestoneStatus.PLANNED})
        self.assertEqual(len(response.context["milestones"]), 1)
        self.assertEqual(response.context["milestones"][0], self.m1)

    def test_filter_by_priority(self):
        """priority=critical returns only critical milestones."""
        response = self.client.get(reverse("milestone-list"), {"priority": Priority.CRITICAL})
        self.assertEqual(len(response.context["milestones"]), 1)
        self.assertEqual(response.context["milestones"][0], self.m4)

    def test_filter_by_nonexistent_status_returns_empty(self):
        """status=nonexistent returns no milestones."""
        response = self.client.get(reverse("milestone-list"), {"status": "nonexistent"})
        self.assertEqual(len(response.context["milestones"]), 0)

    def test_combined_project_and_status_filter(self):
        """Applying both project and status filters returns intersection."""
        response = self.client.get(
            reverse("milestone-list"),
            {"project": self.project1.pk, "status": MilestoneStatus.IN_PROGRESS},
        )
        self.assertEqual(len(response.context["milestones"]), 1)
        self.assertEqual(response.context["milestones"][0], self.m2)

    def test_combined_project_and_priority_filter(self):
        """Applying both project and priority filters returns intersection."""
        response = self.client.get(
            reverse("milestone-list"),
            {"project": self.project2.pk, "priority": Priority.LOW},
        )
        self.assertEqual(len(response.context["milestones"]), 1)
        self.assertEqual(response.context["milestones"][0], self.m3)

    def test_context_includes_project_list(self):
        """Context includes 'project_list' for filter dropdown."""
        response = self.client.get(reverse("milestone-list"))
        self.assertIn("project_list", response.context)
        self.assertEqual(len(response.context["project_list"]), 2)

    def test_paginate_by_is_20(self):
        """View paginates by 20 items per page."""
        response = self.client.get(reverse("milestone-list"))
        self.assertEqual(response.context["paginator"].per_page, 20)


class MilestoneDetailViewTests(TestCase):
    """Tests for MilestoneDetailView: rendering and context."""

    def setUp(self):
        self.user = User.objects.create_user(email="viewer@example.com", username="viewer", password="pw")
        self.project = Project.objects.create(name="Test Project")
        self.milestone = Milestone.objects.create(
            project=self.project,
            title="Detail Test Milestone",
            status=MilestoneStatus.IN_PROGRESS,
            priority=Priority.HIGH,
        )
        self.client.login(username="viewer", password="pw")

    def test_detail_returns_200(self):
        """Milestone detail page returns 200."""
        response = self.client.get(reverse("milestone-detail", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "milestones/milestone_detail.html")

    def test_context_object_is_milestone(self):
        """Context 'milestone' key contains the milestone instance."""
        response = self.client.get(reverse("milestone-detail", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.context["milestone"], self.milestone)

    def test_nonexistent_milestone_returns_404(self):
        """Requesting a non-existent milestone returns 404."""
        response = self.client.get(reverse("milestone-detail", kwargs={"pk": 99999}))
        self.assertEqual(response.status_code, 404)


class MilestoneCreateViewTests(TestCase):
    """Tests for MilestoneCreateView: staff-only create."""

    @classmethod
    def setUpTestData(cls):
        cls.project = Project.objects.create(name="Test Project")
        cls.staff_user = User.objects.create_user(
            email="staff@example.com", username="staff", password="pw", is_staff=True
        )
        cls.regular_user = User.objects.create_user(email="user@example.com", username="user", password="pw")

    def test_staff_can_access_create_page(self):
        """Staff user can access the create form."""
        self.client.login(username="staff", password="pw")
        response = self.client.get(reverse("milestone-create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "milestones/milestone_form.html")

    def test_regular_user_redirected_from_create(self):
        """Non-staff user is redirected (403 or login) from create page."""
        self.client.login(username="user", password="pw")
        response = self.client.get(reverse("milestone-create"))
        self.assertIn(response.status_code, [302, 403])

    def test_unauthenticated_user_redirected_from_create(self):
        """Unauthenticated user is redirected from create page."""
        response = self.client.get(reverse("milestone-create"))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_create_milestone(self):
        """Staff user can POST to create a new milestone."""
        self.client.login(username="staff", password="pw")
        self.client.post(
            reverse("milestone-create"),
            {
                "project": self.project.pk,
                "title": "New Milestone",
                "description": "Created via test",
                "status": MilestoneStatus.PLANNED,
                "priority": Priority.MEDIUM,
                "completion_percentage": 0,
            },
        )
        # Follow redirects to check final destination
        self.assertEqual(Milestone.objects.count(), 1)
        m = Milestone.objects.first()
        self.assertEqual(m.title, "New Milestone")
        self.assertEqual(m.project, self.project)

    def test_regular_user_cannot_create_milestone(self):
        """Non-staff user cannot POST to create a milestone."""
        self.client.login(username="user", password="pw")
        response = self.client.post(
            reverse("milestone-create"),
            {
                "project": self.project.pk,
                "title": "Unauthorized Milestone",
                "status": MilestoneStatus.PLANNED,
                "priority": Priority.MEDIUM,
                "completion_percentage": 0,
            },
        )
        self.assertIn(response.status_code, [302, 403])
        self.assertEqual(Milestone.objects.count(), 0)


class MilestoneUpdateViewTests(TestCase):
    """Tests for MilestoneUpdateView: staff-only update."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.milestone = Milestone.objects.create(
            project=self.project,
            title="Original Title",
            status=MilestoneStatus.PLANNED,
            priority=Priority.LOW,
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com", username="staff", password="pw", is_staff=True
        )
        self.regular_user = User.objects.create_user(email="user@example.com", username="user", password="pw")

    def test_staff_can_access_update_page(self):
        """Staff user can access the update form."""
        self.client.login(username="staff", password="pw")
        response = self.client.get(reverse("milestone-update", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_redirected_from_update(self):
        """Non-staff user is redirected from update page."""
        self.client.login(username="user", password="pw")
        response = self.client.get(reverse("milestone-update", kwargs={"pk": self.milestone.pk}))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_update_milestone(self):
        """Staff user can POST to update a milestone."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(
            reverse("milestone-update", kwargs={"pk": self.milestone.pk}),
            {
                "project": self.project.pk,
                "title": "Updated Title",
                "description": "Updated description",
                "status": MilestoneStatus.IN_PROGRESS,
                "priority": Priority.HIGH,
                "completion_percentage": 75,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.title, "Updated Title")
        self.assertEqual(self.milestone.status, MilestoneStatus.IN_PROGRESS)
        self.assertEqual(self.milestone.priority, Priority.HIGH)
        self.assertEqual(self.milestone.completion_percentage, 75)

    def test_update_redirects_to_detail(self):
        """After update, redirects to milestone detail page."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(
            reverse("milestone-update", kwargs={"pk": self.milestone.pk}),
            {
                "project": self.project.pk,
                "title": "Updated Title",
                "status": MilestoneStatus.PLANNED,
                "priority": Priority.MEDIUM,
                "completion_percentage": 0,
            },
        )
        self.assertRedirects(response, reverse("milestone-detail", kwargs={"pk": self.milestone.pk}))

    def test_regular_user_cannot_update_milestone(self):
        """Non-staff user cannot POST to update a milestone."""
        self.client.login(username="user", password="pw")
        response = self.client.post(
            reverse("milestone-update", kwargs={"pk": self.milestone.pk}),
            {
                "project": self.project.pk,
                "title": "Hacked Title",
                "status": MilestoneStatus.PLANNED,
                "priority": Priority.MEDIUM,
            },
        )
        self.assertIn(response.status_code, [302, 403])
        self.milestone.refresh_from_db()
        self.assertEqual(self.milestone.title, "Original Title")


class MilestoneDeleteViewTests(TestCase):
    """Tests for MilestoneDeleteView: staff-only delete."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.milestone = Milestone.objects.create(
            project=self.project,
            title="To Be Deleted",
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com", username="staff", password="pw", is_staff=True
        )
        self.regular_user = User.objects.create_user(email="user@example.com", username="user", password="pw")

    def test_staff_can_access_delete_page(self):
        """Staff user can access the delete confirmation page."""
        self.client.login(username="staff", password="pw")
        response = self.client.get(reverse("milestone-delete", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "milestones/milestone_confirm_delete.html")

    def test_regular_user_redirected_from_delete(self):
        """Non-staff user is redirected from delete page."""
        self.client.login(username="user", password="pw")
        response = self.client.get(reverse("milestone-delete", kwargs={"pk": self.milestone.pk}))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_delete_milestone(self):
        """Staff user can POST to delete a milestone."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(reverse("milestone-delete", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Milestone.objects.count(), 0)

    def test_delete_redirects_to_list(self):
        """After delete, redirects to milestone list page."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(reverse("milestone-delete", kwargs={"pk": self.milestone.pk}))
        self.assertRedirects(response, reverse("milestone-list"))

    def test_regular_user_cannot_delete_milestone(self):
        """Non-staff user cannot POST to delete a milestone."""
        self.client.login(username="user", password="pw")
        response = self.client.post(reverse("milestone-delete", kwargs={"pk": self.milestone.pk}))
        self.assertIn(response.status_code, [302, 403])
        self.assertEqual(Milestone.objects.count(), 1)


class MilestoneUpdateCreateViewTests(TestCase):
    """Tests for MilestoneUpdateCreateView: staff-only comment creation on a milestone."""

    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.milestone = Milestone.objects.create(
            project=self.project,
            title="Update Target",
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com", username="staff", password="pw", is_staff=True
        )
        self.regular_user = User.objects.create_user(email="user@example.com", username="user", password="pw")

    def test_staff_can_access_update_create_page(self):
        """Staff user can access the update creation form."""
        self.client.login(username="staff", password="pw")
        response = self.client.get(reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "milestones/milestoneupdate_form.html")

    def test_regular_user_redirected_from_update_create(self):
        """Non-staff user is redirected from update creation page."""
        self.client.login(username="user", password="pw")
        response = self.client.get(reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_create_update(self):
        """Staff user can POST to create a milestone update."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(
            reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}),
            {"comment": "Good progress this week"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MilestoneUpdate.objects.count(), 1)
        u = MilestoneUpdate.objects.first()
        self.assertEqual(u.milestone, self.milestone)
        self.assertEqual(u.comment, "Good progress this week")
        self.assertEqual(u.updated_by, self.staff_user)

    def test_update_sets_milestone_automatically(self):
        """The milestone FK is set from the URL pk, not form data."""
        self.client.login(username="staff", password="pw")
        self.client.post(
            reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}),
            {"comment": "Auto-linked"},
        )
        u = MilestoneUpdate.objects.first()
        self.assertEqual(u.milestone, self.milestone)

    def test_update_sets_updated_by_to_request_user(self):
        """The updated_by FK is set to the logged-in staff user."""
        self.client.login(username="staff", password="pw")
        self.client.post(
            reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}),
            {"comment": "User attribution"},
        )
        u = MilestoneUpdate.objects.first()
        self.assertEqual(u.updated_by, self.staff_user)

    def test_update_redirects_to_milestone_detail(self):
        """After creating an update, redirects to the milestone detail page."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(
            reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}),
            {"comment": "Redirect test"},
        )
        self.assertRedirects(response, reverse("milestone-detail", kwargs={"pk": self.milestone.pk}))

    def test_regular_user_cannot_create_update(self):
        """Non-staff user cannot POST to create a milestone update."""
        self.client.login(username="user", password="pw")
        response = self.client.post(
            reverse("milestone-update-create", kwargs={"pk": self.milestone.pk}),
            {"comment": "Unauthorized update"},
        )
        self.assertIn(response.status_code, [302, 403])
        self.assertEqual(MilestoneUpdate.objects.count(), 0)

    def test_nonexistent_milestone_returns_404(self):
        """Creating an update for a non-existent milestone returns 404."""
        self.client.login(username="staff", password="pw")
        response = self.client.post(
            reverse("milestone-update-create", kwargs={"pk": 99999}),
            {"comment": "Ghost milestone"},
        )
        self.assertEqual(response.status_code, 404)
