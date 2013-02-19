import sublime
import sublime_plugin
import re
from .package_resources.package_resources import *

class ListPackageFilesCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.packages = get_packages_list()
        self.show_quick_panel(self.packages, self.callback_function)

    def callback_function(self, index):
        if index == -1:
            return
        self.package = self.packages[index]
        ignored_dirs = sublime.load_settings("PackageHelper.sublime-settings").get("ignored_directories", [])
        self.files = list_package_files(self.package, ignored_dirs)

        self.show_quick_panel(self.files, self.package_file_callback)

    def package_file_callback(self, index):
        if index == -1:
            return
        self.window.run_command("open_file", {"file": "${packages}/" + self.package + "/" + self.files[index]})

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)