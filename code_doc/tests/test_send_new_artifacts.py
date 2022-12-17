from django.test import TestCase
from django.test import LiveServerTestCase
from django.test import Client
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse

from ..models.projects import Project, ProjectSeries
from ..models.authors import Author
from ..utils.send_new_artifact import PostMultipartWithSession

import tempfile
import datetime
import os
import json


class ProjectLiveSendArtifactTest(LiveServerTestCase):
    """Testing the project series functionality"""

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

        # path for the queries to the project details
        self.path = "project_series_all"

        self.first_user = User.objects.create_user(
            username="test_series_user", password="test_series_user"
        )

        self.author1 = Author.objects.create(
            lastname="1",
            firstname="1f",
            gravatar_email="",
            email="1@1.fr",
            home_page_url="",
        )
        self.project = Project.objects.create(name="test_project")
        self.project.authors = [self.author1]
        self.project.administrators = [self.first_user]

        self.series = ProjectSeries.objects.create(
            series="12345", project=self.project, release_date=datetime.datetime.now()
        )

    def test_send_new_file_new_api(self):
        """In this test, we know in advance the login url"""
        self.assertEqual(len(self.series.artifacts.all()), 0)

        s = "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

        # not necessarily a tar file
        from StringIO import StringIO

        f = StringIO()
        f.name = "test"
        f.write(s)
        f.seek(0)

        fields = {
            "description": "revision from client based application",
            "is_documentation": "False",
            "documentation_entry_file": "",
            "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "branch": "blah",
            "revision": "blahblah",
        }

        files = [("artifactfile", f)]

        instance = PostMultipartWithSession(host=self.live_server_url)

        post_url = "/artifacts/%d/%d/add" % (self.project.id, self.series.id)

        instance.login(
            login_page="/accounts/login/",
            username=self.first_user.username,
            password="test_series_user",
        )

        ret = instance.post_multipart(post_url, fields, files, avoid_redirections=False)

        self.assertEqual(self.series.artifacts.count(), 1)
        artifact = self.series.artifacts.first()

        try:
            self.assertEqual(artifact.filename(), os.path.basename(f.name))
        except AssertionError:
            self.assertIn(os.path.basename(f.name), artifact.filename())
            path_already_taken = os.path.join(
                os.path.dirname(artifact.full_path_name()), os.path.basename(f.name)
            )
            self.assertTrue(os.path.exists(os.path.abspath(path_already_taken)))

        import hashlib

        f.seek(0)
        self.assertEqual(artifact.md5hash, hashlib.md5(f.read()).hexdigest())

        self.assertEqual(ret.code, 200)

    def test_send_new_file_new_api_user_permissions(self):
        """Check the capability of a user to create new artifact from the remote API."""

        self.assertEqual(len(self.series.artifacts.all()), 0)

        s = "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

        # not necessarily a tar file
        from StringIO import StringIO

        f = StringIO()
        f.name = "test"
        f.write(s)
        f.seek(0)

        fields = {
            "description": "revision from client based application",
            "is_documentation": "False",
            "documentation_entry_file": "",
            "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "branch": "blah",
            "revision": "blahblah",
        }

        files = [("artifactfile", f)]

        instance = PostMultipartWithSession(host=self.live_server_url)

        post_url = "/artifacts/%d/%d/add" % (self.project.id, self.series.id)

        current_permission = "code_doc.series_artifact_add"

        # User with no permission
        second_user = User.objects.create_user(username="james bond", password="007")

        instance.login(
            login_page="/accounts/login/", username=second_user, password="007"
        )

        self.assertFalse(second_user.has_perm(current_permission, self.series))

        ret = instance.post_multipart(post_url, fields, files, avoid_redirections=False)

        self.assertEqual(ret.code, 401)

        # Now give the user permissions to james
        self.series.perms_users_artifacts_add.add(second_user)
        self.assertTrue(second_user.has_perm(current_permission, self.series))

        ret = instance.post_multipart(post_url, fields, files, avoid_redirections=False)

        self.assertEqual(
            ret.code, 200
        )  # a get follows the post, so we have 200 instead of 302
        self.assertEqual(self.series.artifacts.count(), 1)
        artifact = self.series.artifacts.first()

        try:
            self.assertEqual(artifact.filename(), os.path.basename(f.name))
        except AssertionError:
            self.assertIn(os.path.basename(f.name), artifact.filename())
            path_already_taken = os.path.join(
                os.path.dirname(artifact.full_path_name()), os.path.basename(f.name)
            )
            self.assertTrue(os.path.exists(os.path.abspath(path_already_taken)))

        import hashlib

        f.seek(0)
        self.assertEqual(artifact.md5hash, hashlib.md5(f.read()).hexdigest())

        self.assertEqual(ret.code, 200)

    def test_send_new_file_new_api_group_permissions(self):
        """Check the capability of a group to create new artifact from the remote API."""

        self.assertEqual(len(self.series.artifacts.all()), 0)

        s = "GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

        # not necessarily a tar file
        from StringIO import StringIO

        f = StringIO()
        f.name = "test"
        f.write(s)
        f.seek(0)

        fields = {
            "description": "revision from client based application",
            "is_documentation": "False",
            "documentation_entry_file": "",
            "upload_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "branch": "blah",
            "revision": "blahblah",
        }

        files = [("artifactfile", f)]

        instance = PostMultipartWithSession(host=self.live_server_url)

        post_url = "/artifacts/%d/%d/add" % (self.project.id, self.series.id)

        current_permission = "code_doc.series_artifact_add"

        # User and group with no permission
        second_user = User.objects.create_user(username="james bond", password="007")
        group = Group.objects.create(name="MI6")
        second_user.groups.add(group)

        instance.login(
            login_page="/accounts/login/", username=second_user, password="007"
        )

        self.assertFalse(second_user.has_perm(current_permission, self.series))

        ret = instance.post_multipart(post_url, fields, files, avoid_redirections=False)

        self.assertEqual(ret.code, 401)

        # Now give the user permissions to james via the group
        self.series.perms_groups_artifacts_add.add(group)
        self.assertTrue(second_user.has_perm(current_permission, self.series))

        ret = instance.post_multipart(post_url, fields, files, avoid_redirections=False)

        self.assertEqual(self.series.artifacts.count(), 1)
        artifact = self.series.artifacts.first()

        try:
            self.assertEqual(artifact.filename(), os.path.basename(f.name))
        except AssertionError:
            self.assertIn(os.path.basename(f.name), artifact.filename())
            path_already_taken = os.path.join(
                os.path.dirname(artifact.full_path_name()), os.path.basename(f.name)
            )
            self.assertTrue(os.path.exists(os.path.abspath(path_already_taken)))

        import hashlib

        f.seek(0)
        self.assertEqual(artifact.md5hash, hashlib.md5(f.read()).hexdigest())

        self.assertEqual(ret.code, 200)

    def test_get_redirection(self):
        """Tests if the redirection is ok"""
        instance = PostMultipartWithSession(host=self.live_server_url)

        post_url = f"/s/{self.project.name}/{self.series.series}/"
        _ = instance.get(post_url)
        redir = instance.get_redirection(post_url)
        self.assertEqual(
            redir, reverse("project_series", args=[self.project.id, self.series.id])
        )

    def test_get_json_for_project_id(self):
        """Tests if the json mapping the name of project/series to ids is ok"""

        instance = PostMultipartWithSession(host=self.live_server_url)
        instance.login(
            login_page="/accounts/login/",
            username=self.first_user.username,
            password="test_series_user",
        )

        post_url = f"/api/{self.project.name}/{self.series.series}/"
        response = instance.get(post_url)

        dic_ids = json.loads(response.read())
        self.assertEquals(dic_ids["project_id"], self.project.id)
        self.assertEquals(dic_ids["series_id"], self.series.id)


class TestSendArtifactCompanion(TestCase):
    def test_get_script_file(self):
        """Checks that the script file can be downloaded"""

        path = "script"
        self.client = Client()

        print(os.path.abspath(__file__))
        response = self.client.get(reverse(path))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content,
            open(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    os.pardir,
                    "utils",
                    "send_new_artifact.py",
                ),
                "rb",
            ).read(),
        )
