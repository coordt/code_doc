# this file tests the correct behaviour of the decorators


from django.test import TestCase
from django.test import RequestFactory
from django.core.exceptions import PermissionDenied

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectSeries
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse

from code_doc.permissions.decorators import permission_required_on_object


class DecoratorSimpleTest(TestCase):
    def setUp(self):
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project_revisions_all'

        # dummy setup
        self.first_user = User.objects.create_user(username='toto', password='titi')
        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

        # self.project_getter = lambda : self.project

        self.factory = RequestFactory()

    def project_getter(self, request, *args, **kwargs):
        return self.project

    def test_non_existing_permission(self):
        """in case of non managed permission, the suer has never access"""

        @permission_required_on_object(('code_doc.non_existing_permission',), self.project_getter)
        def internal_test_func(request):
            return True

        request = self.factory.get('nothing')
        request.user = self.first_user

        with self.assertRaises(PermissionDenied):
            internal_test_func(request)

    def test_project_administrate_permission(self):
        """Administrators have all permissions"""

        @permission_required_on_object(('code_doc.project_administrate',), self.project_getter)
        def internal_test_func(request):
            return True

        request = self.factory.get('nothing')
        request.user = self.first_user
        self.assertTrue(internal_test_func(request))

    def test_project_administrate_permission_non_access(self):
        """Tests the response of a non admin user against admin only functions"""
        # user2 is not admin of this project
        user2 = User.objects.create_user(username='user2', password='user2')

        @permission_required_on_object(('code_doc.project_administrate',),
                                       self.project_getter,
                                       raise_exception=True)
        def toto_func(request):
            return True

        request = self.factory.get('nothing')
        request.user = user2

        with self.assertRaises(PermissionDenied):
            toto_func(request)

    def test_decorator_handling_error_function(self):
        """Tests the response of a non admin user against admin only functions"""
        # user2 is not admin of this project
        user2 = User.objects.create_user(username='user2', password='user2')

        def error_handler(obj):
            return "my error handler"

        @permission_required_on_object(('code_doc.project_administrate',),
                                       self.project_getter,
                                       raise_exception=True,
                                       handle_access_error=error_handler)
        def toto_func(request):
            return True

        request = self.factory.get('nothing')
        request.user = self.first_user

        self.assertTrue(toto_func(request))

        request = self.factory.get('nothing')
        request.user = user2

        self.assertEqual(toto_func(request), "my error handler")
