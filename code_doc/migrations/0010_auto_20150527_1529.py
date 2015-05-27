# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('code_doc', '0009_auto_20150430_1310'),
    ]

    operations = [
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('nr_of_revisions_kept', models.IntegerField(default=15)),
            ],
        ),
        migrations.CreateModel(
            name='Revision',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('revision', models.CharField(max_length=200)),
                ('commit_time', models.DateTimeField(help_text=b'Automatic field that is set when this revision is created', verbose_name=b'Time of creation', auto_now_add=True)),
                ('project', models.ForeignKey(related_name='revisions', to='code_doc.Project')),
            ],
            options={
                'get_latest_by': 'commit_time',
            },
        ),
        migrations.AddField(
            model_name='branch',
            name='revisions',
            field=models.ManyToManyField(related_name='branches', to='code_doc.Revision'),
        ),
        migrations.AddField(
            model_name='artifact',
            name='revision',
            field=models.ForeignKey(related_name='artifacts', blank=True, to='code_doc.Revision', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='revision',
            unique_together=set([('project', 'revision')]),
        ),
    ]
