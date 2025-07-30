import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import tarfile
import os
import threading
import shutil
import io
import configparser

# 根据您的定义，此字典用于查找OTA包
ota_inner_dir = {
    "cn": {
        "10.1": "10_1920_1200_vvx10f002a",
        "13.3": "13_1920_1080_nv156fhm",
        "16": "16_1920_1200_vvx10f002a",
        "qunchuang": "10_800_1280_fp7721bx2_innolux",
        "BOE": "10_800_1280_fp7721bx2_boe"
    },
    "en": {
        "10.1": "10_1920_1200_vvx10f002a",
        "13.3": "13_1920_1080_nv156fhm",
        "16": "16_1920_1200_vvx10f002a",
        "qunchuang": "10_800_1280_fp7721bx2_innolux",
        "BOE": "10_800_1280_fp7721bx2_boe"
    },
    "ts": {
        "10.1": "10_1920_1200_vvx10f002a",
        "13.3": "13_1920_1080_nv156fhm",
        "16": "16_1920_1200_vvx10f002a",
        "qunchuang": "10_800_1280_fp7721bx2_innolux",
        "BOE": "10_800_1280_fp7721bx2_boe"
    }
}

class OtaPatcher:
    """
    负责处理OTA包解包、修改、重新打包的核心逻辑，独立于GUI。
    """
    def __init__(self, log_callback):
        self.log = log_callback

    def is_binary_file(self, file_path):
        binary_extensions = {
            '.exe', '.bin', '.so', '.dll', '.img', '.iso', '.zip', '.gz',
            '.rar', '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.mp3', '.wav', '.mp4', '.avi', '.mkv', '.o', '.a', '.obj'
        }
        if any(file_path.lower().endswith(ext) for ext in binary_extensions):
            return True
        try:
            with open(file_path, 'rb') as f:
                return b'\x00' in f.read(1024)
        except (IOError, OSError):
            return False
        return False

    def list_contents(self, archive_path):
        """列出tar.gz包的内容"""
        contents = []
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    contents.append(member.name)
            return contents
        except tarfile.ReadError as e:
            self.log(f"错误: 无法读取归档文件 {os.path.basename(archive_path)}。可能不是有效的tar.gz文件。 {e}")
            return None
        except Exception as e:
            self.log(f"列出内容时发生未知错误: {e}")
            return None

    def _clone_tarinfo(self, tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
        """安全地从一个现有的TarInfo对象创建一个新的副本。"""
        new_info = tarfile.TarInfo(name=tarinfo.name)
        new_info.size = tarinfo.size
        new_info.mtime = tarinfo.mtime
        new_info.mode = tarinfo.mode
        new_info.type = tarinfo.type
        new_info.uid = tarinfo.uid
        new_info.gid = tarinfo.gid
        new_info.uname = tarinfo.uname
        new_info.gname = tarinfo.gname
        return new_info

    def patch_package(self, source_path, deletions, additions, new_version):
        """
        对OTA包执行补丁操作。
        :param source_path: SStarOta.bin.gz 的路径
        :param deletions: 要删除的内部文件/目录路径列表
        :param additions: 要添加的 { "source": "本地路径", "dest": "归档内路径" } 字典列表
        :param new_version: 新的版本号字符串, 如果为None则不修改
        """
        temp_path = source_path + ".tmp"
        deletions_set = set(deletions)

        try:
            with tarfile.open(source_path, "r:gz") as source_tar, tarfile.open(temp_path, "w:gz") as temp_tar:
                
                # 1. 遍历旧包，复制需要保留的文件，并修改版本文件
                for member in source_tar.getmembers():
                    # 检查是否应该删除此成员
                    if any(member.name == item or member.name.startswith(item + '/') for item in deletions_set):
                        self.log(f"- 已删除: {member.name}")
                        continue
                    
                    # --- FIX: Clone TarInfo object instead of reusing it ---
                    new_info = self._clone_tarinfo(member)

                    # 如果是目录等非文件类型，直接添加元数据即可
                    if not member.isfile():
                        temp_tar.addfile(new_info)
                        continue

                    # 对于文件，需要提取其内容
                    file_obj = source_tar.extractfile(member)
                    if not file_obj:
                         # Should not happen if member.isfile() is true, but as a safeguard
                        continue

                    # 如果是version.ini并且需要修改版本号
                    if member.name.endswith('version.ini') and new_version:
                        self.log(f"* 正在修改版本文件: {member.name}")
                        config = configparser.ConfigParser()
                        config.read_string(file_obj.read().decode('utf-8'))
                        config['version']['sversion'] = new_version
                        
                        string_io = io.StringIO()
                        config.write(string_io)
                        new_content_bytes = string_io.getvalue().encode('utf-8')
                        
                        new_info.size = len(new_content_bytes)
                        temp_tar.addfile(new_info, io.BytesIO(new_content_bytes))
                        self.log(f"  -> 版本号更新为: {new_version}")
                    else:
                        # 直接复制其他文件
                        temp_tar.addfile(new_info, file_obj)

                # 2. 添加新文件
                for item in additions:
                    source_file = item['source']
                    dest_path = item['dest']
                    
                    self.log(f"+ 正在添加: {source_file} -> {dest_path}")
                    if os.path.isdir(source_file):
                        # 递归添加目录
                        for root, _, files in os.walk(source_file):
                            for file in files:
                                full_path = os.path.join(root, file)
                                arcname = os.path.join(dest_path, os.path.relpath(full_path, source_file)).replace("\\", "/")
                                
                                tarinfo = tarfile.TarInfo(name=arcname)
                                tarinfo.size = os.path.getsize(full_path)
                                tarinfo.mtime = int(os.path.getmtime(full_path))
                                tarinfo.mode = 0o755 if self.is_binary_file(full_path) else 0o644
                                
                                with open(full_path, 'rb') as f:
                                    temp_tar.addfile(tarinfo, f)
                                self.log(f"  -> 添加文件: {arcname} (权限: {oct(tarinfo.mode)})")
                    else: # 是文件
                        arcname = os.path.join(dest_path, os.path.basename(source_file)).replace("\\", "/")
                        
                        tarinfo = tarfile.TarInfo(name=arcname)
                        tarinfo.size = os.path.getsize(source_file)
                        tarinfo.mtime = int(os.path.getmtime(source_file))
                        tarinfo.mode = 0o755 if self.is_binary_file(source_file) else 0o644
                        
                        with open(source_file, 'rb') as f:
                            temp_tar.addfile(tarinfo, f)
                        self.log(f"  -> 添加文件: {arcname} (权限: {oct(tarinfo.mode)})")

            # 3. 备份原文件并替换
            backup_path = source_path.replace(".bin.gz", ".bin.old.gz")
            self.log(f"正在备份原文件到: {os.path.basename(backup_path)}")
            shutil.move(source_path, backup_path)
            
            self.log(f"正在用新包替换: {os.path.basename(source_path)}")
            shutil.move(temp_path, source_path)
            
            self.log("打包成功！")
            return True

        except Exception as e:
            self.log(f"打包过程中发生严重错误: {e}")
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

class PatcherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("OTA 补丁工具 (OTA Patcher)")
        self.geometry("1200x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.patcher = OtaPatcher(self.log)
        self.selected_package = None
        self.files_to_add = []
        self.files_to_delete = []
        self.context_menu_widget = None

        self._setup_ui()
        self._setup_context_menu()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- LEFT PANEL ---
        left_panel = ctk.CTkFrame(self, width=350)
        left_panel.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="ns")
        left_panel.grid_rowconfigure(2, weight=1)
        
        ctk.CTkButton(left_panel, text="选择OTA根目录", command=self.find_ota_packages).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        ctk.CTkLabel(left_panel, text="找到的升级包:").grid(row=1, column=0, padx=10, pady=(10,0), sticky="w")

        # --- FIX: Frame for listbox and scrollbars ---
        listbox_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        listbox_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        listbox_frame.grid_rowconfigure(0, weight=1)
        listbox_frame.grid_columnconfigure(0, weight=1)

        y_scrollbar = ctk.CTkScrollbar(listbox_frame, orientation=tk.VERTICAL)
        x_scrollbar = ctk.CTkScrollbar(listbox_frame, orientation=tk.HORIZONTAL)
        
        self.package_listbox = tk.Listbox(listbox_frame, bg="#2B2B2B", fg="white", borderwidth=0, highlightthickness=0, yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        y_scrollbar.configure(command=self.package_listbox.yview)
        x_scrollbar.configure(command=self.package_listbox.xview)

        self.package_listbox.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")

        self.package_listbox.bind("<<ListboxSelect>>", self.on_package_select)

        # --- RIGHT PANEL ---
        right_panel = ctk.CTkFrame(self)
        right_panel.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        right_panel.grid_rowconfigure(0, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(right_panel)
        self.tab_view.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.tab_view.add("文件操作")
        self.tab_view.add("版本与打包")
        
        self._setup_files_tab()
        self._setup_pack_tab()

        # --- LOG / OUTPUT ---
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.log_textbox.configure(state="disabled", font=("Courier", 12))

    def _setup_files_tab(self):
        files_tab = self.tab_view.tab("文件操作")
        files_tab.grid_columnconfigure(0, weight=1)
        files_tab.grid_rowconfigure(0, weight=1)

        # Main paned window to split tree and deletion list
        paned_window = tk.PanedWindow(files_tab, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg="#2B2B2B")
        paned_window.grid(row=0, column=0, sticky="nsew")

        # --- Top Pane: Treeview for browsing ---
        tree_frame = ctk.CTkFrame(paned_window, fg_color="transparent")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        self.tree = ttk.Treeview(tree_frame, columns=("fullpath",), displaycolumns=())
        self.tree.heading("#0", text="包内文件浏览器 (右键添加到删除列表)", anchor='w')
        self.tree.grid(row=0, column=0, sticky="nsew")
        paned_window.add(tree_frame, height=300)

        # --- Bottom Pane: Deletion and Addition lists ---
        control_frame = ctk.CTkFrame(paned_window, fg_color="transparent")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_rowconfigure(1, weight=1)

        # Deletion List
        ctk.CTkLabel(control_frame, text="待删除项目列表:").grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")
        self.delete_listbox = tk.Listbox(control_frame, bg="#333333", fg="white", borderwidth=0, highlightthickness=0, selectmode=tk.EXTENDED)
        self.delete_listbox.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        ctk.CTkButton(control_frame, text="从列表移除选中项", command=self.remove_from_delete_list).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        # Addition Controls
        add_files_frame = ctk.CTkFrame(control_frame)
        add_files_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        ctk.CTkButton(add_files_frame, text="添加文件", command=self.add_file).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(add_files_frame, text="添加目录", command=self.add_folder).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(add_files_frame, text="清空待添加列表", command=self.clear_add_list).pack(side="left", padx=5, pady=5)
        self.add_list_label = ctk.CTkLabel(add_files_frame, text="待添加: 0 项")
        self.add_list_label.pack(side="left", padx=10)

        paned_window.add(control_frame)


    def _setup_pack_tab(self):
        pack_tab = self.tab_view.tab("版本与打包")
        pack_tab.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(pack_tab, text="新版本号 (留空则不修改):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.version_entry = ctk.CTkEntry(pack_tab, placeholder_text="例如: 2.00.34.4")
        self.version_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.start_button = ctk.CTkButton(pack_tab, text="对所有包执行批量打包", command=self.start_patching_thread, height=40)
        self.start_button.grid(row=1, column=0, columnspan=2, padx=10, pady=20)
        self.start_button.configure(state="disabled")

    def _setup_context_menu(self):
        """创建并绑定右键菜单"""
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2B2B2B", fg="white")
        self.context_menu.add_command(label="复制路径", command=self.copy_selection_to_clipboard)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="添加到待删除列表", command=self.add_selection_to_delete_list)

        self.package_listbox.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """根据点击的控件和位置，显示右键菜单"""
        widget = event.widget
        self.context_menu_widget = widget  # --- FIX: Store the widget that was right-clicked

        # Dynamically enable/disable menu items
        self.context_menu.entryconfigure("添加到待删除列表", state="disabled")

        if widget == self.package_listbox:
            self.package_listbox.selection_clear()
            index = self.package_listbox.nearest(event.y)
            if index != -1:
                self.package_listbox.selection_set(index)
                self.context_menu.post(event.x_root, event.y_root)
        elif widget == self.tree:
            item_id = self.tree.identify_row(event.y)
            if item_id:
                self.tree.selection_set(item_id)
                self.context_menu.entryconfigure("添加到待删除列表", state="normal")
                self.context_menu.post(event.x_root, event.y_root)

    def copy_selection_to_clipboard(self):
        """复制当前选中项的路径到剪贴板"""
        # --- FIX: Use the stored widget instead of unreliable focus_get() ---
        widget = self.context_menu_widget
        path_to_copy = None

        if widget == self.package_listbox and self.package_listbox.curselection():
            path_to_copy = self.package_listbox.get(self.package_listbox.curselection()[0])
        elif widget == self.tree and self.tree.selection():
            item_id = self.tree.selection()[0]
            path_to_copy = self.tree.item(item_id, "values")[0]
        
        if path_to_copy:
            self.clipboard_clear()
            self.clipboard_append(path_to_copy)
            self.log(f"已复制到剪贴板: {path_to_copy}")

    def log(self, message):
        def _log():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", message + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _log)

    def find_ota_packages(self):
        root_dir = filedialog.askdirectory(title="选择包含所有OTA包的根目录")
        if not root_dir: return
        
        self.package_listbox.delete(0, "end")
        self.log("正在搜索升级包...")
        
        found_packages = []
        for lang in ota_inner_dir:
            for screen_type in ota_inner_dir[lang]:
                package_dir = os.path.join(root_dir, lang, ota_inner_dir[lang][screen_type])
                package_path = os.path.join(package_dir, "SStarOta.bin.gz")
                if os.path.exists(package_path):
                    found_packages.append(package_path)
                    self.log(f"  找到: {package_path}")
        
        if not found_packages:
            self.log("未找到任何 'SStarOta.bin.gz' 文件。")
            messagebox.showwarning("未找到", "在指定目录下未根据规则找到任何升级包。")
            return
            
        for pkg in sorted(list(set(found_packages))): # Use set to avoid duplicates
             self.package_listbox.insert("end", pkg)
             
    def on_package_select(self, event=None):
        selection_indices = self.package_listbox.curselection()
        if not selection_indices: return
        
        self.selected_package = self.package_listbox.get(selection_indices[0])
        self.log(f"已选择升级包: {self.selected_package}")
        
        # Populate treeview
        self.tree.delete(*self.tree.get_children())
        contents = self.patcher.list_contents(self.selected_package)
        if contents:
            nodes = {'': ''} # path -> node_id mapping. Root is ''.
            for path in sorted(contents):
                if not path: continue
                
                # --- FIX START: Ensure parent nodes are created ---
                # Normalize path separators for consistency
                norm_path = path.replace("\\", "/")
                
                # Handle directory paths that end with a slash
                if norm_path.endswith('/'):
                    norm_path = norm_path.rstrip('/')
                
                parent_path, name = os.path.split(norm_path)
                
                # If parent does not exist in our node tracker, create it.
                # This loop handles nested parents (e.g., creating 'a' then 'a/b' for 'a/b/c').
                if parent_path and parent_path not in nodes:
                    temp_parent_id = ''
                    # Iterate through parts of the parent path and create nodes
                    path_parts = parent_path.split('/')
                    cumulative_path = ''
                    for part in path_parts:
                        if cumulative_path:
                            cumulative_path += '/'
                        cumulative_path += part
                        if cumulative_path not in nodes:
                            node_id = self.tree.insert(temp_parent_id, 'end', text=part, values=[cumulative_path], open=False)
                            nodes[cumulative_path] = node_id
                            temp_parent_id = node_id
                        else:
                            temp_parent_id = nodes[cumulative_path]

                parent_id = nodes.get(parent_path, '')
                
                # Do not re-insert a node if it was created as a parent directory
                if norm_path not in nodes:
                    node_id = self.tree.insert(parent_id, 'end', text=name, values=[path], open=False)
                    nodes[norm_path] = node_id
                # --- FIX END ---
        
        self.start_button.configure(state="normal" if self.package_listbox.size() > 0 else "disabled")
    
    def add_selection_to_delete_list(self):
        """从Treeview获取选中项并添加到删除列表"""
        if not self.tree.selection(): return
        
        current_delete_list = self.delete_listbox.get(0, "end")
        for item_id in self.tree.selection():
            path_to_add = self.tree.item(item_id, "values")[0]
            if path_to_add not in current_delete_list:
                self.delete_listbox.insert("end", path_to_add)
                self.log(f"已添加至删除列表: {path_to_add}")

    def remove_from_delete_list(self):
        """从删除列表中移除选中的项目"""
        selected_indices = self.delete_listbox.curselection()
        for i in reversed(selected_indices):
            self.delete_listbox.delete(i)

    def get_delete_list(self):
        return list(self.delete_listbox.get(0, "end"))

    def add_file(self):
        path = filedialog.askopenfilename(title="选择要添加的文件")
        if not path: return
        dest = simpledialog.askstring("输入路径", "输入文件在包内的目标目录 (例如 'system/bin'):", parent=self)
        if dest is not None:
            self.files_to_add.append({"source": path, "dest": dest})
            self.add_list_label.configure(text=f"待添加: {len(self.files_to_add)} 项")

    def add_folder(self):
        path = filedialog.askdirectory(title="选择要添加的目录")
        if not path: return
        dest = simpledialog.askstring("输入路径", "输入目录在包内的目标父目录 (例如 'system/'):", parent=self)
        if dest is not None:
            self.files_to_add.append({"source": path, "dest": dest})
            self.add_list_label.configure(text=f"待添加: {len(self.files_to_add)} 项")

    def clear_add_list(self):
        self.files_to_add.clear()
        self.add_list_label.configure(text=f"待添加: 0 项")
        self.log("待添加列表已清空。")
            
    def start_patching_thread(self):
        all_packages = self.package_listbox.get(0, "end")
        if not all_packages:
            messagebox.showerror("错误", "左侧列表中没有任何升级包可供操作。")
            return

        deletions = self.get_delete_list()
        new_version = self.version_entry.get() or None
        
        if not deletions and not self.files_to_add and not new_version:
            messagebox.showwarning("无操作", "您没有定义任何操作 (删除、添加、版本变更)。")
            return

        # --- MODIFICATION START: Detailed confirmation message ---
        msg = f"请确认将对列表中的 {len(all_packages)} 个升级包执行以下所有操作:\n\n"
        if deletions:
            msg += "--- 将删除以下项目 ---\n"
            for item in deletions[:10]: # Show up to 10 items
                msg += f" - {item}\n"
            if len(deletions) > 10:
                msg += f" ...等另外 {len(deletions) - 10} 个项目\n"
            msg += "\n"

        if self.files_to_add:
            msg += "--- 将添加以下项目 ---\n"
            for item in self.files_to_add[:10]: # Show up to 10 items
                msg += f" - {os.path.basename(item['source'])} -> {item['dest']}\n"
            if len(self.files_to_add) > 10:
                msg += f" ...等另外 {len(self.files_to_add) - 10} 个项目\n"
            msg += "\n"

        if new_version:
            msg += f"--- 版本号将更新为 ---\n - {new_version}\n\n"
        
        msg += f"确定要继续吗?"
        # --- MODIFICATION END ---

        if messagebox.askyesno("确认操作", msg):
            self.start_button.configure(state="disabled")
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.configure(state="disabled")
            
            thread = threading.Thread(
                target=self.run_batch_patcher,
                args=(all_packages, deletions, self.files_to_add.copy(), new_version)
            )
            thread.start()

    def run_batch_patcher(self, packages, deletions, additions, new_version):
        total = len(packages)
        for i, package_path in enumerate(packages):
            self.log(f"\n--- [{i+1}/{total}] 开始处理包: {os.path.basename(package_path)} ---")
            success = self.patcher.patch_package(package_path, deletions, additions, new_version)
            if not success:
                self.log(f"*** 包 {os.path.basename(package_path)} 处理失败! 终止批量操作。 ***")
                self.after(0, lambda: messagebox.showerror("失败", f"处理包 {os.path.basename(package_path)} 时发生错误，请查看日志。\n批量操作已终止。"))
                self.after(0, lambda: self.start_button.configure(state="normal"))
                return
        
        self.log("\n*** 所有包均已成功处理! ***")
        self.after(0, lambda: messagebox.showinfo("成功", f"全部 {total} 个升级包已成功打包！"))
        # Clear additions for next run
        self.files_to_add.clear()
        self.delete_listbox.delete(0, "end")
        self.after(0, lambda: self.add_list_label.configure(text=f"待添加: 0 项"))
        self.after(0, lambda: self.start_button.configure(state="normal"))

if __name__ == "__main__":
    app = PatcherApp()
    app.mainloop()
