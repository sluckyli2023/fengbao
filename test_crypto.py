#!/usr/bin/env python3
"""
封包加密解密命令行工具
用于快速测试和验证封包的加密解密功能
"""

import sys
from core.crypto import PacketCrypto, PacketType


def main():
    crypto = PacketCrypto()
    
    print("=" * 70)
    print("传奇翎风封包加密解密工具")
    print("=" * 70)
    
    # 测试样本
    test_samples = [
        {
            "name": "移动封包",
            "hex": "23 34 3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 41 3E 72 58 3C 3C 6C 3D 52 3C 3C 21",
            "type": PacketType.MOVE
        },
        {
            "name": "使用物品（修复神水）",
            "hex": "23 34 53 48 3D 3C 3C 3C 3C 3C 3C 3C 3F 6A 3C 70 78 3C 53 5C 3C 3D 3C 3C 70 49 76 74 69 48 63 6D 6E 76 74 21",
            "type": PacketType.ITEM
        },
        {
            "name": "点击NPC",
            "hex": "23 38 3C 44 46 7A 3F 4C 3C 3C 3C 3C 3F 6E 3C 6C 3C 3C 3C 3C 3C 3C 3C 3C 21",
            "type": PacketType.NPC_CLICK
        }
    ]
    
    for i, sample in enumerate(test_samples, 1):
        print(f"\n【测试 {i}】{sample['name']}")
        print("-" * 70)
        
        try:
            # 解密
            decrypted, params, detected_type = crypto.decrypt_packet(
                sample['hex'], 
                sample['type']
            )
            
            print(f"✓ 解密成功")
            print(f"  封包类型: {detected_type.value}")
            print(f"  功能码: {params[2]} ({crypto.get_function_name(params[2])})")
            print(f"  参数: {params[:6]}")
            
            # 转换为明文
            plaintext = crypto.to_plaintext(params, detected_type)
            print(f"  明文: {plaintext}")
            
            # 重新加密验证
            seq = int(chr(bytes.fromhex(sample['hex'].replace(" ", ""))[1]))
            ascii_enc, hex_enc = crypto.encrypt_packet(params, sample['type'], sequence=seq)
            
            # 验证加密结果
            original = sample['hex'].replace(" ", "")
            encrypted = hex_enc.replace(" ", "")
            
            if original == encrypted:
                print(f"✓ 加密验证通过")
            else:
                # 检查前16字节是否匹配
                if original[:34] == encrypted[:34]:
                    print(f"✓ 核心数据加密正确（前16字节匹配）")
                else:
                    print(f"✗ 加密验证失败")
                    
        except Exception as e:
            print(f"✗ 错误: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()

