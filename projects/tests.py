from django.db import IntegrityError
from django.test import TestCase

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
