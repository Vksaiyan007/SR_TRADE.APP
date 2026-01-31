"""
SR TRADE APK Builder for Android
Run this to create APK file
"""
import os
import subprocess
import shutil
from pathlib import Path

def build_apk():
    print("🚀 Building SR TRADE APK...")
    
    # Create build directory
    build_dir = "build_sr_trade"
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    
    # Copy all necessary files
    files_to_copy = [
        "main.py",
        "requirements.txt",
        "config.json",
        "README.md"
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy(file, build_dir)
            print(f"📄 Copied {file}")
    
    # Create main entry point
    with open(os.path.join(build_dir, "__main__.py"), "w") as f:
        f.write("""
from main import main

if __name__ == "__main__":
    main()
""")
    
    # Create setup.py for buildozer
    setup_content = """
from setuptools import setup

setup(
    name='SR TRADE',
    version='2.0',
    author='SR Analytics',
    author_email='support@srtrade.com',
    description='Professional Trading Application',
    packages=[],
    install_requires=[
        'kivy',
        'pandas',
        'numpy',
        'matplotlib',
        'yfinance'
    ]
)
"""
    
    with open(os.path.join(build_dir, "setup.py"), "w") as f:
        f.write(setup_content)
    
    # Create buildozer.spec
    spec_content = """
[app]

# (str) Title of your application
title = SR TRADE

# (str) Package name
package.name = srtrade

# (str) Package domain (needed for android/ios packaging)
package.domain = com.srtrade

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
#source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
#source.exclude_dirs = tests, bin

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 2.0

# (str) Application versioning (method 2)
# version.regex = __version__ = ['"](.*)['"]
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.1.0,kivymd,pandas,numpy,matplotlib,yfinance,plyer,requests

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivymd = /path/to/kivymd

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
#services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT_TO_PY2

# (bool) Use the recommended minimum Android API level
android.minapi = 21

# (bool) Use the recommended maximum Android API level
android.maxapi = 0

# (int) Target Android API, should be as high as possible.
android.api = 30

# (int) Minimum Android API version supported by your application
android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 23

# (str) Android NDK version to use
#android.ndk = 19b

# (int) Android NDK API to use. This is the minimum API your app will support.
#android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
#android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when the SDK is first
# installed.
#android.accept_sdk_license = False

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy-based app
# android.theme = "@android:style/Theme.NoTitleBar"

# (str) Full name including package path of the Java class that implements Python Activity
#android.activity_class_name = org.kivy.android.PythonActivity

# (str) Extra xml to write directly inside the <manifest> element of AndroidManifest.xml
# use it to add any permissions or features.
#android.extra_manifest_xml =

# (str) Extra xml to write directly inside the <manifest><application> tag of AndroidManifest.xml
#android.extra_manifest_application_xml =

# (str) Full name including package path of the Java class that implements Python Service
#android.service_class_name = org.kivy.android.PythonService

# (str) Android app theme, default is ok for Kivy-based app
# android.theme = "@android:style/Theme.NoTitleBar"

# (list) Permissions
#android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# (list) features (adds uses-feature -tags to manifest)
#android.features = android.hardware.usb.host

# (int) Target Android API, should be as high as possible.
#android.api = 27

# (int) Minimum Android API version supported by your application
#android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 27

# (str) Android NDK version to use
#android.ndk = 19b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
#android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when the SDK is first
# installed.
#android.accept_sdk_license = False

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.arch = arm64-v8a

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
#android.arch = arm64-v8a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# buildozer.build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .ipa) storage
# buildozer.bin_dir = ./bin

#    -----------------------------------------------------------------------------
#    List as sections
#
#    You can define all the "list" as [section:key].
#    Each line will be considered as a option to the list.
#    Let's take [app] / source.exclude_patterns.
#    Instead of doing:
#
#[app]
#source.exclude_patterns = license,data/audio/*.wav,data/images/original/*
#
#    This can be translated into:
#
#[app:source.exclude_patterns]
#license
#data/audio/*.wav
#data/images/original/*
#
#    -----------------------------------------------------------------------------
#    Profiles
#
#    You can extend section / key with a profile
#    For example, you want to deploy a demo version of your application without
#    HD content. You could first change the title to add "(demo)" in the name
#    and extend the excluded directories to remove the HD content.
#
#[app@demo]
#title = My Application (demo)
#
#[app:source.exclude_patterns@demo]
#images/hd/*
#
#    Then, invoke the command line with the "demo" profile:
#
#buildozer --profile demo android debug
"""
    
    with open(os.path.join(build_dir, "buildozer.spec"), "w") as f:
        f.write(spec_content)
    
    print("\n✅ Build directory created!")
    print(f"📁 Location: {build_dir}")
    
    print("\n📱 To build APK, follow these steps:")
    print("1. Install Buildozer on Linux/WSL:")
    print("   pip install buildozer")
    print("2. Navigate to build directory:")
    print(f"   cd {build_dir}")
    print("3. Build APK:")
    print("   buildozer android debug")
    print("4. Find APK in bin/ directory")
    
    return build_dir

if __name__ == "__main__":
    build_apk()