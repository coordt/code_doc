# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0016_auto_20150730_1351")]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="administrators",
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True),
        ),
        migrations.AlterField(
            model_name="project",
            name="copyright_holder",
            field=models.ManyToManyField(to="code_doc.CopyrightHolder", blank=True),
        ),
        migrations.AlterField(
            model_name="project",
            name="topics",
            field=models.ManyToManyField(to="code_doc.Topic", blank=True),
        ),
        migrations.AlterField(
            model_name="projectseries",
            name="view_artifacts_groups",
            field=models.ManyToManyField(
                related_name="view_artifact_groups", to="auth.Group", blank=True
            ),
        ),
        migrations.AlterField(
            model_name="projectseries",
            name="view_artifacts_users",
            field=models.ManyToManyField(
                related_name="view_artifact_users",
                to=settings.AUTH_USER_MODEL,
                blank=True,
            ),
        ),
        migrations.AlterField(
            model_name="projectseries",
            name="view_groups",
            field=models.ManyToManyField(
                related_name="view_groups", to="auth.Group", blank=True
            ),
        ),
        migrations.AlterField(
            model_name="projectseries",
            name="view_users",
            field=models.ManyToManyField(
                related_name="view_users", to=settings.AUTH_USER_MODEL, blank=True
            ),
        ),
    ]
