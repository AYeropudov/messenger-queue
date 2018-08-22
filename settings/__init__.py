import os

BASE_DIR = os.path.dirname(os.path.realpath(os.path.dirname(__file__) + "/.."))

if os.path.exists(os.path.join(BASE_DIR, 'settings/local.py')):
    from .local import *
else:
    from .prod import *