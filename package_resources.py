"""
MIT License
Copyright (c) 2013 Scott Kuroda <scott.kuroda@gmail.com>

SHA Hash: c25c048ec6
"""
import sublime
import os
import zipfile
import tempfile
import re
import codecs

def get_package_resource(package_name, asset_name, get_path=False, recursive_search=False, return_binary=False, encoding="utf-8"):
    """
    Retrieve the asset specified in the specified package or None if it
    cannot be found.

    Arguments:
    package_name    Name of the packages whose asset you are searching for.
    asset_name      Name of the asset to search for

    Keyword arguments:
    get_path            Boolean representing if the path or the content of the
                        asset should be returned (default False)

    recursive_search    Boolean representing if the file specified should
                        search for assets recursively or take the file as
                        an absolute path (default False).

    return_binary       Boolean representing if the binary representation of
                        a file should be returned. Only takes affect if get_path
                        is True (default False).

    encoding            String representing the encoding to use when reading.
                        Only takes affect when return_binary is False
                        (default utf-8).

    Return Value:
    None if the asset does not exists. The contents of the asset if get_path is
    False. A path to the file if get_path is True.
    """

    packages_path = sublime.packages_path()
    sublime_package = package_name + ".sublime-package"
    path = None

    if os.path.exists(os.path.join(packages_path, package_name)):
        if recursive_search:
            path = _find_file(os.path.join(packages_path, package_name), asset_name)
        elif os.path.exists(os.path.join(packages_path, package_name, asset_name)):
            path = os.path.join(packages_path, package_name, asset_name)

        if path != None and os.path.exists(path):

            if get_path:
                return  path
            else:
                if return_binary:
                    mode = "rb"
                    encoding = None
                else:
                    mode = "r"
                with codecs.open(path, mode, encoding=encoding) as file_obj:
                    content = file_obj.read()

                return content

    if int(sublime.version()) >= 3006:
        packages_path = sublime.installed_packages_path()

        if os.path.exists(os.path.join(packages_path, sublime_package)):
            ret_value = _search_zip_for_file(packages_path, sublime_package, asset_name, get_path, recursive_search, return_binary, encoding)
            if ret_value != None:
                return ret_value

        packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

        if os.path.exists(os.path.join(packages_path, sublime_package)):
            ret_value = _search_zip_for_file(packages_path, sublime_package, asset_name, get_path, recursive_search, return_binary, encoding)
            if ret_value != None:
                return ret_value

    return None

def list_package_files(package, ignored_directories=[]):
    package_path = os.path.join(sublime.packages_path(), package) + os.sep
    sublime_package = package + ".sublime-package"
    path = None
    file_set = set()
    file_list = []
    if os.path.exists(package_path):
        for root, directories, filenames in os.walk(package_path):
            for directory in directories:
                if directory in ignored_directories:
                    directories.remove(directory)

            temp = root.replace(package_path, "")
            for filename in filenames:
                file_list.append(os.path.join(temp, filename))

    file_set.update(file_list)

    if int(sublime.version()) >= 3006:
        packages_path = sublime.installed_packages_path()

        if os.path.exists(os.path.join(packages_path, sublime_package)):
            file_set.update(_list_files_in_zip(packages_path, sublime_package))


        packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

        if os.path.exists(os.path.join(packages_path, sublime_package)):
           file_set.update(_list_files_in_zip(packages_path, sublime_package))

    ignored_regex_list = []
    file_list = []

    for ignored_directory in ignored_directories:
        temp = "%s[/\\\]" % ignored_directory
        ignored_regex_list.append(re.compile(temp))

    is_ignored = False
    for filename in file_set:
        is_ignored = False
        for ignored_regex in ignored_regex_list:
            if ignored_regex.search(filename):
                is_ignored = True
                break

        if is_ignored:
            continue

        if os.sep == "/":
            replace_sep = "\\"
        else:
            replace_sep = "/"
        file_list.append(filename.replace(replace_sep, os.sep))

    return sorted(file_list)


def get_package_and_asset_name(path):
    """
    This method will return the package name and asset name from a path.

    Arguments:
    path    Path to parse for package and asset name.
    """
    package = None
    asset = None

    if os.path.isabs(path):
        packages_path = sublime.packages_path()
        if path.startswith(packages_path):
            package, asset = _search_for_package_and_resource(path, packages_path)

        if int(sublime.version()) >= 3006:
            packages_path = sublime.installed_packages_path()
            if path.startswith(packages_path):
                package, asset = _search_for_package_and_resource(path, packages_path)

            packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
            if path.startswith(packages_path):
                package, asset = _search_for_package_and_resource(path, packages_path)
    else:
        path = re.sub(r"^Packages[/\\]", "", path)
        split = re.split(r"[/\\]", path, 1)
        package = split[0]
        asset = split[1]

    return (package, asset)

def get_packages_list(ignore_packages=True):
    package_set = set()
    package_set.update(_get_packages_from_directory(sublime.packages_path()))

    if int(sublime.version()) >= 3006:
        package_set.update(_get_packages_from_directory(sublime.installed_packages_path(), ".sublime-package"))

        executable_package_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
        package_set.update(_get_packages_from_directory(executable_package_path, ".sublime-package"))

    if ignore_packages:
        ignored_package_list = sublime.load_settings(
            "Preferences.sublime-settings").get("ignored_packages")
        for ignored in ignored_package_list:
            package_set.discard(ignored)

    return sorted(list(package_set))

def _get_packages_from_directory(directory, file_ext=""):
    package_list = []
    for package in os.listdir(directory):
        if not package.endswith(file_ext):
            continue
        else:
            package = package.replace(file_ext, "")

        package_list.append(package)
    return package_list

def _search_for_package_and_resource(path, packages_path):
    """
    Derive the package and asset from  a path.
    """
    package = os.path.basename(os.path.dirname(path))

    directory, asset = os.path.split(path)
    if directory == packages_path:
        package = asset.replace(".sublime-package", "")
        asset = None
    else:
        package, temp_asset = _search_for_package_and_resource(directory, packages_path)

        if temp_asset is not None:
            temp_asset += os.sep + asset
            asset = temp_asset

    return (package, asset)

def _list_files_in_zip(package_path, package):
    if not os.path.exists(os.path.join(package_path, package)):
        return []

    ret_value = []
    with zipfile.ZipFile(os.path.join(package_path, package)) as zip_file:
        ret_value = zip_file.namelist()
    return ret_value


def _search_zip_for_file(packages_path, package, file_name, path, recursive_search, return_binary, encoding):
    """
    Search a zip for an asset.
    """
    if not os.path.exists(os.path.join(packages_path, package)):
        return None

    ret_value = None
    with zipfile.ZipFile(os.path.join(packages_path, package)) as zip_file:
        namelist = zip_file.namelist()
        if recursive_search:
            indices = [i for i, name in enumerate(namelist) if name.endswith(file_name)]
            if len(indices) > 0:
                file_name = namelist[indices[0]]
        if file_name in namelist:
            if path:
                temp_dir = tempfile.mkdtemp()
                file_location = zip_file.extract(file_name, temp_dir)
                ret_value =  file_location
            else:
                ret_value = zip_file.read(file_name)
                if not return_binary:
                    ret_value = ret_value.decode(encoding)

    return ret_value

def _find_file(abs_dir, file_name):
    """
    Find the absolute path to a specified file. Note that the first entry
    matching the file will be used, even if it exists elsewhere in the
    directory structure.
    """
    ret_path = None

    split = os.path.split(file_name)
    abs_dir = os.path.join(abs_dir, split[0])
    file_name = split[1]

    for root, dirnames, filenames in os.walk(abs_dir):
        if file_name in filenames:
            ret_path = os.path.join(root, file_name)
            break

    return ret_path
