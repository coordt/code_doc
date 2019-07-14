import os

from .default import *  # NOQA

# creating needed directories
if not os.path.exists(USER_UPLOAD_TEMPORARY_STORAGE):  # NOQA
    os.makedirs(USER_UPLOAD_TEMPORARY_STORAGE)  # NOQA
