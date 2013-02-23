import sublime
import sublime_plugin
import re
import os

VERSION = int(sublime.version())

if VERSION >=3006:
    from PackageResourceViewer.package_resources import *
else:
    from package_resources import *

class PackageResourceViewerBase(sublime_plugin.WindowCommand):
    def run(self):
        self.packages = get_packages_list()
        self.show_quick_panel(self.packages, self.package_list_callback)
        self.settings = sublime.load_settings("PackageResourceViewer.sublime-settings")

    def package_list_callback(self, index):
        if index == -1:
            return
        self.package = self.packages[index]
        ignore_patterns = self.settings.get("ignore_patterns", [])
        self.files = [".."]
        self.files += list_package_files(self.package, ignore_patterns)
        self.show_quick_panel(self.files, self.package_file_callback)

    def package_file_callback(self, index):
        raise "Should be implemented by child class"

    def show_quick_panel(self, options, done_callback):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done_callback), 10)

    def open_file(self, package, resource):
        resource_path = os.path.join(sublime.packages_path(), package, resource)
        view = self.window.open_file(resource_path)
        if not os.path.exists(resource_path):
            content = get_package_resource(package, resource)
            sublime.set_timeout(lambda: self.insert_text(content, view), 10)
        return view

    def insert_text(self, content, view):
        if not view.is_loading():
            view.run_command("insert_content", {"content": content})
        else:
            sublime.set_timeout(lambda: self.insert_text(content, view), 10)

class ViewPackageFileCommand(PackageResourceViewerBase):
    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            view = self.open_file(self.package, entry)
            sublime.set_timeout(lambda: self.setup_view(view), 10)

            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)

    def setup_view(self, view):
        if not view.is_loading():
            view.set_read_only(True)
            view.set_scratch(True)
        else:
            sublime.set_timeout(lambda: self.setup_view(view), 10)


class EditPackageFileCommand(PackageResourceViewerBase):
    def package_file_callback(self, index):
        if index == -1:
            return
        entry = self.files[index]
        if entry == "..":
            self.show_quick_panel(self.packages, self.package_list_callback)
        else:
            package_path = os.path.join(sublime.packages_path(), self.package)
            resource_path = os.path.join(package_path, entry)
            self.create_folder(package_path)
            view = self.open_file(self.package, entry)

            sublime.set_timeout(lambda: self.setup_view(view), 15)
            if self.settings.get("open_multiple", False):
                self.show_quick_panel(self.files, self.package_file_callback)


    def create_folder(self, base):
        if not os.path.exists(base):
            parent = os.path.split(base)[0]
            if not os.path.exists(parent):
                self.create_folder(parent)
            os.mkdir(base)

    def setup_view(self, view):
        if not view.is_loading():
            view.set_read_only(False)
            view.run_command("save")
        else:
            sublime.set_timeout(lambda: self.setup_view(view), 15)


class InsertContentCommand(sublime_plugin.TextCommand):
    def run(self, edit, content):
        self.view.insert(edit, 0, content)
