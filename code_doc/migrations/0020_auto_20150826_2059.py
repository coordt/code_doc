# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0019_auto_20150826_1431")]

    operations = [
        migrations.AlterField(
            model_name="projectseries",
            name="perms_users_artifacts_add",
            field=models.ManyToManyField(
                related_name="perms_users_artifacts_add",
                to=settings.AUTH_USER_MODEL,
                blank=True,
            ),
        )
    ]
