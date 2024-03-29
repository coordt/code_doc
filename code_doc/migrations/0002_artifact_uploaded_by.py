# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="artifact",
            name="uploaded_by",
            field=models.CharField(
                help_text=b"User/agent uploading the file",
                max_length=50,
                null=True,
                blank=True,
            ),
            preserve_default=True,
        )
    ]
