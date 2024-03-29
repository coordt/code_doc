import os
from .default import *


# cannot be this directory since this is a symbolic link to the previous
# instance
# CODEDOC_ROOT_LOCATION = '/www/code_doc/current/'
CODEDOC_ROOT_LOCATION = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

# loading the secrets file, this should be absolute
secret_file = os.environ["DJANGO_SETTINGS_SECRET_FILE"]
secret_dict = {}
with open(secret_file) as secret:
    exec(secret.read(), secret_dict)

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATIC_ROOT = os.path.join(CODEDOC_ROOT_LOCATION, "static") + "/"
MEDIA_ROOT = os.path.join(CODEDOC_ROOT_LOCATION, "media") + "/"

# path used to upload temporary files, maybe a proper /tmp dir for production?
USER_UPLOAD_TEMPORARY_STORAGE = os.path.join(CODEDOC_ROOT_LOCATION, "temporary_upload")
FILE_LOGGING_LOCATION = os.path.join(
    CODEDOC_ROOT_LOCATION, "logs", "%s.log" % SITE_NAME
)

if not os.path.exists(USER_UPLOAD_TEMPORARY_STORAGE):
    os.makedirs(USER_UPLOAD_TEMPORARY_STORAGE)

if not os.path.exists(os.path.dirname(FILE_LOGGING_LOCATION)):
    os.makedirs(os.path.dirname(FILE_LOGGING_LOCATION))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secret_dict["DJANGO_ENV_SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ["staging.code.is.localnet", "127.0.0.1", "localhost"]
ADMINS = (("Raffi Enficiaud", "raffi.enficiaud@tuebingen.mpg.de"),)

# the ppl receiving notifications for broken links if BrokenLinkEmailsMiddleware is active
MANAGERS = (("Raffi Enficiaud", "raffi.enficiaud@tuebingen.mpg.de"),)


# ###### EMAIL
#
#

# change to a valid email backend
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# The email address that error messages come from, such as those sent to ADMINS and MANAGERS.
SERVER_EMAIL = "raffi.enficiaud@tuebingen.mpg.de"

# Default email address to use for various automated correspondence from
# the site managers.
DEFAULT_FROM_EMAIL = "raffi.enficiaud@tuebingen.mpg.de"

# Subject-line prefix for email messages send with django.core.mail.mail_admins
# or ...mail_managers.  Make sure to include the trailing space.
# NB.: not for end users
EMAIL_SUBJECT_PREFIX = "[staging.code.is.localnet] "

# Host for sending email.
EMAIL_HOST = "mailhost.tuebingen.mpg.de"

# Port for sending email.
EMAIL_PORT = 25

# Optional SMTP authentication information for EMAIL_HOST.
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = True


# fix logging thinggy (need to rewrite)
LOGGING["handlers"]["file"]["filename"] = FILE_LOGGING_LOCATION


print("MEDIA_ROOT set to production", MEDIA_ROOT)
print("STATIC_ROOT set to production", STATIC_ROOT)


# CROWD REST Settings
INSTALLED_APPS += ("crowdrest",)
AUTHENTICATION_BACKENDS += ("crowdrest.backend.CrowdRestBackend",)

# Uncomment for setting up the Crowd - authentification application
AUTH_CROWD_ALWAYS_UPDATE_USER = True
AUTH_CROWD_ALWAYS_UPDATE_GROUPS = True
AUTH_CROWD_CREATE_GROUPS = True

AUTH_CROWD_STAFF_GROUP = "jira-developers"
AUTH_CROWD_SUPERUSER_GROUP = "jira-administrators"

AUTH_CROWD_APPLICATION_USER = secret_dict["DJANGO_CROWD_USER"]
AUTH_CROWD_APPLICATION_PASSWORD = secret_dict["DJANGO_CROWD_PASS"]

AUTH_CROWD_SERVER_REST_URI = (
    "https://atlas.is.localnet/crowd/rest/usermanagement/latest"
)
AUTH_CROWD_SERVER_TRUSTED_ROOT_CERTS_FILE = None

# We do not want the superuser/staff status to be overridden
AUTH_CROWD_ALWAYS_UPDATE_SUPERUSER_STAFF_STATUS = False
