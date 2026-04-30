from django.test import TestCase

from .forms import ProjectForm
from .models import ProjectCategory


class ProjectFormTests(TestCase):
    def test_save_creates_new_category_from_name(self):
        form = ProjectForm(data={
            'name': 'Ethernet MAC',
            'description': 'Ethernet controller verification',
            'new_category_name': 'Networking',
            'status': 'active',
            'repository_url': '',
            'is_active': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.category.name, 'Networking')
        self.assertEqual(ProjectCategory.objects.filter(name='Networking').count(), 1)

    def test_save_reuses_existing_category_from_name(self):
        category = ProjectCategory.objects.create(name='Controller')
        form = ProjectForm(data={
            'name': 'USB Controller',
            'description': 'USB controller verification',
            'new_category_name': 'controller',
            'status': 'active',
            'repository_url': '',
            'is_active': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.category, category)
        self.assertEqual(ProjectCategory.objects.filter(name__iexact='controller').count(), 1)
