from tkinter import filedialog


def create_truncated_image(img, size, dst_path):
    with open(img, 'rb') as f:
        data = f.read()
    bk_data = data[:size]
    with open(dst_path, 'wb') as f:
        f.write(bk_data)


img_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
output_path = img_path.replace(".jpg", "_truncated.jpg")
create_truncated_image(img_path, 1024, output_path)
