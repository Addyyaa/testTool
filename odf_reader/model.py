from odf.opendocument import load
from odf.text import P

class ODFModel:
    def __init__(self):
        self.content = ""

    def load_file(self, file_path):
        try:
            doc = load(file_path)
            paragraphs = doc.getElementsByType(P)
            self.content = "\n".join([str(p) for p in paragraphs])
        except Exception as e:
            raise RuntimeError(f"文件读取失败: {e}")

# 新增OFDModel
class OFDModel:
    def __init__(self):
        self.content = ""
        self.images = []  # 新增，存储图片

    def load_file(self, file_path):
        try:
            try:
                from easyofd import OFD
            except ImportError:
                raise RuntimeError("未安装 easyofd 库，请先运行 pip install easyofd")
            ofd = OFD()
            ofd.read(file_path, fmt="path")
            text = []
            if hasattr(ofd.data, 'pages'):
                for page in ofd.data.pages:
                    if hasattr(page, 'text'):
                        page_text = page.text()
                        if page_text:
                            text.append(page_text)
            if text:
                self.content = '\n'.join(text)
                self.images = []
            else:
                # 提取图片
                try:
                    images = ofd.to_jpg()
                    if images:
                        self.content = "[该OFD为图片型，已为你显示图片]"
                        self.images = images
                    else:
                        self.content = "[未能提取OFD文本内容]"
                        self.images = []
                except Exception as e:
                    self.content = "[未能提取OFD文本内容]"
                    self.images = []
        except Exception as e:
            raise RuntimeError(f"OFD文件读取失败: {e}")
