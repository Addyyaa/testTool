import argparse
import sys
import os
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

def merge_fonts(main_path, secondary_path, output_path, log_path=None):
    """
    将次字体文件中独有的字符合并到主字体文件中。
    最终决定版：放弃创建临时文件，直接在内存中将缺失的字形和度量数据注入主字体。

    :param main_path: 主字体文件的路径。
    :param secondary_path: 次字体文件的路径。
    :param output_path: 合并后新字体文件的输出路径。
    :param log_path: 将缺失字符记录到文件的路径 (可选)。
    """
    try:
        # --- 步骤 1: 加载主字体和次字体到内存 ---
        main_font = TTFont(main_path)
        secondary_font = TTFont(secondary_path)

        # --- 步骤 2: 分析和比较字符集 ---
        main_upem = main_font['head'].unitsPerEm
        secondary_upem = secondary_font['head'].unitsPerEm
        
        main_cmap = main_font.getBestCmap()
        main_charset = set(main_cmap.keys()) if main_cmap else set()
        
        secondary_cmap = secondary_font.getBestCmap()
        secondary_charset = set(secondary_cmap.keys()) if secondary_cmap else set()

        missing_unicodes = secondary_charset - main_charset
        
        if not missing_unicodes:
            print("次字体中的所有字符都已存在于主字体中，无需合并。")
            main_font.close()
            secondary_font.close()
            return
        
        print(f"发现 {len(missing_unicodes)} 个需要合并的独立字符。")

        # --- 步骤 3: 从次字体中提取所需的字形名称 ---
        # 我们需要一个反向的 cmap 来从 unicode 找到字形名称
        reverse_secondary_cmap = {v: k for k, v in secondary_cmap.items()}
        missing_glyph_names = {reverse_secondary_cmap[uni] for uni in missing_unicodes if uni in reverse_secondary_cmap}

        # --- 步骤 4: 提取、缩放并注入数据 ---
        print("正在提取、缩放并注入缺失的字符数据...")
        
        # 获取主字体和次字体的 glyf 和 hmtx 表
        main_glyf = main_font.get('glyf')
        main_hmtx = main_font.get('hmtx')
        secondary_glyf = secondary_font.get('glyf')
        secondary_hmtx = secondary_font.get('hmtx')

        # 检查必要的表是否存在
        if not all([main_glyf, main_hmtx, secondary_glyf, secondary_hmtx]):
            raise RuntimeError("一个或多个字体缺少必要的 'glyf' 或 'hmtx' 表。")

        # 计算缩放因子
        scale_factor = 1.0
        if main_upem != secondary_upem:
            print(f"警告: 字体 'unitsPerEm' 值不匹配。正在缩放...")
            scale_factor = main_upem / secondary_upem

        # 遍历缺失的字形，进行数据注入
        for glyph_name in missing_glyph_names:
            if glyph_name not in main_glyf:
                # 1. 注入字形轮廓 (glyf)
                glyph = secondary_glyf[glyph_name]
                if scale_factor != 1.0:
                    # 对字形进行缩放
                    if hasattr(glyph, 'coordinates'):
                        for i in range(len(glyph.coordinates)):
                            x, y = glyph.coordinates[i]
                            glyph.coordinates[i] = (round(x * scale_factor), round(y * scale_factor))
                    if glyph.isComposite():
                        for comp in glyph.components:
                            comp.x = round(comp.x * scale_factor)
                            comp.y = round(comp.y * scale_factor)
                main_glyf[glyph_name] = glyph

                # 2. 注入字符宽度 (hmtx)
                aw, lsb = secondary_hmtx[glyph_name]
                main_hmtx[glyph_name] = (round(aw * scale_factor), round(lsb * scale_factor))

                # 3. 注入字符映射 (cmap)
                # 找到该字形对应的 unicode
                uni = next((u for u, gn in secondary_cmap.items() if gn == glyph_name), None)
                if uni is not None:
                    main_cmap[uni] = glyph_name
        
        # --- 步骤 5: 更新主字体的 maxp 表 ---
        # 这是非常关键的一步，告诉主字体现在总共有多少个字形了
        main_font['maxp'].numGlyphs = len(main_glyf)
        print("数据注入完成。")

        # --- 步骤 6: 保存最终的合并字体 ---
        print(f"正在保存合并后的字体到: {output_path}")
        main_font.save(output_path)
        print("成功！")

    except Exception as e:
        print(f"发生错误: {e}", file=sys.stderr)
        
    finally:
        # --- 步骤 7: 清理 ---
        if 'main_font' in locals():
            main_font.close()
        if 'secondary_font' in locals():
            secondary_font.close()
        
def main():
    parser = argparse.ArgumentParser(
        description="将一个字体文件(次)中独有的字符合并到另一个字体文件(主)中。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("main_font", help="主字体文件的路径 (例如: base.ttf)")
    parser.add_argument("secondary_font", help="次字体文件的路径，从中提取新字符 (例如: new_chars.ttf)")
    parser.add_argument("output_font", help="合并后新字体文件的保存路径 (例如: combined.ttf)")
    parser.add_argument(
        "--log-chars-to",
        help="将需要合并的字符列表保存到指定的文件路径。(可选)"
    )

    args = parser.parse_args()
    # Log path is not used in this version, but kept for compatibility
    merge_fonts(args.main_font, args.secondary_font, args.output_font, args.log_chars_to)

if __name__ == "__main__":
    # 使用示例:
    # python font_tool/font_combined.py "path/to/main_font.ttf" "path/to/secondary_font.ttf" "path/to/output_font.ttf"
    #
    # 保存缺失字符日志:
    # python font_tool/font_combined.py main.ttf secondary.ttf merged.ttf --log-chars-to missing_chars.txt
    main()
                                                                                                                    