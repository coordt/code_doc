"""Some test helpers functions."""

import random
import string


def generate_random_string():
    """Generate a random string of random length using upper/lower case letters and digits."""

    length = random.randint(5, 64)
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in xrange(length))
