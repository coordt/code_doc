
from .default import *

# creating needed directories
if(not os.path.exists(USER_UPLOAD_TEMPORARY_STORAGE)):
    os.makedirs(USER_UPLOAD_TEMPORARY_STORAGE)

print "MEDIA_ROOT set to", MEDIA_ROOT


