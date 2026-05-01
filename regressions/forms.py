from django import forms

from .models import Regression, RegressionRun


class RegressionForm(forms.ModelForm):
    class Meta:
        model = Regression
        fields = [
            "project",
            "name",
            "description",
            "is_active",
            "owner",
            "default_branch_name",
            "default_suite_name",
            "default_config_name",
            "metadata",
        ]
        widgets = {
            "project": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
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
            "is_active": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"}
            ),
            "owner": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "default_branch_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "default_suite_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "default_config_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "metadata": forms.HiddenInput(),
        }


class RegressionRunForm(forms.ModelForm):
    class Meta:
        model = RegressionRun
        fields = [
            "regression",
            "run_name",
            "status",
            "trigger_type",
            "branch_name",
            "suite_name",
            "config_name",
            "build_id",
            "git_commit",
            "start_time",
            "end_time",
            "notes",
            "metadata",
        ]
        widgets = {
            "regression": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "run_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "trigger_type": forms.Select(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "branch_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "suite_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "config_name": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "build_id": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "git_commit": forms.TextInput(
                attrs={
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                }
            ),
            "start_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
                }
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm",
                }
            ),
            "metadata": forms.HiddenInput(),
        }
