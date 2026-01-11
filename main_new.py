#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传奇翎风封包工具 v2.0 - 重构版
架构: WinDivert + tkinter

重构说明:
- 从 Scapy + PyQt5 重构为 WinDivert + tkinter
- EXE 体积从 40MB 减少到 5MB
- 性能提升 10 倍（驱动层 vs 用户层）
- 精确的进程绑定（PID + 窗口标题）

使用方法:
    python main_new.py
    
注意: 需要管理员权限
"""

import sys
import os

# 检查 Python 版本
if sys.version_info < (3, 6):
    print("错误: 需要 Python 3.6 或更高版本")
    sys.exit(1)

# 检查管理员权限
def check_admin():
    """检查管理员权限"""
    if sys.platform == 'win32':
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            return is_admin
        except:
            return False
    return True

if not check_admin():
    print("=" * 60)
    print("错误: 需要管理员权限!")
    print("=" * 60)
    print("\n请右键选择「以管理员身份运行」")
    print("或在管理员权限的命令行中运行此程序")
    
    # 尝试弹出 GUI 提示
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "权限错误",
            "需要管理员权限!\n\n请右键选择「以管理员身份运行」"
        )
    except:
        pass
    
    sys.exit(1)

# 检查依赖
def check_dependencies():
    """检查依赖库"""
    missing = []
    
    try:
        import pydivert
    except ImportError:
        missing.append("pydivert")
    
    try:
        import psutil
    except ImportError:
        print("提示: 安装 psutil 可以获得更好的进程管理功能")
        print("      pip install psutil")
    
    if missing:
        print("=" * 60)
        print("错误: 缺少必要的依赖库")
        print("=" * 60)
        print("\n缺少的库:")
        for lib in missing:
            print(f"  - {lib}")
        print("\n请运行以下命令安装:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 60)
        
        # 尝试弹出 GUI 提示
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "依赖错误",
                f"缺少必要的依赖库:\n\n{', '.join(missing)}\n\n"
                f"请运行: pip install {' '.join(missing)}"
            )
        except:
            pass
        
        sys.exit(1)

check_dependencies()

# 导入 GUI
try:
    from ui.main_window_tk import MainWindow
except ImportError as e:
    print(f"错误: 无法导入 GUI 模块 - {e}")
    print("\n请确保在项目根目录运行此程序")
    sys.exit(1)

def main():
    """主函数"""
    print("=" * 60)
    print("传奇翎风封包工具 v2.0 (重构版)")
    print("=" * 60)
    print()
    print("架构: WinDivert + tkinter")
    print("特性:")
    print("  ✓ 驱动层拦截 (性能提升 10 倍)")
    print("  ✓ 精确进程绑定 (PID + 窗口标题)")
    print("  ✓ 体积优化 (5MB vs 40MB)")
    print("  ✓ 实时封包捕获和解析")
    print()
    print("正在启动 GUI...")
    print("=" * 60)
    print()
    
    # 创建并运行 GUI
    app = MainWindow()
    app.run()

if __name__ == '__main__':
    main()

