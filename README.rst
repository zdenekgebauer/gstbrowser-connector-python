Server connector for gstbrowser
===============================

Server side part of gstbrowser (filemanager for TinymCE, CKEditor and web apps,
https://github.com/zdenekgebauer/gstbrowser)
Based on Django framework.

Instalation
------------


Configuration
------------
Add the following to ``settings.py``::

# default configuration for gstbrowser
GSTBROWSER_ROOT_DIR = dict(default='')
GSTBROWSER_MODE_DIR = dict(default=0755)
GSTBROWSER_MODE_FILE = dict(default=0644)
GSTBROWSER_THUMB_MAX_WIDTH = dict(default=90)
GSTBROWSER_THUMB_MAX_HEIGHT = dict(default=90)

Optionally add named configuration  to ``settings.py``, i.e.::

# override default configuration with named config
GSTBROWSER_ROOT_DIR['test1'] = 'd:/temp/'
GSTBROWSER_ROOT_DIR['test2'] = 'd:/tmp/'
GSTBROWSER_THUMB_MAX_WIDTH['test2'] = 60
GSTBROWSER_THUMB_MAX_HEIGHT['test2'] = 60


Configure required url to connector in ``urls.py``, i.e.::

urlpatterns += patterns('',
    url(r'^gstbrowser/', include('connector.urls')),
)

License
-------
Released under the WTFPL license, http://www.wtfpl.net/about/.