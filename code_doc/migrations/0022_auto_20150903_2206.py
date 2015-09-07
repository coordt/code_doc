# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0021_auto_20150831_1403'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artifact',
            name='description',
            field=models.TextField(max_length=1024, null=True, verbose_name=b'description of the artifact', blank=True),
        ),

        migrations.AlterField(
            model_name='artifact',
            name='uploaded_by',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text=b'User/agent uploading the file', null=True),
        ),
    ]
