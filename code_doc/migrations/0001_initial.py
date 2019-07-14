# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import code_doc.models.artifacts


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Artifact",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("md5hash", models.CharField(max_length=1024)),
                (
                    "description",
                    models.TextField(
                        max_length=1024, verbose_name=b"description of the artifact"
                    ),
                ),
                (
                    "artifactfile",
                    models.FileField(
                        help_text=b"the artifact file that will be stored on the server",
                        upload_to=code_doc.models.artifacts.get_artifact_location,
                    ),
                ),
                (
                    "is_documentation",
                    models.BooleanField(
                        default=False,
                        help_text=b"Check if the artifact contains a documentation that should be processed by the server",
                    ),
                ),
                (
                    "documentation_entry_file",
                    models.CharField(
                        help_text=b"the documentation entry file if the artifact is documentation type, relative to the root of the deflated package",
                        max_length=255,
                        null=True,
                        blank=True,
                    ),
                ),
                (
                    "upload_date",
                    models.DateTimeField(
                        help_text=b"Automatic field that indicates the file upload time",
                        null=True,
                        verbose_name=b"Upload date",
                        blank=True,
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Author",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("lastname", models.CharField(max_length=50)),
                ("firstname", models.CharField(max_length=50)),
                ("gravatar_email", models.CharField(max_length=50)),
                ("email", models.EmailField(unique=True, max_length=50, db_index=True)),
                ("home_page_url", models.CharField(max_length=250)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Copyright",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("content", models.TextField(max_length=2500)),
                ("url", models.CharField(max_length=50)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="CopyrightHolder",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("year", models.IntegerField(default=2014)),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(unique=True, max_length=50)),
                (
                    "description",
                    models.TextField(
                        max_length=2500, null=True, verbose_name=b"hidden", blank=True
                    ),
                ),
                (
                    "short_description",
                    models.TextField(
                        max_length=200,
                        null=True,
                        verbose_name=b"short description of the project (200 chars)",
                        blank=True,
                    ),
                ),
                (
                    "description_mk",
                    models.TextField(
                        max_length=2500,
                        null=True,
                        verbose_name=b"text in Markdown",
                        blank=True,
                    ),
                ),
                (
                    "icon",
                    models.ImageField(
                        null=True, upload_to=b"project_icons/", blank=True
                    ),
                ),
                ("slug", models.SlugField()),
                (
                    "home_page_url",
                    models.CharField(max_length=250, null=True, blank=True),
                ),
                (
                    "code_source_url",
                    models.CharField(max_length=250, null=True, blank=True),
                ),
                (
                    "administrators",
                    models.ManyToManyField(
                        to=settings.AUTH_USER_MODEL, null=True, blank=True
                    ),
                ),
                ("authors", models.ManyToManyField(to="code_doc.Author")),
                (
                    "copyright",
                    models.ForeignKey(blank=True, to="code_doc.Copyright", null=True),
                ),
                (
                    "copyright_holder",
                    models.ManyToManyField(
                        to="code_doc.CopyrightHolder", null=True, blank=True
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("project_view", "Can see the project"),
                    ("project_administrate", "Can administrate the project"),
                )
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="ProjectVersion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("version", models.CharField(max_length=500)),
                ("release_date", models.DateField(verbose_name=b"Release date")),
                ("is_public", models.BooleanField(default=False)),
                (
                    "description",
                    models.TextField(
                        max_length=500, verbose_name=b"Description of the version"
                    ),
                ),
                (
                    "description_mk",
                    models.TextField(
                        max_length=200,
                        null=True,
                        verbose_name=b"Description in Markdown format",
                        blank=True,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(related_name="versions", to="code_doc.Project"),
                ),
                (
                    "view_artifacts_groups",
                    models.ManyToManyField(
                        related_name="view_artifact_groups",
                        null=True,
                        to="auth.Group",
                        blank=True,
                    ),
                ),
                (
                    "view_artifacts_users",
                    models.ManyToManyField(
                        related_name="view_artifact_users",
                        null=True,
                        to=settings.AUTH_USER_MODEL,
                        blank=True,
                    ),
                ),
                (
                    "view_groups",
                    models.ManyToManyField(
                        related_name="view_groups",
                        null=True,
                        to="auth.Group",
                        blank=True,
                    ),
                ),
                (
                    "view_users",
                    models.ManyToManyField(
                        related_name="view_users",
                        null=True,
                        to=settings.AUTH_USER_MODEL,
                        blank=True,
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("version_view", "User of group has access to this revision"),
                    (
                        "version_artifacts_view",
                        "Access to the artifacts of this revision",
                    ),
                )
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name="Topic",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=20)),
                (
                    "description",
                    models.TextField(max_length=200, null=True, blank=True),
                ),
                (
                    "description_mk",
                    models.TextField(
                        max_length=200,
                        null=True,
                        verbose_name=b"Description in Markdown format",
                        blank=True,
                    ),
                ),
            ],
            options={},
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name="projectversion", unique_together=set([("project", "version")])
        ),
        migrations.AddField(
            model_name="project",
            name="topics",
            field=models.ManyToManyField(to="code_doc.Topic", null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="artifact",
            name="project_version",
            field=models.ForeignKey(
                related_name="artifacts", to="code_doc.ProjectVersion"
            ),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name="artifact", unique_together=set([("project_version", "md5hash")])
        ),
    ]
