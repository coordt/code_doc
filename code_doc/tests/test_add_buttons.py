# this file tests the correct behaviour of the add buttons

from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

import datetime

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author


class TemplateAddButtonTest(TestCase):

    def setUp(self):
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project_series_all'

        # dummy setup
        self.first_user = User.objects.create_user(username='toto', password='titi',
                                                   first_name='toto', last_name='titi',
                                                   email='blah@blah.org')
        self.admin_user = User.objects.create_superuser(username='admin',
                                                        email='blah@blah.com',
                                                        password='test')
        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

    def test_add_series_button_enabled(self):
        """Tests the button is enabled for maintainer"""
        from django.template import Context, Template

        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        context = Context({'user': self.first_user, 'project': self.project})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_add_series_with_permission user project %}'
        ).render(context)
        self.assertNotIn('disabled', rendered)

    def test_add_series_button_disabled(self):
        """Tests the button is disabled for non maintainer"""
        from django.template import Context, Template

        not_allowed_for_project = User.objects.create_user(username='not', password='allowed', email="a@a.com")
        response = self.client.login(username='not', password='allowed')
        self.assertTrue(response)

        context = Context({'user': not_allowed_for_project, 'project': self.project})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_add_series_with_permission user project %}'
        ).render(context)
        self.assertIn('"disabled"', rendered)

    def test_edit_author_button_enabled_for_admin(self):
        """Tests that the button is enabled for admins."""
        from django.template import Context, Template

        response = self.client.login(username='admin', password='test')
        self.assertTrue(response)

        context = Context({'user': self.admin_user, 'author': self.author1})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_edit_author_with_permission user author %}'
        ).render(context)
        self.assertNotIn('disabled', rendered)

    def test_edit_author_button_enabled_for_non_admin(self):
        """Tests that the button is enabled for the User corresponding to
           the Author.
        """
        from django.template import Context, Template

        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        context = Context({'user': self.first_user, 'author': self.first_user.author})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_edit_author_with_permission user author %}'
        ).render(context)
        self.assertNotIn('disabled', rendered)

    def test_edit_author_button_disabled(self):
        """Tests that the button is disabled for a User that is not an
           administrator or linked to the Author.
        """
        from django.template import Context, Template

        not_allowed = User.objects.create_user(username='not', password='allowed')
        response = self.client.login(username='not', password='allowed')
        self.assertTrue(response)

        context = Context({'user': not_allowed, 'author': self.first_user.author})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_edit_author_with_permission user author %}'
        ).render(context)
        self.assertIn('disabled', rendered)


class TemplateSeriesAddButtonTest(TestCase):

    def setUp(self):
        self.client = Client()

        # dummy setup
        self.first_user = User.objects.create_user(username='toto', password='titi',
                                                   first_name='toto', last_name='titi',
                                                   email='blah@blah.org')
        self.project = Project.objects.create(name='test_project')
        self.project.administrators = [self.first_user]

        self.series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                   release_date=datetime.datetime.now())

        self.test_user = User.objects.create_user(username='dirk', password='41', email='dirk@mavs.com')

        # path for the queries to the series details
        self.url = reverse('project_series', args=[self.project.id, self.series.id])

    def test_add_artifact_button_enabled(self):
        """Tests the button is enabled for user with the corresponding permission."""
        from django.template import Context, Template

        response = self.client.login(username='dirk', password='41')
        self.assertTrue(response)

        # Give dirk view permissions only
        self.series.view_users.add(self.test_user)
        self.series.perms_users_artifacts_add.add(self.test_user)
        self.assertTrue(self.series.has_user_series_artifact_add_permission(self.test_user))

        # Check state of the button
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        context = Context({'user': self.test_user, 'series': self.series})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_add_artifact_with_permission user series %}'
        ).render(context)
        self.assertNotIn('disabled', rendered)

    def test_add_artifact_button_disabled(self):
        """Tests the button is enabled for user without the corresponding permission."""
        from django.template import Context, Template

        response = self.client.login(username='dirk', password='41')
        self.assertTrue(response)

        # Give dirk view permissions only
        self.series.view_users.add(self.test_user)
        self.assertFalse(self.series.has_user_series_artifact_add_permission(self.test_user))

        # Check state of the button
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        context = Context({'user': self.test_user, 'series': self.series})
        rendered = Template(
            '{% load button_add_with_permission %}'
            '{% button_add_artifact_with_permission user series %}'
        ).render(context)
        self.assertIn('disabled', rendered)

