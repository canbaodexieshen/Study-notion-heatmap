import os
import subprocess
import datetime
import re
import sys

def process_svg_colors(file_path):
    """核心逻辑：根据 SVG 中的数据提示重新着色"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def color_replacer(match):
        rect_tag = match.group(0)
        # 提取方块里记录的“分钟”数据
        val_match = re.search(r'(\d+\.?\d*)\s*分钟', rect_tag)
        if val_match:
            val = float(val_match.group(1))
            # 你的专属判定逻辑：
            if val == 0:
                color = "#EBEDF0"  # 0h：空白/浅灰底色
            elif val < 240:
                color = "#D1D5DB"  # <4h：灰色
            elif val < 480:
                color = "#3B82F6"  # 4~8h：蓝色 (包含 4~6h)
            else:
                color = "#10B981"  # ≥8h：绿色
            
            # 将原始颜色替换为判定后的专属颜色
            return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        return rect_tag

    # 扫描并替换所有的方块标签
    new_content = re.sub(r'<rect[^>]*>.*?<\/rect>', color_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    # 安全检查
    if not notion_token or not database_id:
        print("❌ 致命错误：未找到 NOTION_TOKEN 或 NOTION_DATABASE_ID！")
        sys.exit(1)

    current_year = datetime.datetime.now().year

    # 👇 核心修复：在这里把 --dom-color 等画板颜色全部加回来！
    # 这样工具就会乖乖地画出完整的基础格子，方便我们后续上色。
    command = f'github_heatmap notion --notion_token {notion_token} --database_id {database_id} --date_prop_name 日期 --value_prop_name 我的运动热力图 --unit 分钟 --year {current_year} --me 学习热力图 --without-type-name --background-color=#FFFFFF --track-color=#EBEDF0 --special-color1=#CBE2F9 --special-color2=#8AB4F8 --dom-color=#EBEDF0 --text-color=#000000'
    
    print("🚀 开始请求 Notion 数据并生成基础热力图...")
    subprocess.run(command, shell=True, check=True)

    # 给方块重新判定上色
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        process_svg_colors(svg_path)
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("✅ 学习热力图已生成并重新着色完成！")
    else:
        print("❌ 错误：未在 OUT_FOLDER 找到生成的 notion.svg 文件。")
        sys.exit(1)

if __name__ == "__main__":
    main()
