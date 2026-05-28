from django.db import transaction
from django.utils.text import slugify

from common.choices import FailureCategory, ProjectStatus, ResultStatus, RunStatus, TriggerType
from projects.models import Project
from regressions.models import Regression, RegressionRun
from regressions.services import get_next_run_number
from results.models import Result
from results.services import get_or_create_signature, recalculate_run_counters, update_signature_counts


def _choice_value(value, choices, default):
    if not value:
        return default
    valid_values = {choice.value for choice in choices}
    if value not in valid_values:
        raise ValueError(f"Invalid value '{value}'. Expected one of: {', '.join(sorted(valid_values))}.")
    return value


@transaction.atomic
def ingest_run(payload, user):
    project_data = payload["project"]
    regression_data = payload["regression"]
    run_data = payload["run"]
    results_data = payload.get("results", [])

    project_slug = project_data.get("slug") or slugify(project_data["name"])
    project_defaults = {
        "name": project_data["name"],
        "description": project_data.get("description", ""),
        "status": _choice_value(project_data.get("status"), ProjectStatus, ProjectStatus.ACTIVE),
        "repository_url": project_data.get("repository_url", ""),
    }
    project, project_created = Project.objects.update_or_create(slug=project_slug, defaults=project_defaults)

    regression_defaults = {
        "description": regression_data.get("description", ""),
        "default_branch_name": regression_data.get("branch_name", ""),
        "default_suite_name": regression_data.get("suite_name", ""),
        "default_config_name": regression_data.get("config_name", ""),
        "metadata": regression_data.get("metadata", {}),
    }
    regression, regression_created = Regression.objects.update_or_create(
        project=project,
        name=regression_data["name"],
        defaults=regression_defaults,
    )

    run_number = run_data.get("run_number") or get_next_run_number(regression)
    run_defaults = {
        "run_name": run_data.get("run_name", ""),
        "status": _choice_value(run_data.get("status"), RunStatus, RunStatus.COMPLETED),
        "trigger_type": _choice_value(run_data.get("trigger_type"), TriggerType, TriggerType.API),
        "triggered_by": user,
        "branch_name": run_data.get("branch_name", regression.default_branch_name),
        "suite_name": run_data.get("suite_name", regression.default_suite_name),
        "config_name": run_data.get("config_name", regression.default_config_name),
        "build_id": run_data.get("build_id", ""),
        "git_commit": run_data.get("git_commit", ""),
        "start_time": run_data.get("start_time"),
        "end_time": run_data.get("end_time"),
        "notes": run_data.get("notes", ""),
        "metadata": run_data.get("metadata", {}),
    }
    run, run_created = RegressionRun.objects.update_or_create(
        regression=regression,
        run_number=run_number,
        defaults=run_defaults,
    )

    run.results.all().delete()
    run.failure_signatures.all().delete()

    touched_signatures = set()
    for result_data in results_data:
        status = _choice_value(result_data.get("status"), ResultStatus, ResultStatus.UNKNOWN)
        failure_signature = None
        signature_data = result_data.get("failure_signature")
        if signature_data:
            category = _choice_value(signature_data.get("category"), FailureCategory, FailureCategory.UNKNOWN)
            failure_signature, _ = get_or_create_signature(
                run,
                signature_data["title"],
                category=category,
                description=signature_data.get("description", ""),
                is_known_issue=signature_data.get("is_known_issue", False),
                is_infra_issue=signature_data.get("is_infra_issue", False),
            )
            touched_signatures.add(failure_signature.pk)

        Result.objects.create(
            regression_run=run,
            failure_signature=failure_signature,
            test_name=result_data["test_name"],
            status=status,
            seed=result_data.get("seed", ""),
            duration_seconds=result_data.get("duration_seconds"),
            machine_name=result_data.get("machine_name", ""),
            error_message=result_data.get("error_message", ""),
            log_path=result_data.get("log_path", ""),
            wave_path=result_data.get("wave_path", ""),
            artifact_path=result_data.get("artifact_path", ""),
            started_at=result_data.get("started_at"),
            ended_at=result_data.get("ended_at"),
            rerun_index=result_data.get("rerun_index", 0),
            metadata=result_data.get("metadata", {}),
        )

    for signature in run.failure_signatures.filter(pk__in=touched_signatures):
        update_signature_counts(signature)
    recalculate_run_counters(run)
    run.refresh_from_db()

    return {
        "project": project,
        "regression": regression,
        "run": run,
        "created": {
            "project": project_created,
            "regression": regression_created,
            "run": run_created,
        },
        "result_count": len(results_data),
    }
