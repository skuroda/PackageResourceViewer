import sublime
import sublime_plugin
import re
from ListPackageFiles.package_resources.package_resources import *


class ListPackageFilesCommand(sublime_plugin.WindowCommand):
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
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            self.window.run_command("open_file", {"file": "${packages}/" + self.package + "/" + entry})
            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)
