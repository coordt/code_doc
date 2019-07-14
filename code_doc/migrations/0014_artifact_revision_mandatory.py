# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


import logging

logger = logging.getLogger(__name__)


def set_default_revision(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Artifact = apps.get_model("code_doc", "Artifact")
    Revision = apps.get_model("code_doc", "Revision")
    for art in Artifact.objects.all():
        art.revision = Revision.objects.create(
            revision=art.md5hash, project=art.project_series_backup.project
        )
        if art.project_series_backup.project is None:
            logger.debug("Project was None")
        art.save()


def set_project_for_artifact(apps, schema_editor):
    Artifact = apps.get_model("code_doc", "Artifact")

    for art in Artifact.objects.all():
        art.project = art.project_series_backup.project
        if art.project_series_backup.project is None:
            logger.debug("Failed to link artifact %s to any project", art)

        art.project_series.add(art.project_series_backup)
        logger.debug(
            "Artifact %s linked to series %s",
            art.artifactfile,
            art.project_series_backup.series,
        )
        art.save()


class Migration(migrations.Migration):

    dependencies = [("code_doc", "0013_artifact_project_series")]

    operations = [
        # Operations for the Revision field of the Artifact
        # First we add data to each revision field
        # Then we set it to be non nullable
        migrations.RunPython(set_default_revision),
        migrations.AlterField(
            model_name="Artifact",
            name="revision",
            field=models.ForeignKey(
                related_name="artifacts",
                blank=False,
                null=False,
                to="code_doc.Revision",
            ),
        ),
        # Operations for the Project field of the Artifact
        # First we add a nullable Field
        # Then we fill in the data
        # Then we change back to non nullable
        migrations.AddField(
            model_name="Artifact",
            name="project",
            field=models.ForeignKey(
                related_name="revisions", blank=True, null=True, to="code_doc.Project"
            ),
        ),
        migrations.RunPython(set_project_for_artifact),
        migrations.AlterField(
            model_name="Artifact",
            name="project",
            field=models.ForeignKey(
                related_name="artifacts", blank=False, null=False, to="code_doc.Project"
            ),
        ),
        # Remove the project_series_backup, the project data was already copied out of it
        # so we don't need it anymore
        migrations.RemoveField(model_name="Artifact", name="project_series_backup"),
    ]
