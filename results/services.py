import hashlib

from django.db import models

from common.utils import normalize_signature


def normalize_and_hash_signature(text):
    normalized = normalize_signature(text)
    signature_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, signature_hash


def get_or_create_signature(
    regression_run, title, category=None, description="", is_known_issue=False, is_infra_issue=False
):
    from .models import FailureSignature

    normalized, signature_hash = normalize_and_hash_signature(title)
    sig, created = FailureSignature.objects.get_or_create(
        regression_run=regression_run,
        signature_hash=signature_hash,
        defaults={
            "signature_title": title,
            "normalized_signature": normalized,
            "category": category or "unknown",
            "description": description,
            "is_known_issue": is_known_issue,
            "is_infra_issue": is_infra_issue,
        },
    )
    return sig, created


def update_signature_counts(signature):
    from .models import Result

    signature.result_count = Result.objects.filter(failure_signature=signature).count()
    signature.save(update_fields=["result_count", "updated_at"])


def recalculate_run_counters(run):
    from common.choices import ResultStatus

    from .models import Result

    counts = Result.objects.filter(regression_run=run).aggregate(
        total=models.Count("id"),
        pass_count=models.Count("id", filter=models.Q(status=ResultStatus.PASS)),
        fail_count=models.Count("id", filter=models.Q(status=ResultStatus.FAIL)),
        timeout_count=models.Count("id", filter=models.Q(status=ResultStatus.TIMEOUT)),
        killed_count=models.Count("id", filter=models.Q(status=ResultStatus.KILLED)),
        skip_count=models.Count("id", filter=models.Q(status=ResultStatus.SKIPPED)),
        unknown_count=models.Count("id", filter=models.Q(status=ResultStatus.UNKNOWN)),
    )
    run.total_count = counts["total"] or 0
    run.pass_count = counts["pass_count"] or 0
    run.fail_count = counts["fail_count"] or 0
    run.timeout_count = counts["timeout_count"] or 0
    run.killed_count = counts["killed_count"] or 0
    run.skip_count = counts["skip_count"] or 0
    run.unknown_count = counts["unknown_count"] or 0
    from common.utils import calculate_pass_rate

    run.pass_rate = calculate_pass_rate(run.pass_count, run.total_count)
    run.save(
        update_fields=[
            "total_count",
            "pass_count",
            "fail_count",
            "timeout_count",
            "killed_count",
            "skip_count",
            "unknown_count",
            "pass_rate",
            "updated_at",
        ]
    )
