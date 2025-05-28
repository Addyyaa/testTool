import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ExifTags

ORIENTATION_VALUES = {
    1: "正常",
    2: "水平翻转",
    3: "旋转180°",
    4: "垂直翻转",
    5: "顺时针90°后水平翻转",
    6: "顺时针旋转90°",
    7: "顺时针270°后水平翻转",
    8: "逆时针旋转90°",
}

OUTPUT_DIR = "outputImg"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


class OrientationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("设置图片 EXIF 方向")

        self.image_path = None

        # GUI布局
        tk.Button(root, text="选择图片", command=self.select_image).grid(row=0, column=0, padx=10, pady=10)
        self.path_label = tk.Label(root, text="未选择图片", width=50, anchor="w")
        self.path_label.grid(row=0, column=1, columnspan=2, padx=10)

        tk.Label(root, text="选择 Orientation 值（1~8）").grid(row=1, column=0, padx=10, pady=10)
        self.orient_var = tk.IntVar(value=1)
        self.orient_menu = tk.OptionMenu(root, self.orient_var, *ORIENTATION_VALUES.keys())
        self.orient_menu.grid(row=1, column=1, sticky="w")

        self.desc_label = tk.Label(root, text=ORIENTATION_VALUES[1])
        self.desc_label.grid(row=1, column=2, sticky="w")

        self.orient_var.trace("w", self.update_description)

        tk.Button(root, text="生成修改图片", command=self.modify_orientation).grid(row=2, column=0, columnspan=3,
                                                                                   pady=10)

        # 工具说明区域
        explanation = "Orientation 值说明：\n"
        for k in sorted(ORIENTATION_VALUES):
            explanation += f"{k}: {ORIENTATION_VALUES[k]}\n"

        self.explain_label = tk.Label(root, text=explanation, justify="left", fg="gray", anchor="w", font=("Arial", 10))
        self.explain_label.grid(row=3, column=0, columnspan=3, padx=10, pady=(10, 20), sticky="w")

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if path:
            self.image_path = path
            self.path_label.config(text=os.path.basename(path))

    def update_description(self, *args):
        val = self.orient_var.get()
        self.desc_label.config(text=ORIENTATION_VALUES.get(val, ""))

    def modify_orientation(self):
        if not self.image_path:
            messagebox.showwarning("未选择图片", "请先选择一张图片")
            return

        try:
            image = Image.open(self.image_path)
            exif = image.getexif()

            orientation_tag = next((k for k, v in ExifTags.TAGS.items() if v == "Orientation"), None)
            if orientation_tag:
                exif[orientation_tag] = self.orient_var.get()

            filename = os.path.basename(self.image_path)
            name, ext = os.path.splitext(filename)
            output_path = os.path.join(OUTPUT_DIR, f"{name}_orient{self.orient_var.get()}{ext}")

            image.save(output_path, exif=exif)
            messagebox.showinfo("成功", f"已保存到：{output_path}")

        except Exception as e:
            messagebox.showerror("错误", f"处理图片时出错：{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = OrientationApp(root)
    root.mainloop()
