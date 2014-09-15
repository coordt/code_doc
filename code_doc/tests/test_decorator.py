# this file tests the correct behaviour of the decorators


from django.test import TestCase
from django.test import RequestFactory
from django.core.exceptions import PermissionDenied

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse

from code_doc.permissions.decorators import permission_required_on_object


class DecoratorSimpleTest(TestCase):
  def setUp(self):
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project_revisions_all'
    
    # dummy setup
    self.first_user             = User.objects.create_user(username='toto', password='titi')
    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]
    
    self.project_getter         = lambda : self.project
    
    self.factory                = RequestFactory()

  def test_non_existing_permission(self):
    """Tests the response in case of non managed permission"""
    
    @permission_required_on_object(('code_doc.non_existing_permission',), self.project_getter)
    def internal_test_func(request):
      return True
    
    request = self.factory.get('nothing')
    request.user = self.first_user
    self.assertTrue(internal_test_func(request))

  def test_project_administrate_permission(self):
    """Tests the response for administrators"""
    
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
    
    @permission_required_on_object(('code_doc.project_administrate',), self.project_getter, raise_exception = True)
    def toto_func(request):
      return True
    
    request = self.factory.get('nothing')
    request.user = user2
        
    with self.assertRaises(PermissionDenied):
      toto_func(request)
    
