[app]
title = Sandesh
package.name = dailynewsapp
package.domain = org.sovereign
source.dir = .
icon.filename = %(source.dir)s/icon.png
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,requests,urllib3,idna,charset-normalizer,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = armeabi-v7a, arm64-v8a
android.accept_sdk_license = True
p4a.branch = v2024.01.21
[buildozer]
log_level = 2
warn_on_root = 1
