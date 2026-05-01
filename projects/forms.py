from django import forms

from .models import Project, ProjectCategory


class ProjectForm(forms.ModelForm):
    new_category_name = forms.CharField(
        label="New category",
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            }
        ),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "description",
            "category",
            "new_category_name",
            "owner",
            "status",
            "repository_url",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "owner": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "repository_url": forms.URLInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"}
            ),
        }

    def save(self, commit=True):
        project = super().save(commit=False)
        new_category_name = self.cleaned_data.get("new_category_name", "").strip()
        if new_category_name:
            category = ProjectCategory.objects.filter(name__iexact=new_category_name).first()
            if category is None:
                category = ProjectCategory.objects.create(name=new_category_name)
            project.category = category

        if commit:
            project.save()
            self.save_m2m()

        return project
