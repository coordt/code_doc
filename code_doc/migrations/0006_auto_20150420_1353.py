# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0005_auto_20141204_2201")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="gravatar_email",
            field=models.CharField(max_length=50, blank=True),
        ),
        migrations.AlterField(
            model_name="copyrightholder",
            name="year",
            field=models.IntegerField(default=2015),
        ),
    ]
