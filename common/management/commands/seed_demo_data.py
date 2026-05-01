import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import User
from common.choices import (
    FailureCategory,
    MilestoneStatus,
    Priority,
    ProjectStatus,
    ResultStatus,
    RunStatus,
    TriggerType,
)
from milestones.models import Milestone, MilestoneUpdate
from projects.models import Project, ProjectCategory
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result
from results.services import get_or_create_signature, recalculate_run_counters, update_signature_counts


class Command(BaseCommand):
    help = "Seed demo data for SimTrack"

    def add_arguments(self, parser):
        parser.add_argument(
            "--small",
            action="store_true",
            help="Create a compact demo dataset for tests and quick local smoke checks.",
        )

    def handle(self, *args, **options):
        small = options["small"]
        self.stdout.write("Creating demo data...")

        # Create users
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@simtrack.local",
                "full_name": "Admin User",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if _:
            admin.set_password("admin")
            admin.save()
        user1, _ = User.objects.get_or_create(
            username="engineer1", defaults={"email": "eng1@simtrack.local", "full_name": "Engineer One"}
        )
        if _:
            user1.set_password("password")
            user1.save()
        user2, _ = User.objects.get_or_create(
            username="engineer2", defaults={"email": "eng2@simtrack.local", "full_name": "Engineer Two"}
        )
        if _:
            user2.set_password("password")
            user2.save()

        # Create project categories
        vip_category, _ = ProjectCategory.objects.get_or_create(
            slug="verification-ip",
            defaults={
                "name": "Verification IP",
                "description": "Reusable verification IP and protocol components.",
            },
        )
        controller_category, _ = ProjectCategory.objects.get_or_create(
            slug="controller",
            defaults={
                "name": "Controller",
                "description": "Controller design and verification projects.",
            },
        )
        subsystem_category, _ = ProjectCategory.objects.get_or_create(
            slug="subsystem",
            defaults={
                "name": "Subsystem",
                "description": "Integrated subsystem-level verification projects.",
            },
        )

        # Create projects
        project_specs = [
            ("AXI VIP", "AXI verification IP project", vip_category, user1, ProjectStatus.ACTIVE),
            ("PCIe Controller", "PCIe controller verification", controller_category, user2, ProjectStatus.ACTIVE),
            ("Memory Subsystem", "Memory subsystem verification", subsystem_category, user1, ProjectStatus.ON_HOLD),
            ("USB4 PHY", "USB4 physical layer verification", vip_category, user2, ProjectStatus.ACTIVE),
            ("Ethernet MAC", "Ethernet MAC regression tracking", controller_category, user1, ProjectStatus.ACTIVE),
            ("RISC-V Core", "Processor core verification", controller_category, user2, ProjectStatus.ACTIVE),
            ("AI Accelerator", "Accelerator subsystem verification", subsystem_category, user1, ProjectStatus.ACTIVE),
            ("Display Pipeline", "Display and compositor validation", subsystem_category, user2, ProjectStatus.ACTIVE),
            (
                "Security Engine",
                "Crypto and secure boot verification",
                controller_category,
                user1,
                ProjectStatus.ACTIVE,
            ),
            ("NoC Fabric", "Network-on-chip fabric verification", subsystem_category, user2, ProjectStatus.ACTIVE),
        ]
        if small:
            project_specs = project_specs[:1]
        projects = []
        for name, description, category, owner, status in project_specs:
            slug = slugify(name)
            project, _ = Project.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "category": category,
                    "owner": owner,
                    "status": status,
                    "repository_url": f"https://github.com/example/{slug}",
                },
            )
            update_fields = []
            for field, value in [
                ("name", name),
                ("description", description),
                ("category", category),
                ("owner", owner),
                ("status", status),
            ]:
                if getattr(project, field) != value:
                    setattr(project, field, value)
                    update_fields.append(field)
            if update_fields:
                project.save(update_fields=update_fields + ["updated_at"])
            projects.append(project)

        # Create milestones
        for index, project in enumerate(projects, start=1):
            for milestone_index in range(1, 4):
                pct = min(100, max(5, (index * 9 + milestone_index * 17) % 115))
                status = (
                    MilestoneStatus.COMPLETED
                    if pct == 100
                    else random.choice(
                        [
                            MilestoneStatus.PLANNED,
                            MilestoneStatus.IN_PROGRESS,
                            MilestoneStatus.BLOCKED,
                            MilestoneStatus.DELAYED,
                        ]
                    )
                )
                title = f"{project.name} Milestone {milestone_index}"
                ms, created = Milestone.objects.get_or_create(
                    project=project,
                    title=title,
                    defaults={
                        "description": f"Milestone {milestone_index} for {project.name}",
                        "status": status,
                        "priority": random.choice([Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]),
                        "owner": random.choice([user1, user2, None]),
                        "target_date": timezone.now().date() + timedelta(days=milestone_index * 14),
                        "completion_percentage": pct,
                    },
                )
                if created:
                    MilestoneUpdate.objects.create(milestone=ms, comment="Initial milestone created.", updated_by=user1)

        # Create regressions
        regression_kinds = [
            ("Smoke", "smoke", "main"),
            ("Nightly", "nightly", "main"),
            ("Stress", "stress", "main"),
            ("Protocol", "protocol", "develop"),
            ("Performance", "perf", "develop"),
            ("Power", "power", "main"),
            ("Reset", "reset", "main"),
            ("Error Injection", "error-injection", "feature-error"),
            ("Coverage", "coverage", "coverage"),
            ("Long Haul", "long-haul", "main"),
        ]
        regressions = []
        if small:
            regression_kinds = regression_kinds[:1]
        for project in projects:
            for kind, suite, branch in regression_kinds:
                name = f"{project.name} {kind}"
                reg, _ = Regression.objects.get_or_create(
                    project=project,
                    name=name,
                    defaults={
                        "description": f"{kind} regression for {project.name}",
                        "is_active": True,
                        "owner": random.choice([user1, user2]),
                        "default_branch_name": branch,
                        "default_suite_name": suite,
                        "default_config_name": "default",
                    },
                )
                regressions.append(reg)
        regressions = list(Regression.objects.select_related("project").all())

        # Create runs and results
        test_names = [
            "test_basic_read",
            "test_basic_write",
            "test_burst_transfer",
            "test_error_injection",
            "test_reset_sequence",
            "test_concurrent_access",
            "test_bandwidth",
            "test_latency",
            "test_boundary",
            "test_random_stress",
        ]
        error_messages = [
            "Assertion failed: expected data mismatch",
            "Timeout waiting for ready signal",
            "UVM_ERROR: driver returned error status",
            "Config mismatch: register value incorrect",
            "Simulation killed due to memory limit",
            "Protocol violation detected on channel A",
        ]
        signatures_pool = [
            ("Data Mismatch", FailureCategory.DESIGN),
            ("Timeout Error", FailureCategory.TIMEOUT),
            ("UVM Driver Error", FailureCategory.INFRA),
            ("Config Error", FailureCategory.CONFIG),
            ("Protocol Violation", FailureCategory.DESIGN),
            ("Memory Limit Kill", FailureCategory.INFRA),
        ]

        now = timezone.now()
        runs_per_regression = 2 if small else 30
        for reg_index, reg in enumerate(regressions):
            run_dates = []
            current_date = (now - timedelta(days=55 + (reg_index % 5))).replace(
                hour=1, minute=30, second=0, microsecond=0
            )
            for _run_idx in range(1, runs_per_regression + 1):
                run_dates.append(current_date)
                current_date += timedelta(days=random.choice([1, 1, 1, 2, 2, 3]))

            for run_idx, run_date in enumerate(run_dates, start=1):
                total_count = random.randint(6, 10) if small else random.randint(28, 52)
                pass_bias = 62 + (run_idx * 0.9) + random.randint(-10, 10)
                pass_count = max(0, min(total_count, int(total_count * pass_bias / 100)))
                remaining = total_count - pass_count
                fail_count = random.randint(0, remaining) if remaining else 0
                remaining -= fail_count
                timeout_count = random.randint(0, remaining) if remaining else 0
                remaining -= timeout_count
                killed_count = random.randint(0, remaining) if remaining else 0
                remaining -= killed_count
                skip_count = random.randint(0, remaining) if remaining else 0
                unknown_count = remaining - skip_count
                run_status = (
                    RunStatus.COMPLETED
                    if fail_count == 0 and timeout_count == 0 and killed_count == 0
                    else random.choice([RunStatus.COMPLETED, RunStatus.PARTIAL, RunStatus.FAILED])
                )

                run, created = RegressionRun.objects.get_or_create(
                    regression=reg,
                    run_number=run_idx,
                    defaults={
                        "run_name": f"Nightly {run_idx}",
                        "status": run_status,
                        "trigger_type": random.choice([TriggerType.SCHEDULED, TriggerType.SCHEDULED, TriggerType.CI]),
                        "triggered_by": random.choice([user1, user2, None]),
                        "branch_name": reg.default_branch_name,
                        "suite_name": reg.default_suite_name,
                        "config_name": reg.default_config_name,
                        "build_id": f"build-{random.randint(1000, 9999)}",
                        "git_commit": f"abc{random.randint(10000, 99999)}",
                        "start_time": run_date,
                        "end_time": run_date + timedelta(minutes=random.randint(25, 180)),
                        "total_count": total_count,
                        "pass_count": pass_count,
                        "fail_count": fail_count,
                        "timeout_count": timeout_count,
                        "killed_count": killed_count,
                        "skip_count": skip_count,
                        "unknown_count": unknown_count,
                        "notes": "Auto-generated demo run.",
                    },
                )
                if created:
                    RegressionRun.objects.filter(pk=run.pk).update(created_at=run_date, updated_at=run_date)

                # Create results for this run
                if run.results.exists():
                    recalculate_run_counters(run)
                    continue
                statuses = (
                    [ResultStatus.PASS] * pass_count
                    + [ResultStatus.FAIL] * fail_count
                    + [ResultStatus.TIMEOUT] * timeout_count
                    + [ResultStatus.KILLED] * killed_count
                    + [ResultStatus.SKIPPED] * skip_count
                    + [ResultStatus.UNKNOWN] * unknown_count
                )
                random.shuffle(statuses)
                touched_signatures = set()
                result_rows = []
                for res_idx, status in enumerate(statuses, start=1):
                    sig = None
                    if status == ResultStatus.FAIL:
                        sig_title, sig_cat = random.choice(signatures_pool)
                        sig, _ = get_or_create_signature(run, sig_title, category=sig_cat)
                        touched_signatures.add(sig.pk)

                    result_rows.append(
                        Result(
                            regression_run=run,
                            failure_signature=sig,
                            test_name=random.choice(test_names) + f"_{res_idx}",
                            status=status,
                            seed=str(random.randint(1, 999999)),
                            duration_seconds=random.randint(1, 300),
                            machine_name=f"runner-{random.randint(1, 5)}",
                            error_message=random.choice(error_messages) if status != ResultStatus.PASS else "",
                            log_path=f"/logs/{run.id}/{res_idx}.log",
                            wave_path=f"/waves/{run.id}/{res_idx}.vcd",
                            artifact_path=f"/artifacts/{run.id}/{res_idx}/",
                            started_at=run.start_time,
                            ended_at=run.end_time,
                            rerun_index=0,
                        )
                    )
                Result.objects.bulk_create(result_rows, batch_size=500)
                for sig in FailureSignature.objects.filter(pk__in=touched_signatures):
                    update_signature_counts(sig)

        self.stdout.write(self.style.SUCCESS("Demo data created successfully."))
