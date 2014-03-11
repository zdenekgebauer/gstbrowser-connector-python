import os, sys  

sys.path.append('d:/projekty/filebrowser-connector-python/')
sys.path.append('c:/Python27/Lib/site-packages/')
os.environ['DJANGO_SETTINGS_MODULE'] = 'gstbrowser.settings'

import django.core.handlers.wsgi  
application = django.core.handlers.wsgi.WSGIHandler()
