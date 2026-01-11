# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 配置文件 - 重构版
架构: WinDivert + tkinter

优化目标:
- EXE 体积 < 5MB
- 排除所有不必要的依赖
- 请求管理员权限
"""

block_cipher = None

a = Analysis(
    ['main_new.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 如果有数据文件，在这里添加
        # ('data', 'data'),
    ],
    hiddenimports=[
        # 核心依赖
        'pydivert',
        'psutil',
        
        # tkinter 相关
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        
        # 核心模块
        'core.crypto',
        'core.packet_interceptor',
        'core.packet_sender',
        
        # UI 模块
        'ui.main_window_tk',
        
        # 标准库
        'json',
        'datetime',
        'threading',
        'queue',
        'collections',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除大型库
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'Pillow',
        
        # 排除其他 GUI 框架
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        'kivy',
        
        # 排除废弃的网络库
        'scapy',
        
        # 排除测试框架
        'pytest',
        'unittest',
        'nose',
        
        # 排除文档工具
        'sphinx',
        'docutils',
        
        # 排除开发工具
        'IPython',
        'jupyter',
        'notebook',
        
        # 排除其他不需要的库
        'setuptools',
        'pip',
        'wheel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='fengbao',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 无控制台窗口（GUI 程序）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 如果有图标文件，在这里指定
    uac_admin=True,  # 请求管理员权限
    uac_uiaccess=False,
)

