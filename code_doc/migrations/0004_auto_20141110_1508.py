# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0003_auto_20141107_1708'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='description',
        ),
        migrations.RemoveField(
            model_name='projectversion',
            name='description',
        ),
        migrations.RemoveField(
            model_name='topic',
            name='description',
        ),
    ]
