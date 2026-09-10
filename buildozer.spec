[app]

title = Anomaly Scanner V2.4
package.name = anomalyscanner
package.domain = org.anomalyscanner

source.dir = .
source.include_exts = py,png,csv,kv

version = 2.4

requirements = python3,kivy,plyer

orientation = portrait
fullscreen = 0

presplash.filename = %(source.dir)s/presplash.png
icon.filename = %(source.dir)s/icon.png


[buildozer]

log_level = 2
warn_on_root = 1


[android]

permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

android.api = 35
android.minapi = 24

android.archs = arm64-v8a

android.allow_backup = True
