import os
import subprocess
import datetime
import re

def process_svg_colors(file_path):
    """核心逻辑：根据 SVG 中的数据提示重新着色"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def color_replacer(match):
        rect_tag = match.group(0)
        val_match = re.search(r'(\d+\.?\d*)\s*分钟', rect_tag)
        if val_match:
            val = float(val_match.group(1))
            if val == 0: color = "#EBEDF0" # 空白
            elif val < 240: color = "#D1D5DB" # <4h 灰色
            elif val < 480: color = "#3B82F6" # 4-8h 蓝色 (包含4-6h)
            else: color = "#10B981" # >8h 绿色
            return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        return rect_tag

    new_content = re.sub(r'<rect[^>]*>.*?<\/rect>', color_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_ID") # ⚠️ 请确保这里替换为了你真实的32位ID！
    current_year = datetime.datetime.now().year

    # 1. 生成原始 SVG
    command = [
        "github_heatmap", "notion",
        "--notion_token", notion_token,
        "--database_id", database_id,
        "--date_prop_name", "日期",
        "--value_prop_name", "我的运动热力图", 
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
        
        # 3. 移动并改名
        os.makedirs("study_heatmap", exist_ok=True)
        os.rename(svg_path, "study_heatmap/main.svg")
        print("学习热力图已生成并重新着色完成！")
    else:
        print("错误：未找到生成的 notion.svg 文件。")

if __name__ == "__main__":
    main()
