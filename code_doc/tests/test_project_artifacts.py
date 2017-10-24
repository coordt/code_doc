from django.test import TestCase
from django.db import IntegrityError
from django.test import Client
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.conf import settings

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..models.artifacts import Artifact, get_deflation_directory
from ..models.revisions import Revision, Branch


import tempfile
import tarfile
import os
import datetime


class ProjectSeriesArtifactTest(TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = 'project_artifacts_add'

        self.first_user = User.objects.create_user(username='toto', password='titi', email="b@b.com")  # , is_active=True)

        self.author1 = Author.objects.create(lastname='1', firstname='1f', gravatar_email='',
                                             email='1@1.fr', home_page_url='')
        self.project = Project.objects.create(name='test_project')
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

        self.new_series = ProjectSeries.objects.create(series="12345", project=self.project,
                                                       release_date=datetime.datetime.now())
        self.revision = Revision.objects.create(project=self.project, revision="FEDABC")

        import StringIO
        self.imgfile = StringIO.StringIO('GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        self.imgfile.name = 'test_img_file1.gif'
        self.imgfile1 = StringIO.StringIO('GIF87a\x11\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        self.imgfile1.name = 'test_img_file1.gif'
        self.imgfile2 = StringIO.StringIO('GIF87a\x10\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')
        self.imgfile2.name = 'test_img_file2.gif'

    def create_artifact_file(self, file_to_add=None, is_documentation=False):
        """Utility for creating a tar in memory"""
        from StringIO import StringIO
        from inspect import getsourcefile

        f = StringIO()

        if is_documentation:
            # in case of a documentation artifact, we tar the content
            # create a temporary tar object
            tar = tarfile.open(fileobj=f, mode='w:bz2')

            if file_to_add is not None:
                info = tarfile.TarInfo(name='myfile')
                info.size = len(file_to_add.read())
                file_to_add.seek(0)
                tar.addfile(tarinfo=info,
                            fileobj=file_to_add)
                source_file = 'myfile'
            else:
                source_file = getsourcefile(lambda _: None)
                tar.add(os.path.abspath(source_file),
                        arcname=os.path.basename(source_file))

                dummy = tarfile.TarInfo('basename2')
                dummy.type = tarfile.DIRTYPE
                tar.addfile(dummy)
                tar.add(os.path.abspath(source_file),
                        arcname='basename/' + os.path.basename(source_file) + '2')

                source_file = os.path.basename(source_file)
            tar.close()
        else:
            if file_to_add is not None:
                source_file = 'myfile'
                f.write(file_to_add.read())
            else:
                source_file = getsourcefile(lambda _: None)
                f.write(open(source_file, "rb").read())

        f.seek(0)
        return f, source_file

    def test_series_uniqueness(self):
        with self.assertRaises(IntegrityError):
            ProjectSeries.objects.create(series="12345", project=self.project,
                                         release_date=datetime.datetime.now())

    def test_project_series_artifact_wrong_id(self):
        """Test if giving the wrong series yields the proper error"""
        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id + 1])
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)
        response = self.client.get(initial_path)
        # 401 because we do not distinguish between an unauthorized access and a malformed url,
        # ON PURPOSE
        self.assertEqual(response.status_code, 401)

    def test_project_series_artifact_no_anonymous_access(self):
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

    def test_project_series_artifact_possible_for_admins(self):
        """Creation of a new project series and its artifacts always possible for admins"""
        _ = User.objects.create_superuser(username='admin',
                                          email='bla@bla.com',
                                          password='admin')
        response = self.client.login(username='admin', password='admin')
        self.assertTrue(response)

        response = self.client.get(reverse(self.path, args=[self.project.id, self.new_series.id]),
                                   follow=False)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['artifacts']), 0)

    def test_send_new_artifact_no_login(self):
        """This test should redirect to the login page:
            we cannot upload a file without a proper login"""
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
        self.assertEqual(response.status_code, 302)  # redirection status

    def test_send_new_artifact_with_login_malformed(self):
        """Testing the upload capabilities: malformed form filling should not yield an access error
        but an error message"""
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        self.assertEqual(self.new_series.artifacts.count(), 0)

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        response = self.client.post(initial_path,
                                    {'name': 'fred'},  # , 'attachment': self.imgfile}, # attachement missing while required
                                    follow=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn('errorlist', response.content)

    def test_send_new_artifact_with_login(self):
        """Testing the upload capabilities. The returned hash should be ok"""
        import hashlib
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        self.assertEqual(self.new_series.artifacts.count(), 0)

        f, _ = self.create_artifact_file()

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': f,
                                     'is_documentation': False,
                                     'branch': 'blahblah',
                                     'revision': 'blah'},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('errorlist', response.content)

        # Test that the on the fly generation was successfull and that
        # the new artifact properly references the Revision.
        self.assertEqual(self.new_series.artifacts.count(), 1)
        self.assertEqual(Revision.objects.count(), 2)  # self.revision and revision 'blah'
        self.assertEqual(Branch.objects.count(), 1)

        artifact = self.new_series.artifacts.all()[0]
        revision = Revision.objects.get(revision='blah')
        branch = Branch.objects.get(name='blahblah')

        self.assertEqual(artifact.project_series.count(), 1)
        self.assertEqual(artifact.project_series.all()[0], self.new_series)
        self.assertEqual(artifact.revision, revision)

        # Check if the Revision is referenced by the correct branch and project
        self.assertEqual(artifact.revision.project, self.project)
        self.assertIn(branch, artifact.revision.branches.all())

        # Check the response content
        f.seek(0)
        self.assertIn(hashlib.md5(f.read()).hexdigest().upper(), response.content)

    def test_get_all_artifacts_json(self):
        """Tests if the json received by the api view is correct"""

        import hashlib
        import json
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        self.assertEqual(self.new_series.artifacts.count(), 0)

        art = self.create_artifact_file(file_to_add=self.imgfile)[0]
        art.name = 'f1'

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)

        self.assertEqual(self.new_series.artifacts.count(), 1)
        self.assertEqual(response.status_code, 200)

        json_artifact_path = reverse('api_get_artifacts',
                                     args=[self.project.id, self.new_series.id])
        response = self.client.get(json_artifact_path)

        dic_ids = json.loads(response.content)
        self.assertEquals(len(dic_ids), 1)
        self.assertEquals(len(dic_ids['artifacts']), 1)
        self.assertIn(str(Artifact.objects.first().id), dic_ids['artifacts'])

        artifact_dict_entry = dic_ids['artifacts'][str(Artifact.objects.first().id)]

        artifact_object = Artifact.objects.get(md5hash=artifact_dict_entry['md5'])

        # Test that the on the fly generation was successfull and that
        # the new artifact properly references the Revision.
        self.assertEqual(Revision.objects.count(), 2)  # self.revision and revision 'blah1'
        self.assertEqual(Branch.objects.count(), 1)

        revision = Revision.objects.get(revision='blah1')
        branch = Branch.objects.get(name='blah')

        # self.fail(artifact)
        self.assertEqual(artifact_object.project_series.count(), 1)
        self.assertEqual(artifact_object.project_series.all()[0], self.new_series)
        self.assertEqual(artifact_object.revision, revision)

        # Check if the Revision is referenced by the correct branch and project
        self.assertEqual(artifact_object.revision.project, self.project)
        self.assertIn(branch, artifact_object.revision.branches.all())

        art.seek(0)
        self.assertEquals(artifact_dict_entry['md5'].upper(),
                          hashlib.md5(art.read()).hexdigest().upper())

    def test_revision_and_branch_creation_on_artifact_upload(self):
        """Test if the on-the-fly Revision and Branch generation works, when we upload an Artifact
        """

        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        f, _ = self.create_artifact_file()

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': f,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        try:
            Revision.objects.get(revision='blah1')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] The Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] The Revisions returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        try:
            Branch.objects.get(name='blah')
        except Branch.DoesNotExist:
            self.fail("[Branch.DoesNotExist] The Branches returned no object from the get query")
        except Branch.MultipleObjectsReturned:
            self.fail("[Branch.MultipleObjectsReturned] The Branches returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        # We tested that this get returns exactly 1 element.
        branch = Branch.objects.get(name='blah')
        self.assertEqual(branch.revisions.count(), 1)

    def test_multiple_upload_of_artifacts_for_same_branch(self):
        """Tests if we can upload multiple revisions for the same branch
        """
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])

        art = self.create_artifact_file(file_to_add=self.imgfile)[0]
        art.name = 'f1'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        art = self.create_artifact_file(file_to_add=self.imgfile1)[0]
        art.name = 'f2'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah2'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        art = self.create_artifact_file(file_to_add=self.imgfile2)[0]
        art.name = 'f3'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah3'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        try:
            Revision.objects.get(revision='blah1')
            Revision.objects.get(revision='blah2')
            Revision.objects.get(revision='blah3')
        except Revision.DoesNotExist:
            self.fail("[DoesNotExist] One of the Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[MultipleObjectsReturned] One of the Revisions returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        try:
            Branch.objects.get(name='blah')
        except Branch.DoesNotExist:
            self.fail("[Branch.DoesNotExist] The Branches returned no object from the get query")
        except Branch.MultipleObjectsReturned:
            self.fail("[Branch.MultipleObjectsReturned] The Branches returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        # Returns exactly one element
        branch = Branch.objects.get(name='blah')

        self.assertEqual(branch.revisions.count(), 3)
        self.assertEqual(Branch.objects.count(), 1)

    def test_multiple_upload_of_artifacts_for_same_revision(self):
        """Tests if we can upload multiple Artifacts for the same revision
        """
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        art = self.create_artifact_file(file_to_add=self.imgfile)[0]
        art.name = 'f1'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        art = self.create_artifact_file(file_to_add=self.imgfile1)[0]
        art.name = 'f2'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        art = self.create_artifact_file(file_to_add=self.imgfile2)[0]
        art.name = 'f3'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     },
                                    follow=True)
        self.assertEqual(response.status_code, 200)

        try:
            Revision.objects.get(revision='blah1')
        except Revision.DoesNotExist:
            self.fail("[Revision.DoesNotExist] The Revisions returned no object from the get query")
        except Revision.MultipleObjectsReturned:
            self.fail("[Revision.MultipleObjectsReturned] The Revisions returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        revision = Revision.objects.get(revision='blah1')
        self.assertEqual(revision.artifacts.count(), 3)

        try:
            Branch.objects.get(name='blah')
        except Branch.DoesNotExist:
            self.fail("[Branch.DoesNotExist] The Branches returned no object from the get query")
        except Branch.MultipleObjectsReturned:
            self.fail("[Branch.MultipleObjectsReturned] The Branches returned more than one object from the get query")
        except Exception:
            self.fail("Unexpected Exception in get query")
            raise

        branch = Branch.objects.get(name='blah')
        self.assertEqual(branch.revisions.count(), 1)
        self.assertEqual(Branch.objects.count(), 1)

    def test_send_new_artifact_with_login_twice(self):
        """Sending the same file twice should not create a new file"""
        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        self.assertEqual(self.new_series.artifacts.count(), 0)

        art = self.create_artifact_file(file_to_add=self.imgfile)[0]
        art.name = 'f1'

        initial_path = reverse(self.path, args=[self.project.id, self.new_series.id])
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blahblah',
                                     'revision': 'blah'},
                                    follow=True)

        import hashlib
        self.assertEqual(response.status_code, 200)
        art.seek(0)
        self.assertIn(hashlib.md5(art.read()).hexdigest().upper(), response.content)

        self.assertEqual(self.new_series.artifacts.count(), 1)

        # warning, the input file here should be reseted to its origin
        self.imgfile.seek(0)
        art = self.create_artifact_file(file_to_add=self.imgfile)[0]
        art.name = 'f1'

        # second send should not create a new one for a specific revision
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'artifactfile': art,
                                     'is_documentation': False,
                                     'branch': 'blahblah',
                                     'revision': 'blah'},
                                    follow=True)

        # indicates the conflict
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.new_series.artifacts.count(), 1)

    def test_create_documentation_artifact(self):
        """Checks if the documentation is properly stored and deflated on the server"""
        from django.core.files.uploadedfile import SimpleUploadedFile
        import shutil

        with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE,
                                         suffix='.tar.bz2') as f:
            # create a temporary tar object
            tar = tarfile.open(fileobj=f, mode='w:bz2')

            from inspect import getsourcefile
            source_file = getsourcefile(lambda _: None)

            tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
            tar.close()

            f.seek(0)
            test_file = SimpleUploadedFile('filename.tar.bz2', f.read())

            new_artifact = Artifact.objects.create(project=self.project,
                                                   revision=self.revision,
                                                   md5hash='1',
                                                   description='test artifact',
                                                   is_documentation=True,
                                                   documentation_entry_file=os.path.basename(__file__),
                                                   artifactfile=test_file)
            new_artifact.project_series.add(self.new_series)

            # not a documentation artifact
            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

            if(os.path.exists(get_deflation_directory(new_artifact))):
                shutil.rmtree(get_deflation_directory(new_artifact))

    def test_check_artifact_consistency_on_upload(self):
        """Checks the consistency of a documentation artifact"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        f, source_file = self.create_artifact_file(is_documentation=True)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())

        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        initial_path = reverse(self.path, args=[self.project.id,
                                                self.new_series.id])

        response_get = self.client.get(initial_path)

        # invalid file (empty size)
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': SimpleUploadedFile('filename.tar.bz2', ''),
                                     'is_documentation': True,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 0)
        self.assertFormError(response,
                             'form',
                             field=None,
                             errors="The submitted file is invalid")

        # entry point not given
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 0)
        self.assertFormError(response,
                             'form',
                             field=None,
                             errors="The field 'documentation entry' should be filled for an artifact of type documentation")

        # entry point non-existent
        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'documentation_entry_file': 'non-existent',
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 0)
        self.assertFormError(response,
                             'form',
                             field=None,
                             errors='The documentation entry "non-existent" was not found in the archive')

        # invalid tar
        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', 'toto' + f.read())
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'documentation_entry_file': 'non-existent',
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 0)
        self.assertFormError(response,
                             'form',
                             field=None,
                             errors='The submitted file does not seem to be a valid tar file')

        # entry point not file
        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'documentation_entry_file': 'basename2',
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Artifact.objects.count(), 0)
        self.assertFormError(response,
                             'form',
                             field=None,
                             errors='The documentation entry "basename2" does points to a directory')

        # now this should work
        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'documentation_entry_file': 'basename/' + source_file + '2',
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertRedirects(response, self.new_series.get_absolute_url())
        self.assertEqual(Artifact.objects.count(), 1)

    def test_check_documentation_flag_changed(self):
        """Checks if the upload behaves correctly when the flag for documentation is changed. """

        from django.core.files.uploadedfile import SimpleUploadedFile

        f, source_file = self.create_artifact_file(is_documentation=True)

        response = self.client.login(username='toto', password='titi')
        self.assertTrue(response)

        initial_path = reverse(self.path, args=[self.project.id,
                                                self.new_series.id])
        response_get = self.client.get(initial_path)

        # Normal submission
        test_file = SimpleUploadedFile('new_filename.tar.bz2', f.read())
        entry_file = 'basename/' + source_file + '2'
        response = self.client.post(initial_path,
                                    {'description': 'blabla',
                                     'csrf_token': response_get.context['csrf_token'],
                                     'artifactfile': test_file,
                                     'is_documentation': True,
                                     'documentation_entry_file': entry_file,
                                     'branch': 'blah',
                                     'revision': 'blah1'
                                     })

        self.assertRedirects(response, self.new_series.get_absolute_url())
        self.assertEqual(Artifact.objects.count(), 1)

        # Check that the deflate directory has been created
        art = Artifact.objects.first()
        deflate_directory = get_deflation_directory(art)
        self.assertTrue(os.path.exists(deflate_directory))

        # Now unflag it as a documentation - deflate directory should have been deleted
        art.is_documentation = False
        art.save()
        self.assertFalse(os.path.exists(deflate_directory))
        self.assertEqual(art.documentation_entry_file, None)

        # Put it back as documentation
        art.is_documentation = True
        art.documentation_entry_file = unicode(entry_file)
        art.save()
        self.assertTrue(os.path.exists(deflate_directory))

    def test_check_documentation_flag_changed_non_tars(self):
        """Checks if the upload behaves correctly when the flag for documentation is changed. """
        from django.core.files.uploadedfile import SimpleUploadedFile

        f, source_file = self.create_artifact_file(is_documentation=False)

        new_artifact = Artifact.objects.create(description='blabla',
                                               artifactfile=SimpleUploadedFile("some", f.read()),
                                               is_documentation=False,
                                               documentation_entry_file=None,
                                               project=self.project)

        self.assertEqual(Artifact.objects.count(), 1)

        # flag as documentation: should not be possible because of the content not being tar
        new_artifact.is_documentation = True
        with self.assertRaises(IntegrityError) as exp:
            new_artifact.save()
        self.assertIn('has incorrect', exp.exception.message)

        new_artifact.documentation_entry_file = "some file"
        with self.assertRaises(IntegrityError) as exp:
            new_artifact.save()

        self.assertIn('not valid tar file', exp.exception.message)

        f, source_file = self.create_artifact_file(is_documentation=True)
        test_file = SimpleUploadedFile('new_filename.tar.bz2', f.read())
        entry_file = 'basename/' + source_file + '2'

        new_artifact.documentation_entry_file = entry_file
        new_artifact.artifactfile = test_file
        new_artifact.md5hash = None
        new_artifact.save()

    def test_remove_artifact(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f, _ = self.create_artifact_file()

        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())

        new_artifact = Artifact.objects.create(project=self.project,
                                               revision=self.revision,
                                               md5hash='1',
                                               description='test artifact',
                                               is_documentation=False,
                                               documentation_entry_file=os.path.basename(__file__),
                                               artifactfile=test_file)
        new_artifact.project_series.add(self.new_series)

        test_file.close()

        # a file has been created
        self.assertTrue(os.path.exists(new_artifact.full_path_name()),
                        "Artifact not existent on disk %s" % new_artifact.full_path_name())

        # not a documentation artifact
        self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

        new_artifact.save()

        # file still here
        self.assertTrue(os.path.exists(new_artifact.full_path_name()),
                        "Artifact not existent on disk %s" % new_artifact.full_path_name())

        self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

        new_artifact.delete()

        self.assertFalse(os.path.exists(new_artifact.full_path_name()))
        self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

    def test_remove_documentation_artifact(self):
        """Tests that the deflated documentation is removed as well"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        f, _ = self.create_artifact_file(is_documentation=True)

        f.seek(0)
        test_file = SimpleUploadedFile('filename.tar.bz2', f.read())

        new_artifact = Artifact.objects.create(project=self.project,
                                               revision=self.revision,
                                               md5hash='1',
                                               description='test artifact',
                                               is_documentation=True,
                                               documentation_entry_file=os.path.basename(__file__),
                                               artifactfile=test_file)
        new_artifact.project_series.add(self.new_series)

        test_file.close()

        self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

        new_artifact.save()

        self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))

        new_artifact.delete()

        self.assertFalse(os.path.exists(get_deflation_directory(new_artifact)))

    def test_prune_directories_on_remove(self):
        """Tests that the directory containing the artifact is properly pruned, only
        when there is no other files/directories in it"""
        from django.core.files.uploadedfile import SimpleUploadedFile

        with tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE,
                                         suffix='.tar.bz2') as f, \
             tempfile.NamedTemporaryFile(dir=settings.USER_UPLOAD_TEMPORARY_STORAGE,
                                         suffix='.tar.bz2') as f2:

            from inspect import getsourcefile

            # create a temporary tar object
            tar = tarfile.open(fileobj=f, mode='w:bz2')
            source_file = getsourcefile(lambda _: None)

            tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
            tar.close()
            f.seek(0)

            tar = tarfile.open(fileobj=f2, mode='w:gz')
            source_file = getsourcefile(lambda _: None)
            tar.add(os.path.abspath(source_file), arcname=os.path.basename(source_file))
            tar.close()
            f2.seek(0)

            test_file = SimpleUploadedFile('filename.tar.bz2', f.read())
            test_file2 = SimpleUploadedFile('filename.tar.gz', f2.read())

            new_artifact = Artifact.objects.create(project=self.project,
                                                   revision=self.revision,
                                                   description='test artifact',
                                                   is_documentation=True,
                                                   documentation_entry_file=os.path.basename(__file__),
                                                   artifactfile=test_file)
            new_artifact.project_series.add(self.new_series)
            test_file.close()

            new_artifact2 = Artifact.objects.create(project=self.project,
                                                    revision=self.revision,
                                                    description='test artifact',
                                                    is_documentation=True,
                                                    documentation_entry_file=os.path.basename(__file__),
                                                    artifactfile=test_file2)
            new_artifact2.project_series.add(self.new_series)
            test_file2.close()

            # adding new artifact 1 and 2
            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))
            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact2)))

            new_artifact.save()

            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact)))
            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact2)))

            new_artifact.delete()
            self.assertFalse(os.path.exists(os.path.abspath(get_deflation_directory(new_artifact))))
            self.assertFalse(os.path.exists(os.path.abspath(os.path.dirname(new_artifact.full_path_name()))))
            self.assertTrue(os.path.exists(get_deflation_directory(new_artifact2)))
            self.assertTrue(os.path.exists(new_artifact2.full_path_name()))

            directory = os.path.abspath(os.path.dirname(new_artifact2.full_path_name()))
            with tempfile.NamedTemporaryFile(dir=os.path.dirname(new_artifact2.full_path_name())) as ftemp:

                self.assertTrue(os.path.exists(ftemp.name))  # file is accessible
                new_artifact2.delete()

                self.assertFalse(os.path.exists(os.path.abspath(get_deflation_directory(new_artifact))))
                self.assertFalse(os.path.exists(os.path.abspath(get_deflation_directory(new_artifact2))))
                self.assertFalse(os.path.exists(os.path.abspath(new_artifact2.full_path_name())))
                # not deleted because there is another file
                self.assertTrue(os.path.exists(os.path.abspath(os.path.join(get_deflation_directory(new_artifact2), os.pardir))))
                self.assertTrue(os.path.exists(directory))

            # removing the remaining directory
            import shutil
            shutil.rmtree(directory)
