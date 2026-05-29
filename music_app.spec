# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['schemas', 'schemas.auth', 'schemas.lesson', 'schemas.topic', 'schemas.admin_stats', 'schemas.profile_stats', 'schemas.role', 'pydantic_settings', 'pydantic.deprecated.decorator', 'mido.backends.rtmidi', 'mido.backends.pygame', 'rtmidi']
hiddenimports += collect_submodules('PyQt6.QtCore')
hiddenimports += collect_submodules('PyQt6.QtGui')
hiddenimports += collect_submodules('PyQt6.QtWidgets')
hiddenimports += collect_submodules('PyQt6.QtNetwork')
hiddenimports += collect_submodules('PyQt6.QtSvg')
hiddenimports += collect_submodules('PyQt6.QtSvgWidgets')


a = Analysis(
    ['/home/vasilisqq/MY_WORLD/music_app/launcher.py'],
    pathex=['/home/vasilisqq/MY_WORLD/music_app', '/home/vasilisqq/MY_WORLD/music_app/app'],
    binaries=[],
    datas=[('app/photos', 'app/photos'), ('schemas', 'schemas'), ('single-piano-note-c4_100bpm_C_major.wav', '.'), ('piano_cache.pkl', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='music_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
