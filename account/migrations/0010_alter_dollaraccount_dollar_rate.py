# Generated by Django 4.2.3 on 2025-02-04 20:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0009_dollaraccount_dollar_rate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dollaraccount',
            name='dollar_rate',
            field=models.DecimalField(decimal_places=2, default=87.0, max_digits=12),
        ),
    ]
