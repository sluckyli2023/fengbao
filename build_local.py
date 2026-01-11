#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地打包测试脚本

功能:
- 检查依赖
- 执行 PyInstaller 打包
- 验证 EXE 文件
- 检查体积
- 生成报告

使用方法:
    python build_local.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def check_dependencies():
    """检查依赖"""
    print_section("检查依赖")
    
    missing = []
    
    # 检查 Python 版本
    print(f"Python 版本: {sys.version}")
    if sys.version_info < (3, 6):
        print("❌ 错误: 需要 Python 3.6 或更高版本")
        return False
    print("✓ Python 版本符合要求")
    
    # 检查必要的库
    required_packages = ['pydivert', 'psutil', 'pyinstaller']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"❌ {package} 未安装")
            missing.append(package)
    
    if missing:
        print(f"\n缺少的包: {', '.join(missing)}")
        print(f"请运行: pip install {' '.join(missing)}")
        return False
    
    return True

def clean_build():
    """清理旧的构建文件"""
    print_section("清理旧的构建文件")
    
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"删除 {dir_name}/ ...")
            shutil.rmtree(dir_name)
            print(f"✓ 已删除 {dir_name}/")
        else:
            print(f"✓ {dir_name}/ 不存在，跳过")
    
    # 清理 __pycache__
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"删除 {pycache_path} ...")
            shutil.rmtree(pycache_path)
    
    print("✓ 清理完成")

def build_exe():
    """执行 PyInstaller 打包"""
    print_section("执行 PyInstaller 打包")
    
    if not os.path.exists('fengbao.spec'):
        print("❌ 错误: fengbao.spec 文件不存在")
        return False
    
    print("运行: pyinstaller --clean --noconfirm fengbao.spec")
    print()
    
    try:
        result = subprocess.run(
            ['pyinstaller', '--clean', '--noconfirm', 'fengbao.spec'],
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            print(f"\n❌ PyInstaller 执行失败，退出码: {result.returncode}")
            return False
        
        print("\n✓ PyInstaller 执行成功")
        return True
        
    except FileNotFoundError:
        print("❌ 错误: 找不到 pyinstaller 命令")
        print("请运行: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def verify_exe():
    """验证 EXE 文件"""
    print_section("验证 EXE 文件")
    
    exe_path = Path('dist/fengbao.exe')
    
    if not exe_path.exists():
        print("❌ 错误: dist/fengbao.exe 不存在")
        print("\n检查 dist 目录内容:")
        if os.path.exists('dist'):
            for item in os.listdir('dist'):
                print(f"  - {item}")
        else:
            print("  dist 目录不存在")
        return False
    
    print(f"✓ EXE 文件存在: {exe_path}")
    
    # 检查文件大小
    size_bytes = exe_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    print(f"✓ 文件大小: {size_mb:.2f} MB ({size_bytes:,} 字节)")
    
    # 评估大小
    if size_mb < 5:
        print(f"✓ 优秀! 文件大小 < 5MB")
    elif size_mb < 10:
        print(f"✓ 良好! 文件大小 < 10MB")
    elif size_mb < 20:
        print(f"⚠️  警告: 文件大小 < 20MB，但超过目标")
    else:
        print(f"❌ 文件大小过大 (> 20MB)")
    
    return True

def generate_report():
    """生成打包报告"""
    print_section("生成打包报告")
    
    report_lines = []
    report_lines.append("# 打包报告\n")
    report_lines.append(f"**日期**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append(f"**Python 版本**: {sys.version}\n")
    report_lines.append("\n## 构建结果\n")
    
    exe_path = Path('dist/fengbao.exe')
    if exe_path.exists():
        size_bytes = exe_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        report_lines.append(f"- ✅ 构建成功\n")
        report_lines.append(f"- 文件路径: `{exe_path}`\n")
        report_lines.append(f"- 文件大小: {size_mb:.2f} MB ({size_bytes:,} 字节)\n")
        
        if size_mb < 5:
            report_lines.append(f"- 评级: ⭐⭐⭐ 优秀 (< 5MB)\n")
        elif size_mb < 10:
            report_lines.append(f"- 评级: ⭐⭐ 良好 (< 10MB)\n")
        elif size_mb < 20:
            report_lines.append(f"- 评级: ⭐ 一般 (< 20MB)\n")
        else:
            report_lines.append(f"- 评级: ❌ 需要优化 (> 20MB)\n")
    else:
        report_lines.append(f"- ❌ 构建失败\n")
    
    report_lines.append("\n## 依赖列表\n")
    try:
        result = subprocess.run(
            ['pip', 'list'],
            capture_output=True,
            text=True
        )
        report_lines.append("```\n")
        report_lines.append(result.stdout)
        report_lines.append("```\n")
    except:
        report_lines.append("无法获取依赖列表\n")
    
    report_content = ''.join(report_lines)
    
    # 保存报告
    report_path = 'BUILD_REPORT.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✓ 报告已保存到: {report_path}")
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("  构建摘要")
    print("=" * 60)
    print(report_content)

def main():
    """主函数"""
    print("=" * 60)
    print("  传奇翎风封包工具 - 本地打包测试")
    print("  架构: WinDivert + tkinter")
    print("  目标: EXE < 5MB")
    print("=" * 60)
    
    # 1. 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请先安装缺少的依赖")
        return 1
    
    # 2. 清理旧文件
    clean_build()
    
    # 3. 执行打包
    if not build_exe():
        print("\n❌ 打包失败")
        return 1
    
    # 4. 验证 EXE
    if not verify_exe():
        print("\n❌ EXE 验证失败")
        return 1
    
    # 5. 生成报告
    generate_report()
    
    print("\n" + "=" * 60)
    print("  ✅ 打包完成!")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 测试 EXE: dist/fengbao.exe")
    print("  2. 查看报告: BUILD_REPORT.md")
    print("  3. 如果体积过大，检查 fengbao.spec 的 excludes 配置")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

