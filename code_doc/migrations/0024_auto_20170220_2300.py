# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-02-20 23:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


import logging
logger = logging.getLogger(__name__)


def move_repository_url(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Project = apps.get_model("code_doc", "Project")
    ProjectRepository = apps.get_model("code_doc", "ProjectRepository")
    db_alias = schema_editor.connection.alias

    for project in Project.objects.all():
        if project.code_source_url.strip():
            repository = ProjectRepository.objects.create(project=project,
                                                          code_source_url=project.code_source_url.strip())


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0023_auto_20160408_1829'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectRepository',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_source_url', models.CharField(max_length=500)),
            ],
        ),

        migrations.AddField(
            model_name='projectrepository',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repositories', to='code_doc.Project'),
        ),

        # Operations for moving the repository URL prior to deleting it
        migrations.RunPython(
            move_repository_url,
        ),

        migrations.RemoveField(
            model_name='project',
            name='code_source_url',
        ),

    ]
