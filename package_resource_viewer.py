import sublime
import sublime_plugin
import re
from PackageResourceViewer.package_resources.package_resources import *

VERSION = sublime.version()
PACKAGES_PATH = sublime.packages_path()


class PackageResourceViewerBase(sublime_plugin.WindowCommand):
    def run(self):
        self.packages = get_packages_list()
        self.show_quick_panel(self.packages, self.package_list_callback)
        self.settings = sublime.load_settings("ListPackageFiles.sublime-settings")

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

    def set_read_only(self, read_only):
        sublime.set_timeout(lambda: self.window.active_view().set_read_only(read_only), 10)

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)


class ViewPackageFileCommand(PackageResourceViewerBase):
    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            self.window.run_command("open_file", {"file": "${packages}/" + package_file})
            if self.package != "User" and self.settings.get("read_only_non_user", True):
                self.set_read_only(True)
            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)


class EditPackageFileCommand(PackageResourceViewerBase):
    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            self.create_folder(os.path.join(sublime.packages_path(), self.package))
            self.window.run_command("open_file", {"file": "${packages}/" + self.package + "/" + entry})
            self.set_read_only(False)
            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)

    def create_folder(self, base):
        if not os.path.exists(base):
            parent = os.path.split(base)[0]
            if not os.path.exists(parent):
                self.create_folder(parent)
            os.mkdir(base)