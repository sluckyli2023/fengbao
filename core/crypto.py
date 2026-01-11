"""
传奇翎风封包加密/解密引擎
支持多种封包类型，每种类型使用不同的XOR密钥表

重构版本：添加通用封包解析器
- 不依赖参数含义，只关心数据结构
- 基于功能码的XOR表映射
- 支持动态添加新的封包类型
"""

import struct
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum


class PacketType(Enum):
    """封包类型枚举"""
    MOVE = "移动"
    ITEM = "使用物品"
    ITEM_TO_DIALOG = "放入物品到对话框"
    NPC_CLICK = "点击NPC"
    NPC_DIALOG = "NPC对话"
    SKILL = "使用技能"
    UNKNOWN = "未知"


class UniversalPacketParser:
    """
    通用封包解析器
    
    核心理念：
    1. 不关心参数的业务含义，只关心数据结构
    2. 基于功能码自动选择XOR表
    3. 支持动态添加新的封包类型
    """
    
    # XOR表映射：功能码 -> XOR表
    XOR_TABLE_MAP = {
        # 移动相关
        0x0BC3: [  # 3011 - 移动_旧坐标系
            0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xF9, 0x37, 0x58, 0x41, 0x3D, 0x72, 0x0E, 0x3C,
        ],
        0x0BC5: [  # 3013 - 移动_新坐标系
            0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xF9, 0x37, 0x58, 0x41, 0x3D, 0x72, 0x0E, 0x3C,
        ],
        0x0BC9: [  # 3017 - 使用技能
            0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xF9, 0x37, 0x58, 0x41, 0x3D, 0x72, 0x0E, 0x3C,
        ],
        # 物品相关
        0x03EE: [  # 1006 - 使用物品
            0x0F, 0x88, 0x7D, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xD2, 0x3F, 0x70, 0x6A, 0x62, 0x70, 0x68, 0x3C,
            0x83, 0x82, 0x84, 0x89, 0xF5, 0xCD, 0xBB, 0xE7,
        ],
        0x1396: [  # 5014 - 放入物品到对话框
            0x6A, 0x26, 0x50, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xAA, 0x2F, 0x30, 0x52, 0x40, 0x6C, 0x74, 0x3C,
            0xF2, 0xE2, 0xD4, 0x9A, 0x89, 0xF8, 0xBE, 0xDA,
        ],
        0x1397: [  # 5015 - 从对话框取出物品
            0x6A, 0x26, 0x50, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xAA, 0x2F, 0x30, 0x52, 0x40, 0x6C, 0x74, 0x3C,
            0xF2, 0xE2, 0xD4, 0x9A, 0x89, 0xF8, 0xBE, 0xDA,
        ],
        # NPC相关
        0x03F2: [  # 1010 - 点击NPC
            0x3C, 0xC6, 0xF8, 0x77, 0x3F, 0x4C, 0x3C, 0x3C,
            0xCE, 0x3F, 0x3F, 0x6E, 0x3C, 0x6C, 0x3C, 0x3C,
        ],
        0x03F3: [  # 1011 - NPC对话选项
            0x3C, 0xC6, 0xF8, 0x77, 0x3F, 0x4C, 0x3C, 0x3C,
            0xCF, 0x3F, 0x3F, 0x6F, 0x3C, 0x6C, 0x3C, 0x3C,
            0x7C, 0xEB, 0x8C, 0x8D, 0x84, 0xF6, 0xB8, 0x99,
        ],
    }
    
    # 功能码名称映射
    FUNCTION_NAMES = {
        0x0BC3: "移动_旧坐标系",
        0x0BC5: "移动_新坐标系", 
        0x0BC9: "使用技能",
        0x03EE: "使用物品",
        0x1396: "放入物品到对话框",
        0x1397: "从对话框取出物品",
        0x03F2: "点击NPC",
        0x03F3: "NPC对话选项"
    }
    
    def __init__(self):
        self.sequence = 1  # 封包序号（1-9循环）
    
    def parse(self, encrypted_hex: str) -> Dict[str, Any]:
        """
        通用封包解析算法
        
        Args:
            encrypted_hex: 加密的十六进制字符串
            
        Returns:
            解析结果字典：
            {
                'success': bool,              # 是否解析成功
                'raw_hex': str,               # 原始十六进制
                'sequence': int,              # 封包序号
                'function_code': int,         # 功能码
                'function_name': str,         # 功能名称
                'core_data': {                # 核心16字节数据
                    'param1': int,
                    'param2': int,
                    'param3': int,
                    'param4': int,
                    'param5': int,
                },
                'extended_data': {            # 扩展数据（可选）
                    'length': int,
                    'raw_bytes': bytes,
                    'text': str,              # GBK解码后的文本
                },
                'decrypted_hex': str,         # 解密后的十六进制
                'plaintext': str,             # 明文格式
            }
        """
        result = {
            'success': False,
            'raw_hex': encrypted_hex,
            'error': None
        }
        
        try:
            # 1. 验证封包格式
            hex_bytes = bytes.fromhex(encrypted_hex.replace(" ", ""))
            
            if len(hex_bytes) < 19:
                result['error'] = f"封包长度不足，至少需要19字节，当前{len(hex_bytes)}字节"
                return result
            
            if hex_bytes[0] != 0x23 or hex_bytes[-1] != 0x21:
                result['error'] = "封包格式错误：头尾标识不匹配（应为 # 和 !）"
                return result
            
            # 2. 提取序号
            sequence = int(chr(hex_bytes[1]))
            result['sequence'] = sequence
            
            # 3. 提取加密数据
            encrypted_data = hex_bytes[2:-1]
            
            # 4. 智能识别：尝试所有XOR表，找到最合理的匹配
            candidates = []  # 存储所有可能的匹配 (func_code, xor_table, decrypted_data, score)
            
            for test_func_code, xor_table in self.XOR_TABLE_MAP.items():
                # 尝试用当前XOR表解密
                temp_decrypt = bytearray()
                for i in range(len(encrypted_data)):
                    xor_val = xor_table[i] if i < len(xor_table) else 0x3C
                    temp_decrypt.append(encrypted_data[i] ^ xor_val)
                
                # 检查解密后的功能码
                if len(temp_decrypt) >= 10:
                    detected_func_code = struct.unpack('<H', bytes(temp_decrypt[8:10]))[0]
                    
                    # 如果检测到的功能码与XOR表对应的功能码匹配
                    if detected_func_code == test_func_code:
                        # 计算匹配分数（用于区分多个候选）
                        score = 0
                        
                        # 1. 参数2通常为0（+100分）
                        param2 = struct.unpack('<I', bytes(temp_decrypt[4:8]))[0]
                        if param2 == 0:
                            score += 100
                        
                        # 2. 参数1的合理性
                        param1 = struct.unpack('<I', bytes(temp_decrypt[0:4]))[0]
                        # 移动封包：param1应该为0
                        if test_func_code in [0x0BC3, 0x0BC5, 0x0BC9] and param1 == 0:
                            score += 200  # 移动封包特征明显，高分
                        # NPC/物品封包：param1应该不为0
                        elif test_func_code in [0x03EE, 0x03F2, 0x03F3, 0x1396, 0x1397] and param1 != 0:
                            score += 50
                        
                        # 3. 参数值的合理范围（避免异常大的数值）
                        if param1 < 0xFFFFFF:  # 参数1小于16M
                            score += 10
                        
                        # 4. XOR表长度（更长的XOR表通常更准确）
                        score += len(xor_table)
                        
                        # 5. 扩展数据的合理性（如果有扩展数据）
                        if len(encrypted_data) > 16:
                            # 尝试解密扩展数据，检查是否有可打印字符
                            ext_start = 16
                            ext_end = min(24, len(temp_decrypt))
                            ext_data = bytes(temp_decrypt[ext_start:ext_end])
                            try:
                                text = ext_data.decode('gbk', errors='ignore')
                                printable_count = sum(1 for c in text if c.isprintable())
                                score += printable_count * 5  # 每个可打印字符+5分
                            except:
                                pass
                        
                        candidates.append((detected_func_code, xor_table, temp_decrypt, score))
            
            # 如果没有找到匹配
            if not candidates:
                result['error'] = "无法识别封包类型（未找到匹配的XOR表）"
                return result
            
            # 选择得分最高的候选
            candidates.sort(key=lambda x: x[3], reverse=True)
            func_code, matched_xor_table, decrypted_data, best_score = candidates[0]
            decrypted_data = bytearray(decrypted_data)
            
            # 5. 解析核心16字节数据
            result['function_code'] = func_code
            result['function_name'] = self.FUNCTION_NAMES.get(func_code, f"未知功能_{func_code}")
            
            # 正确的参数位置（参考程序验证）：
            # [0-3]   param1 (4字节)
            # [4-7]   param2 (4字节)
            # [8-9]   功能码 (2字节) - 已在上面识别
            # [10-11] param3 (2字节)
            # [12-13] param4 (2字节)
            # [14-15] param5 (2字节)
            core_data = {
                'param1': struct.unpack('<I', bytes(decrypted_data[0:4]))[0],
                'param2': struct.unpack('<I', bytes(decrypted_data[4:8]))[0],
                'function_code': func_code,  # 功能码在 [8:10]
                'param3': struct.unpack('<H', bytes(decrypted_data[10:12]))[0],
                'param4': struct.unpack('<H', bytes(decrypted_data[12:14]))[0],
                'param5': struct.unpack('<H', bytes(decrypted_data[14:16]))[0],
            }
            result['core_data'] = core_data
            
            # 6. 解析扩展数据（如果有）
            if len(decrypted_data) > 16:
                extended_data = {
                    'length': len(decrypted_data) - 16,
                    'raw_bytes': bytes(decrypted_data[16:]),
                    'text': None
                }
                
                # 尝试解析为GBK文本
                try:
                    # 扩展数据从第16字节开始
                    text_bytes = bytes(decrypted_data[16:])
                    
                    # 移除尾部的 0x00 和不可打印字符
                    text_bytes = text_bytes.rstrip(b'\x00')
                    
                    if text_bytes:
                        # 解码为 GBK
                        text = text_bytes.decode('gbk', errors='ignore')
                        
                        # 清理不可打印字符（保留中文和常见符号）
                        text = ''.join(c for c in text if c.isprintable() or ord(c) > 127)
                        
                        if text:
                            extended_data['text'] = text
                except Exception as e:
                    # 解码失败时，尝试显示十六进制
                    pass
                
                result['extended_data'] = extended_data
            
            # 7. 生成解密后的十六进制
            result['decrypted_hex'] = ' '.join(f'{b:02X}' for b in decrypted_data)
            
            # 8. 生成明文格式
            result['plaintext'] = self._generate_plaintext(core_data, result.get('extended_data'))
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = f"解析异常: {str(e)}"
        
        return result
    
    def _generate_plaintext(self, core_data: Dict, extended_data: Optional[Dict]) -> str:
        """生成明文格式 - 参考程序格式"""
        # 参考程序格式：发送封包（param1，param2，功能码，param3，param4，文本）
        params = [
            core_data['param1'],
            core_data['param2'],
            core_data['function_code'],  # 添加功能码
            core_data['param3'],
            core_data['param4']
        ]
        
        # 扩展数据（文本）
        if extended_data and extended_data.get('text'):
            params.append(extended_data['text'])
        
        return f"发送封包（{('，'.join(map(str, params)))}，）"
    
    def reconstruct(self, parsed_data: Dict, sequence: Optional[int] = None) -> Tuple[str, str]:
        """
        通用封包重构算法
        
        Args:
            parsed_data: parse()返回的解析结果
            sequence: 封包序号（可选）
            
        Returns:
            (ASCII格式, 十六进制格式)
        """
        if not parsed_data.get('success'):
            raise ValueError("无法重构失败的解析结果")
        
        func_code = parsed_data['function_code']
        core_data = parsed_data['core_data']
        extended_data = parsed_data.get('extended_data')
        
        # 获取XOR表
        xor_table = self.XOR_TABLE_MAP.get(func_code)
        if xor_table is None:
            raise ValueError(f"未知功能码: {func_code}")
        
        # 构建原始数据
        data = bytearray()
        data.extend(struct.pack('<I', core_data['param1']))
        data.extend(struct.pack('<I', core_data['param2']))
        data.extend(struct.pack('<H', func_code))
        data.extend(struct.pack('<H', core_data['param3']))
        data.extend(struct.pack('<H', core_data['param4']))
        data.extend(struct.pack('<H', core_data['param5']))
        
        # 添加扩展数据
        if extended_data and extended_data.get('text'):
            data.extend(extended_data['text'].encode('gbk'))
        
        # 填充到至少22字节
        while len(data) < 22:
            data.append(0x00)
        
        # 加密
        if sequence is None:
            sequence = self.sequence
            self.sequence = (self.sequence % 9) + 1
        
        encrypted = bytearray()
        encrypted.append(0x23)  # #
        encrypted.append(ord(str(sequence)))
        
        for i, byte in enumerate(data):
            xor_val = xor_table[i] if i < len(xor_table) else 0x3C
            encrypted.append(byte ^ xor_val)
        
        encrypted.append(0x21)  # !
        
        ascii_format = encrypted.decode('latin-1')
        hex_format = ' '.join(f'{b:02X}' for b in encrypted)
        
        return ascii_format, hex_format
    
    def add_xor_table(self, func_code: int, xor_table: List[int], func_name: str = None):
        """
        动态添加新的XOR表
        
        Args:
            func_code: 功能码
            xor_table: XOR表
            func_name: 功能名称（可选）
        """
        self.XOR_TABLE_MAP[func_code] = xor_table
        if func_name:
            self.FUNCTION_NAMES[func_code] = func_name
    
    def extract_xor_table(self, encrypted_hex: str, decrypted_hex: str) -> List[int]:
        """
        从加密和解密数据中提取XOR表
        
        Args:
            encrypted_hex: 加密的十六进制字符串（完整封包，包含 # 和 !）
            decrypted_hex: 解密的十六进制字符串（仅数据部分，不含头尾）
            
        Returns:
            XOR表
        """
        enc_bytes = bytes.fromhex(encrypted_hex.replace(" ", ""))
        dec_bytes = bytes.fromhex(decrypted_hex.replace(" ", ""))
        
        # 跳过头部的 # 和序号，以及尾部的 !
        enc_data = enc_bytes[2:-1]
        
        # 如果解密数据较短，只提取对应长度的XOR表
        min_len = min(len(enc_data), len(dec_bytes))
        
        xor_table = [enc_data[i] ^ dec_bytes[i] for i in range(min_len)]
        
        # 如果加密数据更长，剩余部分假设使用 0x3C
        if len(enc_data) > len(dec_bytes):
            for i in range(len(dec_bytes), len(enc_data)):
                # 假设扩展部分的原始数据为 0x00，可以反推XOR值
                # 但这不准确，所以只返回已知部分
                pass
        
        return xor_table


class PacketCrypto:
    """封包加密解密核心类（保留向后兼容）"""
    
    # 不同操作类型的XOR密钥表
    XOR_TABLES = {
        PacketType.MOVE: [
            0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xF9, 0x37, 0x58, 0x41, 0x3D, 0x72, 0x0E, 0x3C,
        ],
        PacketType.ITEM: [
            0x0F, 0x88, 0x7D, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xD2, 0x3F, 0x70, 0x6A, 0x62, 0x70, 0x68, 0x3C,
            0x83, 0x82, 0x84, 0x89, 0xF5, 0xCD, 0xBB, 0xE7,  # 扩展部分（中文等）
        ],
        PacketType.ITEM_TO_DIALOG: [
            0x6A, 0x26, 0x50, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C,
            0xAA, 0x2F, 0x30, 0x52, 0x40, 0x6C, 0x74, 0x3C,
            0xF2, 0xE2, 0xD4, 0x9A, 0x89, 0xF8, 0xBE, 0xDA,  # 扩展部分（中文等）
        ],
        PacketType.NPC_CLICK: [
            0x3C, 0xC6, 0xF8, 0x77, 0x3F, 0x4C, 0x3C, 0x3C,
            0xCE, 0x3F, 0x3F, 0x6E, 0x3C, 0x6C, 0x3C, 0x3C,
        ],
        PacketType.NPC_DIALOG: [
            0x0C, 0x20, 0xCC, 0x77, 0x3F, 0x4C, 0x3C, 0x3C,
            0xCF, 0x3F, 0x3F, 0x6F, 0x3C, 0x6C, 0x3C, 0x3C,
            0x7C, 0xEB, 0x8C, 0x8D, 0x84, 0xF6, 0xB8, 0x99,  # 扩展部分（中文等）
        ],
    }
    
    # 功能码到封包类型的映射
    FUNC_CODE_TO_TYPE = {
        0x0BC3: PacketType.MOVE,           # 3011
        0x0BC5: PacketType.MOVE,           # 3013
        0x0BC9: PacketType.SKILL,          # 3017
        0x03EE: PacketType.ITEM,           # 1006
        0x1396: PacketType.ITEM_TO_DIALOG, # 5014 - 放入物品到对话框
        0x1397: PacketType.ITEM_TO_DIALOG, # 5015 - 从对话框取出物品
        0x03F2: PacketType.NPC_CLICK,      # 1010
        0x03F3: PacketType.NPC_DIALOG,     # 1011
    }
    
    # 功能码名称映射
    FUNCTION_NAMES = {
        0x0BC3: "移动_旧坐标系",
        0x0BC5: "移动_新坐标系", 
        0x0BC9: "使用技能",
        0x03EE: "使用物品",
        0x1396: "放入物品到对话框",
        0x1397: "从对话框取出物品",
        0x03F2: "点击NPC",
        0x03F3: "NPC对话选项"
    }
    
    def __init__(self):
        self.sequence = 1  # 封包序号（1-9循环）
    
    def auto_detect_type(self, encrypted_hex: str) -> PacketType:
        """
        自动检测封包类型（尝试用所有XOR表解密，看哪个合理）
        """
        hex_bytes = bytes.fromhex(encrypted_hex.replace(" ", ""))
        encrypted_data = hex_bytes[2:-1]
        
        for ptype, xor_table in self.XOR_TABLES.items():
            try:
                # 尝试解密
                decrypted = bytearray()
                for i, enc_byte in enumerate(encrypted_data[:16]):
                    if i < len(xor_table):
                        decrypted.append(enc_byte ^ xor_table[i])
                    else:
                        decrypted.append(enc_byte ^ 0x3C)
                
                # 检查功能码是否合理
                if len(decrypted) >= 10:
                    func_code = struct.unpack('<H', bytes(decrypted[8:10]))[0]
                    expected_type = self.FUNC_CODE_TO_TYPE.get(func_code)
                    if expected_type == ptype:
                        return ptype
            except:
                continue
        
        return PacketType.UNKNOWN
    
    def decrypt_packet(self, encrypted_hex: str, packet_type: Optional[PacketType] = None) -> Tuple[bytes, List, PacketType]:
        """
        解密封包
        
        Args:
            encrypted_hex: 十六进制字符串
            packet_type: 封包类型（可选，不指定则自动检测）
            
        Returns:
            (解密后的字节数据, 明文参数列表, 封包类型)
        """
        hex_bytes = bytes.fromhex(encrypted_hex.replace(" ", ""))
        
        if len(hex_bytes) < 19:
            raise ValueError(f"封包长度不足，至少需要19字节，当前{len(hex_bytes)}字节")
        
        # 验证封包头尾
        if hex_bytes[0] != 0x23 or hex_bytes[-1] != 0x21:
            raise ValueError("封包格式错误：头尾标识不匹配")
        
        # 提取序号
        sequence = int(chr(hex_bytes[1]))
        
        # 自动检测封包类型
        if packet_type is None:
            packet_type = self.auto_detect_type(encrypted_hex)
        
        # 获取对应的XOR表
        xor_table = self.XOR_TABLES.get(packet_type, self.XOR_TABLES[PacketType.MOVE])
        
        # 解密数据部分
        encrypted_data = hex_bytes[2:-1]
        decrypted = bytearray()
        
        for i, enc_byte in enumerate(encrypted_data):
            if i < len(xor_table):
                xor_val = xor_table[i]
            else:
                xor_val = 0x3C
            
            decrypted.append(enc_byte ^ xor_val)
        
        # 解析明文参数
        params = self._parse_params(bytes(decrypted), packet_type)
        
        return bytes(decrypted), params, packet_type
    
    def _parse_params(self, data: bytes, packet_type: PacketType) -> List:
        """
        解析解密后的数据为参数列表
        
        不同封包类型有不同的参数结构
        """
        if len(data) < 16:
            raise ValueError("数据长度不足16字节")
        
        params = []
        
        # 参数1：4字节整数
        param1 = struct.unpack('<I', data[0:4])[0]
        params.append(param1)
        
        # 参数2：4字节整数
        param2 = struct.unpack('<I', data[4:8])[0]
        params.append(param2)
        
        # 功能码：2字节
        func_code = struct.unpack('<H', data[8:10])[0]
        params.append(func_code)
        
        # 根据封包类型解析后续参数
        if packet_type in [PacketType.ITEM, PacketType.ITEM_TO_DIALOG]:
            # 使用物品/放入物品：param3(4字节) + param4(2字节)
            param3 = struct.unpack('<I', data[10:14])[0]
            param4 = struct.unpack('<H', data[14:16])[0]
            params.extend([param3, param4])
        else:
            # 其他类型：param3-5各2字节
            param3 = struct.unpack('<H', data[10:12])[0]
            param4 = struct.unpack('<H', data[12:14])[0]
            param5 = struct.unpack('<H', data[14:16])[0]
            params.extend([param3, param4, param5])
        
        # 扩展数据：中文字符串（GBK编码）
        if len(data) > 16:
            try:
                # 对于使用物品/放入物品封包，中文在16-23字节
                if packet_type in [PacketType.ITEM, PacketType.ITEM_TO_DIALOG] and len(data) >= 24:
                    extra_data = data[16:24]
                else:
                    extra_data = data[16:]
                
                # 移除填充的0x00字节
                extra_data = extra_data.rstrip(b'\x00')
                if extra_data:
                    # 尝试解码为GBK
                    text = extra_data.decode('gbk', errors='ignore')
                    # 移除不可打印字符
                    text = ''.join(c for c in text if c.isprintable())
                    if text:
                        params.append(text)
            except:
                pass
        
        return params
    
    def encrypt_packet(self, params: List, packet_type: PacketType, sequence: Optional[int] = None) -> Tuple[str, str]:
        """
        加密封包
        
        Args:
            params: 参数列表
                - 移动/NPC: [param1, param2, func_code, param3, param4, param5, extra_text?]
                - 使用物品: [param1, param2, func_code, param3, param4, extra_text?]
            packet_type: 封包类型
            sequence: 序号（1-9），不指定则自动递增
            
        Returns:
            (ASCII格式, 十六进制格式)
        """
        if sequence is None:
            sequence = self.sequence
            self.sequence = (self.sequence % 9) + 1
        
        # 构建原始数据（16字节基础）
        data = bytearray()
        
        # 参数1-2：各4字节
        data.extend(struct.pack('<I', params[0]))
        data.extend(struct.pack('<I', params[1]))
        
        # 功能码：2字节
        data.extend(struct.pack('<H', params[2]))
        
        # 根据封包类型构建后续参数
        if packet_type in [PacketType.ITEM, PacketType.ITEM_TO_DIALOG]:
            # 使用物品/放入物品：param3(4字节) + param4(2字节)
            data.extend(struct.pack('<I', params[3]))
            data.extend(struct.pack('<H', params[4]))
            extra_text_idx = 5
        else:
            # 其他类型：param3-5各2字节
            data.extend(struct.pack('<H', params[3]))
            data.extend(struct.pack('<H', params[4]))
            data.extend(struct.pack('<H', params[5]))
            extra_text_idx = 6
        
        # 扩展数据：中文字符串
        if len(params) > extra_text_idx and isinstance(params[extra_text_idx], str):
            data.extend(params[extra_text_idx].encode('gbk'))
        
        # 填充到至少22字节（移动和NPC封包需要）
        if packet_type in [PacketType.MOVE, PacketType.NPC_CLICK, PacketType.NPC_DIALOG]:
            while len(data) < 22:
                data.append(0x00)
        
        # 获取对应的XOR表
        xor_table = self.XOR_TABLES.get(packet_type, self.XOR_TABLES[PacketType.MOVE])
        
        # 加密数据
        encrypted = bytearray()
        encrypted.append(0x23)  # 头：#
        encrypted.append(ord(str(sequence)))  # 序号
        
        for i, byte in enumerate(data):
            if i < len(xor_table):
                xor_val = xor_table[i]
            else:
                xor_val = 0x3C
            
            encrypted.append(byte ^ xor_val)
        
        encrypted.append(0x21)  # 尾：!
        
        # 生成两种格式
        ascii_format = encrypted.decode('latin-1')
        hex_format = ' '.join(f'{b:02X}' for b in encrypted)
        
        return ascii_format, hex_format
    
    def to_plaintext(self, params: List, packet_type: PacketType) -> str:
        """转换为明文格式"""
        if params[0] == 0 and params[1] == 0:
            # 格式1: 发送封包（0，0，功能码，参数...）
            if packet_type in [PacketType.ITEM, PacketType.ITEM_TO_DIALOG]:
                parts = [0, 0, params[2], params[3], params[4]]
                extra_idx = 5
            else:
                parts = [0, 0, params[2], params[3], params[4], params[5]]
                extra_idx = 6
        else:
            # 格式2: 发送封包（参数1，0，0，功能码，参数3，）
            parts = [params[0], params[1], 0, params[2], params[3]]
            extra_idx = 6 if packet_type not in [PacketType.ITEM, PacketType.ITEM_TO_DIALOG] else 5
        
        # 添加扩展数据
        if len(params) > extra_idx:
            parts.append(params[extra_idx])
        
        parts_str = '，'.join(str(p) for p in parts)
        return f"发送封包（{parts_str}，）"
    
    def get_function_name(self, func_code: int) -> str:
        """获取功能码对应的功能名称"""
        return self.FUNCTION_NAMES.get(func_code, f"未知功能_{func_code}")


# 测试验证函数
def test_crypto():
    """使用提供的样本数据验证加密解密算法"""
    crypto = PacketCrypto()
    
    print("=" * 60)
    print("封包加密解密引擎测试（多类型支持）")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "移动封包",
            "hex": "23 34 3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 41 3E 72 58 3C 3C 6C 3D 52 3C 3C 21",
            "expected_plaintext": "发送封包（0，0，3013，103，3，86，）",
            "type": PacketType.MOVE
        },
        {
            "name": "使用物品",
            "hex": "23 34 53 48 3D 3C 3C 3C 3C 3C 3C 3C 3F 6A 3C 70 78 3C 53 5C 3C 3D 3C 3C 70 49 76 74 69 48 63 6D 6E 76 74 21",
            "expected_plaintext": "发送封包（4243548，0，0，1006，6160463，修复神水）",
            "type": PacketType.ITEM
        },
        {
            "name": "点击NPC",
            "hex": "23 38 3C 44 46 7A 3F 4C 3C 3C 3C 3C 3F 6E 3C 6C 3C 3C 3C 3C 3C 3C 3C 3C 21",
            "expected_plaintext": "发送封包（230588928，0，0，1010，0，）",
            "type": PacketType.NPC_CLICK
        }
    ]
    
    success_count = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test['name']}")
        print(f"输入HEX: {test['hex']}")
        
        try:
            decrypted, params, detected_type = crypto.decrypt_packet(test['hex'], test['type'])
            
            print(f"解密数据: {' '.join(f'{b:02X}' for b in decrypted[:16])}")
            print(f"解析参数: {params}")
            print(f"封包类型: {detected_type.value}")
            
            plaintext = crypto.to_plaintext(params, detected_type)
            print(f"明文格式: {plaintext}")
            print(f"预期格式: {test['expected_plaintext']}")
            
            func_name = crypto.get_function_name(params[2])
            print(f"功能名称: {func_name}")
            
            # 反向加密验证
            seq = int(chr(bytes.fromhex(test['hex'].replace(" ", ""))[1]))
            ascii_enc, hex_enc = crypto.encrypt_packet(params, test['type'], sequence=seq)
            print(f"重新加密: {hex_enc}")
            
            # 检查匹配（忽略末尾的0x21）
            original_data = test['hex'].replace(" ", "")[:-2]
            encrypted_data = hex_enc.replace(" ", "")[:-2]
            match = encrypted_data == original_data
            print(f"加密匹配: {'✓' if match else '✗'}")
            
            if plaintext == test['expected_plaintext'] and match:
                success_count += 1
                print("✓ 测试通过")
            else:
                print("✗ 测试失败")
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"测试结果: {success_count}/{len(test_cases)} 通过")
    print("=" * 60)


def test_universal_parser():
    """测试通用封包解析器"""
    parser = UniversalPacketParser()
    
    print("=" * 80)
    print("通用封包解析器测试")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "移动封包",
            "hex": "23 34 3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 41 3E 72 58 3C 3C 6C 3D 52 3C 3C 21",
            "expected": "发送封包（0，0，3013，103，3，86，）"
        },
        {
            "name": "使用物品-修复神水",
            "hex": "23 34 53 48 3D 3C 3C 3C 3C 3C 3C 3C 3F 6A 3C 70 78 3C 53 5C 3C 3D 3C 3C 70 49 76 74 69 48 63 6D 6E 76 74 21",
            "expected": "发送封包（4243548，0，0，1006，6160463，修复神水）"
        },
        {
            "name": "使用物品-回城石",
            "hex": "23 31 7A 54 48 3C 3C 3C 3C 3C 3C 3C 3F 6A 3C 70 70 3C 54 3C 3C 3D 3C 3C 6A 79 5E 6F 6D 78 66 6B 21",
            "expected": "发送封包（33785，0，0，1006，6291533，回城石）"
        },
        {
            "name": "点击NPC",
            "hex": "23 38 3C 44 46 7A 3F 4C 3C 3C 3C 3C 3F 6E 3C 6C 3C 3C 3C 3C 3C 3C 3C 3C 21",
            "expected": "发送封包（230588928，0，0，1010，0，）"
        },
        {
            "name": "NPC对话",
            "hex": "23 37 3C 44 46 7A 3F 4C 3C 3C 3C 3C 3F 6F 3C 6C 3C 3C 3C 3C 3C 3C 3C 3C 4C 47 6F 4F 6E 4A 6B 42 77 78 66 7B 6F 58 50 6D 46 3F 3C 68 49 4F 5C 68 68 7B 52 79 71 6E 60 21",
            "expected": "发送封包（230588928，0，0，1011，0，@加入骑士团1(0,58,初阶)）"
        },
        {
            "name": "放入物品",
            "hex": "23 38 47 53 50 3C 3C 3C 3C 3C 3C 3C 3E 52 40 6C 74 3C 3C 3C 3C 3C 3C 3C 6F 69 77 64 65 67 53 40 70 57 4A 71 6C 49 53 5B 71 66 77 3C 74 4C 21",
            "expected": "发送封包（29997，0，0，5014，14，无瑕的殉道者之泪）"
        }
    ]
    
    success_count = 0
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"测试 {i}: {test['name']}")
        print(f"{'='*80}")
        print(f"输入HEX: {test['hex']}")
        
        # 解析
        result = parser.parse(test['hex'])
        
        if result['success']:
            print(f"\n✓ 解析成功")
            print(f"  序号: {result['sequence']}")
            print(f"  功能码: {result['function_code']} (0x{result['function_code']:04X})")
            print(f"  功能名称: {result['function_name']}")
            print(f"\n  核心数据:")
            for key, value in result['core_data'].items():
                print(f"    {key}: {value}")
            
            if 'extended_data' in result:
                print(f"\n  扩展数据:")
                print(f"    长度: {result['extended_data']['length']} 字节")
                if result['extended_data']['text']:
                    print(f"    文本: {result['extended_data']['text']}")
            
            print(f"\n  解密HEX: {result['decrypted_hex'][:48]}...")
            print(f"  明文格式: {result['plaintext']}")
            
            # 重构测试
            try:
                ascii_enc, hex_enc = parser.reconstruct(result, sequence=result['sequence'])
                print(f"\n  重构HEX: {hex_enc}")
                
                # 验证匹配
                original = test['hex'].replace(" ", "")
                reconstructed = hex_enc.replace(" ", "")
                match = original == reconstructed
                print(f"  重构匹配: {'✓' if match else '✗'}")
                
                if match:
                    success_count += 1
            except Exception as e:
                print(f"  ✗ 重构失败: {e}")
        else:
            print(f"\n✗ 解析失败")
            print(f"  错误: {result['error']}")
    
    print("\n" + "=" * 80)
    print(f"测试结果: {success_count}/{len(test_cases)} 通过")
    print("=" * 80)
    
    # 测试XOR表提取
    print("\n" + "=" * 80)
    print("XOR表提取测试")
    print("=" * 80)
    
    enc_hex = "23 34 3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 41 3E 72 58 3C 3C 6C 3D 52 3C 3C 21"
    dec_hex = "00 00 00 00 00 00 00 00 C5 0B 67 00 03 00 56 00"
    
    print(f"\n加密HEX: {enc_hex}")
    print(f"解密HEX: {dec_hex}")
    
    try:
        xor_table = parser.extract_xor_table(enc_hex, dec_hex)
        print(f"\n提取的XOR表:")
        print(f"  {xor_table}")
        print(f"  十六进制: {' '.join(f'0x{x:02X}' for x in xor_table)}")
        
        # 验证
        expected = [0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0x3C, 0xF9, 0x37, 0x58, 0x41, 0x3D, 0x72, 0x0E, 0x3C]
        match = xor_table == expected
        print(f"\n  验证: {'✓ 匹配已知XOR表' if match else '✗ 不匹配'}")
    except Exception as e:
        print(f"\n✗ 提取失败: {e}")


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = "3"  # 默认全部测试
    
    print("=" * 80)
    print("传奇翎风封包工具 - 加密引擎测试")
    print("=" * 80)
    print(f"测试模式: {choice}")
    print("  1 = 原有功能测试")
    print("  2 = 通用解析器测试")
    print("  3 = 全部测试")
    print("=" * 80)
    
    if choice in ["1", "3"]:
        test_crypto()
    
    if choice in ["2", "3"]:
        print("\n\n")
        test_universal_parser()
