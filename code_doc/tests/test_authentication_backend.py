# this file tests the correct behaviour of the authentication backend
# this one is used for permissions management

from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import AnonymousUser

import datetime

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..models.revisions import Revision
from ..models.artifacts import Artifact


class AuthenticationBackendTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='toto', password='titi', email="b@b.com")

    def test_authenticate_existing_user(self):
        """Authenticate an existing user"""
        self.assertTrue(self.client.login(username='toto', password='titi'))

    def test_authenticate_existing_user_wrong_password(self):
        """Authenticate an existing user wrong password should not throw"""
        self.assertFalse(self.client.login(username='toto', password='wrong'))

    def test_authenticate_non_existing_user(self):
        """Tries to authenticate an non existing user, the backend should not throw"""
        self.assertFalse(self.client.login(username='non', password='existing'))

    def test_authenticate_group(self):
        """Test the authentication backend with group"""
        newgroup = Group.objects.create(name='group1')
        self.user.groups.add(newgroup)

        self.assertFalse(self.client.login(username='group1', password=''))
        self.assertTrue(self.client.login(username='toto', password='titi'))


class PermissionBackendTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.first_user = User.objects.create_user(username='toto', password='titi', email="b@b.com")  # , is_active=True)

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

        self.new_series = ProjectSeries.objects.create(series="12345", project=self.project,
                                                       release_date=datetime.datetime.now())

        self.revision = Revision.objects.create(revision='revision', project=self.project)

        self.art1 = Artifact.objects.create(project=self.project,
                                            revision=self.revision,
                                            md5hash='1',
                                            artifactfile='blabla')

    def test_administrator_has_proper_permissions(self):
        """Test the permissions of administrators"""
        self.assertTrue(self.first_user.has_perm('code_doc.project_administrate', self.project))

    def test_administrator_has_proper_permissions_no_object(self):
        """Test the permissions of administrators"""
        self.assertFalse(self.first_user.has_perm('code_doc.project_administrate'))

    def test_non_existing_permissions(self):
        self.assertFalse(self.first_user.has_perm('code_doc.non_existing', self.project))

    def test_all_permissions_user(self):
        self.assertIn('code_doc.project_administrate',
                      self.first_user.get_all_permissions(self.project))
        self.assertNotIn('code_doc.project_administrate', self.first_user.get_all_permissions())

        user2 = User.objects.create_user(username='user2', password='user2', email="c@c.com")
        self.assertNotIn('code_doc.project_administrate', user2.get_all_permissions(self.project))
        self.assertNotIn('code_doc.project_administrate', user2.get_all_permissions())

    def test_anonymous_user_permission_non_public_object(self):
        anon_user = AnonymousUser()

        # anon user cannot administrate
        self.assertFalse(anon_user.has_perm('code_doc.project_administrate', self.project))

        # anon user cannot access non-public series
        self.assertFalse(anon_user.has_perm('code_doc.series_view', self.new_series))

        # anon user cannot access corresponding revision
        self.art1.project_series = [self.new_series]
        self.assertFalse(anon_user.has_perm('code_doc.revision_view', self.revision))

    def test_anonymous_user_permission_public_object(self):
        anon_user = AnonymousUser()

        public_series = ProjectSeries.objects.create(series="public",
                                                     project=self.project,
                                                     release_date=datetime.datetime.now(),
                                                     is_public=True)
        # anon user can access public series
        self.assertTrue(anon_user.has_perm('code_doc.series_view', public_series))

        # anon user cannot access corresponding revision
        self.art1.project_series = [public_series]
        self.assertTrue(anon_user.has_perm('code_doc.revision_view', self.revision))
