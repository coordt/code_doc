# this file tests the correct behaviour of the Users and Authors

from django.test import TestCase

from django.test import Client
from django.contrib.auth.models import User


class UserAuthorLinkTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User.objects.create_user(username='toto', password='titi')

    def test_author_link_with_existing_user(self):
        """Test, that on user creation a corresponding author was created"""
        self.assertTrue(hasattr(self.user, 'author'))

    def test_author_link_with_new_user(self):
        """Test, that the User's information is copied correctly to the corresponding Author"""
        new_user = User.objects.create_user(username='toto2',
                                            password='titi2',
                                            first_name='Toto',
                                            last_name='Titi',
                                            email="test@test.com"
                                            )
        self.assertTrue(hasattr(new_user, 'author'))

        linked_author = new_user.author
        self.assertTrue(linked_author.firstname == 'Toto')
        self.assertTrue(linked_author.lastname == 'Titi')
        self.assertTrue(linked_author.email == 'test@test.com')
        self.assertTrue(linked_author.django_user == new_user)
