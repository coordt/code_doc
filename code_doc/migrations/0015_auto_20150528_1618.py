# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0014_artifact_revision_mandatory")]

    operations = [
        migrations.AlterField(
            model_name="author",
            name="email",
            field=models.EmailField(unique=True, max_length=50, db_index=True),
        ),
        migrations.AlterUniqueTogether(
            name="artifact", unique_together=set([("project", "md5hash")])
        ),
    ]
