import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
import sys

print("当前Python路径：", sys.executable)
try:
    from easyofd.ofd import OFD
except ImportError:
    print("easyofd 未安装")


class ODFReaderView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ODF 阅读器")
        self.geometry("800x600")
        self.resizable(True, True)
        self.controller = None

        self._last_width = self.winfo_width()

        self.create_widgets()
        self.bind("<Configure>", self._on_resize)  # 监听窗口大小变化

    def create_widgets(self):
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)
        file_menu = tk.Menu(self.menu, tearoff=0)
        file_menu.add_command(label="打开", command=self.open_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        self.menu.add_cascade(label="文件", menu=file_menu)

        # 滚动区域
        self.canvas = tk.Canvas(self, bg="white")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.content_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.img_labels = []

    def set_controller(self, controller):
        self.controller = controller

    def open_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("ODF 文档", "*.odt"), ("OFD 文档", "*.ofd"), ("所有文件", "*.*")]
        )
        if file_path and self.controller:
            self.controller.load_file(file_path)

    def show_content(self, content, images=None):
        # 清空内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.img_labels = []
        self.pil_images = images if images else []

        # 显示文本
        text_label = tk.Label(self.content_frame, text=content, anchor="nw", justify="left", bg="white", font=("微软雅黑", 12))
        text_label.pack(fill=tk.X, anchor="nw", pady=5)

        # 显示图片
        if images:
            for img in images:
                frame_width = self.canvas.winfo_width() or 800
                img_width, img_height = img.size
                scale = min(frame_width / img_width, 1.0)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                tk_img = ImageTk.PhotoImage(resized_img)
                lbl = tk.Label(self.content_frame, image=tk_img, bg="white")
                lbl.image = tk_img  # 防止被回收
                lbl.pack(anchor="nw", pady=5)
                self.img_labels.append(lbl)

        self.content_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_resize(self, event):
        # 只在宽度变化时重绘，防止递归死循环
        new_width = self.winfo_width()
        if hasattr(self, "pil_images") and self.pil_images and new_width != getattr(self, "_last_width", None):
            self._last_width = new_width
            # 重新触发内容显示，传递原始图片
            text = ""
            for widget in self.content_frame.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget("text"):
                    text = widget.cget("text")
                    break
            self.show_content(text, self.pil_images)

    def show_error(self, message):
        messagebox.showerror("错误", message)

    def show_info(self, message):
        messagebox.showinfo("提示", message)
