# 逆向工程指南 - OK.exe 解密算法提取

## 目标

从 OK.exe 中提取动态 XOR 表生成算法，用于正确解密游戏封包。

## 背景

### 问题描述

我们发现封包加密使用的 XOR 表是**动态生成**的，每个封包都不同：

```
封包 #3 (序号3): XOR[10]=0x02, XOR[14]=0x4F
封包 #4 (序号4): XOR[10]=0x01, XOR[14]=0x4B
封包 #8 (序号8): XOR[10]=0x0E, XOR[14]=0x0A
封包 #9 (序号9): XOR[10]=0x0E, XOR[14]=0x0B
```

### 已知信息

**封包结构**：
```
[0]     0x23 (#)           - 固定头
[1]     0x31-0x39         - 序号(1-9循环)
[2-17]  加密数据(16字节)   - 核心数据
[18+]   扩展数据          - 可变长度
[末尾]  0x21 (!)          - 固定尾
```

**解密后结构**：
```
[0-3]   参数1 (4字节，小端序)
[4-7]   参数2 (4字节，小端序)
[8-9]   功能码 (2字节，小端序)
[10-11] 参数3 (2字节，小端序)
[12-13] 参数4 (2字节，小端序)
[14-15] 参数5 (2字节，小端序)
```

**测试数据**：
- `jilu/2.txt` - 参考程序的正确解密结果
- `jilu/3.json` - 我们程序的错误解密结果
- `jilu/4.txt` - 参考程序的最新测试数据

---

## 工具准备

### 推荐工具

1. **Ghidra** (主要工具)
   - 下载：https://ghidra-sre.org/
   - 免费开源，功能强大
   - 支持自动反编译

2. **x64dbg** (动态调试)
   - 下载：https://x64dbg.com/
   - 用于运行时分析
   - 可以设置断点观察

3. **PE-bear** (可选)
   - 快速查看 PE 文件结构
   - 找到入口点和导入表

---

## 逆向分析步骤

### 第一步：静态分析（Ghidra）

#### 1.1 导入程序

```bash
1. 打开 Ghidra
2. File -> New Project -> Non-Shared Project
3. 项目名称：fengbao_reverse
4. Import File -> 选择 OK.exe
5. 双击打开 CodeBrowser
6. 分析选项：使用默认设置，点击 Analyze
```

#### 1.2 查找关键字符串

在 Ghidra 中搜索关键字符串：

```
Window -> Defined Strings
搜索关键词：
- "解密"
- "封包"
- "XOR"
- "发送封包"
- "套："
```

#### 1.3 定位解密函数

根据字符串引用，找到解密函数。可能的特征：

```c
// 伪代码特征
for (i = 0; i < 16; i++) {
    decrypted[i] = encrypted[i] ^ xor_table[i];
}
```

#### 1.4 分析 XOR 表生成

重点关注：
- XOR 表是如何初始化的
- 是否使用了序号（封包第2字节）
- 是否使用了时间戳或随机数
- 是否有种子值（seed）

### 第二步：动态调试（x64dbg）

#### 2.1 设置断点

```
1. 打开 x64dbg，加载 OK.exe
2. 在 Ghidra 找到的解密函数地址设置断点
3. 运行程序，触发封包捕获
4. 观察寄存器和内存中的 XOR 表
```

#### 2.2 追踪 XOR 表生成

```
1. 在 XOR 表内存地址设置内存断点
2. 回溯调用栈，找到生成函数
3. 记录生成算法的输入参数
```

### 第三步：算法提取

#### 3.1 记录关键信息

创建文档记录：

```markdown
## XOR 表生成算法

### 输入参数
- 序号：[值]
- 功能码：[值]
- 其他：[...]

### 算法伪代码
[从 Ghidra 反编译结果整理]

### 关键常量
- 种子值：0x[...]
- 魔数：0x[...]
```

#### 3.2 Python 实现

根据伪代码实现 Python 版本：

```python
def generate_xor_table(sequence, function_code):
    """
    动态生成 XOR 表
    
    Args:
        sequence: 封包序号 (1-9)
        function_code: 功能码
    
    Returns:
        list: 16字节的 XOR 表
    """
    xor_table = [0x3C] * 16
    
    # TODO: 根据逆向结果实现算法
    
    return xor_table
```

#### 3.3 验证算法

使用测试数据验证：

```python
# 测试封包 #3
encrypted = bytes.fromhex('3C 3C 3C 3C 3C 3C 3C 3C 3C 3C 3F 3F 3E 6F 70 3D 3D 5C 3C 7B 3C 4C')
expected = bytes.fromhex('00 00 00 00 00 00 00 00 C3 0B 3D 01 06 00 3F 01')

xor_table = generate_xor_table(sequence=3, function_code=0x0BC3)
decrypted = bytes([encrypted[i] ^ xor_table[i] for i in range(16)])

assert decrypted == expected, "解密失败！"
print("✓ 验证成功！")
```

---

## 常见问题

### Q1: Ghidra 反编译结果看不懂？

**A**: 
1. 右键函数 -> Edit Function Signature，修正参数类型
2. 重命名变量（右键 -> Rename Variable）
3. 添加注释（; 键）

### Q2: 找不到解密函数？

**A**: 
1. 搜索 XOR 指令：`Search -> For Instruction Patterns -> XOR`
2. 查找循环结构（for/while）
3. 搜索常量 0x3C（XOR 表的常见值）

### Q3: 动态调试程序崩溃？

**A**: 
1. 检查是否有反调试保护
2. 使用 ScyllaHide 插件
3. 尝试附加到已运行的进程

---

## 输出成果

完成逆向后，提供以下文件：

1. **算法文档** (`DECRYPT_ALGORITHM.md`)
   - 详细的算法说明
   - 伪代码
   - 关键常量

2. **Python 实现** (`dynamic_xor.py`)
   - `generate_xor_table()` 函数
   - 单元测试
   - 使用示例

3. **Ghidra 项目** (可选)
   - 导出的反编译结果
   - 注释和标记

---

## 集成到项目

将提取的算法集成到 `core/crypto.py`：

```python
class UniversalPacketParser:
    def _get_xor_table(self, sequence, function_code):
        """
        动态生成 XOR 表（从逆向工程提取）
        
        Args:
            sequence: 封包序号
            function_code: 功能码
        
        Returns:
            list: XOR 表
        """
        # 从 dynamic_xor.py 导入
        from .dynamic_xor import generate_xor_table
        return generate_xor_table(sequence, function_code)
```

---

## 时间估算

- **静态分析**：1-2 小时
- **动态调试**：1-2 小时
- **算法实现**：30 分钟
- **测试验证**：30 分钟

**总计**：3-5 小时

---

## 注意事项

⚠️ **法律和道德**：
- 仅用于学习和研究目的
- 不要用于破坏游戏平衡
- 尊重原作者的知识产权

⚠️ **技术风险**：
- 程序可能有反调试保护
- 算法可能定期更新
- 需要持续维护

---

*创建日期：2026-01-11*
*用途：提取 OK.exe 的动态 XOR 表生成算法*

