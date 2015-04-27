# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0006_auto_20150420_1353'),
    ]

    operations = [
        migrations.RenameModel('ProjectVersion', 'ProjectSeries')
    ]
