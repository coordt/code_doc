# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('code_doc', '0018_auto_20150826_1419'),
    ]

    operations = [

        migrations.RenameField(
            model_name='projectseries',
            old_name='view_artifacts_groups',
            new_name='perms_groups_artifacts_add',
        ),

        migrations.AlterField(
            model_name='projectseries',
            name='perms_groups_artifacts_add',
            field=models.ManyToManyField(to='auth.Group', blank=True, related_name='perms_groups_artifacts_add'),
        ),

        migrations.RenameField(
            model_name='projectseries',
            old_name='view_artifacts_users',
            new_name='perms_users_artifacts_add',
        ),

        migrations.AlterField(
            model_name='projectseries',
            name='perms_users_artifacts_add',
            field=models.ManyToManyField(to='auth.Group', blank=True, related_name='perms_users_artifacts_add'),
        ),

        migrations.AddField(
            model_name='projectseries',
            name='perms_groups_artifacts_del',
            field=models.ManyToManyField(to='auth.Group', blank=True, related_name='perms_groups_artifacts_del'),
        ),
        migrations.AddField(
            model_name='projectseries',
            name='perms_users_artifacts_del',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True, related_name='perms_users_artifacts_del'),
        ),
    ]
