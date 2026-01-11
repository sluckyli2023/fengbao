"""
主窗口 - 基于 tkinter 的简洁 GUI
重构自 PyQt5 方案

设计理念:
- 简洁实用，避免过度设计
- 参考 cankao/svhost.py 的优秀 UX
- 体积小，打包后 < 5MB
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime
import sys
import os

# Windows API (用于进程选择)
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi


class ProcessSelector:
    """进程选择器 - 支持列表选择和拖动瞄准器"""
    
    @staticmethod
    def list_processes():
        """列出所有进程"""
        processes = []
        
        if sys.platform != 'win32':
            return processes
        
        try:
            arr = (wintypes.DWORD * 2048)()
            cb_needed = wintypes.DWORD()
            
            if psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(cb_needed)):
                count = cb_needed.value // ctypes.sizeof(wintypes.DWORD)
                
                for i in range(count):
                    pid = arr[i]
                    if pid == 0:
                        continue
                    
                    try:
                        h_process = kernel32.OpenProcess(0x0410, False, pid)
                        if h_process:
                            exe_name = (ctypes.c_wchar * 260)()
                            if psapi.GetModuleBaseNameW(h_process, None, exe_name, 260):
                                name = exe_name.value
                                if name and len(name.strip()) > 0:
                                    # 获取窗口标题
                                    title = ProcessSelector.get_window_title_by_pid(pid)
                                    processes.append({
                                        "pid": pid, 
                                        "name": name,
                                        "title": title
                                    })
                            kernel32.CloseHandle(h_process)
                    except:
                        pass
        except Exception as e:
            print(f"列举进程错误: {e}")
        
        return processes
    
    @staticmethod
    def get_window_title_by_pid(pid):
        """根据 PID 获取窗口标题"""
        if sys.platform != 'win32':
            return ""
        
        titles = []
        
        def enum_windows_callback(hwnd, lParam):
            if user32.IsWindowVisible(hwnd):
                window_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
                
                if window_pid.value == pid:
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        if buff.value:
                            titles.append(buff.value)
            return True
        
        try:
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int)
            )
            user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        except:
            pass
        
        return titles[0] if titles else ""


class MainWindow:
    """主窗口 - tkinter 实现"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("传奇翎风封包工具")
        self.root.geometry("1000x700")
        
        # 状态变量
        self.interceptor = None
        self.interceptor_thread = None
        self.target_pid = None
        self.target_process_name = None
        self.is_running = False
        
        # 捕获的封包列表
        self.captured_packets = []
        
        # 设置 UI
        self.setup_ui()
        
        # 设置关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """设置界面"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部：进程选择区域
        self.setup_process_selection(main_frame)
        
        # 中部：控制按钮
        self.setup_control_buttons(main_frame)
        
        # 中部：封包列表
        self.setup_packet_list(main_frame)
        
        # 底部：日志区域
        self.setup_log_area(main_frame)
        
        # 状态栏
        self.setup_status_bar(main_frame)
    
    def setup_process_selection(self, parent):
        """进程选择区域"""
        frame = ttk.LabelFrame(parent, text="🎯 进程选择", padding=10)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 当前选择的进程
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text="目标进程:").pack(side=tk.LEFT)
        self.process_label = ttk.Label(
            info_frame, 
            text="未选择", 
            foreground="red",
            font=("", 10, "bold")
        )
        self.process_label.pack(side=tk.LEFT, padx=10)
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(
            btn_frame, 
            text="📋 从列表选择", 
            command=self.select_from_list
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="🎯 拖动瞄准器", 
            command=self.select_by_crosshair
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="🌐 全局模式", 
            command=self.select_global_mode
        ).pack(side=tk.LEFT, padx=5)
    
    def setup_control_buttons(self, parent):
        """控制按钮区域"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧：捕获控制
        left_frame = ttk.Frame(frame)
        left_frame.pack(side=tk.LEFT)
        
        self.start_btn = ttk.Button(
            left_frame,
            text="▶ 开始捕获",
            command=self.start_capture,
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            left_frame,
            text="⏹ 停止捕获",
            command=self.stop_capture,
            state=tk.DISABLED,
            width=15
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧：其他功能
        right_frame = ttk.Frame(frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            right_frame,
            text="🔄 清空列表",
            command=self.clear_packets
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            right_frame,
            text="💾 导出封包",
            command=self.export_packets
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            right_frame,
            text="🔌 服务器连接",
            command=self.connect_server
        ).pack(side=tk.LEFT, padx=5)
    
    def setup_packet_list(self, parent):
        """封包列表区域"""
        frame = ttk.LabelFrame(parent, text="📦 捕获的封包", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建 Treeview
        columns = ("序号", "时间", "方向", "功能", "明文预览")
        self.packet_tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=10
        )
        
        # 设置列
        self.packet_tree.heading("序号", text="序号")
        self.packet_tree.heading("时间", text="时间")
        self.packet_tree.heading("方向", text="方向")
        self.packet_tree.heading("功能", text="功能")
        self.packet_tree.heading("明文预览", text="明文预览")
        
        self.packet_tree.column("序号", width=60, anchor=tk.CENTER)
        self.packet_tree.column("时间", width=150, anchor=tk.CENTER)
        self.packet_tree.column("方向", width=80, anchor=tk.CENTER)
        self.packet_tree.column("功能", width=150, anchor=tk.CENTER)
        self.packet_tree.column("明文预览", width=400, anchor=tk.W)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.packet_tree.yview)
        self.packet_tree.configure(yscrollcommand=scrollbar.set)
        
        self.packet_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击查看详情
        self.packet_tree.bind("<Double-1>", self.view_packet_detail)
    
    def setup_log_area(self, parent):
        """日志区域"""
        frame = ttk.LabelFrame(parent, text="📝 运行日志", padding=5)
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            frame,
            height=8,
            state=tk.DISABLED,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置标签颜色
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
    
    def setup_status_bar(self, parent):
        """状态栏"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(frame, text="状态: 就绪")
        self.status_label.pack(side=tk.LEFT)
        
        self.stats_label = ttk.Label(frame, text="")
        self.stats_label.pack(side=tk.RIGHT)
    
    # ==================== 进程选择功能 ====================
    
    def select_from_list(self):
        """从列表选择进程"""
        if sys.platform != 'win32':
            messagebox.showinfo("提示", "仅支持 Windows 系统")
            return
        
        # 创建选择窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("选择进程")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 说明
        ttk.Label(
            dialog,
            text="提示: 显示进程名、PID 和窗口标题，方便识别",
            foreground="gray"
        ).pack(pady=10)
        
        # 创建列表
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("进程名", "PID", "窗口标题")
        tree = ttk.Treeview(frame, columns=columns, show="headings")
        
        tree.heading("进程名", text="进程名")
        tree.heading("PID", text="PID")
        tree.heading("窗口标题", text="窗口标题")
        
        tree.column("进程名", width=150)
        tree.column("PID", width=80, anchor=tk.CENTER)
        tree.column("窗口标题", width=400)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 加载进程列表
        self.log("正在加载进程列表...")
        processes = ProcessSelector.list_processes()
        
        for p in sorted(processes, key=lambda x: x['name'].lower()):
            tree.insert("", tk.END, values=(
                p['name'],
                p['pid'],
                p['title'] if p['title'] else "(无窗口)"
            ))
        
        self.log(f"已加载 {len(processes)} 个进程")
        
        # 选择按钮
        def on_select():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一个进程")
                return
            
            item = tree.item(selection[0])
            values = item['values']
            
            self.target_pid = values[1]
            self.target_process_name = values[0]
            
            title_info = f" - {values[2]}" if values[2] != "(无窗口)" else ""
            self.process_label.config(
                text=f"{values[0]} (PID: {values[1]}){title_info}",
                foreground="green"
            )
            
            self.log(f"✓ 已选择进程: {values[0]} (PID: {values[1]})")
            dialog.destroy()
        
        ttk.Button(dialog, text="选择", command=on_select).pack(pady=10)
    
    def select_by_crosshair(self):
        """拖动瞄准器选择进程"""
        messagebox.showinfo(
            "功能开发中",
            "拖动瞄准器功能正在开发中\n\n"
            "当前请使用「从列表选择」功能"
        )
        # TODO: 实现拖动瞄准器功能
    
    def select_global_mode(self):
        """全局模式"""
        self.target_pid = None
        self.target_process_name = None
        self.process_label.config(text="全局模式 (所有进程)", foreground="blue")
        self.log("✓ 已切换到全局模式")
    
    # ==================== 捕获控制功能 ====================
    
    def start_capture(self):
        """开始捕获"""
        try:
            # 导入拦截器
            from core.packet_interceptor import PacketInterceptor
            
            # 创建拦截器
            self.interceptor = PacketInterceptor(
                target_pid=self.target_pid,
                callback=self.on_packet_captured
            )
            
            # 启动拦截线程
            self.interceptor_thread = threading.Thread(
                target=self.interceptor.start,
                daemon=True
            )
            self.interceptor_thread.start()
            
            # 更新 UI
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_label.config(text="状态: 运行中")
            
            mode = f"进程 {self.target_process_name} (PID: {self.target_pid})" if self.target_pid else "全局模式"
            self.log(f"✓ 开始捕获封包 - {mode}", "SUCCESS")
            
            # 启动统计更新
            self.update_stats()
            
        except ImportError as e:
            messagebox.showerror("错误", f"无法导入拦截器模块:\n{e}\n\n请确保已安装 pydivert")
        except Exception as e:
            messagebox.showerror("错误", f"启动失败:\n{e}")
            self.log(f"✗ 启动失败: {e}", "ERROR")
    
    def stop_capture(self):
        """停止捕获"""
        if self.interceptor:
            self.interceptor.stop()
            self.interceptor = None
        
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 已停止")
        
        self.log("✓ 已停止捕获", "SUCCESS")
    
    def on_packet_captured(self, packet_data):
        """封包捕获回调"""
        # 添加到列表
        self.captured_packets.append(packet_data)
        
        # 更新 UI (在主线程中)
        self.root.after(0, self._add_packet_to_tree, packet_data)
    
    def _add_packet_to_tree(self, packet_data):
        """添加封包到树形列表"""
        seq = len(self.captured_packets)
        timestamp = packet_data['timestamp'].strftime('%H:%M:%S.%f')[:-3]
        direction = packet_data['direction']
        
        parsed = packet_data.get('parsed_data', {})
        if parsed.get('success'):
            function = parsed.get('function_name', '未知')
            plaintext = parsed.get('plaintext', '')
            if len(plaintext) > 50:
                plaintext = plaintext[:50] + "..."
        else:
            function = "解析失败"
            plaintext = parsed.get('error', '')
        
        self.packet_tree.insert("", tk.END, values=(
            seq,
            timestamp,
            direction,
            function,
            plaintext
        ))
        
        # 自动滚动到底部
        self.packet_tree.yview_moveto(1.0)
    
    def view_packet_detail(self, event):
        """查看封包详情"""
        selection = self.packet_tree.selection()
        if not selection:
            return
        
        item = self.packet_tree.item(selection[0])
        seq = int(item['values'][0])
        
        if seq > len(self.captured_packets):
            return
        
        packet_data = self.captured_packets[seq - 1]
        
        # 创建详情窗口
        dialog = tk.Toplevel(self.root)
        dialog.title(f"封包详情 - #{seq}")
        dialog.geometry("800x600")
        
        # 详情文本
        text = scrolledtext.ScrolledText(dialog, font=("Consolas", 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 格式化显示
        text.insert(tk.END, f"序号: {seq}\n")
        text.insert(tk.END, f"时间: {packet_data['timestamp']}\n")
        text.insert(tk.END, f"方向: {packet_data['direction']}\n")
        text.insert(tk.END, f"源地址: {packet_data['src_addr']}:{packet_data['src_port']}\n")
        text.insert(tk.END, f"目标地址: {packet_data['dst_addr']}:{packet_data['dst_port']}\n")
        text.insert(tk.END, f"\n原始数据 (十六进制):\n")
        
        payload_hex = ' '.join(f'{b:02X}' for b in packet_data['payload'])
        text.insert(tk.END, payload_hex + "\n")
        
        # 添加 ASCII 码显示
        text.insert(tk.END, f"\nASCII 码:\n")
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in packet_data['payload'])
        text.insert(tk.END, ascii_str + "\n")
        
        # 添加解密后的十六进制（如果有）
        parsed = packet_data.get('parsed_data', {})
        if parsed.get('success'):
            text.insert(tk.END, f"\n解密后数据 (十六进制):\n")
            text.insert(tk.END, parsed.get('decrypted_hex', '') + "\n")
            
            text.insert(tk.END, f"\n解析结果:\n")
            text.insert(tk.END, f"功能: {parsed.get('function_name', '未知')}\n")
            text.insert(tk.END, f"功能码: {parsed.get('function_code', 0)}\n")
            
            # 显示核心数据
            core_data = parsed.get('core_data', {})
            if core_data:
                text.insert(tk.END, f"\n核心参数:\n")
                text.insert(tk.END, f"  参数1: {core_data.get('param1', 0)}\n")
                text.insert(tk.END, f"  参数2: {core_data.get('param2', 0)}\n")
                text.insert(tk.END, f"  参数3: {core_data.get('param3', 0)}\n")
                text.insert(tk.END, f"  参数4: {core_data.get('param4', 0)}\n")
                text.insert(tk.END, f"  参数5: {core_data.get('param5', 0)}\n")
            
            # 显示扩展数据
            ext_data = parsed.get('extended_data')
            if ext_data:
                text.insert(tk.END, f"\n扩展数据:\n")
                if ext_data.get('text'):
                    text.insert(tk.END, f"  文本: {ext_data['text']}\n")
                text.insert(tk.END, f"  长度: {ext_data.get('length', 0)} 字节\n")
                if ext_data.get('raw_bytes'):
                    raw_hex = ' '.join(f'{b:02X}' for b in ext_data['raw_bytes'])
                    text.insert(tk.END, f"  原始: {raw_hex}\n")
            
            text.insert(tk.END, f"\n明文格式:\n")
            text.insert(tk.END, parsed.get('plaintext', '') + "\n")
        else:
            text.insert(tk.END, f"\n解析失败:\n")
            text.insert(tk.END, parsed.get('error', '未知错误') + "\n")
        
        text.config(state=tk.DISABLED)
    
    def clear_packets(self):
        """清空封包列表"""
        if messagebox.askyesno("确认", "确定要清空封包列表吗？"):
            self.captured_packets.clear()
            for item in self.packet_tree.get_children():
                self.packet_tree.delete(item)
            self.log("✓ 已清空封包列表")
    
    def export_packets(self):
        """导出封包"""
        if not self.captured_packets:
            messagebox.showinfo("提示", "没有可导出的封包")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            try:
                import json
                
                data = []
                for i, packet in enumerate(self.captured_packets, 1):
                    # 处理解析结果，移除不可序列化的对象
                    parsed = packet.get('parsed_data', {})
                    parsed_clean = {}
                    
                    if parsed:
                        for key, value in parsed.items():
                            if key == 'extended_data' and isinstance(value, dict):
                                # 处理扩展数据中的 bytes
                                ext_clean = {}
                                for k, v in value.items():
                                    if k == 'raw_bytes' and isinstance(v, bytes):
                                        ext_clean[k] = v.hex()  # 转换为十六进制字符串
                                    else:
                                        ext_clean[k] = v
                                parsed_clean[key] = ext_clean
                            elif isinstance(value, bytes):
                                parsed_clean[key] = value.hex()
                            else:
                                parsed_clean[key] = value
                    
                    data.append({
                        "序号": i,
                        "时间": packet['timestamp'].isoformat(),
                        "方向": packet['direction'],
                        "源地址": f"{packet['src_addr']}:{packet['src_port']}",
                        "目标地址": f"{packet['dst_addr']}:{packet['dst_port']}",
                        "原始数据": packet['payload'].hex(),
                        "解析结果": parsed_clean
                    })
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.log(f"✓ 已导出 {len(data)} 个封包到: {filename}", "SUCCESS")
                messagebox.showinfo("成功", f"已导出 {len(data)} 个封包")
                
            except Exception as e:
                messagebox.showerror("错误", f"导出失败:\n{e}")
                self.log(f"✗ 导出失败: {e}", "ERROR")
    
    def connect_server(self):
        """连接服务器"""
        messagebox.showinfo(
            "功能开发中",
            "服务器连接功能正在开发中\n\n"
            "当前版本专注于封包捕获和解析"
        )
        # TODO: 实现服务器连接功能
    
    # ==================== 辅助功能 ====================
    
    def update_stats(self):
        """更新统计信息"""
        if self.is_running and self.interceptor:
            stats = self.interceptor.get_stats()
            self.stats_label.config(
                text=f"总计: {stats['total']} | 解析成功: {stats['parsed']} | 解析失败: {stats['failed']} | 速率: {stats['rate']}"
            )
            self.root.after(1000, self.update_stats)
    
    def log(self, msg, level="INFO"):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        line = f"[{timestamp}] {msg}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line, level)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def on_closing(self):
        """关闭窗口"""
        if self.is_running:
            if messagebox.askyesno("确认", "捕获正在运行，确定要退出吗？"):
                self.stop_capture()
                time.sleep(0.5)
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """运行程序"""
        self.log("=" * 60)
        self.log("传奇翎风封包工具 v2.0 (重构版)")
        self.log("=" * 60)
        self.log("")
        self.log("架构: WinDivert + tkinter")
        self.log("特性: 驱动层拦截 + 精确进程绑定")
        self.log("")
        self.log("使用方法:")
        self.log("  1. 选择目标进程（或使用全局模式）")
        self.log("  2. 点击「开始捕获」")
        self.log("  3. 双击封包查看详情")
        self.log("")
        self.log("准备就绪")
        self.log("=" * 60)
        self.log("")
        
        self.root.mainloop()


if __name__ == '__main__':
    """测试代码"""
    # 检查管理员权限
    if sys.platform == 'win32':
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                messagebox.showerror(
                    "错误",
                    "需要管理员权限!\n\n请右键选择「以管理员身份运行」"
                )
                sys.exit(1)
        except:
            pass
    
    app = MainWindow()
    app.run()

