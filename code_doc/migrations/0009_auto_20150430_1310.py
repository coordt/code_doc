# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('code_doc', '0008_auto_20150420_1404'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='django_user',
            field=models.OneToOneField(related_name='author', null=True, blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='author',
            name='email',
            field=models.EmailField(max_length=50, db_index=True),
        ),
    ]
