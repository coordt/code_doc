from django.test import TestCase
from django.db import IntegrityError

from django.test import Client
from code_doc.models import Project, Author, ProjectSeries, Artifact
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse

import datetime


class ProjectTest(TestCase):
    """Tests on the project objects"""
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project'

        self.first_user = User.objects.create_user(username='toto')

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

    def test_project_details(self):
        """Tests the project detail view"""
        response = self.client.get(reverse(self.path, args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['authors']), len(self.project.authors.all()))

        # non existing project
        response = self.client.get(reverse(self.path, args=[self.project.id+1]))
        self.assertEqual(response.status_code, 404)

    def test_project_administrator(self):
        """Tests if the admins only have the right to modify the project configuration"""

        # user2 is not admin
        user2 = User.objects.create_user(username='user2', password='user2')

        self.assertFalse(self.project.has_user_project_series_add_permission(user2))
        self.assertTrue(self.project.has_user_project_series_add_permission(self.first_user))

    def test_project_get_number_of_revisions(self):
        """Number of revisions tests"""
        self.assertEqual(self.project.get_number_of_revisions(), 0)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        self.assertEqual(self.project.get_number_of_revisions(), 1)

    def test_project_get_number_of_files(self):
        """Number of files tests"""

        self.assertEqual(self.project.get_number_of_files(), 0)

        new_series = ProjectSeries.objects.create(series="1234", project=self.project,
                                                  release_date=datetime.datetime.now())
        new_artifact = Artifact.objects.create(project_series=new_series, md5hash='0')

        self.assertEqual(self.project.get_number_of_files(), 1)

        new_artifact2 = Artifact.objects.create(project_series=new_series, md5hash='1')
        self.assertEqual(self.project.get_number_of_files(), 2)
