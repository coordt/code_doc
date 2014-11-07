# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0002_artifact_uploaded_by'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'permissions': (('project_view', 'Can see the project'), ('project_administrate', 'Can administrate the project'), ('project_version_add', 'Can add a version to the project'), ('project_artifact_add', 'Can add an artifact to the project'))},
        ),
        migrations.AlterModelOptions(
            name='projectversion',
            options={'permissions': (('version_view', 'User of group has access to this revision'), ('version_edit', 'User can edit the content of this version'), ('version_artifact_view', 'Access to the artifacts of this revision'))},
        ),
    ]
