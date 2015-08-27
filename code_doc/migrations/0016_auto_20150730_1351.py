# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0015_auto_20150528_1618'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artifact',
            name='revision',
            field=models.ForeignKey(related_name='artifacts', blank=True, to='code_doc.Revision', null=True),
        ),
    ]
