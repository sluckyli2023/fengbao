#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的 PacketInterceptor (WinDivert)

使用方法:
    python test_interceptor.py
    
注意: 需要管理员权限
"""

import sys
import time
from datetime import datetime

# 检查是否有管理员权限
def check_admin():
    """检查管理员权限"""
    import ctypes
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        return is_admin
    except:
        return False

if not check_admin():
    print("=" * 60)
    print("错误: 需要管理员权限!")
    print("=" * 60)
    print("\n请右键选择「以管理员身份运行」")
    print("或在管理员权限的命令行中运行此脚本")
    sys.exit(1)

# 导入拦截器
try:
    from core.packet_interceptor import PacketInterceptor
except ImportError as e:
    print(f"错误: 无法导入拦截器 - {e}")
    print("\n请确保:")
    print("1. 已安装 pydivert: pip install pydivert")
    print("2. 在项目根目录运行此脚本")
    sys.exit(1)

# 统计信息
packet_count = 0
parsed_count = 0
last_print_time = time.time()

def on_packet(packet_data):
    """封包回调函数"""
    global packet_count, parsed_count, last_print_time
    
    packet_count += 1
    
    # 每秒最多打印一次，避免刷屏
    current_time = time.time()
    if current_time - last_print_time < 1.0:
        return
    
    last_print_time = current_time
    
    # 打印封包信息
    print(f"\n[{packet_data['timestamp'].strftime('%H:%M:%S')}] "
          f"{packet_data['direction']} "
          f"{packet_data['src_addr']}:{packet_data['src_port']} → "
          f"{packet_data['dst_addr']}:{packet_data['dst_port']}")
    
    # 打印解析结果
    parsed_data = packet_data.get('parsed_data', {})
    if parsed_data.get('success'):
        parsed_count += 1
        print(f"  ✓ 功能: {parsed_data.get('function_name', '未知')}")
        plaintext = parsed_data.get('plaintext', '')
        if len(plaintext) > 50:
            plaintext = plaintext[:50] + "..."
        print(f"  ✓ 明文: {plaintext}")
    else:
        print(f"  ✗ 解析失败: {parsed_data.get('error', '未知错误')}")
    
    # 打印统计
    print(f"  统计: 总计 {packet_count} | 解析成功 {parsed_count}")

def main():
    """主函数"""
    print("=" * 60)
    print("PacketInterceptor 测试 (WinDivert)")
    print("=" * 60)
    print()
    
    # 询问模式
    print("选择测试模式:")
    print("1. 全局模式 (拦截所有 TCP 封包)")
    print("2. 指定端口 (例如: 7000)")
    print("3. 指定进程 PID")
    
    choice = input("\n请选择 (1/2/3): ").strip()
    
    target_pid = None
    target_port = None
    
    if choice == '2':
        port_str = input("请输入端口号: ").strip()
        try:
            target_port = int(port_str)
        except:
            print("无效的端口号，使用全局模式")
    elif choice == '3':
        pid_str = input("请输入进程 PID: ").strip()
        try:
            target_pid = int(pid_str)
        except:
            print("无效的 PID，使用全局模式")
    
    # 创建拦截器
    print("\n创建拦截器...")
    interceptor = PacketInterceptor(
        target_pid=target_pid,
        target_port=target_port,
        callback=on_packet
    )
    
    # 启动拦截
    print("启动拦截...")
    print("\n提示:")
    print("- 封包会实时显示在下方")
    print("- 按 Ctrl+C 停止拦截")
    print("- 如果没有封包，请检查过滤条件")
    print("\n" + "=" * 60)
    
    try:
        interceptor.start()
        
        # 等待用户中断
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("停止拦截...")
        print("=" * 60)
    
    finally:
        # 停止拦截器
        interceptor.stop()
        
        # 打印统计信息
        interceptor.print_stats()
        
        print("\n测试完成!")

if __name__ == '__main__':
    main()

