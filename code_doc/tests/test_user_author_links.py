# this file tests the correct behaviour of the Users and Authors

from django.test import TestCase
from django.test import Client
from django.contrib.auth.models import User

from ..models.authors import Author


class UserAuthorLinkTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(
            username="toto",
            password="titi",
            first_name="toto",
            last_name="titi",
            email="blah@blah.com",
        )

        self.admin_user = User.objects.create_superuser(
            username="admin", email="blah@blah.com", password="1234"
        )

    def test_author_link_with_existing_user(self):
        """Test, that on user creation a corresponding author was created"""
        self.assertTrue(hasattr(self.user, "author"))

    def test_author_link_with_new_user(self):
        """Test, that the User's information is copied correctly to the corresponding Author"""
        new_user = User.objects.create_user(
            username="toto2",
            password="titi2",
            first_name="Toto",
            last_name="Titi",
            email="test@test.com",
        )
        self.assertTrue(hasattr(new_user, "author"))

        linked_author = new_user.author
        self.assertEqual(linked_author.firstname, "Toto")
        self.assertEqual(linked_author.lastname, "Titi")
        self.assertEqual(linked_author.email, "test@test.com")
        self.assertEqual(linked_author.django_user, new_user)

    def test_author_link_for_existing_author_and_new_corresponding_user(self):
        """Tests that we map a new User correctly to an already existing Author"""
        author = Author.objects.create(
            firstname="existing", lastname="author", email="existing.author@auth.org"
        )

        new_user = User.objects.create_user(
            username="new",
            password="user",
            # Chosing different first and last name but same email
            first_name="new",
            last_name="user",
            email="existing.author@auth.org",
        )
        self.assertEqual(new_user.author, author)

    def test_author_link_for_existing_author_and_non_corresponding_user(self):
        """Tests that we do _not_ map a new User to an already existing Author
           if the two objects differ in their email.
        """
        author = Author.objects.create(
            firstname="existing", lastname="author", email="existing.author@auth.org"
        )

        new_user = User.objects.create_user(
            username="new",
            password="user",
            # Chosing same first and last name but different email
            first_name="existing",
            last_name="author",
            email="non_existing.author@auth.org",
        )
        # We should have created an author
        self.assertIsNotNone(new_user.author)

        # The new_user and author differ in their email, so we should not link them,
        # even if they have the same first and last names.
        self.assertNotEqual(new_user.author, author)

    def test_has_user_author_edit_permission(self):
        """Tests the 'has_user_author_edit_permission' function of the Author"""
        author = self.user.author
        self.assertTrue(author.has_user_author_edit_permission(self.admin_user))
        self.assertTrue(author.has_user_author_edit_permission(self.user))

        new_user = User.objects.create_user(
            username="not_allowed",
            password="blah",
            first_name="not",
            last_name="allowed",
            email="not_allowed@allowance.org",
        )
        # Should _not_ be allowed to edit the author that corresponds to self.user
        self.assertFalse(author.has_user_author_edit_permission(new_user))
        # We should however be able to edit the author we are linked to
        self.assertTrue(new_user.author.has_user_author_edit_permission(new_user))

    def test_author_edit_permissions_for_admin(self):
        """Test that an admin has author edit permissions on the Users"""

        permission = "code_doc.author_edit"

        new_author = Author.objects.create(firstname="1", lastname="1", email="1@1.com")

        self.assertTrue(self.admin_user.has_perm(permission, self.user.author))
        self.assertTrue(self.admin_user.has_perm(permission, new_author))

    def test_author_edit_permissions_for_non_admin(self):
        """Tests that a User has the proper permissions on the Authors"""

        permission = "code_doc.author_edit"

        self.assertIn(permission, self.user.get_all_permissions(self.user.author))

        new_author = Author.objects.create(firstname="1", lastname="1", email="1@1.com")

        self.assertNotIn(permission, self.user.get_all_permissions(new_author))
        self.assertTrue(self.user.has_perm(permission, self.user.author))

    def test_author_creation_on_enough_information(self):
        """Tests that we create an Author if the User specifies enough information.

           The author should be created if it provides a non-empty firstname, lastname
           and email.
        """

        old_author_count = Author.objects.count()

        User.objects.create_user(
            username="a", password="b", first_name="c", last_name="d", email="f@g.h"
        )

        new_user_count = Author.objects.count()

        self.assertEqual(new_user_count - old_author_count, 1)

    def test_author_creation_on_too_little_information(self):
        """Tests that we do not associate a User to an Author if the user does not
           provide enough information
        """

        old_author_count = Author.objects.count()

        User.objects.create_user(
            username="1",
            password="1",
            # first_name='c',
            last_name="1",
            email="1@1.h",
        )
        User.objects.create_user(
            username="2",
            password="2",
            first_name="2",
            # last_name='1',
            email="2@2.h",
        )
        User.objects.create_user(
            username="3",
            password="3",
            first_name="3",
            last_name="3",
            # email='1@1.h'
        )
        User.objects.create_user(
            username="4",
            password="4",
            # first_name='c',
            # last_name='1',
            # email='1@1.h'
        )
        User.objects.create_user(
            username="5", password="5", first_name="", last_name="", email=""
        )

        new_author_count = Author.objects.count()

        # None of the previous creations should have created an Author
        self.assertEqual(old_author_count, new_author_count)
