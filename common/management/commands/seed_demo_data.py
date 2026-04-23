
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from projects.models import Project
from milestones.models import Milestone, MilestoneUpdate
from regressions.models import Regression, RegressionRun
from results.models import FailureSignature, Result
from results.services import get_or_create_signature
from common.choices import ProjectStatus, MilestoneStatus, Priority, RunStatus, TriggerType, ResultStatus, FailureCategory

class Command(BaseCommand):
    help = 'Seed demo data for SimTrack'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')

        # Create users
        admin, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@simtrack.local', 'full_name': 'Admin User', 'is_staff': True, 'is_superuser': True})
        if _:
            admin.set_password('admin')
            admin.save()
        user1, _ = User.objects.get_or_create(username='engineer1', defaults={'email': 'eng1@simtrack.local', 'full_name': 'Engineer One'})
        if _:
            user1.set_password('password')
            user1.save()
        user2, _ = User.objects.get_or_create(username='engineer2', defaults={'email': 'eng2@simtrack.local', 'full_name': 'Engineer Two'})
        if _:
            user2.set_password('password')
            user2.save()

        # Create projects
        p1, _ = Project.objects.get_or_create(slug='axi-vip', defaults={'name': 'AXI VIP', 'description': 'AXI verification IP project', 'owner': user1, 'status': ProjectStatus.ACTIVE, 'repository_url': 'https://github.com/example/axi-vip'})
        p2, _ = Project.objects.get_or_create(slug='pcie-controller', defaults={'name': 'PCIe Controller', 'description': 'PCIe controller verification', 'owner': user2, 'status': ProjectStatus.ACTIVE, 'repository_url': 'https://github.com/example/pcie-controller'})
        p3, _ = Project.objects.get_or_create(slug='memory-subsystem', defaults={'name': 'Memory Subsystem', 'description': 'Memory subsystem verification', 'owner': user1, 'status': ProjectStatus.ON_HOLD})

        projects = [p1, p2, p3]

        # Create milestones
        milestones_data = [
            ('AXI VIP', p1, MilestoneStatus.IN_PROGRESS, Priority.HIGH, 65),
            ('PCIe Bringup', p2, MilestoneStatus.PLANNED, Priority.CRITICAL, 10),
            ('Memory Tuning', p3, MilestoneStatus.DELAYED, Priority.MEDIUM, 30),
            ('Regression Cleanup', p1, MilestoneStatus.COMPLETED, Priority.LOW, 100),
            ('Tool Migration', p2, MilestoneStatus.BLOCKED, Priority.HIGH, 40),
        ]
        for title, project, status, priority, pct in milestones_data:
            ms, created = Milestone.objects.get_or_create(project=project, title=title, defaults={
                'description': f'Milestone for {title}',
                'status': status,
                'priority': priority,
                'owner': random.choice([user1, user2, None]),
                'target_date': timezone.now().date(),
                'completion_percentage': pct,
            })
            if created:
                MilestoneUpdate.objects.create(milestone=ms, comment='Initial milestone created.', updated_by=user1)

        # Create regressions
        regression_defs = [
            (p1, 'AXI Smoke', 'Basic AXI smoke tests', 'main', 'smoke', 'default'),
            (p1, 'AXI Stress', 'AXI stress tests', 'main', 'stress', 'default'),
            (p1, 'AXI Protocol', 'AXI protocol checker tests', 'develop', 'protocol', 'default'),
            (p2, 'PCIe Smoke', 'PCIe smoke tests', 'main', 'smoke', 'default'),
            (p2, 'PCIe LTSSM', 'PCIe LTSSM tests', 'main', 'ltssm', 'default'),
            (p2, 'PCIe DMA', 'PCIe DMA tests', 'feature-dma', 'dma', 'default'),
            (p3, 'DDR Smoke', 'DDR smoke tests', 'main', 'smoke', 'default'),
        ]
        regressions = []
        for project, name, desc, branch, suite, config in regression_defs:
            reg, _ = Regression.objects.get_or_create(project=project, name=name, defaults={
                'description': desc,
                'is_active': True,
                'created_by': random.choice([user1, user2]),
                'default_branch_name': branch,
                'default_suite_name': suite,
                'default_config_name': config,
            })
            regressions.append(reg)

        # Create runs and results
        test_names = ['test_basic_read', 'test_basic_write', 'test_burst_transfer', 'test_error_injection', 'test_reset_sequence', 'test_concurrent_access', 'test_bandwidth', 'test_latency', 'test_boundary', 'test_random_stress']
        error_messages = [
            'Assertion failed: expected data mismatch',
            'Timeout waiting for ready signal',
            'UVM_ERROR: driver returned error status',
            'Config mismatch: register value incorrect',
            'Simulation killed due to memory limit',
            'Protocol violation detected on channel A',
        ]
        signatures_pool = [
            ('Data Mismatch', FailureCategory.DESIGN),
            ('Timeout Error', FailureCategory.TIMEOUT),
            ('UVM Driver Error', FailureCategory.INFRA),
            ('Config Error', FailureCategory.CONFIG),
            ('Protocol Violation', FailureCategory.DESIGN),
            ('Memory Limit Kill', FailureCategory.INFRA),
        ]

        for reg in regressions:
            num_runs = random.randint(3, 8)
            for run_idx in range(1, num_runs + 1):
                run, _ = RegressionRun.objects.get_or_create(regression=reg, run_number=run_idx, defaults={
                    'run_name': f'Nightly {run_idx}',
                    'status': random.choice([RunStatus.COMPLETED, RunStatus.PARTIAL, RunStatus.FAILED]),
                    'trigger_type': random.choice([TriggerType.SCHEDULED, TriggerType.MANUAL, TriggerType.CI]),
                    'triggered_by': random.choice([user1, user2, None]),
                    'branch_name': reg.default_branch_name,
                    'suite_name': reg.default_suite_name,
                    'config_name': reg.default_config_name,
                    'build_id': f'build-{random.randint(1000, 9999)}',
                    'git_commit': f'abc{random.randint(10000, 99999)}',
                    'start_time': timezone.now(),
                    'end_time': timezone.now(),
                    'notes': 'Auto-generated demo run.',
                })

                # Create results for this run
                num_results = random.randint(15, 40)
                for res_idx in range(num_results):
                    status = random.choices(
                        [ResultStatus.PASS, ResultStatus.FAIL, ResultStatus.TIMEOUT, ResultStatus.KILLED, ResultStatus.SKIPPED, ResultStatus.UNKNOWN],
                        weights=[70, 15, 5, 3, 4, 3]
                    )[0]

                    sig = None
                    if status == ResultStatus.FAIL:
                        sig_title, sig_cat = random.choice(signatures_pool)
                        sig, _ = get_or_create_signature(run, sig_title, category=sig_cat)

                    Result.objects.create(
                        regression_run=run,
                        failure_signature=sig,
                        test_name=random.choice(test_names) + f'_{res_idx}',
                        status=status,
                        seed=str(random.randint(1, 999999)),
                        duration_seconds=random.randint(1, 300),
                        machine_name=f'runner-{random.randint(1, 5)}',
                        error_message=random.choice(error_messages) if status != ResultStatus.PASS else '',
                        log_path=f'/logs/{run.id}/{res_idx}.log',
                        wave_path=f'/waves/{run.id}/{res_idx}.vcd',
                        artifact_path=f'/artifacts/{run.id}/{res_idx}/',
                        started_at=timezone.now(),
                        ended_at=timezone.now(),
                        rerun_index=0,
                    )

        self.stdout.write(self.style.SUCCESS('Demo data created successfully.'))
