from django.test import TestCase
from django.db import IntegrityError



# Create your tests here.
from django.test import Client
from code_doc.models import Project, Author, ProjectSeries, Artifact
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.files import File

from django.core.urlresolvers import reverse

from django.conf import settings

import tempfile
import tarfile
import os
import datetime


class ProjectSeriesArtifactTest(TestCase):
  def setUp(self):
    # Every test needs a client.
    self.client = Client()

    # path for the queries to the project details
    self.path                   = 'project_artifacts_add'

    self.first_user             = User.objects.create_user(username='toto', password='titi')#, is_active=True)

    self.author1                = Author.objects.create(lastname='1', firstname='1f', gravatar_email='', email='1@1.fr', home_page_url='')
    self.project                = Project.objects.create(name='test_project')
    self.project.authors        = [self.author1]
    self.project.administrators = [self.first_user]

    self.new_series            = ProjectSeries.objects.create(series="12345", project=self.project, release_date=datetime.datetime.now())
    self.new_series.save()

    import StringIO
    self.imgfile      = StringIO.StringIO('GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
    self.imgfile.name = 'test_img_file.gif'

  def test_series_uniqueness(self):
    with self.assertRaises(IntegrityError):
      new_series = ProjectSeries.objects.create(series="12345", project=self.project, release_date=datetime.datetime.now())

  def test_project_revision_artifact_wrong(self):
    """Test if giving the wrong series yields the proper error"""
    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id + 1])
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)
    response = self.client.get(initial_path)
    # 401 because we do not distinguish between an unauthorized access and a malformed url, ON PURPOSE
    self.assertEqual(response.status_code, 401)


  def test_project_revision_artifact_no_anonymous_access(self):
    """Creation of a new project series and its artifacts not allowed for anonymous"""
    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.get(initial_path, follow=False)
    # redirects to login page
    self.assertRedirects(response, reverse('login') + '?next=' + initial_path)
    self.assertEqual(response.status_code, 302)

    response = self.client.get(initial_path, follow=True)
    # redirects to login page
    self.assertRedirects(response, reverse('login') + '?next=' + initial_path)
    self.assertEqual(response.status_code, 200)


  def test_project_revision_artifact_possible_for_admins(self):
    """Creation of a new project series and its artifacts always possible for admins"""
    admin_user = User.objects.create_superuser(username='admin', email = 'bla@bla.com', password='admin')
    response = self.client.login(username='admin', password='admin')
    self.assertTrue(response)

    response = self.client.get(reverse(self.path, args=[self.project.id, self.new_series.id]), follow=False)
    self.assertEqual(response.status_code, 200)

    self.assertEqual(len(response.context['artifacts']), 0)

  def test_send_new_artifact_no_login(self):
    """This test should redirect to the login page: we cannot upload a file without a proper login"""
    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=True)

    self.assertEqual(response.status_code, 200)
    self.assertRedirects(response, reverse('login') + '?next=' + initial_path)

  def test_send_new_artifact_no_login_no_follow(self):
    """This test should indicate that no login means redirection"""
    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)
    self.assertEqual(response.status_code, 302) # redirection status

  def test_send_new_artifact_with_login_malformed(self):
    """Testing the upload capabilities. The returned hash should be ok"""
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    self.assertEqual(self.new_series.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'name': 'fred', 'attachment': self.imgfile},
                     follow=False)

    self.assertEqual(response.status_code, 200)
    self.assertIn('errorlist', response.content)

  def test_send_new_artifact_with_login(self):
    """Testing the upload capabilities. The returned hash should be ok"""
    import hashlib
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    self.assertEqual(self.new_series.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'description': 'blabla',
                      'artifactfile': self.imgfile,
                      'is_documentation' : False},
                     follow=True)
    self.assertNotIn('errorlist', response.content)

    self.assertEqual(self.new_series.artifacts.count(), 1)
    self.assertEqual(response.status_code, 200)
    self.assertIn(hashlib.md5(self.imgfile.getvalue()).hexdigest().upper(), response.content)

  def test_get_all_artifacts_json(self):
    """Tests if the json received by the api view is correct"""

    import hashlib, json
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    self.assertEqual(self.new_series.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'description': 'blabla',
                      'artifactfile': self.imgfile,
                      'is_documentation' : False},
                     follow=True)

    self.assertEqual(self.new_series.artifacts.count(), 1)
    self.assertEqual(response.status_code, 200)

    json_artifact_path = reverse('api_get_artifacts', args=[self.project.id, self.new_series.id])
    response = self.client.get(json_artifact_path)

    dic_ids = json.loads(response.content)
    self.assertEquals(len(dic_ids), 1)
    self.assertEquals(len(dic_ids['artifacts']), 1)
    self.assertTrue(dic_ids['artifacts'].has_key(str(Artifact.objects.first().id)))

    artifact = dic_ids['artifacts'][str(Artifact.objects.first().id)]

    self.assertEquals(artifact['md5'].upper(), hashlib.md5(self.imgfile.getvalue()).hexdigest().upper())


  def test_send_new_artifact_with_login_twice(self):
    """Sending the same file twice should not create a new file"""
    response = self.client.login(username='toto', password='titi')
    self.assertTrue(response)

    self.assertEqual(self.new_series.artifacts.count(), 0)

    initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
    response = self.client.post(initial_path,
                     {'description': 'blabla',
                      'artifactfile': self.imgfile,
                      'is_documentation' : False},
                     follow=True)

    import hashlib
    self.assertEqual(response.status_code, 200)
    self.assertIn(hashlib.md5(self.imgfile.getvalue()).hexdigest().upper(), response.content)

    self.assertEqual(self.new_series.artifacts.count(), 1)

    # warning, the input file here should be reseted to its origin
    self.imgfile.seek(0)

    # second send should not create a new one for a specific revision
    response = self.client.post(initial_path,
                     {'description': 'blabla',
                      'artifactfile': self.imgfile,
                      'is_documentation' : False},
                     follow=True)

    # indicates the conflict
    self.assertEqual(response.status_code, 409)
    self.assertEqual(self.new_series.artifacts.count(), 1)


  def test_create_documentation_artifact(self):
    """Checks if the documentation is properly stored and deflated on the server"""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from code_doc.models import get_deflation_directory
    import shutil

    with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE, suffix='.tar.bz2') as f:
      # create a temporary tar object
      tar = tarfile.open(fileobj=f, mode='w:bz2')

      from inspect import getsourcefile
      source_file = getsourcefile(lambda _: None)

      tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
      tar.close()

      f.seek(0)
      test_file = SimpleUploadedFile('filename.tar.bz2', f.read())


      new_artifact = Artifact.objects.create(
                        project_series=self.new_series,
                        md5hash = '1',
                        description = 'test artifact',
                        is_documentation = True,
                        documentation_entry_file = os.path.basename(__file__),
                        artifactfile = test_file)


      new_artifact.save()

      # not a documentation artifact
      self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

      if(os.path.exists(get_deflation_directory(new_artifact))):
        shutil.rmtree(get_deflation_directory(new_artifact))



  def test_remove_artifact(self):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from code_doc.models import get_deflation_directory
    import shutil

    with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE, suffix='.tar.bz2') as f:
      # create a temporary tar object
      tar = tarfile.open(fileobj=f, mode='w:bz2')

      from inspect import getsourcefile
      source_file = getsourcefile(lambda _: None)

      tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
      tar.close()

      f.seek(0)
      test_file = SimpleUploadedFile('filename.tar.bz2', f.read())


      new_artifact = Artifact.objects.create(
                        project_series=self.new_series,
                        md5hash = '1',
                        description = 'test artifact',
                        is_documentation = False,
                        documentation_entry_file = os.path.basename(__file__),
                        artifactfile = test_file)

      test_file.close()

      # a file has been created
      self.assertTrue(os.path.exists(new_artifact.full_path_name()), "Artifact not existent on disk %s" % new_artifact.full_path_name())

      # not a documentation artifact
      self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

      new_artifact.save()

      # file still here
      self.assertTrue(os.path.exists(new_artifact.full_path_name()), "Artifact not existent on disk %s" % new_artifact.full_path_name())

      self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

      new_artifact.delete()

      self.assertFalse(os.path.exists(new_artifact.full_path_name()))
      self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))




  def test_remove_documentation_artifact(self):
    """Tests that the deflated documentation is removed as well"""
    from django.core.files.uploadedfile import SimpleUploadedFile
    from code_doc.models import get_deflation_directory
    import shutil

    with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE, suffix='.tar.bz2') as f:
      # create a temporary tar object
      tar = tarfile.open(fileobj=f, mode='w:bz2')

      from inspect import getsourcefile
      source_file = getsourcefile(lambda _: None)

      tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
      tar.close()

      f.seek(0)
      test_file = SimpleUploadedFile('filename.tar.bz2', f.read())


      new_artifact = Artifact.objects.create(
                        project_series=self.new_series,
                        md5hash = '1',
                        description = 'test artifact',
                        is_documentation = True,
                        documentation_entry_file = os.path.basename(__file__),
                        artifactfile = test_file)

      test_file.close()

      self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

      new_artifact.save()


      self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

      new_artifact.delete()

      self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))


