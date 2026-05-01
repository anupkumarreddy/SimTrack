from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Result
from .services import recalculate_run_counters, update_signature_counts


@receiver(post_save, sender=Result)
def result_post_save(sender, instance, created, **kwargs):
    if instance.regression_run:
        recalculate_run_counters(instance.regression_run)
    if instance.failure_signature:
        update_signature_counts(instance.failure_signature)


@receiver(post_delete, sender=Result)
def result_post_delete(sender, instance, **kwargs):
    if instance.regression_run:
        recalculate_run_counters(instance.regression_run)
    if instance.failure_signature:
        update_signature_counts(instance.failure_signature)
