# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import code_doc.models


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0010_auto_20150430_1617'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='author',
            options={'permissions': (('author_edit', "Can edit the Author's details"),)},
        ),
        migrations.AddField(
            model_name='author',
            name='image',
            field=models.ImageField(null=True, upload_to=code_doc.models.get_author_image_location, blank=True),
        ),
        migrations.AlterField(
            model_name='author',
            name='django_user',
            field=models.OneToOneField(related_name='author', null=True, blank=True, to=settings.AUTH_USER_MODEL, help_text=b'The Django User, this Author is corresponding to.'),
        ),
    ]
