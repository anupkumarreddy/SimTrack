from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .forms import ProjectForm
from .models import Project, ProjectCategory


class ProjectFormTests(TestCase):
    def test_save_creates_new_category_from_name(self):
        form = ProjectForm(
            data={
                "name": "Ethernet MAC",
                "description": "Ethernet controller verification",
                "new_category_name": "Networking",
                "status": "active",
                "repository_url": "",
                "is_active": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.category.name, "Networking")
        self.assertEqual(ProjectCategory.objects.filter(name="Networking").count(), 1)

    def test_save_reuses_existing_category_from_name(self):
        category = ProjectCategory.objects.create(name="Controller")
        form = ProjectForm(
            data={
                "name": "USB Controller",
                "description": "USB controller verification",
                "new_category_name": "controller",
                "status": "active",
                "repository_url": "",
                "is_active": "on",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.category, category)
        self.assertEqual(ProjectCategory.objects.filter(name__iexact="controller").count(), 1)


class ProjectCategoryModelTests(TestCase):
    """Tests for ProjectCategory auto-slug, __str__, and save behavior."""

    def test_str_returns_name(self):
        category = ProjectCategory.objects.create(name="Networking")
        self.assertEqual(str(category), "Networking")

    def test_auto_slug_from_name_when_blank(self):
        category = ProjectCategory.objects.create(name="Networking")
        self.assertEqual(category.slug, "networking")

    def test_auto_slug_slugifies_name_correctly(self):
        category = ProjectCategory.objects.create(name="Code & Verification")
        self.assertEqual(category.slug, "code-verification")

    def test_auto_slug_handles_mixed_case_and_spaces(self):
        category = ProjectCategory.objects.create(name="  UVM  Testbench  ")
        self.assertEqual(category.slug, "uvm-testbench")

    def test_preset_slug_is_preserved_on_save(self):
        category = ProjectCategory.objects.create(name="Networking", slug="custom-network-slug")
        self.assertEqual(category.slug, "custom-network-slug")

    def test_preset_slug_does_not_change_with_update(self):
        category = ProjectCategory.objects.create(name="Networking", slug="custom-slug")
        category.name = "Updated Name"
        category.save()
        category.refresh_from_db()
        self.assertEqual(category.slug, "custom-slug")

    def test_slug_is_auto_generated_from_updated_name_when_slug_was_blank(self):
        """If slug was blank on first save (auto-generated), changing name should NOT change slug."""
        category = ProjectCategory.objects.create(name="Original")
        original_slug = category.slug
        category.name = "Updated"
        category.save()
        category.refresh_from_db()
        # Slug was populated on first save, so update should preserve it
        self.assertEqual(category.slug, original_slug)

    def test_duplicate_slug_raises_integrity_error(self):
        ProjectCategory.objects.create(name="Networking")
        with self.assertRaises(IntegrityError):
            ProjectCategory.objects.create(name="networking")


class ProjectModelTests(TestCase):
    """Tests for Project auto-slug, __str__, and save behavior."""

    def test_str_returns_name(self):
        project = Project.objects.create(name="AXI VIP")
        self.assertEqual(str(project), "AXI VIP")

    def test_auto_slug_from_name_when_blank(self):
        project = Project.objects.create(name="AXI VIP")
        self.assertEqual(project.slug, "axi-vip")

    def test_auto_slug_slugifies_name_correctly(self):
        project = Project.objects.create(name="DDR Memory Controller Verif")
        self.assertEqual(project.slug, "ddr-memory-controller-verif")

    def test_auto_slug_handles_mixed_case_and_spaces(self):
        project = Project.objects.create(name="  PCIe  Gen5  ")
        self.assertEqual(project.slug, "pcie-gen5")

    def test_preset_slug_is_preserved_on_save(self):
        project = Project.objects.create(name="AXI VIP", slug="my-axi-vip")
        self.assertEqual(project.slug, "my-axi-vip")

    def test_preset_slug_does_not_change_with_update(self):
        project = Project.objects.create(name="AXI VIP", slug="original-slug")
        project.name = "Updated VIP"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.slug, "original-slug")

    def test_slug_is_auto_generated_from_updated_name_when_slug_was_blank(self):
        """If slug was blank on first save (auto-generated), changing name should NOT change slug."""
        project = Project.objects.create(name="Original")
        original_slug = project.slug
        project.name = "Updated"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.slug, original_slug)

    def test_duplicate_slug_raises_integrity_error(self):
        Project.objects.create(name="AXI VIP")
        with self.assertRaises(IntegrityError):
            Project.objects.create(name="AXI-VIP")


class ProjectListViewTests(TestCase):
    """Tests for ProjectListView — filtering, search, and pagination."""

    @classmethod
    def setUpTestData(cls):
        """Create test projects with different statuses."""
        from accounts.models import User

        cls.user = User.objects.create_user(email="listviewer@example.com", username="listviewer", password="password")
        cls.active1 = Project.objects.create(name="AXI VIP", status="active", description="AXI verification IP")
        cls.active2 = Project.objects.create(name="PCIe Controller", status="active", description="PCIe verification")
        cls.on_hold = Project.objects.create(name="DDR Memory", status="on_hold", description="DDR memory controller")
        cls.completed = Project.objects.create(name="USB 3.0", status="completed", description="USB verification")
        cls.archived = Project.objects.create(name="Legacy SPI", status="archived", description="Old SPI project")

    def setUp(self):
        self.client.login(username="listviewer", password="password")

    def test_returns_all_projects_without_filters(self):
        """Unfiltered list returns all projects."""
        response = self.client.get("/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_list.html")
        self.assertEqual(len(response.context["projects"]), 5)

    def test_filter_by_active_status(self):
        """status=active returns only active projects."""
        response = self.client.get("/projects/", {"status": "active"})
        self.assertEqual(response.status_code, 200)
        projects = list(response.context["projects"])
        self.assertEqual(len(projects), 2)
        self.assertIn(self.active1, projects)
        self.assertIn(self.active2, projects)

    def test_filter_by_on_hold_status(self):
        """status=on_hold returns only on-hold projects."""
        response = self.client.get("/projects/", {"status": "on_hold"})
        self.assertEqual(response.status_code, 200)
        projects = list(response.context["projects"])
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], self.on_hold)

    def test_filter_by_completed_status(self):
        """status=completed returns only completed projects."""
        response = self.client.get("/projects/", {"status": "completed"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 1)

    def test_filter_by_archived_status(self):
        """status=archived returns only archived projects."""
        response = self.client.get("/projects/", {"status": "archived"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 1)

    def test_filter_by_nonexistent_status_returns_empty(self):
        """status=nonexistent returns no projects."""
        response = self.client.get("/projects/", {"status": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 0)

    def test_search_by_name_case_insensitive(self):
        """q=axi returns projects matching 'axi' case-insensitively."""
        response = self.client.get("/projects/", {"q": "axi"})
        self.assertEqual(response.status_code, 200)
        projects = list(response.context["projects"])
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], self.active1)

    def test_search_by_partial_name_match(self):
        """q=PCI returns projects with 'PCI' in name."""
        response = self.client.get("/projects/", {"q": "PCI"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 1)
        self.assertEqual(response.context["projects"][0], self.active2)

    def test_search_returns_multiple_matches(self):
        """q=Memory matches multiple projects."""
        response = self.client.get("/projects/", {"q": "Memory"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 1)

    def test_search_returns_no_matches(self):
        """q=nonexistent returns no projects."""
        response = self.client.get("/projects/", {"q": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 0)

    def test_combined_status_and_search_filter(self):
        """Applying both status and q filters returns intersection."""
        response = self.client.get("/projects/", {"status": "active", "q": "AXI"})
        self.assertEqual(response.status_code, 200)
        projects = list(response.context["projects"])
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], self.active1)

    def test_combined_filter_no_overlap(self):
        """status=completed and q=AXI returns nothing (no overlap)."""
        response = self.client.get("/projects/", {"status": "completed", "q": "AXI"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 0)

    def test_context_object_name_is_projects(self):
        """The context variable is named 'projects'."""
        response = self.client.get("/projects/")
        self.assertIn("projects", response.context)

    def test_paginate_by_is_20(self):
        """View paginates by 20 items per page."""
        view = self.client.get("/projects/")
        self.assertEqual(view.context["paginator"].per_page, 20)

    def test_uses_reverse_url(self):
        """Accessing via reverse URL name works."""
        from django.urls import reverse

        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["projects"]), 5)


class ProjectDetailViewTests(TestCase):
    """Tests for ProjectDetailView — stats context data."""

    @classmethod
    def setUpTestData(cls):
        """Create a project with regressions, runs, and milestones."""
        from accounts.models import User
        from milestones.models import Milestone
        from regressions.models import Regression, RegressionRun

        cls.user = User.objects.create_user(email="test@example.com", username="testuser", password="password")
        cls.project = Project.objects.create(name="Test Project", owner=cls.user)

        # Create regressions
        cls.regression1 = Regression.objects.create(
            project=cls.project,
            name="Smoke Suite",
            owner=cls.user,
            is_active=True,
        )
        cls.regression2 = Regression.objects.create(
            project=cls.project,
            name="Full Suite",
            owner=cls.user,
            is_active=True,
        )
        cls.inactive_regression = Regression.objects.create(
            project=cls.project,
            name="Old Suite",
            owner=cls.user,
            is_active=False,
        )

        # Create runs for regression1
        cls.run1_prev = RegressionRun.objects.create(
            regression=cls.regression1,
            run_number=1,
            total_count=100,
            pass_count=80,
            fail_count=20,
            status="completed",
        )
        cls.run1_curr = RegressionRun.objects.create(
            regression=cls.regression1,
            run_number=2,
            total_count=100,
            pass_count=90,
            fail_count=10,
            status="completed",
        )

        # Create runs for regression2
        cls.run2_only = RegressionRun.objects.create(
            regression=cls.regression2,
            run_number=1,
            total_count=50,
            pass_count=50,
            fail_count=0,
            status="completed",
        )

        # Create milestones
        cls.milestone_completed = Milestone.objects.create(
            project=cls.project,
            title="Milestone 1",
            status="completed",
            owner=cls.user,
        )
        cls.milestone_planned = Milestone.objects.create(
            project=cls.project,
            title="Milestone 2",
            status="planned",
            owner=cls.user,
        )
        cls.milestone_in_progress = Milestone.objects.create(
            project=cls.project,
            title="Milestone 3",
            status="in_progress",
            owner=cls.user,
        )

    def setUp(self):
        self.client.login(username="testuser", password="password")

    def test_project_detail_returns_200(self):
        """Project detail page returns 200."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_detail.html")

    def test_project_stats_total_regressions(self):
        """project_stats includes all regressions (active and inactive)."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["total_regressions"], 3)

    def test_project_stats_total_runs(self):
        """project_stats counts all regression runs."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["total_runs"], 3)

    def test_project_stats_pass_percentage(self):
        """project_stats calculates correct pass percentage."""
        # Total: 100 + 100 + 50 = 250 tests
        # Passed: 80 + 90 + 50 = 220
        # 220/250 = 88.00%
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["project_pass_percentage"], "88.00%")

    def test_project_stats_milestones_completed(self):
        """project_stats counts completed milestones."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["milestones_completed"], 1)

    def test_project_stats_total_milestones(self):
        """project_stats counts all milestones."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["total_milestones"], 3)

    def test_project_stats_milestone_progress(self):
        """project_stats shows correct milestone progress string."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["milestone_progress"], "1/3")

    def test_project_context_is_project_object(self):
        """Context 'project' key contains the project instance."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        self.assertEqual(response.context["project"], self.project)

    def test_regression_summaries_present(self):
        """regression_summaries is present and is a list."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        self.assertIsInstance(summaries, list)

    def test_regression_summaries_contains_latest_runs(self):
        """Each regression summary has current and previous runs."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        smoke_summary = next(s for s in summaries if s["regression"] == self.regression1)
        self.assertEqual(smoke_summary["current_run"], self.run1_curr)
        self.assertEqual(smoke_summary["previous_run"], self.run1_prev)

    def test_regression_summaries_single_run_no_previous(self):
        """Regression with only one run has None as previous_run."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        full_summary = next(s for s in summaries if s["regression"] == self.regression2)
        self.assertEqual(full_summary["current_run"], self.run2_only)
        self.assertIsNone(full_summary["previous_run"])

    def test_regression_trend_improved(self):
        """Trend is 'improved' when current pass_rate > previous."""
        # run1_curr: 90%, run1_prev: 80%
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        smoke_summary = next(s for s in summaries if s["regression"] == self.regression1)
        self.assertEqual(smoke_summary["trend"], "improved")

    def test_regression_trend_same_for_single_run(self):
        """Trend is 'same' when there's no previous run."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        full_summary = next(s for s in summaries if s["regression"] == self.regression2)
        self.assertEqual(full_summary["trend"], "same")

    def test_regression_trend_reduced(self):
        """Trend is 'reduced' when current pass_rate < previous."""
        # Make run2 have a second run with worse pass rate
        from regressions.models import RegressionRun

        RegressionRun.objects.create(
            regression=self.regression2,
            run_number=2,
            total_count=50,
            pass_count=30,
            fail_count=20,
            status="completed",
        )
        response = self.client.get(f"/projects/{self.project.slug}/")
        summaries = response.context["regression_summaries"]
        full_summary = next(s for s in summaries if s["regression"] == self.regression2)
        self.assertEqual(full_summary["trend"], "reduced")

    def test_recent_runs_context(self):
        """recent_runs context contains ordered regression runs."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        runs = response.context["recent_runs"]
        self.assertEqual(len(runs), 3)

    def test_milestones_context(self):
        """milestones context contains project milestones."""
        response = self.client.get(f"/projects/{self.project.slug}/")
        milestones = response.context["milestones"]
        self.assertEqual(len(milestones), 3)

    def test_empty_project_stats(self):
        """Stats for a project with no regressions/runs/milestones."""
        empty_project = Project.objects.create(name="Empty Project")
        response = self.client.get(f"/projects/{empty_project.slug}/")
        stats = response.context["project_stats"]
        self.assertEqual(stats["total_regressions"], 0)
        self.assertEqual(stats["total_runs"], 0)
        self.assertEqual(stats["project_pass_percentage"], "0.00%")
        self.assertEqual(stats["milestones_completed"], 0)
        self.assertEqual(stats["total_milestones"], 0)
        self.assertEqual(stats["milestone_progress"], "0/0")

    def test_uses_reverse_url(self):
        """Accessing via reverse URL name works."""
        from django.urls import reverse

        response = self.client.get(reverse("project-detail", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_project_returns_404(self):
        """Requesting a non-existent project slug returns 404."""
        from django.urls import reverse

        response = self.client.get(reverse("project-detail", kwargs={"slug": "nonexistent"}))
        self.assertEqual(response.status_code, 404)


class ProjectCRUDViewTests(TestCase):
    """Tests for ProjectCreateView, ProjectUpdateView, ProjectDeleteView with staff enforcement."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            email="crudstaff@example.com", username="crudstaff", password="password", is_staff=True
        )
        cls.regular = User.objects.create_user(
            email="crudregular@example.com", username="crudregular", password="password", is_staff=False
        )
        cls.project = Project.objects.create(name="CRUD Project", owner=cls.staff, slug="crud-project")

    def setUp(self):
        self.category = ProjectCategory.objects.create(name="Test Category")

    # --- ProjectCreateView ---

    def test_staff_can_access_create_form(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.get(reverse("project-create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_form.html")

    def test_non_staff_blocked_from_create_form(self):
        self.client.login(username="crudregular", password="password")
        response = self.client.get(reverse("project-create"))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_create_project_via_form(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-create"),
            {
                "name": "New Via Form",
                "description": "Created via CRUD test",
                "status": "active",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(name="New Via Form").exists())

    def test_create_project_redirects_to_list(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-create"),
            {
                "name": "Redirect Test",
                "status": "active",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("project-list"))

    def test_create_project_with_new_category(self):
        """Creating a project with a new category name creates the category."""
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-create"),
            {
                "name": "Cat Test Project",
                "description": "",
                "new_category_name": "Brand New Category",
                "status": "active",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProjectCategory.objects.filter(name__iexact="brand new category").exists())

    def test_create_project_form_invalid_shows_errors(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-create"),
            {
                "name": "",
                "status": "active",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "name", "This field is required.")

    def test_create_project_sets_auto_slug(self):
        self.client.login(username="crudstaff", password="password")
        self.client.post(
            reverse("project-create"),
            {
                "name": "Auto Slug Test",
                "status": "active",
                "is_active": "on",
            },
        )
        project = Project.objects.get(name="Auto Slug Test")
        self.assertEqual(project.slug, "auto-slug-test")

    # --- ProjectUpdateView ---

    def test_staff_can_access_update_form(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.get(reverse("project-update", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_form.html")

    def test_non_staff_blocked_from_update_form(self):
        self.client.login(username="crudregular", password="password")
        response = self.client.get(reverse("project-update", kwargs={"slug": self.project.slug}))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_update_project_name(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-update", kwargs={"slug": self.project.slug}),
            {
                "name": "Updated Name",
                "description": self.project.description,
                "status": "active",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated Name")

    def test_update_project_redirects_to_detail(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-update", kwargs={"slug": self.project.slug}),
            {
                "name": "Update Redirect",
                "description": "",
                "status": "active",
                "is_active": "on",
            },
        )
        updated = Project.objects.get(name="Update Redirect")
        self.assertRedirects(response, reverse("project-detail", kwargs={"slug": updated.slug}))

    def test_update_project_preserves_slug(self):
        """Updating name doesn't change the existing slug."""
        original_slug = self.project.slug
        self.client.login(username="crudstaff", password="password")
        self.client.post(
            reverse("project-update", kwargs={"slug": self.project.slug}),
            {
                "name": "Name Changed",
                "description": "",
                "status": "active",
                "is_active": "on",
            },
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.slug, original_slug)

    def test_update_project_form_invalid_shows_errors(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(
            reverse("project-update", kwargs={"slug": self.project.slug}),
            {
                "name": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "name", "This field is required.")

    def test_update_nonexistent_project_returns_404(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.get(reverse("project-update", kwargs={"slug": "nonexistent"}))
        self.assertEqual(response.status_code, 404)

    # --- ProjectDeleteView ---

    def test_staff_can_access_delete_confirmation(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.get(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "projects/project_confirm_delete.html")

    def test_non_staff_blocked_from_delete_confirmation(self):
        self.client.login(username="crudregular", password="password")
        response = self.client.get(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertIn(response.status_code, [302, 403])

    def test_staff_can_delete_project(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_delete_project_redirects_to_list(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.post(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertRedirects(response, reverse("project-list"))

    def test_delete_nonexistent_project_returns_404(self):
        self.client.login(username="crudstaff", password="password")
        response = self.client.get(reverse("project-delete", kwargs={"slug": "nonexistent"}))
        self.assertEqual(response.status_code, 404)

    # --- Unauthenticated access ---

    def test_unauthenticated_blocked_from_create(self):
        response = self.client.get(reverse("project-create"))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_blocked_from_update(self):
        response = self.client.get(reverse("project-update", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_blocked_from_delete(self):
        response = self.client.get(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_cannot_post_create(self):
        response = self.client.post(reverse("project-create"), {"name": "Hacked"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(name="Hacked").exists())

    def test_unauthenticated_cannot_post_update(self):
        response = self.client.post(reverse("project-update", kwargs={"slug": self.project.slug}), {"name": "Hacked"})
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertNotEqual(self.project.name, "Hacked")

    def test_unauthenticated_cannot_post_delete(self):
        response = self.client.post(reverse("project-delete", kwargs={"slug": self.project.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())
