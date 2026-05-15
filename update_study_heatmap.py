import os
import subprocess
import datetime
import re
from keep2notion.notion_helper import NotionHelper

def process_svg_colors(file_path):
    """核心逻辑：根据 SVG 中的数据提示重新着色"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 这里的正则会寻找包含分钟数的方块
    # 逻辑：查找包含 <title>... 分钟</title> 的 rect 标签
    def color_replacer(match):
        rect_tag = match.group(0)
        # 提取数值
        val_match = re.search(r'(\d+\.?\d*)\s*分钟', rect_tag)
        if val_match:
            val = float(val_match.group(1))
            if val == 0: color = "#EBEDF0" # 空白
            elif val < 240: color = "#D1D5DB" # <4h 灰色
            elif val < 480: color = "#3B82F6" # 4-8h 蓝色 (包含4-6h)
            else: color = "#10B981" # >8h 绿色
            # 替换 fill 属性
            return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        return rect_tag

    # 匹配所有的 rect 标签及其 title
    new_content = re.sub(r'<rect[^>]*>.*?<\/rect>', color_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_helper = NotionHelper()
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = "你的日计划数据库ID" # 填入你确认的那个ID
    current_year = datetime.datetime.now().year

    # 1. 生成原始 SVG (先用一个基础颜色生成)
    command = [
        "github_heatmap", "notion",
        "--notion_token", notion_token,
        "--database_id", database_id,
        "--date_prop_name", "日期",
        "--value_prop_name", "我的运动热力图", # 即使名字叫这个也没关系
        "--unit", "分钟",
        "--year", str(current_year),
        "--me", "学习热力图",
        "--without-type-name"
    ]
    subprocess.run(" ".join(command), shell=True)

    # 2. 对生成的 notion.svg 进行后处理着色
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        process_svg_colors(svg_path)
        
        # 3. 移动到 study_heatmap 文件夹并改名为 main.svg
        os.makedirs("study_heatmap", exist_ok=True)
        os.rename(svg_path, "study_heatmap/main.svg")
        print("学习热力图已生成并重新着色完成！")

if __name__ == "__main__":
    main()
