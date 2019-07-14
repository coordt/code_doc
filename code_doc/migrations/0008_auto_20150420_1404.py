# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0007_auto_20150420_1355")]

    operations = [
        migrations.AlterModelOptions(
            name="project",
            options={
                "permissions": (
                    ("project_view", "Can see the project"),
                    ("project_administrate", "Can administrate the project"),
                    ("project_series_add", "Can add a series to the project"),
                    ("project_artifact_add", "Can add an artifact to the project"),
                )
            },
        ),
        migrations.AlterModelOptions(
            name="projectseries",
            options={
                "permissions": (
                    ("series_view", "User of group has access to this revision"),
                    ("series_edit", "User can edit the content of this series"),
                    (
                        "series_artifact_view",
                        "Access to the artifacts of this revision",
                    ),
                )
            },
        ),
        migrations.RenameField(
            model_name="artifact", old_name="project_version", new_name="project_series"
        ),
        migrations.RenameField(
            model_name="projectseries", old_name="version", new_name="series"
        ),
        migrations.AlterField(
            model_name="projectseries",
            name="project",
            field=models.ForeignKey(related_name="series", to="code_doc.Project"),
        ),
        migrations.AlterUniqueTogether(
            name="artifact", unique_together=set([("project_series", "md5hash")])
        ),
        migrations.AlterUniqueTogether(
            name="projectseries", unique_together=set([("project", "series")])
        ),
    ]
