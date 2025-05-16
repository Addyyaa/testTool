from file_factory import FileFactory

class ODFReaderController:
    def __init__(self, view):
        self.view = view
        self.model = None

    def load_file(self, file_path):
        try:
            self.model = FileFactory.get_reader(file_path)
            self.model.load_file(file_path)
            self.view.show_content(self.model.content, getattr(self.model, 'images', None))
            self.view.show_info("文件加载成功！")
        except Exception as e:
            self.view.show_error(str(e)) 