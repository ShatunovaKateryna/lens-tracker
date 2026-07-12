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

# Мінімальна та цільова версія Android API
android.minapi = 21
android.api = 33
android.ndk = 25b
android.archs = arm64-v8a

# Дозволи: сповіщення (Android 13+ вимагає окремий дозвіл)
android.permissions = POST_NOTIFICATIONS

# Автоприйняття ліцензій Android SDK при першій збірці
android.accept_sdk_license = True

# Закріплюємо стабільний реліз python-for-android (Python 3.11),
# бо гілка master вже перейшла на Python 3.14, з якою pyjnius/kivy 2.3.0 несумісні
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
