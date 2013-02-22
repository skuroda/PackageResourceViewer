"""
MIT License
Copyright (c) 2013 Scott Kuroda <scott.kuroda@gmail.com>

SHA Hash: b685c10
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

    packages_path = sublime.installed_packages_path()

    if os.path.exists(os.path.join(packages_path, sublime_package)):
        file_set.update(_list_files_in_zip(packages_path, sublime_package))


    packages_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"

    if os.path.exists(os.path.join(packages_path, sublime_package)):
       file_set.update(_list_files_in_zip(packages_path, sublime_package))

    file_list = []
    ignored_regex_list = []
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

##################################### TESTS ####################################
import sys
import unittest

class GetPackageAssetTests(unittest.TestCase):
    def test_list_package_files(self):
        tc = list_package_files
        aseq = self.assertEquals
        default_files = ['Add Line Before.sublime-macro',
        'Add Line in Braces.sublime-macro', 'Add Line.sublime-macro',
        'Context.sublime-menu', 'Default (Linux).sublime-keymap',
        'Default (Linux).sublime-mousemap', 'Default (OSX).sublime-keymap',
        'Default (OSX).sublime-mousemap', 'Default (Windows).sublime-keymap',
        'Default (Windows).sublime-mousemap', 'Default.sublime-commands',
        'Delete Left Right.sublime-macro', 'Delete Line.sublime-macro',
        'Delete to BOL.sublime-macro', 'Delete to EOL.sublime-macro',
        'Delete to Hard BOL.sublime-macro', 'Delete to Hard EOL.sublime-macro',
        'Distraction Free.sublime-settings', 'Find Results.hidden-tmLanguage',
        'Find in Files.sublime-menu', 'Icon.png',
        'Indentation Rules - Comments.tmPreferences',
        'Indentation Rules.tmPreferences', 'Indentation.sublime-menu',
        'Indexed Symbol List.tmPreferences', 'Main.sublime-menu',
        'Minimap.sublime-settings', 'Preferences (Linux).sublime-settings',
        'Preferences (OSX).sublime-settings', 'Preferences (Windows).sublime-settings',
        'Preferences.sublime-settings', 'Regex Format Widget.sublime-settings',
        'Regex Widget.sublime-settings', 'Side Bar Mount Point.sublime-menu',
        'Side Bar.sublime-menu', 'Symbol List.tmPreferences', 'Syntax.sublime-menu',
        'Tab Context.sublime-menu', 'Widget Context.sublime-menu',
        'Widget.sublime-settings', 'block.py', 'comment.py', 'copy_path.py',
        'delete_word.py', 'detect_indentation.py', 'duplicate_line.py',
        'echo.py', 'exec.py', 'fold.py', 'font.py', 'goto_line.py',
        'indentation.py', 'kill_ring.py', 'mark.py', 'new_templates.py',
        'open_file_settings.py', 'open_in_browser.py', 'pane.py', 'paragraph.py',
        'save_on_focus_lost.py', 'scroll.py',
        'send2trash\\__init__.py', 'send2trash\\plat_osx.py',
        'send2trash\\plat_other.py', 'send2trash\\plat_win.py',
        'set_unsaved_view_name.py', 'side_bar.py', 'sort.py', 'swap_line.py',
        'switch_file.py', 'symbol.py', 'transform.py', 'transpose.py',
        'trim_trailing_white_space.py']

        aseq(tc("Default"), sorted(default_files))

        default_files = ['Add Line Before.sublime-macro',
        'Add Line in Braces.sublime-macro', 'Add Line.sublime-macro',
        'Context.sublime-menu', 'Default (Linux).sublime-keymap',
        'Default (Linux).sublime-mousemap', 'Default (OSX).sublime-keymap',
        'Default (OSX).sublime-mousemap', 'Default (Windows).sublime-keymap',
        'Default (Windows).sublime-mousemap', 'Default.sublime-commands',
        'Delete Left Right.sublime-macro', 'Delete Line.sublime-macro',
        'Delete to BOL.sublime-macro', 'Delete to EOL.sublime-macro',
        'Delete to Hard BOL.sublime-macro', 'Delete to Hard EOL.sublime-macro',
        'Distraction Free.sublime-settings', 'Find Results.hidden-tmLanguage',
        'Find in Files.sublime-menu', 'Icon.png',
        'Indentation Rules - Comments.tmPreferences',
        'Indentation Rules.tmPreferences', 'Indentation.sublime-menu',
        'Indexed Symbol List.tmPreferences', 'Main.sublime-menu',
        'Minimap.sublime-settings', 'Preferences (Linux).sublime-settings',
        'Preferences (OSX).sublime-settings', 'Preferences (Windows).sublime-settings',
        'Preferences.sublime-settings', 'Regex Format Widget.sublime-settings',
        'Regex Widget.sublime-settings', 'Side Bar Mount Point.sublime-menu',
        'Side Bar.sublime-menu', 'Symbol List.tmPreferences', 'Syntax.sublime-menu',
        'Tab Context.sublime-menu', 'Widget Context.sublime-menu',
        'Widget.sublime-settings', 'block.py', 'comment.py', 'copy_path.py',
        'delete_word.py', 'detect_indentation.py', 'duplicate_line.py',
        'echo.py', 'exec.py', 'fold.py', 'font.py', 'goto_line.py',
        'indentation.py', 'kill_ring.py', 'mark.py', 'new_templates.py',
        'open_file_settings.py', 'open_in_browser.py', 'pane.py', 'paragraph.py',
        'save_on_focus_lost.py', 'scroll.py',
        'set_unsaved_view_name.py', 'side_bar.py', 'sort.py', 'swap_line.py',
        'switch_file.py', 'symbol.py', 'transform.py', 'transpose.py',
        'trim_trailing_white_space.py']

        aseq(tc("Default", ["send2trash"]), sorted(default_files))

    def test_get_packages_list(self):
        packages_list = ['ASP', 'ActionScript', 'AdvancedNewFile', 'AppleScript',
        'Batch File', 'C#', 'C++', 'CSS', 'Clojure', 'Color Scheme - Default',
        'D', 'Default', 'Diff', 'Erlang', 'FuzzyFileNav', 'Go', 'Graphviz',
        'Groovy', 'HTML', 'Haskell', 'Java', 'JavaScript', 'LaTeX',
        'Language - English', 'Lisp', 'Lua', 'Makefile', 'Markdown', 'Matlab',
        'OCaml', 'Objective-C', 'PHP', 'PackageResources', 'Perl', 'Python', 'R',
        'Rails', 'Regular Expressions', 'RestructuredText', 'Ruby', 'SQL', 'Scala',
        'ShellScript', 'TCL', 'Text', 'Textile', 'Theme - Default', 'User', 'XML',
        'YAML', 'PackageHelper']

        tc = get_packages_list
        aseq = self.assertEquals
        aseq(tc(), sorted(packages_list))

    def test_get_package_asset(self):
        tc = get_package_resource
        aseq = self.assertEquals

        # Search sublime-package
        res = tc("Default", "copy_path.py")
        aseq(res, """\
import sublime, sublime_plugin

class CopyPathCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if len(self.view.file_name()) > 0:
            sublime.set_clipboard(self.view.file_name())
            sublime.status_message("Copied file path")

    def is_enabled(self):
        return self.view.file_name() != None and len(self.view.file_name()) > 0
""")
        res = tc("Default", "not_here.txt")
        aseq(res, None)



    def test_get_package_and_asset_name(self):
        tc = get_package_and_asset_name
        aseq = self.assertEquals

        # Test relative unneted
        r1 = (tc("Packages/Relative/one.py"))
        r2 = (tc("Packages\\Relative\\one.py"))
        r3 = (tc("Packages/Relative/nested/one.py"))
        r4 = (tc("Packages\\Relative\\nested\\one.py"))

        # Test nested
        r5 = (tc("C:\\Abs\\Packages\\ZipPseudo.sublime-package\\nested\\sort.py"))
        r6 = (tc(sublime.packages_path() + "/Absolute/Nested/asset.pth"))
        r7 = (tc(sublime.packages_path() + "\\Absolute\\Nested\\asset.pth"))
        r8 = (tc(sublime.installed_packages_path() + "/Absolute.sublime-package/Nested/asset.pth"))
        r9 = (tc(sublime.installed_packages_path() + "\\Absolute.sublime-package\\Nested\\asset.pth"))
        executable_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
        r10 = (tc(executable_path + "/Absolute.sublime-package/Nested/asset.pth"))
        r11 = (tc(executable_path + "\\Absolute.sublime-package\\Nested\\asset.pth"))

        # Test Unnested
        r12 = (tc(sublime.packages_path() + "/Absolute/asset.pth"))
        r13 = (tc(sublime.packages_path() + "\\Absolute\\asset.pth"))
        r14 = (tc(sublime.installed_packages_path() + "/Absolute.sublime-package/asset.pth"))
        r15 = (tc(sublime.installed_packages_path() + "\\Absolute.sublime-package\\asset.pth"))
        executable_path = os.path.dirname(sublime.executable_path()) + os.sep + "Packages"
        r16 = (tc(executable_path + "/Absolute.sublime-package/asset.pth"))
        r17 = (tc(executable_path + "\\Absolute.sublime-package\\asset.pth"))

        aseq(r1, ('Relative',   'one.py'))
        aseq(r2, ('Relative',   'one.py'))
        aseq(r3, ('Relative',   'nested/one.py'))
        aseq(r4, ('Relative',   'nested\\one.py'))
        aseq(r5, (None,  None))
        aseq(r6, ('Absolute',   'Nested' + os.sep + 'asset.pth'))
        aseq(r7, ('Absolute',   'Nested' + os.sep + 'asset.pth'))
        aseq(r8, ('Absolute',   'Nested' + os.sep + 'asset.pth'))
        aseq(r9, ('Absolute',   'Nested' + os.sep + 'asset.pth'))
        aseq(r10, ('Absolute',   'Nested' + os.sep + 'asset.pth'))
        aseq(r11, ('Absolute',   'Nested' + os.sep + 'asset.pth'))

        aseq(r12, ('Absolute', 'asset.pth'))
        aseq(r13, ('Absolute', 'asset.pth'))
        aseq(r14, ('Absolute', 'asset.pth'))
        aseq(r15, ('Absolute', 'asset.pth'))
        aseq(r16, ('Absolute', 'asset.pth'))
        aseq(r17, ('Absolute', 'asset.pth'))

################ ONLY LOAD TESTS WHEN DEVELOPING NOT ON START UP ###############

try:               times_module_has_been_reloaded  += 1
except NameError:  times_module_has_been_reloaded  =  0       #<em>re</em>loaded

if times_module_has_been_reloaded:
    target = __name__
    suite = unittest.TestLoader().loadTestsFromName(target)

    unittest.TextTestRunner(stream = sys.stdout,  verbosity=0).run(suite)

    print ("running tests", target)
    print ('\nReloads: %s' % times_module_has_been_reloaded)

################################################################################
