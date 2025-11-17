# Generated manually for SumUp payment polling system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_sumupcheckout_checkout_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='sumupcheckout',
            name='should_poll',
            field=models.BooleanField(default=True, help_text='Whether this checkout should be polled for status updates'),
        ),
        migrations.AddField(
            model_name='sumupcheckout',
            name='polling_started_at',
            field=models.DateTimeField(blank=True, help_text='When polling started for this checkout', null=True),
        ),
        migrations.AddField(
            model_name='sumupcheckout',
            name='last_polled_at',
            field=models.DateTimeField(blank=True, help_text='Last time we checked the payment status', null=True),
        ),
        migrations.AddField(
            model_name='sumupcheckout',
            name='poll_count',
            field=models.IntegerField(default=0, help_text="Number of times we've polled this checkout"),
        ),
        migrations.AddField(
            model_name='sumupcheckout',
            name='max_poll_duration_minutes',
            field=models.IntegerField(default=120, help_text='Maximum duration to poll this checkout (in minutes)'),
        ),
        migrations.AddIndex(
            model_name='sumupcheckout',
            index=models.Index(fields=['status', 'should_poll', 'last_polled_at'], name='payments_su_status_idx'),
        ),
    ]
