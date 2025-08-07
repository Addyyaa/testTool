# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main_gui.py'],
    pathex=['.', '..'],
    binaries=[],
    datas=[('gui', 'gui'), ('requirements.txt', '.'), ('../resource', 'resource'), ('../telnetTool', 'telnetTool')],
    hiddenimports=['tkinterdnd2', 'win32gui', 'win32con', 'win32api', 'win32com.client', 'psutil', 'PIL', 'send2trash'],
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
    name='文件传输工具',
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
