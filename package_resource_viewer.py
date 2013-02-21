import sublime
import sublime_plugin
import re
from PackageResourceViewer.package_resources.package_resources import *

VERSION = sublime.version()


class PackageResourceViewerBase(sublime_plugin.WindowCommand):
    def run(self):
        self.packages = get_packages_list()
        self.show_quick_panel(self.packages, self.package_list_callback)
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")

    def package_list_callback(self, index):
        if index == -1:
            return
        self.package = self.packages[index]
        ignored_dirs = self.settings.get("ignored_directories", [])
        self.files = [".."]
        self.files += list_package_files(self.package, ignored_dirs)
        self.show_quick_panel(self.files, self.package_file_callback)

    def package_file_callback(self, index):
        raise "Should be implemented by child class"

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)


class ViewPackageFileCommand(PackageResourceViewerBase):
    view_package_file = False
    view_package_file_list = []
    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            self.window.run_command("open_file", {"file": "${packages}/" + self.package + "/" + entry})

            ViewPackageFileCommand.view_package_file = True
            ViewPackageFileCommand.view_package_file_list.append(os.path.join(sublime.packages_path(), self.package, entry))

            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)


class EditPackageFileCommand(PackageResourceViewerBase):
    edit_package_file = False
    edit_package_file_list = []

    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            self.create_folder(os.path.join(sublime.packages_path(), self.package))
            EditPackageFileCommand.edit_package_file = True
            EditPackageFileCommand.edit_package_file_list.append(os.path.join(sublime.packages_path(), self.package, entry))
            self.window.run_command("open_file", {"file": "${packages}/" + self.package + "/" + entry})

            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)

    def create_folder(self, base):
        if not os.path.exists(base):
            parent = os.path.split(base)[0]
            if not os.path.exists(parent):
                self.create_folder(parent)
            os.mkdir(base)

class EventListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        if EditPackageFileCommand.edit_package_file:
            edit_package_file_list = EditPackageFileCommand.edit_package_file_list
            if view.file_name() in edit_package_file_list:
                view.run_command("save")
                view.set_read_only(False)
                edit_package_file_list.remove(view.file_name())                            
                if len(edit_package_file_list) == 0:
                    edit_package_file = False
        elif ViewPackageFileCommand.view_package_file:
            view_package_file_list = ViewPackageFileCommand.view_package_file_list
            if view.file_name() in view_package_file_list:
                view.set_read_only(True)
                view_package_file_list.remove(view.file_name())                            
                if len(edit_package_file_list) == 0:
                    view_package_file = False