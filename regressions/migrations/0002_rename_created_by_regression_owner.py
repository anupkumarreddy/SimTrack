from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('regressions', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='regression',
            old_name='created_by',
            new_name='owner',
        ),
    ]
