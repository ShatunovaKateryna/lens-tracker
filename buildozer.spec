[app]

title = Lens Tracker
package.name = lenstracker
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 1.0

# Бібліотеки застосунку - тільки ті, що офіційно підтримуються python-for-android
requirements = python3,kivy==2.3.0,plyer

orientation = portrait
fullscreen = 0

icon.filename = %(source.dir)s/icon.png

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
# Мінімальна та цільова версія Android API
android.minapi = 21
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

# Дозволи: сповіщення (Android 13+ вимагає окремий дозвіл) та вібрація/вихід у мережу не потрібні
android.permissions = POST_NOTIFICATIONS

# Автоприйняття ліцензій Android SDK при першій збірці
android.accept_sdk_license = True
