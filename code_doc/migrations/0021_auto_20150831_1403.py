# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0020_auto_20150826_2059'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='branch',
            name='nr_of_revisions_kept',
        ),
        migrations.AddField(
            model_name='branch',
            name='nb_revisions_to_keep',
            field=models.IntegerField(default=None, null=True, verbose_name=b'default number of revisions to keep. Overrides the projects and series default', blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='nb_revisions_to_keep',
            field=models.IntegerField(default=None, null=True, verbose_name=b'default number of revisions to keep', blank=True),
        ),
        migrations.AddField(
            model_name='projectseries',
            name='nb_revisions_to_keep',
            field=models.IntegerField(default=None, null=True, verbose_name=b'default number of revisions to keep. Overrides the projects default', blank=True),
        ),
    ]
