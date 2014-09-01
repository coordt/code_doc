from django.test import TestCase
from django.db import IntegrityError

from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse



class ProjectTest(TestCase):
  """Tests on the project objects"""
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project'
    
    self.first_user             = User.objects.create(username='toto')

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
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
    user2 = User.objects.create(username='user2', password='user2')
    
    self.assertFalse(self.project.has_version_add_permissions(user2))
    self.assertTrue(self.project.has_version_add_permissions(self.first_user))
    
    
    