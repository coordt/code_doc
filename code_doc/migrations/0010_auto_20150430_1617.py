# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0009_auto_20150430_1310")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="home_page_url",
            field=models.CharField(max_length=250, blank=True),
        )
    ]
