import sublime
import sublime_plugin
import os
import threading
import errno

VERSION = int(sublime.version())
IS_ST3 = VERSION >=3006
if IS_ST3:
    from PackageResourceViewer.package_resources import *
else:
    from package_resources import *

def no_packages_available_message():
    sublime.message_dialog("PackageResourceViewer\n\nThere are no more packages available to extract.")

def show_quick_panel(window, informations, on_done, selected_index=0):
    window.show_quick_panel( informations, on_done, sublime.KEEP_OPEN_ON_FOCUS_LOST, selected_index )

def format_packages_list(packages_list, maximum_length=500):
    length = 0
    contents = []

    for index, name in enumerate( packages_list ):
        contents.append( "%s. %s" % ( index + 1, name ) )
        length += len( contents[-1] )

        if length > maximum_length:
            remaining = len( packages_list ) - index - 1
            if remaining > 0: contents.append( "and more {} packages!".format( remaining ) )
            break

    return ", ".join( contents )

class PackageResourceViewerBase(sublime_plugin.WindowCommand):
    def run(self):
        self.previous_index = -1
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        self.packages = get_packages_list(True, self.settings.get("ignore_patterns", []))
        self.path = []
        self.path_objs = []
        self.path_index = []
        self.show_quick_panel(self.packages, self.package_list_callback)

    def package_list_callback(self, index):
        if index == -1:
            return

        self.package = self.packages[index]
        ignore_patterns = self.settings.get("ignore_patterns", [])
        self.package_files = {}
        self.quick_panel_files = self.create_quick_panel_file_list(self.package_files)
        self.add_entry_to_path_obj()
        self.path_index.append(index)
        self.show_quick_panel(self.quick_panel_files, self.package_file_callback)

    def add_entry_to_path_obj(self, entry=""):
        if len(self.path_objs) == 0 and entry == "":
            self.path_objs.append(self.package_files)
        else:
            self.path.append(entry)
            self.path_objs.append(self.path_objs[-1][entry])

    def pop_entry_from_path_obj(self):
        if len(self.path_objs) > 0:
            if len(self.path) > 0:
                self.path.pop()
            self.path_objs.pop()

    def is_file(self, entry):
        return len(self.path_objs[-1][entry]) == 0


    def create_quick_panel_file_list(self, files_obj):
        quick_panel_files = [".."]
        if len(files_obj) == 0:
            ignore_patterns = self.settings.get("ignore_patterns", [])
            files_list = list_package_files(self.package, ignore_patterns)
            for entry in files_list:
                self.create_file_entry(entry, self.package_files)
            dirs, files = self.split_dirs_and_files(self.package_files)
        else:
            dirs, files = self.split_dirs_and_files(files_obj)

        quick_panel_files += dirs
        quick_panel_files += files
        return quick_panel_files

    def create_file_entry(self, file_path, obj):
        split_file = file_path.split("/", 1)
        if len(split_file) > 1:
            if split_file[0] not in obj:
                obj[split_file[0]] = {}
            self.create_file_entry(split_file[1], obj[split_file[0]])
        else:
            obj[file_path] = {}

    def split_dirs_and_files(self, obj):
        files = []
        dirs = []

        for key in obj.keys():
            entry = obj[key]
            if len(entry) == 0:
                files.append(key)
            else:
                dirs.append(key + "/")

        return sorted(dirs), sorted(files)

    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.quick_panel_files[index]

        if entry == "..":
            if len(self.path_index) != 0:
                index = self.path_index.pop()
            self.pop_entry_from_path_obj()
            if len(self.path_objs) == 0:
                self.show_quick_panel(self.packages, self.package_list_callback, index)
            else:
                self.quick_panel_files = self.create_quick_panel_file_list(self.path_objs[-1])
                self.show_quick_panel(self.quick_panel_files, self.package_file_callback, index)
        else:
            entry = entry.replace("/", "")
            self.path_index.append(index)
            if self.is_file(entry):
                self.pre_open_file_setup(entry)
                view = self.open_file(self.package, "/".join(self.path + [entry]))
                sublime.set_timeout(lambda: self.setup_view(view), 10)
                if self.settings.get("open_multiple", False):
                    self.show_quick_panel(self.quick_panel_files, self.package_file_callback)
            else:
                self.add_entry_to_path_obj(entry)
                self.quick_panel_files = self.create_quick_panel_file_list(self.path_objs[-1])
                self.show_quick_panel(self.quick_panel_files, self.package_file_callback)

    def pre_open_file_setup(self, entry):
        pass

    def setup_view(self, view):
        pass

    def show_quick_panel(self, options, done_callback, index=None):
        if index is None or not IS_ST3 or not self.settings.get("return_to_previous", False):
            sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)
        else:
            sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback, selected_index=index), 10)

    def open_file(self, package, resource):
        resource_path = os.path.join(sublime.packages_path(), package, resource)
        view = self.find_open_file(resource_path)
        if view:
            self.window.focus_view(view)
        else:
            view = self.window.open_file(resource_path)
            if not os.path.exists(resource_path):
                content = get_resource(package, resource)
                view.settings().set("buffer_empty", True)
                sublime.set_timeout(lambda: self.insert_text(content, view), 10)
                if self.settings.get("single_command", True):
                    view.settings().set("create_dir", True)
                    view.set_scratch(True)

        return view

    def insert_text(self, content, view):
        if not view.is_loading():
            view.run_command("insert_content", {"content": content})
            view.settings().set("buffer_empty", False)
        else:
            sublime.set_timeout(lambda: self.insert_text(content, view), 10)

    def find_open_file(self, path):
        view = None
        if IS_ST3:
            view = self.window.find_open_file(path)
        return view


class PackageResourceViewerCommand(PackageResourceViewerBase):
    def is_visible(self):
        settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        return settings.get("single_command", True)


class ViewPackageFileCommand(PackageResourceViewerBase):
    def setup_view(self, view):
        if not view.is_loading():
            view.set_read_only(True)
            view.set_scratch(True)
        else:
            sublime.set_timeout(lambda: self.setup_view(view), 10)

    def is_visible(self):
        settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        return not settings.get("single_command", True)

class EditPackageFileCommand(PackageResourceViewerBase):
    def pre_open_file_setup(self, entry):
        package_path = os.path.join(sublime.packages_path(), self.package, os.sep.join(self.path))
        self.create_folder(package_path)

    def create_folder(self, path):
        try:
            os.makedirs(path)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

    def setup_view(self, view):
        if not view.is_loading():
            view.set_read_only(False)
            view.run_command("save")
        else:
            sublime.set_timeout(lambda: self.setup_view(view), 15)

    def is_visible(self):
        settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        return not settings.get("single_command", True)

class PackageResourceViewerEvents(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        if view.settings().get("create_dir", False):
            if not os.path.exists(view.file_name()):
                directory = os.path.dirname(view.file_name())
                self.create_folder(directory)

    def on_modified(self, view):
        if view.settings().get("create_dir", False):
            if not view.settings().get("buffer_empty", False):
                if view.is_scratch():
                    view.set_scratch(False)


    def create_folder(self, path):
        try:
            os.makedirs(path)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise

class ExtractPackageCommand(sublime_plugin.WindowCommand):
    def run(self):
        thread = ExtractPackagesThread(self.window)
        thread.start()

    def is_visible(self):
        return VERSION >= 3006

class ExtractPackagesThread(threading.Thread):

    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

        self.exclusion_flag   = " (excluded)"
        self.inclusion_flag   = " (selected)"
        self.last_picked_item = 0
        self.last_excluded_items = 0

    def run(self):
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        self.repositories_list = [""]
        self.repositories_list.extend( get_sublime_packages(True, self.settings.get("ignore_patterns", [])) )

        if len( self.repositories_list ) < 2:
            no_packages_available_message()
            return

        self.update_start_item_name()
        show_quick_panel( self.window, self.repositories_list, self.on_done )

    def on_done(self, picked_index):

        if picked_index < 0:
            return

        if picked_index == 0:

            # No repositories selected, reshow the menu
            if self.get_total_items_selected() < 1:
                show_quick_panel( self.window, self.repositories_list, self.on_done )

            else:
                packages = []

                for index in range( 1, self.last_picked_item + 1 ):
                    package_name = self.repositories_list[index]

                    if package_name.endswith( self.exclusion_flag ):
                        continue

                    if package_name.endswith( self.inclusion_flag ):
                        package_name = package_name[:-len( self.inclusion_flag )]

                    packages.append( package_name )

                def extract():
                    packages_path = sublime.packages_path()

                    for package_name in packages:
                        full_path = os.path.join(packages_path, package_name, '.extracted-sublime-package')

                        if not os.path.exists(full_path):
                            extract_package(package_name)

                    sublime.message_dialog("PackageResourceViewer\n\nSuccessfully extracted the packages:\n%s" % (
                            format_packages_list(packages, 1000) ) )

                thread = threading.Thread( target=extract )
                thread.start()

        else:

            if picked_index <= self.last_picked_item:
                picked_package = self.repositories_list[picked_index]

                if picked_package.endswith( self.inclusion_flag ):
                    picked_package = picked_package[:-len( self.inclusion_flag )]

                if picked_package.endswith( self.exclusion_flag ):

                    if picked_package.endswith( self.exclusion_flag ):
                        picked_package = picked_package[:-len( self.exclusion_flag )]

                    self.last_excluded_items -= 1
                    self.repositories_list[picked_index] = picked_package + self.inclusion_flag

                else:
                    self.last_excluded_items += 1
                    self.repositories_list[picked_index] = picked_package + self.exclusion_flag

            else:
                self.last_picked_item += 1
                self.repositories_list[picked_index] = self.repositories_list[picked_index] + self.inclusion_flag

            self.update_start_item_name()
            self.repositories_list.insert( 1, self.repositories_list.pop( picked_index ) )

            show_quick_panel( self.window, self.repositories_list, self.on_done )

    def update_start_item_name(self):
        items = self.get_total_items_selected()

        if items:
            self.repositories_list[0] = "Start Extraction (%s of %s items selected)" % ( items, len( self.repositories_list ) - 1 )

        else:
            self.repositories_list[0] = "Select all the packages you would like to extract"

    def get_total_items_selected(self):
        return self.last_picked_item - self.last_excluded_items

class ExtractAllPackagesCommand(sublime_plugin.WindowCommand):
    def run(self):
        thread = ExtractAllPackagesThread(self.window)
        thread.start()

    def is_visible(self):
        return VERSION >= 3006

class ExtractAllPackagesThread(threading.Thread):

    def __init__(self, window):
        threading.Thread.__init__(self)
        self.window = window

        self.exclusion_flag   = " (selected)"
        self.inclusion_flag   = " (excluded)"
        self.last_picked_item = 0
        self.last_excluded_items = 0

    def run(self):
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")
        self.repositories_list = [""]
        self.packages = get_sublime_packages(True, self.settings.get("ignore_patterns", []))
        self.repositories_list.extend( self.packages )

        if len( self.repositories_list ) < 2:
            no_packages_available_message()
            return

        self.update_start_item_name()
        show_quick_panel( self.window, self.repositories_list, self.on_done )

    def on_done(self, picked_index):

        if picked_index < 0:
            return

        if picked_index == 0:

            # No repositories selected, reshow the menu
            if self.get_total_items_selected() == len( self.packages ):
                show_quick_panel( self.window, self.repositories_list, self.on_done )

            else:
                packages = set()
                extracted = []

                for index in range( 1, self.last_picked_item + 1 ):
                    package_name = self.repositories_list[index]

                    if package_name.endswith( self.exclusion_flag ):
                        continue

                    if package_name.endswith( self.inclusion_flag ):
                        package_name = package_name[:-len( self.inclusion_flag )]

                    packages.add( package_name )

                def extract():
                    packages_path = sublime.packages_path()

                    for package_name in self.packages:

                        if package_name not in packages:
                            full_path = os.path.join(packages_path, package_name, '.extracted-sublime-package')

                            if not os.path.exists(full_path):
                                extracted.append(package_name)
                                extract_package(package_name)

                    sublime.message_dialog("PackageResourceViewer\n\nSuccessfully extracted the packages:\n%s" % (
                            format_packages_list(extracted, 1000) ) )

                thread = threading.Thread( target=extract )
                thread.start()

        else:

            if picked_index <= self.last_picked_item:
                picked_package = self.repositories_list[picked_index]

                if picked_package.endswith( self.inclusion_flag ):
                    picked_package = picked_package[:-len( self.inclusion_flag )]

                if picked_package.endswith( self.exclusion_flag ):

                    if picked_package.endswith( self.exclusion_flag ):
                        picked_package = picked_package[:-len( self.exclusion_flag )]

                    self.last_excluded_items -= 1
                    self.repositories_list[picked_index] = picked_package + self.inclusion_flag

                else:
                    self.last_excluded_items += 1
                    self.repositories_list[picked_index] = picked_package + self.exclusion_flag

            else:
                self.last_picked_item += 1
                self.repositories_list[picked_index] = self.repositories_list[picked_index] + self.inclusion_flag

            self.update_start_item_name()
            self.repositories_list.insert( 1, self.repositories_list.pop( picked_index ) )

            show_quick_panel( self.window, self.repositories_list, self.on_done )

    def update_start_item_name(self):
        items = self.get_total_items_selected()
        total = len( self.packages )
        self.repositories_list[0] = "Start Extraction (%s of %s items selected)" % ( total - items, total )

    def get_total_items_selected(self):
        return self.last_picked_item - self.last_excluded_items

class InsertContentCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        self.view.insert(edit, 0, content)
