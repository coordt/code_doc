# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0004_auto_20141110_1508")]

    operations = [
        migrations.AlterField(
            model_name="projectversion",
            name="description_mk",
            field=models.TextField(
                max_length=2500,
                null=True,
                verbose_name=b"Description in Markdown format",
                blank=True,
            ),
            preserve_default=True,
        )
    ]
