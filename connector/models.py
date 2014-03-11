"""
models Config, Connector

"""
import os
from os.path import isdir, isfile
import glob
import json
from datetime import datetime
from StringIO import StringIO
import base64
import time
import errno
import unicodedata
import shutil
import re

from PIL import Image
import pytz


class Config(object):
    """ configuration of connector """

    def __init__(self, base_dir):
        self.base_dir = base_dir.strip()
        self.mode_dir = 0755
        self.mode_file = 0644
        self.overwrite = True
        self._thumb_max_width = 90
        self._thumb_max_height = 90

    @property
    def thumb_max_width(self):
        """ returns max width of thumbnail """
        return self._thumb_max_width

    @thumb_max_width.setter
    def thumb_max_width(self, value):
        """ sets max height of thumbnail
        :param value: integer between 20 and 400
        """
        if 20 <= value <= 400:
            self._thumb_max_width = value

    @property
    def thumb_max_height(self):
        """ returns max height of thumbnail """
        return self._thumb_max_height

    @thumb_max_height.setter
    def thumb_max_height(self, value):
        """ sets max height of thumbnail
        :param value: integer between 20 and 400
        """
        if 20 <= value <= 400:
            self._thumb_max_height = value


class Connector:
    """ connector """

    ERR_MISSING_ACTION = 3
    ERR_DIRECTORY_NOT_FOUND = 4
    ERR_FILE_NOT_FOUND = 6
    ERR_INVALID_PARAMETER = 7

    ERR_MKDIR = 10
    ERR_MKDIR_EXISTS = 11

    ERR_RENAME = 20

    ERR_UPLOAD = 30
    ERR_UPLOAD_FILESIZE = 31
    ERR_UPLOAD_FILE_EXISTS = 32

    ERR_DELETE = 40
    ERR_DELETE_NOT_EMPTY_DIR = 41

    ERR_COPY = 50
    ERR_COPY_FILE_EXISTS = 51
    ERR_COPY_DIR_NOT_FOUND = 52

    def __init__(self, config):
        self._config = config

    def get_folders_tree(self):
        """ returns tree of all folders """
        if not os.path.isdir(self._config.base_dir):
            return Connector._output(self.ERR_DIRECTORY_NOT_FOUND)
        return Connector._output(0, None, self._get_tree())

    def _get_tree(self):
        result = []
        sub_tree = self._get_sub_tree(self._config.base_dir)
        tmp = {'name': os.path.basename(os.path.normpath(self._config.base_dir))}
        if sub_tree:
            tmp['children'] = sub_tree
        result.append(tmp)
        return result

    def _get_sub_tree(self, current_directory):
        result = []
        for sub_dir in os.listdir(current_directory):
            if os.path.isdir(current_directory + sub_dir):
                tmp = {'name': os.path.basename(sub_dir)}
                sub_tree = self._get_sub_tree(current_directory + sub_dir + '/')
                if sub_tree:
                    tmp['children'] = sub_tree
                result.append(tmp)
        return result

    def get_files(self, path):
        """ returns list of files in path
        :param path: relative path
        """
        target_dir = self._target_dir(path)
        if not os.path.isdir(target_dir):
            return Connector._output(self.ERR_DIRECTORY_NOT_FOUND)
        return Connector._output(0, self._get_folder_content(target_dir))

    def _target_dir(self, path):
        return self._config.base_dir + path

    @staticmethod
    def _output(err=0, files=None, tree=None):
        ret = {'status': ('OK' if err == 0 else 'ERR')}
        if err > 0:
            ret['err'] = err
        if files is not None:
            ret['files'] = files
        if tree is not None:
            ret['tree'] = tree
        return ret

    def _get_folder_content(self, target_dir):
        cache = CacheDir(target_dir, self._config)
        return cache.get_files()

    def mk_dir(self, path, new_dir):
        """ create new directory
        :param path: relative path
        :param new_dir: name of ew directory
        """
        target_dir = self._target_dir(path)
        if not os.path.isdir(target_dir):
            return Connector._output(self.ERR_DIRECTORY_NOT_FOUND)

        if new_dir == '' or not re.match('^[a-z0-9-_.]+$', new_dir):
            return Connector._output(self.ERR_INVALID_PARAMETER)

        fullpath = target_dir + '/' + new_dir
        if os.path.isdir(fullpath):
            return Connector._output(self.ERR_MKDIR_EXISTS)

        oldumask = os.umask(0)
        try:
            os.mkdir(fullpath, self._config.mode_dir)
        except OSError:
            return Connector._output(self.ERR_MKDIR)

        os.umask(oldumask)
        cache = CacheDir(target_dir, self._config)
        cache.update_item(new_dir)

        return Connector._output(0, self._get_folder_content(target_dir), self._get_tree())

    def upload(self, path, uploaded_file):
        """ upload file
        :param path: relative path
        :param uploaded_file: uploaded file field
        """
        target_dir = self._target_dir(path)
        if not os.path.isdir(target_dir):
            return Connector._output(self.ERR_DIRECTORY_NOT_FOUND)

        filename = uploaded_file.name
        filename = File.remove_accents(filename)
        filename = filename.replace(' ', '-')

        target_fullpath = target_dir + filename
        if not self._config.overwrite and isfile(target_fullpath):
            return Connector._output(self.ERR_UPLOAD_FILE_EXISTS)

        with open(target_fullpath, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        oldumask = os.umask(0)
        try:
            os.chmod(target_fullpath, self._config.mode_file)
        except OSError:
            pass
        os.umask(oldumask)

        cache = CacheDir(target_dir, self._config)
        cache.refresh()

        return Connector._output(0, self._get_folder_content(target_dir))

    def rename(self, path, old, new):
        """ rename folder or file
        :param path: relative path
        :param old: original name of file or folder
        :param new: new name of file or folder
        """
        target_dir = self._target_dir(path)
        if old == '' or new == '' or not re.match('^[a-z0-9-_.]+$', new):
            return Connector._output(self.ERR_INVALID_PARAMETER)

        src = target_dir + old
        is_dir = os.path.isdir(src)
        if not os.path.isfile(src) and not is_dir:
            return Connector._output(self.ERR_FILE_NOT_FOUND)

        try:
            os.rename(src, target_dir + new)
        except OSError:
            return Connector._output(self.ERR_RENAME)

        cache = CacheDir(target_dir, self._config)
        cache.delete_item(old)
        cache.update_item(new)

        if is_dir:
            return Connector._output(0, self._get_folder_content(target_dir), self._get_tree())
        return Connector._output(0, self._get_folder_content(target_dir))

    def delete(self, path, name):
        """ delete folder or file

        :param path: relative path
        :param name: name of file or folder to delete
        """

        target_dir = self._target_dir(path)
        target = target_dir + '/' + name

        if os.path.isdir(target):
            try:
                os.unlink(target + '/' + CacheDir.CACHE_FILENAME)
            except OSError:
                return Connector._output(self.ERR_DELETE)

            try:
                os.rmdir(target)
            except OSError as e:
                if e.errno == errno.ENOTEMPTY:
                    return Connector._output(self.ERR_DELETE_NOT_EMPTY_DIR)
                else:
                    return Connector._output(self.ERR_DELETE)

            cache = CacheDir(target_dir, self._config)
            cache.delete_item(name)
            return Connector._output(0, self._get_folder_content(target_dir), self._get_tree())
        elif os.path.isfile(target):
            try:
                os.unlink(target)
            except OSError:
                return Connector._output(self.ERR_DELETE)

            cache = CacheDir(target_dir, self._config)
            cache.delete_item(name)
            return Connector._output(0, self._get_folder_content(target_dir))
        else:
            return Connector._output(self.ERR_FILE_NOT_FOUND)

    def copy(self, path, name, new_target):
        """ copy file to another folder
        :param path: relative path
        :param name: file to copy
        :param new_target: target folder or file
        """
        target_dir = self._target_dir(path)
        target = target_dir + '/' + name
        if os.path.isdir(target):
            return Connector._output(self.ERR_INVALID_PARAMETER)
        if os.path.isfile(target):
            return Connector._output(self.ERR_FILE_NOT_FOUND)

        copy_target_dir = self._target_dir('') + new_target

        if os.path.isdir(copy_target_dir):
            try:
                shutil.copy(target, copy_target_dir + '/' + name)
            except IOError:
                return Connector._output(self.ERR_COPY)

            cache = CacheDir(copy_target_dir, self._config)
            cache.update_item(name)
            return Connector._output(0)
        else:
            if os.path.isfile(copy_target_dir):
                return Connector._output(self.ERR_COPY_FILE_EXISTS)

            if not os.path.isdir(os.path.dirname(copy_target_dir)):
                return Connector._output(self.ERR_COPY_DIR_NOT_FOUND)

            if not re.match('^[a-z0-9-_.]+$', os.path.basename(copy_target_dir)):
                return Connector._output(self.ERR_INVALID_PARAMETER)

            try:
                shutil.copyfile(target, copy_target_dir)
            except IOError:
                return Connector._output(self.ERR_COPY)

            cache = CacheDir(os.path.dirname(copy_target_dir), self._config)
            cache.update_item(os.path.basename(copy_target_dir))
            return Connector._output(0)

    def move(self, path, name, new_target):
        """ move file to another folder
        :param path: relative path
        :param name: file to move
        :param new_target: target folder or file
        """
        target_dir = self._target_dir(path)
        target = target_dir + '/' + name
        if isdir(target):
            return Connector._output(self.ERR_INVALID_PARAMETER)
        if not isfile(target):
            return Connector._output(self.ERR_FILE_NOT_FOUND)

        copy_target_dir = self._target_dir('') + new_target

        if isdir(copy_target_dir):
            try:
                shutil.move(target, copy_target_dir + '/' + name)
            except IOError:
                return Connector._output(self.ERR_COPY)

            cache = CacheDir(copy_target_dir, self._config)
            cache.update_item(name)
        else:
            if isfile(copy_target_dir):
                return Connector._output(self.ERR_COPY_FILE_EXISTS)

            if not isdir(os.path.dirname(copy_target_dir)):
                return Connector._output(self.ERR_COPY_DIR_NOT_FOUND)

            if not re.match('^[a-z0-9-_.]+$', os.path.basename(copy_target_dir)):
                return Connector._output(self.ERR_INVALID_PARAMETER)

            try:
                os.rename(target, copy_target_dir)
            except IOError:
                return Connector._output(self.ERR_COPY)

            cache = CacheDir(os.path.dirname(copy_target_dir), self._config)
            cache.update_item(os.path.basename(copy_target_dir))

        cache = CacheDir(target_dir, self._config)
        cache.delete_item(name)

        return Connector._output(0, self._get_folder_content(target_dir))


class CacheDir:
    """ manipulate  with cached content of directory """

    CACHE_FILENAME = '.htdircache'

    def __init__(self, cache_directory, config):
        self._dir = cache_directory.rstrip('/') + '/'
        self._config = config
        self._cachefile = self._dir + self.CACHE_FILENAME
        if os.path.isfile(self._cachefile) and os.path.getmtime(self._cachefile) > time.time() - 7200:
            with open(self._cachefile) as data_file:
                try:
                    self._items = json.load(data_file)
                except ValueError:
                    self.refresh()
        else:
            self.refresh()

    def get_files(self):
        """ returns array of folders and files in cache """
        return self._items.values()

    def refresh(self):
        """ refresh entire cache """
        result = {}
        for filename in glob.glob(self._dir + '*'):
            file_info = File(filename, self._config)
            result[os.path.basename(os.path.normpath(filename))] = file_info.get_params()
        self._items = result
        self._save()

    def update_item(self, item_name):
        """ add or update file or directory in cache
        :param item_name: name of file or folder
        """
        file_info = File(self._dir + item_name, self._config)
        self._items[os.path.basename(os.path.normpath(item_name))] = file_info.get_params()
        self._save()

    def delete_item(self, item_name):
        """ delete file or directory in cache
        :param item_name: name of file or folder
        """
        self._items.pop(os.path.basename(os.path.normpath(item_name)), None)
        self._save()

    def _save(self):
        with open(self._cachefile, mode='w') as cache_file:
            json.dump(self._items, cache_file, ensure_ascii=False)


class File:
    """ represent file or folder """

    def __init__(self, filename, config):
        self._file = filename
        self._config = config

    def get_params(self):
        """
        return info about file or folder as dictionary with keys:
        'name' - name of file or folder
        'type' - 'file' or 'dir'
        'size' - filesize in bytes, None for directory
        'date' - date of file in format ISO8601
        'imgsize' - list with width and height if file is image, otherwise None
        'thumbnail' - thumbnail of image as base64 data uri
        """

        return {
            'name': os.path.basename(self._file),
            'type': self._filetype(),
            'size': (os.path.getsize(self._file) if os.path.isfile(self._file) else None),
            'date': self._date(),
            'imgsize': self._image_size(),
            'thumbnail': self._thumbnail()
        }

    def _filetype(self):
        if os.path.isfile(self._file):
            return 'file'
        elif os.path.isdir(self._file):
            return 'dir'
        else:
            return 'unknown'

    def _date(self):
        date = os.path.getmtime(self._file)
        return datetime.fromtimestamp(date, pytz.UTC).isoformat()

    def _image_size(self):
        if not os.path.isfile(self._file):
            return None
        ext = os.path.splitext(self._file)[1][1:].strip().lower()
        if ext != 'jpg' and ext != 'jpeg' and ext != 'gif' and ext != 'png':
            return None

        try:
            im = Image.open(self._file)
        except IOError:
            return None

        return im.size

    def _thumbnail(self):
        if not os.path.isfile(self._file):
            return ''
        ext = os.path.splitext(self._file)[1][1:].strip().lower()
        if ext != 'jpg' and ext != 'jpeg' and ext != 'gif' and ext != 'png':
            return ''

        try:
            im = Image.open(self._file)
        except IOError:
            return None

        im.thumbnail([100, 100], Image.ANTIALIAS)

        string_file = StringIO()
        im.save(string_file, 'JPEG', quality=90)
        return 'data:image/jpeg;base64,' + base64.encodestring(string_file.getvalue())

    @staticmethod
    def remove_accents(input_str):
        """ remove accent from string
        :param input_str: string with accents
        """
        nkfd_form = unicodedata.normalize('NFKD', unicode(input_str))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])