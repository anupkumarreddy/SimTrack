
from django.db.models import Max
from .models import RegressionRun

def get_next_run_number(regression):
    max_num = RegressionRun.objects.filter(regression=regression).aggregate(Max('run_number'))['run_number__max']
    return (max_num or 0) + 1
