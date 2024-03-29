from django.contrib.auth.models import User, Group
from django.conf import settings

import urllib2
import httplib
import socket
import ssl
import json
import logging


crowd_logger = logging.getLogger(__name__)
crowd_logger_handler = logging.StreamHandler()
crowd_logger_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s %(levelname)s %(filename)s(%(lineno)d) %(funcName)s: %(message)s"
    )
)
crowd_logger.addHandler(crowd_logger_handler)
crowd_logger.setLevel(logging.DEBUG)
crowd_logger.setLevel(logging.DEBUG)


class ClientException(Exception):
    def __init__(self, msg):
        super(ClientException, self).__init__(msg)


class UserException(Exception):
    def __init__(self, username):
        super(UserException, self).__init__()
        self.username = username


class InvalidUser(UserException):
    def __init__(self, username):
        super(InvalidUser, self).__init__(username)

    def __str__(self):
        return "User '%s' is not valid Crowd user" % self.username


class AuthFailed(UserException):
    def __init__(self, username):
        super(AuthFailed, self).__init__(username)

    def __str__(self):
        return "Failed to authenticate user '%s' in Crowd" % self.username


class CrowdRestBackend(object):
    """Atlassian Crowd Authentication Backend using REST API
    """

    crowdClient = None

    def check_client_and_app_authentication(self):
        "Create a client to access Crowd."
        try:
            if self.crowdClient is None:
                self.crowdClient = CrowdRestClient()
        except:
            crowd_logger.exception("Create Crowd client failed")

    def create_or_update_user(self, user_id):
        "Create or update django user of given identifier"
        user, created = User.objects.get_or_create(username=user_id)
        saveUser = False

        if created:
            user.set_unusable_password()
            saveUser = True

        if getattr(settings, "AUTH_CROWD_ALWAYS_UPDATE_USER", True):
            self.sync(user)
            saveUser = True

        if getattr(settings, "AUTH_CROWD_ALWAYS_UPDATE_GROUPS", True):
            self.sync_groups(user, is_created=created)
            saveUser = True

        if saveUser:
            user.save()

        return user

    def authenticate(self, request, username=None, password=None):
        "Try to authenticate given user and return a User instance on success."
        user = None
        try:
            crowd_logger.debug("Authenticate user '%s'..." % username)
            self.check_client_and_app_authentication()
            self.crowdClient.authenticate(username, password)
            user = self.create_or_update_user(username)
            crowd_logger.debug("Authenticated user '%s' successfully." % user.username)
        except:
            crowd_logger.exception("Authenticate failed")
        return user

    def sync(self, user):
        "Sync given user instance with data from crowd."
        usrData = self.crowdClient.get_user(user.username)
        if "first-name" in usrData:
            user.first_name = usrData["first-name"]
        if "last-name" in usrData:
            user.last_name = usrData["last-name"]
        if "email" in usrData:
            user.email = usrData["email"]
        if "active" in usrData:
            user.is_active = usrData["active"]

    def sync_groups(self, user, is_created=False):

        data = self.crowdClient.get_user_groups(user.username)

        group_names = set([x["name"] for x in data["groups"]])
        update_admin_staff_always = getattr(
            settings, "AUTH_CROWD_ALWAYS_UPDATE_SUPERUSER_STAFF_STATUS", False
        )

        if update_admin_staff_always or is_created:
            if getattr(settings, "AUTH_CROWD_SUPERUSER_GROUP", None) in group_names:
                user.is_superuser = True
            else:
                user.is_superuser = False
            if getattr(settings, "AUTH_CROWD_STAFF_GROUP", None) in group_names:
                user.is_staff = True
            else:
                user.is_staff = False

        if getattr(settings, "AUTH_CROWD_CREATE_GROUPS", False):
            group_objs = [Group.objects.get_or_create(name=g)[0] for g in group_names]
        else:
            group_objs = Group.objects.all()
            group_objs = filter(lambda x: x.name in group_names, group_objs)

        user.groups = group_objs

    def get_user(self, user_id):
        "Return User instance of given identifier."
        user = None
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            crowd_logger.exception("User not found")
        return user


#########################################################################
# START OF
# Validating https certificate
# Downloaded from https://github.com/josephturnerjr/urllib2.VerifiedHTTPS
class VerifiedHTTPSConnection(httplib.HTTPSConnection):
    def connect(self):
        # overrides the version in httplib so that we do certificate verification
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # wrap the socket using verification with the root certificates of given file
        self.sock = ssl.wrap_socket(
            sock,
            self.key_file,
            self.cert_file,
            cert_reqs=ssl.CERT_REQUIRED,
            ca_certs=getattr(
                settings, "AUTH_CROWD_SERVER_TRUSTED_ROOT_CERTS_FILE", None
            ),
        )


class VerifiedHTTPSHandler(urllib2.HTTPSHandler):
    """Wraps https connections with ssl certificate verification
    """

    def __init__(self, connection_class=VerifiedHTTPSConnection):
        self.specialized_conn_class = connection_class
        urllib2.HTTPSHandler.__init__(self)

    def https_open(self, req):
        return self.do_open(self.specialized_conn_class, req)


# END OF
#########################################################################


class CrowdRestClient(object):
    def __init__(self):
        try:
            self._opener = None
            self._url = settings.AUTH_CROWD_SERVER_REST_URI
            self.connect()
        except:
            crowd_logger.exception("Initialize Crowd client failed")

    def _createOpener(self):
        "Create urllib2 opener to be used for subsequent https requests."
        try:
            handlers = []

            # create a password manager
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()

            # Add the username and password.
            # If we knew the realm, we could use it instead of None.
            password_mgr.add_password(
                None,
                self._url,
                settings.AUTH_CROWD_APPLICATION_USER,
                settings.AUTH_CROWD_APPLICATION_PASSWORD,
            )

            authHandler = urllib2.HTTPBasicAuthHandler(password_mgr)
            handlers += [authHandler]

            certs = getattr(settings, "AUTH_CROWD_SERVER_TRUSTED_ROOT_CERTS_FILE", None)
            if self._url.startswith("https") and certs:
                crowd_logger.debug("Validating certificate with " + certs)
                verifyHandler = VerifiedHTTPSHandler()
                handlers += [verifyHandler]

            # create "opener" (OpenerDirector instance)
            self._opener = urllib2.build_opener(*handlers)
        except:
            crowd_logger.exception("Failed to create opener")

    def connect(self):
        "Connect to Crowd."
        try:
            crowd_logger.debug("Connecting to %s..." % self._url)
            self._createOpener()

            # use the opener to fetch a dummy URL
            fp = self._opener.open(self._url + "/config/cookie.json")
            i = fp.info()
            d = fp.read()

            crowd_logger.debug("Connected to Crowd.")
        except:
            self._opener = None
            crowd_logger.exception("Failed to connect to Crowd")
            raise ClientException("Failed to connect to Crowd")

    def authenticate(self, username, password, maxRetry=3):
        "Authenticate given user via Crowd."
        if not self._opener:
            crowd_logger.debug(
                "Crowd not available !? Failed to authenticate '%s'" % username
            )
            raise AuthFailed(username)

        try:
            crowd_logger.debug("Authenticating '%s'..." % username)
            url = self._url + "/authentication?username=" + username
            creds = {"value": password}
            req = urllib2.Request(url)
            req.add_data(json.dumps(creds))
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            fp = self._opener.open(req)
            usrData = json.load(fp)
            crowd_logger.debug(
                "Authenticated '%s' successfully." % usrData["display-name"]
            )
            return
        except urllib2.URLError as e:
            errData = json.load(e)
            if e.code == 400:
                if errData["reason"] == "USER_NOT_FOUND":
                    raise InvalidUser(username)
                else:
                    crowd_logger.exception("Unknown reason %s" % errData["reason"])
            elif e.code == 500:
                crowd_logger.exception("Internal error on Crowd server")
                if maxRetry > 0:
                    self.authenticate(username, password, maxRetry - 1)
                    return
            else:
                crowd_logger.exception("Unknown response")
        except:
            crowd_logger.exception("Unknown exception")

        # Force auth to fail
        raise AuthFailed(username)

    def get_user(self, username):
        "Query for given user and return dict of user fields from Crowd."
        try:
            crowd_logger.debug("Fetching details of '%s'..." % username)
            url = self._url + "/user.json?username=%s" % username
            u = self._opener.open(url)
            return json.loads(u.read())
        except urllib2.URLError:
            crowd_logger.exception("Failed to fetch user data from Crowd")
        raise InvalidUser(username)

    def get_user_groups(self, username):
        "Query for groups of given user and return dict of group fields from Crowd."
        try:
            crowd_logger.debug("Fetching groups of '%s'..." % username)
            url = self._url + "/user/group/nested.json?username=%s" % username
            u = self._opener.open(url)
            return json.loads(u.read())
        except urllib2.URLError:
            crowd_logger.exception("Failed to fetch user data from Crowd")
        raise InvalidUser(username)
