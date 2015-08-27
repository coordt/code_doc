# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0017_auto_20150730_1354'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'permissions': (('project_view', 'User/group can see the project'), ('project_administrate', 'User/group administrates the project'), ('project_series_add', 'User/group can add a series to the project'), ('project_series_delete', 'User/group can delete a series from the project'), ('project_artifact_add', 'Can add an artifact to the project'))},
        ),
        migrations.AlterModelOptions(
            name='projectseries',
            options={'permissions': (('series_view', 'User/group has access to this serie and its content'), ('series_edit', 'User/group can edit the definition of this series'), ('series_artifact_add', 'User/group is allowed to add an artifact'), ('series_artifact_delete', 'User/group is allowed to delete an artifact'))},
        ),
    ]
