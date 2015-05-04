# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0009_auto_20150430_1310'),
    ]

    operations = [
        migrations.CreateModel(
            name='Revision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('branch', models.CharField(max_length=50)),
                ('date_of_creation', models.DateTimeField(help_text=b'Automatic field that is set when this revision is created', verbose_name=b'Time of creation', auto_now_add=True)),
            ],
            options={
                'get_latest_by': 'date_of_creation',
            },
        ),
        migrations.AddField(
            model_name='artifact',
            name='revision',
            field=models.ForeignKey(related_name='artifacts', blank=True, to='code_doc.Revision', null=True),
        ),
    ]
