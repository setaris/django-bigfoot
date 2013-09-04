try:
    from .elements import *
except ImportError:
    # Can't find project's settings file - this happens during installation.
    # Not sure if there's a better way to solve this.
    pass
