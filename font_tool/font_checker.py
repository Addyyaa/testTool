import argparse
import sys
from fontTools.ttLib import TTFont

def check_font_characters(font_path):
    """
    加载一个字体文件，并循环接收用户输入，以检测字符是否存在于字体中。

    :param font_path: 要检测的字体文件的路径。
    """
    try:
        # 1. 加载字体文件
        print(f"正在加载字体文件: {font_path}")
        font = TTFont(font_path)
        
        # 2. 获取字体支持的 Unicode 字符集
        cmap = font.getBestCmap()
        if not cmap:
            print(f"错误: 字体 '{font_path}' 中没有找到有效的 cmap 表，无法检测。")
            return
        
        charset = set(cmap.keys())
        print(f"字体加载成功，共包含 {len(charset)} 个字符。")
        print("-" * 40)
        print("现在您可以开始输入文字进行检测了。")
        print("（直接按 Enter 或输入 'exit' 即可退出）")
        print("-" * 40)

        # 3. 开始循环检测
        while True:
            try:
                # 获取用户输入
                text_to_check = input("请输入要检测的字符 > ")

                # 检查退出条件
                if not text_to_check or text_to_check.lower() == 'exit':
                    print("程序已退出。")
                    break

                # 4. 逐字检测并报告结果
                all_found = True
                for char in text_to_check:
                    char_code = ord(char)
                    if char_code in charset:
                        print(f"  - 字符 '{char}' (Unicode: {hex(char_code)}): \033[92m已找到\033[0m")
                    else:
                        print(f"  - 字符 '{char}' (Unicode: {hex(char_code)}): \033[91m未找到\033[0m")
                        all_found = False
                
                if all_found:
                    print("\033[92m结论：您输入的所有字符都已在字体中找到！\033[0m")
                else:
                    print("\033[91m结论：部分或全部字符未在字体中找到。\033[0m")
                print("-" * 40)

            except KeyboardInterrupt:
                print("\n程序已退出。")
                break

    except FileNotFoundError:
        print(f"错误: 找不到字体文件 '{font_path}'", file=sys.stderr)
    except Exception as e:
        print(f"发生未知错误: {e}", file=sys.stderr)
    finally:
        if 'font' in locals():
            font.close()

def main():
    parser = argparse.ArgumentParser(
        description="一个交互式工具，用于检测指定字体文件中是否存在某些字符。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("font_file", help="要进行字符检测的字体文件路径 (例如: combined.ttf)")
    args = parser.parse_args()

    check_font_characters(args.font_file)

if __name__ == "__main__":
    main() 