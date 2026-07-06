# Checking out the V8 source code: https://v8.dev/docs/source-code

from .common import *
import sys
import os
import shutil
import urllib.request

def install_depot_tools(root=os.getcwd(), skip_intall_if_exists=True):
    out_path = os.path.join(root, "depot_tools")
    if os.path.exists(out_path):
        if os.path.isdir(out_path):
            if not skip_intall_if_exists:
                os.removedirs(out_path)
        else:
            os.remove(out_path)
    if os.path.exists(out_path) and skip_intall_if_exists:
        return out_path
    if sys.platform == "win32":
        url = "https://storage.googleapis.com/chrome-infra/depot_tools.zip"
        zip_path = os.path.join(root, "depot_tools.zip")
        with urllib.request.urlopen(url) as i:
            with open(zip_path, "wb") as o:
                o.write(i.read())
        shutil.unpack_archive(zip_path, out_path)
        os.remove(zip_path)
    else:
        url = "https://chromium.googlesource.com/chromium/tools/depot_tools.git"
        run("git", "clone", url, cwd=root)
    return out_path

def update_depot_tools(root=os.getcwd()):
    run_cmd("gclient", cwd=root, root=root)

def v8_src_downloaded(root=os.getcwd()):
    gclient_path = os.path.join(root, ".gclient")
    if os.path.exists(gclient_path):
        with open(gclient_path, "r") as gclient:
            return gclient.read().find('"name": "v8"') != -1
    return False

def get_v8_src_code(root=os.getcwd()):
    run_cmd("fetch", "v8", cwd=root, root=root, print_result=True)

def download_all_build_deps(root=os.getcwd()):
    run_cmd("gclient", "sync", cwd=root, root=root, print_result=True)

def switch_to_version(version, root=os.getcwd()):
    v8_path = os.path.join(root, "v8")
    run_cmd("git", "checkout", "tags/{0}".format(version), cwd=v8_path, root=root, print_result=True)

def deps_sync_stamp_path(root=os.getcwd()):
    return os.path.join(root, "config", "deps-synced-version.txt")

def deps_synced_for_version(version, root=os.getcwd()):
    stamp_path = deps_sync_stamp_path(root=root)
    if not os.path.exists(stamp_path):
        return False
    with open(stamp_path, "r") as stamp:
        return stamp.read().strip() == version

def mark_deps_synced_for_version(version, root=os.getcwd()):
    stamp_path = deps_sync_stamp_path(root=root)
    os.makedirs(os.path.dirname(stamp_path), exist_ok=True)
    with open(stamp_path, "w") as stamp:
        stamp.write(version)

def patch_gn_dotfile_for_current_depot_tools(root=os.getcwd()):
    v8_path = os.path.join(root, "v8")
    dotfile_path = os.path.join(v8_path, ".gn")
    settings_path = os.path.join(v8_path, "build", "dotfile_settings.gni")

    if not os.path.exists(dotfile_path) or not os.path.exists(settings_path):
        return

    with open(dotfile_path, "r") as dotfile:
        dotfile_text = dotfile.read()
    with open(settings_path, "r") as settings:
        settings_text = settings.read()

    if (
        "exec_script_whitelist" in dotfile_text
        and "exec_script_allowlist" in settings_text
        and "exec_script_whitelist" not in settings_text
    ):
        print_colored("Patching V8 .gn exec_script_whitelist -> exec_script_allowlist for current depot_tools.")
        dotfile_text = dotfile_text.replace("exec_script_whitelist", "exec_script_allowlist")
        with open(dotfile_path, "w") as dotfile:
            dotfile.write(dotfile_text)

def patch_gn_files_for_current_build_config(root=os.getcwd()):
    cctest_build_path = os.path.join(root, "v8", "test", "cctest", "BUILD.gn")
    if not os.path.exists(cctest_build_path):
        return

    with open(cctest_build_path, "r") as build_file:
        build_text = build_file.read()

    old_expr = 'if (use_gold && target_cpu == "x86")'
    new_expr = 'if (defined(use_gold) && use_gold && target_cpu == "x86")'
    if old_expr in build_text:
        print_colored("Patching V8 test/cctest use_gold guard for current GN defaults.")
        build_text = build_text.replace(old_expr, new_expr)
        with open(cctest_build_path, "w") as build_file:
            build_file.write(build_text)

def download_additional_build_deps(root=os.getcwd(), skip_install_build_deps=False):
    if skip_install_build_deps:
        print_colored("Skipping V8 install-build-deps.sh; platform packages are managed by the parent project.")
        return
    if sys.platform == "linux":
        script_path = os.path.join(root, "v8", "build", "install-build-deps.sh")
        run_cmd(script_path, cwd=root, root=root, print_result=True)

def checkout(version, root=os.getcwd(), skip_install_build_deps=False):
    print_colored("Checking out the V8 source code...")
    print_colored("See https://v8.dev/docs/source-code for more information.")
    if not v8_src_downloaded(root=root):
        print_colored("Installing depot_tools...")
        install_depot_tools(root=root)
        print_colored("Updating depot_tools... This may take some time.")
        update_depot_tools(root=root)
        print_colored("Retrieving V8 source code...")
        get_v8_src_code(root=root)
        print_colored("Downloading all the build dependencies...")
        download_all_build_deps(root=root)
        print_colored("Downloading additional build dependencies...")
        download_additional_build_deps(root=root, skip_install_build_deps=skip_install_build_deps)
    print_colored("Switch to version {0}".format(version))
    switch_to_version(version, root=root)
    if not deps_synced_for_version(version, root=root):
        print_colored("Syncing V8 dependencies for version {0}".format(version))
        download_all_build_deps(root=root)
        mark_deps_synced_for_version(version, root=root)
    patch_gn_dotfile_for_current_depot_tools(root=root)
    patch_gn_files_for_current_build_config(root=root)
