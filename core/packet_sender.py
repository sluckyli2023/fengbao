"""
传奇翎风封包发送模块
支持单个发送、批量发送、脚本化发送

核心功能：
1. Socket 连接管理
2. 封包重构和加密
3. 批量发送（次数、间隔）
4. 脚本解析和执行
"""

import socket
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from threading import Thread, Lock
from datetime import datetime

from .crypto import UniversalPacketParser


@dataclass
class SendResult:
    """发送结果"""
    success: bool
    timestamp: datetime
    packet_hex: str
    error: Optional[str] = None


class PacketSender:
    """
    封包发送器
    
    支持：
    - 单个封包发送
    - 批量发送（指定次数和间隔）
    - 脚本化发送（支持 wait() 命令）
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        初始化发送器
        
        Args:
            host: 服务器地址（None=需要手动连接）
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        
        self.parser = UniversalPacketParser()
        
        # 发送统计
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'start_time': None,
        }
        
        # 发送历史
        self.history: List[SendResult] = []
        self.history_lock = Lock()
        self.max_history = 1000
        
        # 脚本执行状态
        self.script_running = False
        self.script_thread: Optional[Thread] = None
    
    def connect(self, host: str = None, port: int = None) -> bool:
        """
        连接到游戏服务器
        
        Args:
            host: 服务器地址
            port: 服务器端口
            
        Returns:
            是否连接成功
        """
        if host:
            self.host = host
        if port:
            self.port = port
        
        if not self.host or not self.port:
            print("错误：未指定服务器地址和端口")
            return False
        
        try:
            # 关闭旧连接
            if self.socket:
                self.disconnect()
            
            # 创建新连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5秒超时
            
            print(f"正在连接到 {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            
            self.connected = True
            print("✓ 连接成功")
            
            # 重置统计
            self.stats['start_time'] = datetime.now()
            self.stats['total_sent'] = 0
            self.stats['total_failed'] = 0
            
            return True
        
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.connected = False
        print("连接已断开")
    
    def send_raw(self, data: bytes) -> SendResult:
        """
        发送原始数据
        
        Args:
            data: 原始字节数据
            
        Returns:
            发送结果
        """
        result = SendResult(
            success=False,
            timestamp=datetime.now(),
            packet_hex=' '.join(f'{b:02X}' for b in data)
        )
        
        if not self.connected or not self.socket:
            result.error = "未连接到服务器"
            self.stats['total_failed'] += 1
            return result
        
        try:
            self.socket.send(data)
            result.success = True
            self.stats['total_sent'] += 1
        
        except Exception as e:
            result.error = f"发送失败: {e}"
            self.stats['total_failed'] += 1
            self.connected = False
        
        # 添加到历史
        with self.history_lock:
            self.history.append(result)
            if len(self.history) > self.max_history:
                self.history.pop(0)
        
        return result
    
    def send_packet(self, parsed_data: Dict[str, Any], sequence: Optional[int] = None) -> SendResult:
        """
        发送封包（从解析结果）
        
        Args:
            parsed_data: UniversalPacketParser.parse() 的返回结果
            sequence: 序号（1-9，None=自动递增）
            
        Returns:
            发送结果
        """
        if not parsed_data.get('success'):
            return SendResult(
                success=False,
                timestamp=datetime.now(),
                packet_hex="",
                error="解析数据无效"
            )
        
        try:
            # 重构封包
            ascii_enc, hex_enc = self.parser.reconstruct(parsed_data, sequence)
            
            # 转换为字节
            data = bytes.fromhex(hex_enc.replace(" ", ""))
            
            # 发送
            return self.send_raw(data)
        
        except Exception as e:
            return SendResult(
                success=False,
                timestamp=datetime.now(),
                packet_hex="",
                error=f"重构失败: {e}"
            )
    
    def send_hex(self, hex_string: str) -> SendResult:
        """
        发送十六进制字符串
        
        Args:
            hex_string: 十六进制字符串（如 "23 34 53 48..."）
            
        Returns:
            发送结果
        """
        try:
            data = bytes.fromhex(hex_string.replace(" ", ""))
            return self.send_raw(data)
        except Exception as e:
            return SendResult(
                success=False,
                timestamp=datetime.now(),
                packet_hex=hex_string,
                error=f"十六进制解析失败: {e}"
            )
    
    def send_plaintext(self, plaintext: str) -> SendResult:
        """
        发送明文格式封包
        
        Args:
            plaintext: 明文格式（如 "发送封包（0，0，3013，103，3，86，）"）
            
        Returns:
            发送结果
        """
        try:
            # 解析明文
            parsed_data = self._parse_plaintext(plaintext)
            
            # 发送
            return self.send_packet(parsed_data)
        
        except Exception as e:
            return SendResult(
                success=False,
                timestamp=datetime.now(),
                packet_hex="",
                error=f"明文解析失败: {e}"
            )
    
    def _parse_plaintext(self, plaintext: str) -> Dict[str, Any]:
        """
        解析明文格式为结构化数据
        
        Args:
            plaintext: "发送封包（0，0，3013，103，3，86，）"
            
        Returns:
            解析结果（兼容 UniversalPacketParser 格式）
        """
        # 提取参数
        match = re.search(r'发送封包[（(](.+?)[）)]', plaintext)
        if not match:
            raise ValueError("明文格式错误")
        
        params_str = match.group(1)
        params = [p.strip() for p in params_str.split('，') if p.strip()]
        
        # 解析参数
        if len(params) < 3:
            raise ValueError("参数数量不足")
        
        # 构建结构化数据
        result = {
            'success': True,
            'function_code': int(params[2]),
            'core_data': {
                'param1': int(params[0]),
                'param2': int(params[1]),
                'param3': int(params[3]) if len(params) > 3 else 0,
                'param4': int(params[4]) if len(params) > 4 else 0,
                'param5': int(params[5]) if len(params) > 5 else 0,
            }
        }
        
        # 扩展数据（中文字符串）
        if len(params) > 6 and not params[6].isdigit():
            result['extended_data'] = {
                'text': params[6]
            }
        
        return result
    
    def send_batch(self, packets: List[Any], count: int = 1, interval: float = 0.1) -> List[SendResult]:
        """
        批量发送封包
        
        Args:
            packets: 封包列表（可以是 parsed_data、hex_string 或 plaintext）
            count: 每个封包发送次数
            interval: 发送间隔（秒）
            
        Returns:
            发送结果列表
        """
        results = []
        
        for packet in packets:
            for i in range(count):
                # 判断封包类型并发送
                if isinstance(packet, dict):
                    result = self.send_packet(packet)
                elif isinstance(packet, str):
                    if packet.startswith('发送封包'):
                        result = self.send_plaintext(packet)
                    else:
                        result = self.send_hex(packet)
                else:
                    result = SendResult(
                        success=False,
                        timestamp=datetime.now(),
                        packet_hex="",
                        error="不支持的封包类型"
                    )
                
                results.append(result)
                
                # 间隔
                if interval > 0 and (i < count - 1 or packet != packets[-1]):
                    time.sleep(interval)
        
        return results
    
    def send_script(self, script: str) -> List[SendResult]:
        """
        执行脚本
        
        脚本格式：
        ```
        发送封包（0，0，3013，100，200，）
        wait(1000)
        发送封包（4243548，0，0，1006，6160463，修复神水）
        repeat(3)
            发送封包（0，0，3013，100，200，）
            wait(500)
        end
        ```
        
        Args:
            script: 脚本内容
            
        Returns:
            发送结果列表
        """
        results = []
        lines = script.strip().split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                i += 1
                continue
            
            # wait 命令
            if line.startswith('wait('):
                match = re.search(r'wait\((\d+)\)', line)
                if match:
                    ms = int(match.group(1))
                    time.sleep(ms / 1000.0)
                i += 1
                continue
            
            # repeat 命令
            if line.startswith('repeat('):
                match = re.search(r'repeat\((\d+)\)', line)
                if match:
                    repeat_count = int(match.group(1))
                    
                    # 找到对应的 end
                    repeat_lines = []
                    i += 1
                    depth = 1
                    while i < len(lines) and depth > 0:
                        if lines[i].strip().startswith('repeat('):
                            depth += 1
                        elif lines[i].strip() == 'end':
                            depth -= 1
                            if depth == 0:
                                break
                        
                        if depth > 0:
                            repeat_lines.append(lines[i])
                        i += 1
                    
                    # 执行重复
                    for _ in range(repeat_count):
                        repeat_script = '\n'.join(repeat_lines)
                        results.extend(self.send_script(repeat_script))
                
                i += 1
                continue
            
            # 发送封包
            if line.startswith('发送封包'):
                result = self.send_plaintext(line)
                results.append(result)
                i += 1
                continue
            
            # 未知命令
            print(f"警告：未知命令: {line}")
            i += 1
        
        return results
    
    def send_script_async(self, script: str):
        """
        异步执行脚本（在独立线程中）
        
        Args:
            script: 脚本内容
        """
        if self.script_running:
            print("脚本正在运行中")
            return
        
        def run_script():
            self.script_running = True
            try:
                self.send_script(script)
            finally:
                self.script_running = False
        
        self.script_thread = Thread(target=run_script, daemon=True)
        self.script_thread.start()
    
    def stop_script(self):
        """停止脚本执行"""
        self.script_running = False
        if self.script_thread:
            self.script_thread.join(timeout=5)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        
        if stats['start_time']:
            elapsed = (datetime.now() - stats['start_time']).total_seconds()
            stats['elapsed_seconds'] = elapsed
            stats['packets_per_second'] = stats['total_sent'] / elapsed if elapsed > 0 else 0
        
        stats['connected'] = self.connected
        stats['history_count'] = len(self.history)
        
        return stats
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("封包发送统计")
        print("=" * 60)
        print(f"连接状态: {'已连接' if stats['connected'] else '未连接'}")
        if stats.get('start_time'):
            print(f"运行时间: {stats.get('elapsed_seconds', 0):.1f} 秒")
        print(f"成功发送: {stats['total_sent']}")
        print(f"发送失败: {stats['total_failed']}")
        if stats.get('packets_per_second'):
            print(f"发送速率: {stats['packets_per_second']:.2f} 包/秒")
        print(f"历史记录: {stats['history_count']}")
        print("=" * 60)
    
    def get_history(self, count: Optional[int] = None) -> List[SendResult]:
        """
        获取发送历史
        
        Args:
            count: 获取数量（None=全部）
            
        Returns:
            发送结果列表
        """
        with self.history_lock:
            if count is None:
                return self.history.copy()
            else:
                return self.history[-count:].copy()
    
    def clear_history(self):
        """清空发送历史"""
        with self.history_lock:
            self.history.clear()
        print("发送历史已清空")


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("封包发送模块测试")
    print("=" * 60)
    
    # 创建发送器
    sender = PacketSender()
    
    print("\n提示：要测试实际发送功能，需要：")
    print("1. 知道游戏服务器的地址和端口")
    print("2. 游戏客户端已登录")
    print("3. 有有效的封包数据")
    
    print("\n使用示例：")
    print("```python")
    print("sender = PacketSender()")
    print("sender.connect('192.168.1.100', 7000)")
    print("")
    print("# 发送明文格式")
    print("sender.send_plaintext('发送封包（0，0，3013，100，200，）')")
    print("")
    print("# 批量发送")
    print("packets = [")
    print("    '发送封包（0，0，3013，100，200，）',")
    print("    '发送封包（0，0，3013，101，201，）',")
    print("]")
    print("sender.send_batch(packets, count=3, interval=0.5)")
    print("")
    print("# 脚本发送")
    print("script = '''")
    print("发送封包（0，0，3013，100，200，）")
    print("wait(1000)")
    print("发送封包（0，0，3013，101，201，）")
    print("'''")
    print("sender.send_script(script)")
    print("")
    print("sender.print_stats()")
    print("sender.disconnect()")
    print("```")
    print("=" * 60)

