"""
封包发送模块测试脚本

使用方法：
1. 确保游戏客户端已登录
2. 运行此脚本
3. 输入服务器地址和端口
4. 选择发送模式
5. 观察游戏反应
"""

import sys
import time
from core.packet_sender import PacketSender
from core.packet_capture import GameProcessDetector

def test_connection():
    """测试连接"""
    print("=" * 80)
    print("测试1：连接到游戏服务器")
    print("=" * 80)
    
    # 尝试检测游戏进程
    print("\n正在检测游戏进程...")
    detector = GameProcessDetector()
    
    game_names = ["mir.exe", "legend.exe", "game.exe", "client.exe"]
    found_connections = []
    
    for name in game_names:
        processes = detector.find_process_by_name(name)
        for proc in processes:
            connections = detector.get_process_connections(proc)
            if connections:
                found_connections.extend(connections)
                print(f"✓ 找到游戏进程: {name} (PID: {proc.pid})")
                for local_ip, local_port, remote_ip, remote_port in connections:
                    if remote_ip:
                        print(f"  连接: {local_ip}:{local_port} → {remote_ip}:{remote_port}")
    
    # 输入服务器信息
    print("\n请输入服务器信息：")
    
    if found_connections:
        print(f"\n检测到 {len(found_connections)} 个连接，使用检测到的地址？")
        use_detected = input("  (y/n, 默认y): ").strip().lower() or 'y'
        
        if use_detected == 'y' and found_connections:
            _, _, host, port = found_connections[0]
        else:
            host = input("  服务器地址: ").strip()
            port = int(input("  服务器端口: ").strip())
    else:
        host = input("  服务器地址: ").strip()
        port = int(input("  服务器端口: ").strip())
    
    # 创建发送器并连接
    sender = PacketSender()
    
    if sender.connect(host, port):
        print("\n✓ 连接成功！")
        return sender
    else:
        print("\n✗ 连接失败")
        return None


def test_send_single(sender: PacketSender):
    """测试单个发送"""
    print("\n" + "=" * 80)
    print("测试2：发送单个封包")
    print("=" * 80)
    
    print("\n选择发送格式：")
    print("  1. 明文格式（如：发送封包（0，0，3013，100，200，））")
    print("  2. 十六进制格式（如：23 34 3C 3C...）")
    
    choice = input("\n选择 (1-2, 默认1): ").strip() or "1"
    
    if choice == "1":
        print("\n示例：发送封包（0，0，3013，100，200，）")
        plaintext = input("请输入明文格式: ").strip()
        
        if plaintext:
            result = sender.send_plaintext(plaintext)
            
            if result.success:
                print(f"\n✓ 发送成功")
                print(f"  时间: {result.timestamp}")
                print(f"  数据: {result.packet_hex[:60]}...")
            else:
                print(f"\n✗ 发送失败: {result.error}")
    
    elif choice == "2":
        print("\n示例：23 34 3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 41 3E 72 58 3C 3C 6C 3D 52 3C 3C 21")
        hex_string = input("请输入十六进制: ").strip()
        
        if hex_string:
            result = sender.send_hex(hex_string)
            
            if result.success:
                print(f"\n✓ 发送成功")
                print(f"  时间: {result.timestamp}")
            else:
                print(f"\n✗ 发送失败: {result.error}")


def test_send_batch(sender: PacketSender):
    """测试批量发送"""
    print("\n" + "=" * 80)
    print("测试3：批量发送")
    print("=" * 80)
    
    print("\n示例：移动封包（模拟角色移动）")
    print("  发送封包（0，0，3013，100，200，）")
    print("  发送封包（0，0，3013，101，201，）")
    print("  发送封包（0，0，3013，102，202，）")
    
    use_example = input("\n使用示例？(y/n, 默认y): ").strip().lower() or 'y'
    
    if use_example == 'y':
        packets = [
            "发送封包（0，0，3013，100，200，）",
            "发送封包（0，0，3013，101，201，）",
            "发送封包（0，0，3013，102，202，）",
        ]
    else:
        packets = []
        print("\n请输入封包（每行一个，输入空行结束）：")
        while True:
            line = input("  ").strip()
            if not line:
                break
            packets.append(line)
    
    if not packets:
        print("未输入封包")
        return
    
    count = int(input(f"\n每个封包发送次数 (默认1): ").strip() or "1")
    interval = float(input(f"发送间隔（秒，默认0.1）: ").strip() or "0.1")
    
    print(f"\n准备发送 {len(packets)} 个封包，每个 {count} 次，间隔 {interval} 秒")
    confirm = input("确认发送？(y/n): ").strip().lower()
    
    if confirm == 'y':
        print("\n开始发送...")
        results = sender.send_batch(packets, count=count, interval=interval)
        
        success_count = sum(1 for r in results if r.success)
        print(f"\n发送完成：成功 {success_count}/{len(results)}")


def test_send_script(sender: PacketSender):
    """测试脚本发送"""
    print("\n" + "=" * 80)
    print("测试4：脚本发送")
    print("=" * 80)
    
    print("\n脚本示例：")
    print("```")
    print("发送封包（0，0，3013，100，200，）")
    print("wait(1000)")
    print("发送封包（0，0，3013，101，201，）")
    print("wait(500)")
    print("repeat(3)")
    print("    发送封包（0，0，3013，102，202，）")
    print("    wait(200)")
    print("end")
    print("```")
    
    use_example = input("\n使用示例？(y/n, 默认y): ").strip().lower() or 'y'
    
    if use_example == 'y':
        script = """
发送封包（0，0，3013，100，200，）
wait(1000)
发送封包（0，0，3013，101，201，）
wait(500)
repeat(3)
    发送封包（0，0，3013，102，202，）
    wait(200)
end
"""
    else:
        print("\n请输入脚本（输入 END 结束）：")
        lines = []
        while True:
            line = input()
            if line.strip().upper() == 'END':
                break
            lines.append(line)
        script = '\n'.join(lines)
    
    if not script.strip():
        print("未输入脚本")
        return
    
    print(f"\n准备执行脚本")
    confirm = input("确认执行？(y/n): ").strip().lower()
    
    if confirm == 'y':
        print("\n开始执行...")
        results = sender.send_script(script)
        
        success_count = sum(1 for r in results if r.success)
        print(f"\n执行完成：成功 {success_count}/{len(results)}")


def main():
    print("=" * 80)
    print("传奇翎风封包发送工具")
    print("=" * 80)
    
    print("\n⚠️  警告：")
    print("  - 本工具仅供学习研究使用")
    print("  - 使用本工具可能被游戏检测为外挂")
    print("  - 请在测试环境中使用")
    print("  - 不当使用可能导致账号封禁")
    
    confirm = input("\n我已了解风险，继续？(yes/no): ").strip().lower()
    if confirm != 'yes':
        print("已取消")
        return
    
    # 测试连接
    sender = test_connection()
    if not sender:
        return
    
    try:
        while True:
            print("\n" + "=" * 80)
            print("选择测试项目：")
            print("  1. 发送单个封包")
            print("  2. 批量发送")
            print("  3. 脚本发送")
            print("  4. 查看统计")
            print("  5. 清空历史")
            print("  0. 退出")
            print("=" * 80)
            
            choice = input("\n选择 (0-5): ").strip()
            
            if choice == "1":
                test_send_single(sender)
            elif choice == "2":
                test_send_batch(sender)
            elif choice == "3":
                test_send_script(sender)
            elif choice == "4":
                sender.print_stats()
                
                # 显示最近的发送记录
                history = sender.get_history(count=5)
                if history:
                    print("\n最近5条发送记录：")
                    for i, result in enumerate(history, 1):
                        status = "✓" if result.success else "✗"
                        print(f"  {i}. {status} {result.timestamp.strftime('%H:%M:%S')} - {result.packet_hex[:40]}...")
                        if result.error:
                            print(f"     错误: {result.error}")
            
            elif choice == "5":
                sender.clear_history()
            
            elif choice == "0":
                break
            
            else:
                print("无效选择")
    
    except KeyboardInterrupt:
        print("\n\n用户中断")
    
    finally:
        print("\n正在断开连接...")
        sender.disconnect()
        print("测试结束")


if __name__ == "__main__":
    main()

