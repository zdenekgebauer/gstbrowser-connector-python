"""
index view

Expects POST or GET variables
config - predefined configuration. If empty or missing, use 'default'
action - requested action. Some actions requires additional parameters - see bellow
path - current directory path relative to base dir, without starting and leading slash

Returns JSON with properties:
 status - info about processing request [OK|ERR]
 err - optional error number if processing request failed. See Connector.ERR_* constants
 tree - tree of folders. Returned if action change folders
 files - list of folders and files in given path. Returned if action change files in current path

 action "tree"
    returns property "tree" with all directories as array of objects. Each object represents one folder
    and contains array "children" with nested folders and files

 action "files"
    returns property "files" with folders and files in current path

 action "mkdir" create new folder
    require POST['dir'] with name of new folder
    returns property "tree" with all directories

 action "delete" delete file or folder in current path
     require POST['name'] with name of file or folder
     if deleted item is file, returns property "files"
     if deleted item is folder, returns property "tree"

 action "rename" rename file or folder in current path
    require POST['old'] with name of file or folder
    require POST['new'] with new name of file or folder
    if renamed item is file, returns property "files"
    if renamed item is folder, returns property "tree"

action "upload" upload files
    require standard FILES['file']
    returns property "files"

 action "copy" copy file in current path to another folder
    require POST['old'] with name of file
    require POST['new'] with target folder, or target folder/name

 action "move" moves file in current path to another folder
    require POST['old'] with name of file
    require POST['new'] with target folder, or target folder/name
    returns property "files"

"""

import json

from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings

from connector.models import Config, Connector


def index(request):
    """ entry point of connector
    :param request: HTTP request
    """

    # example of check access by session - uncomment and modify if need
    # if request.session.get('some_variable', False) != 'some_value':
    #     return HttpResponseForbidden()

    config = 'default'
    if 'config' in request.GET:
        config = request.GET['config']
    else:
        if 'config' in request.POST:
            config = request.POST['config']

    action = None
    if 'action' in request.GET:
        action = request.GET['action']
    else:
        if 'action' in request.POST:
            action = request.POST['action']

    current_path = ''
    if 'path' in request.GET:
        current_path = request.GET['path']
    else:
        if 'path' in request.POST:
            current_path = request.POST['path']

    gstbrowser_config = Config(settings.GSTBROWSER_ROOT_DIR['default'])
    if config in settings.GSTBROWSER_ROOT_DIR:
        gstbrowser_config.base_dir = settings.GSTBROWSER_ROOT_DIR[config]
    if config in settings.GSTBROWSER_MODE_DIR:
        gstbrowser_config.mode_dir = settings.GSTBROWSER_MODE_DIR[config]
    if config in settings.GSTBROWSER_MODE_FILE:
        gstbrowser_config.mode_dir = settings.GSTBROWSER_MODE_FILE[config]
    if config in settings.GSTBROWSER_THUMB_MAX_WIDTH:
        gstbrowser_config.thumb_max_width = settings.GSTBROWSER_THUMB_MAX_WIDTH[config]
    if config in settings.GSTBROWSER_THUMB_MAX_HEIGHT:
        gstbrowser_config.thumb_max_height = settings.GSTBROWSER_THUMB_MAX_HEIGHT[config]

    connector = Connector(gstbrowser_config)

    if action == 'tree':
        result = connector.get_folders_tree()
    elif action == 'files':
        result = connector.get_files(current_path)
    elif action == 'mkdir':
        new_dir = request.POST['dir'] if request.POST['dir'] else ''
        result = connector.mk_dir(current_path, new_dir)
    elif action == 'upload':
        result = connector.upload(current_path, request.FILES['file'])
    elif action == 'rename':
        old = request.POST['old'] if request.POST['old'] else ''
        new = request.POST['new'] if request.POST['new'] else ''
        result = connector.rename(current_path, old, new)
    elif action == 'delete':
        name = request.POST['name'] if request.POST['name'] else ''
        result = connector.delete(current_path, name)
    elif action == 'copy':
        old = request.POST['old'] if request.POST['old'] else ''
        new = request.POST['new'] if request.POST['new'] else ''
        result = connector.copy(current_path, old, new)
    elif action == 'move':
        old = request.POST['old'] if request.POST['old'] else ''
        new = request.POST['new'] if request.POST['new'] else ''
        result = connector.move(current_path, old, new)
    else:
        result = {
            'status': 'ERR',
            'err': Connector.ERR_MISSING_ACTION
        }

    return HttpResponse(json.dumps(result), content_type='application/json; charset=utf-8')
