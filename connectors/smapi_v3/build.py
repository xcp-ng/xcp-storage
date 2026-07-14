#!/usr/bin/env python3
#
# Copyright (C) 2026  Vates SAS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import ast
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from xcp_storage.typing import Final, List, NoReturn

# ==============================================================================

PLUGINS_FOLDER: Final = "plugins"

PLUGIN_TYPE_FILES: Final = {
    "datapath": ["plugin.py", "data.py", "datapath.py"],
    "volume": ["plugin.py", "sr.py", "volume.py"],
}

SKELETON_TO_PLUGIN_NAME: Final = {
    "Data_skeleton": "Data",
    "Datapath_skeleton": "Datapath",
    "Plugin_skeleton": "Plugin",
    "SR_skeleton": "SR",
    "Volume_skeleton": "Volume",
}

METHOD_TO_SCRIPT_NAME_OVERRIDE: Final = {
    "query": "Query",
}

# ------------------------------------------------------------------------------

def fail(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(1)

# ------------------------------------------------------------------------------

def get_class_base_name(base: ast.expr) -> str:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return ""

def is_override_decorator(decorator: ast.expr) -> bool:
    return (
        isinstance(decorator, ast.Name) and decorator.id == "override" or
        isinstance(decorator, ast.Attribute) and decorator.attr == "override"
    )

# ------------------------------------------------------------------------------

def process_command_names(plugin_path: Path) -> List[str]: # noqa: C901
    command_names: List[str] = []

    try:
        root = ast.parse(plugin_path.read_text(encoding="utf-8"), filename=plugin_path.name)
        for node in root.body:
            # 1. Find a class.
            if not isinstance(node, ast.ClassDef):
                continue

            # 2. Check for a skeleton base (so a plugin name).
            plugin_name = None

            for base in node.bases:
                plugin_name = SKELETON_TO_PLUGIN_NAME.get(get_class_base_name(base))
                if plugin_name:
                    break

            if not plugin_name:
                continue

            # 3. Process methods and list all "override".
            for attribute in node.body:
                if not isinstance(attribute, ast.FunctionDef):
                    continue

                for decorator in attribute.decorator_list:
                    if is_override_decorator(decorator):
                        script_name = METHOD_TO_SCRIPT_NAME_OVERRIDE.get(attribute.name, attribute.name)
                        command_names.append(f"{plugin_name}.{script_name}")
                        break
    except Exception as e:
        fail(f"Unable to process SMAPIv3 plugin command names: `{plugin_path.name}`: `{e}`.")

    return command_names

# ------------------------------------------------------------------------------

def process_plugin(build_path: Path, plugins_path: Path, plugin_path: Path) -> None:
    plugin_name = plugin_path.name
    relative_plugin_path = plugin_path.relative_to(plugins_path)

    # 1. Process command names of a plugin.
    command_names = process_command_names(plugin_path)
    if not command_names:
        print(f"Ignore plugin without command: `{relative_plugin_path}`.", file=sys.stderr)
        return

    # 2. Create destination path.
    destination_path = build_path / relative_plugin_path.parent
    destination_path.mkdir(parents=True, exist_ok=True)

    # 3. Copy the plugin file (.py) to the build destination path.
    copied_plugin_path = destination_path / plugin_name
    try:
        shutil.copy2(plugin_path, copied_plugin_path)
        copied_plugin_path.chmod(0o755)
        print(f"Copy plugin: {relative_plugin_path} -> {copied_plugin_path.relative_to(build_path)}")
    except OSError as e:
        fail(f"Unable to copy SMAPIv3 plugin `{plugin_name}` to build folder: `{e}`.")

    # 4. Create symlinks.
    for command_name in command_names:
        symlink_path = destination_path / command_name
        try:
            symlink_path.symlink_to(plugin_name)
            print(f"{symlink_path.relative_to(build_path)} -> {plugin_name}")
        except OSError as e:
            fail(f"Unable to create SMAPIv3 symlink plugin: `{command_name}`: `{e}`.")

def prepare_build_path(build_path: Path) -> None:
    if build_path.exists():
        try:
            shutil.rmtree(build_path)
        except OSError as e:
            fail(f"Unable to remove SMAPIv3 plugins build folder: `{e}`.")

    try:
        build_path.mkdir()
    except OSError as e:
        fail(f"Unable to create SMAPIv3 plugins build folder: `{e}`.")

def process_plugins(build_path: Path, plugins_path: Path) -> None:
    if not plugins_path.is_dir():
        fail(f"Not a valid SMAPIv3 plugins folder: `{plugins_path}`.")
    prepare_build_path(build_path)

    for plugin_type, allowed_filenames in PLUGIN_TYPE_FILES.items():
        # 1. Process a plugin type directory.
        plugin_type_path = plugins_path / plugin_type
        if not plugin_type_path.is_dir():
            fail(f"Not a valid SMAPIv3 plugin type folder: `{plugin_type_path}`.")

        # 2. Process each plugin directory.
        for root_plugin_path in sorted(plugin_type_path.iterdir()):
            if not root_plugin_path.is_dir():
                continue

            # 3. Process each allowed file of a plugin.
            for allowed_filename in allowed_filenames:
                plugin_path = root_plugin_path / allowed_filename
                if plugin_path.is_file():
                    process_plugin(build_path, plugins_path, plugin_path)

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build SMAPIv3 plugins, copy source files and generate command symlinks."
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Target directory where the plugins and symlinks will be generated."
    )

    try:
        process_plugins(parser.parse_args().output.resolve(), Path(__file__).parent.resolve() / PLUGINS_FOLDER)
    except Exception as e:
        fail(f"Exception during build of SMAPIv3 plugins: `{e}`.")
