# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['log_getter.py'],
    pathex=['F:\\pythonProject\\testTool\\log_tool', 'F:\\pythonProject\\testTool'],  # 包含项目根目录
    binaries=[],
    datas=[
        ('service', 'service'),  # 包含 service 目录
        ('../telnet_connecter.py', 'telnet_connecter.py')  # 包含 telnet_connecter.py
    ],
    hiddenimports=['telnet_connecter'],  # 明确指定模块名
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
    name='log_getter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['..\\resource\\logo\\log.ico'],
)
