# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0010_auto_20150528_1058'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='project_series',
            field=models.ManyToManyField(related_name='artifacts', to='code_doc.ProjectSeries'),
        ),
    ]
