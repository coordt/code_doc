# this file tests the correct behaviour of the add buttons


from django.test import TestCase

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectSeries
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse


class TemplateAddButtonTest(TestCase):
    def setUp(self):
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project_revisions_all'

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

        not_allowed_for_project = User.objects.create_user(username='not', password='allowed')
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
