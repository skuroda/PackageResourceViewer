"""
MIT License
Copyright (c) 2013 Scott Kuroda <scott.kuroda@gmail.com>

SHA: d10b8514a1a7c06ef18677ef07256db65aefff4f
"""
import sublime
import os
import zipfile
import tempfile
import re
import codecs
import sys

__all__ = [
    "get_package_resource",
    "list_package_files",
    "get_package_and_resource_name",
    "get_packages_list"
]


VERSION = int(sublime.version())

def get_package_resource(package_name, resource, get_path=False, recursive_search=False, return_binary=False, encoding="utf-8"):
    """
    Retrieve the resource specified in the specified package or None if it
    cannot be found.

    Arguments:
    package_name    Name of the packages whose resource you are searching for.
    resource        Name of the resource to search for

    Keyword arguments:
    get_path            Boolean representing if the path or the content of the
                        resource should be returned (default False)

    recursive_search    Boolean representing if the file specified should
                        search for resources recursively or take the file as
                        an absolute path. If recursive, the first matching
                        file will be returned (default False).

    return_binary       Boolean representing if the binary representation of
                        a file should be returned. Only takes affect if get_path
                        is True (default False).

    encoding            String representing the encoding to use when reading.
                        Only takes affect when return_binary is False
                        (default utf-8).

    Return Value:
    None if the resource does not exists. The contents of the resource if get_path is
    False. A path to the file if get_path is True.
    """

    packages_path = sublime.packages_path()
    sublime_package = package_name + ".sublime-package"
    path = None

    if VERSION > 3013:
        try:
            content = sublime.load_resource("Package/" + package_name + "/" + resource)
        except IOError:
            content = None
        return content
    else:
        if os.path.exists(os.path.join(packages_path, package_name)):
            if recursive_search:
                path = _find_file(os.path.join(packages_path, package_name), resource)
            elif os.path.exists(os.path.join(packages_path, package_name, resource)):
                path = os.path.join(packages_path, package_name, resource)

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

        if VERSION >= 3006:
            packages_path = sublime.installed_packages_path()

            if os.path.exists(os.path.join(packages_path, sublime_package)):
                ret_value = _search_zip_for_file(packages_path, sublime_package, resource, get_path, recursive_search, return_binary, encoding)
                if ret_value != None:
                    return ret_value

            packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

            if os.path.exists(os.path.join(packages_path, sublime_package)):
                ret_value = _search_zip_for_file(packages_path, sublime_package, resource, get_path, recursive_search, return_binary, encoding)
                if ret_value != None:
                    return ret_value

    return None


def list_package_files(package, ignore_patterns=[]):
    """
    List files in the specified package.
    """
    package_path = os.path.join(sublime.packages_path(), package) + os.sep
    sublime_package = package + ".sublime-package"
    path = None
    file_set = set()
    file_list = []
    if os.path.exists(package_path):
        for root, directories, filenames in os.walk(package_path):
            temp = root.replace(package_path, "")
            for filename in filenames:
                file_list.append(os.path.join(temp, filename))

    file_set.update(file_list)

    if VERSION >= 3006:
        packages_path = sublime.installed_packages_path()

        if os.path.exists(os.path.join(packages_path, sublime_package)):
            file_set.update(_list_files_in_zip(packages_path, sublime_package))

        packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

        if os.path.exists(os.path.join(packages_path, sublime_package)):
           file_set.update(_list_files_in_zip(packages_path, sublime_package))

    file_list = []

    for filename in file_set:
        ignore = False

        if not _ignore_file(filename, ignore_patterns):
            file_list.append(_normalize_to_sublime_path(filename))

    return sorted(file_list)

def _ignore_file(filename, ignore_patterns=[], iteration=0):

    ignore = False
    directory, base = os.path.split(filename)
    for pattern in ignore_patterns:
        if re.match(pattern, base):
            return True

    if len(directory) > 0:
        iteration += 1
        ignore = _ignore_file(directory, ignore_patterns, iteration)

    return ignore


def _normalize_to_sublime_path(path):
    path = os.path.normpath(path)
    path = re.sub(r"^([a-zA-Z]):", "/\\1", path)
    path = re.sub(r"\\", "/", path)
    return path

def get_package_and_resource_name(path):
    """
    This method will return the package name and resource name from a path.

    Arguments:
    path    Path to parse for package and resource name.
    """
    package = None
    resource = None
    path = _normalize_to_sublime_path(path)
    if os.path.isabs(path):
        packages_path = _normalize_to_sublime_path(sublime.packages_path())
        if path.startswith(packages_path):
            package, resource = _search_for_package_and_resource(path, packages_path)

        if int(sublime.version()) >= 3006:
            packages_path = _normalize_to_sublime_path(sublime.installed_packages_path())
            if path.startswith(packages_path):
                package, resource = _search_for_package_and_resource(path, packages_path)

            packages_path = _normalize_to_sublime_path(os.path.dirname(sublime.executable_path()) + os.sep + "Packages")
            if path.startswith(packages_path):
                package, resource = _search_for_package_and_resource(path, packages_path)
    else:
        path = re.sub(r"^Packages/", "", path)
        split = re.split(r"/", path, 1)
        package = split[0]
        package = package.replace(".sublime-package", "")
        resource = split[1]

    return (package, resource)

def get_packages_list(ignore_packages=True):
    """
    Return a list of packages.
    """
    package_set = set()
    package_set.update(_get_packages_from_directory(sublime.packages_path()))

    if int(sublime.version()) >= 3006:
        package_set.update(_get_packages_from_directory(sublime.installed_packages_path(), ".sublime-package"))

        executable_package_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
        package_set.update(_get_packages_from_directory(executable_package_path, ".sublime-package"))

    if ignore_packages:
        ignored_package_list = sublime.load_settings(
            "Preferences.sublime-settings").get("ignored_packages", [])
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
    Derive the package and resource from a path.
    """
    relative_package_path = path.replace(packages_path + "/", "")

    package, resource = re.split(r"/", relative_package_path, 1)
    package = package.replace(".sublime-package", "")
    return (package, resource)


def _list_files_in_zip(package_path, package):
    if not os.path.exists(os.path.join(package_path, package)):
        return []

    ret_value = []
    with zipfile.ZipFile(os.path.join(package_path, package)) as zip_file:
        ret_value = zip_file.namelist()
    return ret_value


def _search_zip_for_file(packages_path, package, file_name, path, recursive_search, return_binary, encoding):
    """
    Search a zip for an resource.
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

####################### Force resource viewer to reload ########################
if VERSION > 3000:
    from imp import reload
    if "PackageResourceViewer.package_resource_viewer" in sys.modules:
        reload(sys.modules["PackageResourceViewer.package_resource_viewer"])
else:
    if ".package_resource_viewer" in sys.modules:
        reload(sys.modules["package_resource_viewer"])