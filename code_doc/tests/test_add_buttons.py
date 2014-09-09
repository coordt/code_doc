# this file tests the correct behaviour of the add buttons


from django.test import TestCase
from django.db import IntegrityError

import datetime

# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectVersion
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from django.core.urlresolvers import reverse


class TemplateAddButtonTest(TestCase):
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
    

  def test_add_version_button_enabled(self):
    """Tests the button is enabled for maintainer"""
    from django.template import Context, Template
    
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)    
    
    context = Context({'user' : self.first_user, 'project': self.project})
    rendered = Template(
        '{% load button_add_with_permission %}'
        '{% button_add_version_with_permission user project %}'
    ).render(context)
    self.assertNotIn('disabled', rendered)
    
    
    
  def test_add_version_button_disabled(self):
    """Tests the button is disabled for non maintainer"""
    from django.template import Context, Template
    
    not_allowed_for_project = User.objects.create_user(username='not', password='allowed')
    response = self.client.login(username='not', password='allowed')
    self.assertTrue(response)    
    
    context = Context({'user' : not_allowed_for_project, 'project': self.project})
    rendered = Template(
        '{% load button_add_with_permission %}'
        '{% button_add_version_with_permission user project %}'
    ).render(context)
    self.assertIn('"disabled"', rendered)
    
    
    
    