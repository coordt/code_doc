# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-08-04 14:15
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0026_auto_20170220_2323'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='projectseries',
            options={'permissions': (('series_view', 'User/group has access to this series and its content'), ('series_edit', 'User/group can edit the definition of this series'), ('series_artifact_add', 'User/group is allowed to add an artifact'), ('series_artifact_delete', 'User/group is allowed to delete an artifact')), 'verbose_name_plural': 'Project series'},
        ),
        migrations.AlterModelOptions(
            name='revision',
            options={'get_latest_by': 'commit_time', 'permissions': (('revision_view', 'User/group has access to this revision and its content'),), 'verbose_name_plural': 'Project revision'},
        ),
    ]