from django.test import TestCase
from django.db import IntegrityError

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse


class ProjectVersionTest(TestCase):
  """Testing the project version functionality"""
  def setUp(self):
    # Every test needs a client.
    self.client = Client()
    
    # path for the queries to the project details
    self.path                   = 'project_version_all'
    
    self.first_user             = User.objects.create_user(username='test_version_user', password='test_version_user')

    self.author1                = Author.objects.create(lastname='1', firstname= '1f', gravatar_email = '', email = '1@1.fr', home_page_url = '')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]  
  
  def test_project_version_empty(self):
    """Tests if the project version is ok"""

    # test non existing project 
    response = self.client.get(reverse(self.path, args=[self.project.id + 1]))
    self.assertEqual(response.status_code, 404)
    
    # test existing project
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 0)
    
  def test_project_version_create_new(self):
    """Test the creation of a new project version"""
    
    new_version = ProjectVersion.objects.create(version="1234", project = self.project, release_date = datetime.datetime.now())    
    response = self.client.get(reverse(self.path, args=[self.project.id]))
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.context['versions']), 1)
  
  
  def test_project_version_addview(self):
    """Test the view access of an existing project"""
    
    response = self.client.login(username='test_version_user', password='test_version_user')
    self.assertTrue(response)
    response = self.client.get(reverse("project_version_add", args=[self.project.id]))
    self.assertEqual(response.status_code, 200)

  def test_project_version_addview_non_existing(self):
    """Test the view access of an non existing project"""
    
    response = self.client.login(username='test_version_user', password='test_version_user')
    self.assertTrue(response)    
    response = self.client.get(reverse("project_version_add", args=[self.project.id+1]))
    self.assertEqual(response.status_code, 404)
     
  
  def test_project_version_addview_restrictions(self):
    """Tests if the admins only have the right to modify the project configuration, and the others don't"""
    
    # user2 is not admin of this project
    user2 = User.objects.create_user(username='user2', password='user2')
    response = self.client.login(username='user2', password='user2')
    self.assertTrue(response)
    response = self.client.get(reverse("project_version_add", args=[self.project.id]))
    self.assertEqual(response.status_code, 401)