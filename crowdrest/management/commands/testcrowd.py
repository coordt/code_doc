from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import authenticate


class Command(BaseCommand):
    args = "<username password>"
    help = "Try to authenticate a user via Crowd (testing crowd backend with current settings)"

    def __init__(self):
        super(Command, self).__init__()

    def handle(self, *args, **options):
        """
        Try authenticate.
        """
        if len(args) < 2:
            raise CommandError("Need user and password argument")

        userName = args[0]
        userPwd = args[1]
        user = authenticate(username=userName, password=userPwd)
        if user is None:
            print("Your username and password were incorrect.")

        elif user.is_active:
            print(f"You provided a correct username and password for '{userName}'!")
        else:
            print("Account '{userName}' has been disabled!")
