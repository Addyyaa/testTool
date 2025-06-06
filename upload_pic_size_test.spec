# -*- mode: python ; coding: utf-8 -*-
import os

# 只排除第三方无关库，保留标准库（如email、encodings.idna、encodings.punycode）
excluded_modules = [
    # GUI 相关
    'tkinter', 'tkinter.*',
    'PyQt5', 'PyQt5.*', 'PyQt6', 'PyQt6.*',
    'PySide2', 'PySide2.*', 'PySide6', 'PySide6.*',
    'wx', 'wx.*',
    # 数据科学相关
    'numpy', 'pandas', 'matplotlib', 'scipy',
    'sklearn', 'seaborn', 'plotly',
    # Web框架相关
    'django', 'flask', 'tornado', 'fastapi',
    'jinja2', 'werkzeug',
    # 测试框架
    'pytest', 'unittest', 'nose',
    # 其他大型库
    'IPython', 'jupyter',
    'docutils', 'sphinx',
    'setuptools', 'pip',
    # 不需要的urllib3和相关模块（requests已包含必要部分）
    'urllib3.packages.six',
    # 其他可选模块
    'pydoc', 'pydoc_data',
    'xml.sax', 'xml.dom',
    'mailbox',
    'ftplib', 'poplib', 'imaplib', 'smtplib',
    'telnetlib', 'socketserver',
    'http.server', 'xmlrpc',
    'multiprocessing',
    'concurrent.futures',
    'asyncio',  # 如果不使用异步功能可以排除
]

hidden_imports = [
    'requests',
    'requests.adapters',
    'requests.auth',
    'requests.sessions',
    'PIL',
    'PIL.Image',
    'PIL.ImageFile',
    'PIL.ImageOps',
    'json',
    'logging',
    'logging.handlers',
    'urllib3',
    'urllib3.util.retry',
    'certifi',
]

a = Analysis(
    ['upload_pic_size_test.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=2,
)

a.datas = [x for x in a.datas if not any(exclude in x[0] for exclude in [
    'test', 'tests', '__pycache__', '.pyc', 
    'matplotlib', 'numpy', 'pandas', 'scipy'
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='upload_pic_size_test',
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
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)
