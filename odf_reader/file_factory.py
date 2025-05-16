from model import ODFModel, OFDModel

class FileFactory:
    @staticmethod
    def get_reader(file_path):
        if file_path.endswith('.odt'):
            return ODFModel()
        elif file_path.endswith('.ofd'):
            return OFDModel()
        else:
            raise ValueError("暂不支持该文件类型") 