import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    print("🔍 正在抓取 Notion 原始数据...")
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    data_dict = {}
    has_more = True
    next_cursor = None
    
    while has_more:
        body = {}
        if next_cursor:
            body["start_cursor"] = next_cursor
            
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read())
                for result in res.get("results", []):
                    props = result.get("properties", {})
                    date_prop = props.get("日期")
                    val_prop = props.get("总时长")
                            
                    # 1. 提取日期
                    date_val = None
                    if date_prop and date_prop.get("date"):
                        date_val = date_prop["date"].get("start")
                            
                    # 2. 提取数值
                    val = 0
                    if val_prop:
                        ptype = val_prop.get("type")
                        if ptype == "formula":
                            f_data = val_prop.get("formula", {})
                            if f_data.get("type") == "number":
                                val = f_data.get("number")
                            elif f_data.get("type") == "string":
                                match = re.search(r'(\d+(\.\d+)?)', str(f_data.get("string", "0")))
                                if match: val = float(match.group(1))
                        elif ptype == "number":
                            val = val_prop.get("number")
                    
                    if date_val and (val or 0) > 0:
                        date_str = str(date_val).split("T")[0]
                        data_dict[date_str] = data_dict.get(date_str, 0) + val
                        
                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            sys.exit(1)
    return data_dict

def interpolate_color(color1, color2, factor):
    factor = max(0.0, min(1.0, factor))
    c1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
    c2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
    res = [int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3)]
    return f"#{res[0]:02x}{res[1]:02x}{res[2]:02x}"

def process_svg_colors(file_path, data_dict, current_year):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 强制注入总时长统计（修复标题下方的 0 分钟问题）
    total_minutes = sum(data_dict.values())
    # 查找年份后面跟着的 0 分钟并替换
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{int(total_minutes)}\g<2>', content)

    # 2. 精准格子变色逻辑
    def rect_replacer(match):
        rect_tag = match.group(0)
        # 只处理带有日期的格子
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match: return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        if val == 0:
            color = "#EBEDF0" # 没打卡的日子：统一灰色
        elif val <= 240:
            color = interpolate_color("#E0E7FF", "#93C5FD", val / 240.0)
        elif val <= 480:
            color = interpolate_color("#60A5FA", "#1E3A8A", (val - 240) / 240.0)
        else:
            color = interpolate_color("#10B981", "#064E3B", min(1.0, (val - 480) / 240.0))
            
        return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)

    # 执行替换
    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    # 3. 补丁：确保 SVG 有白色背景层（防止在某些浏览器下变成透明）
    if 'id="background"' not in content:
        bg_rect = '<rect id="background" width="100%" height="100%" fill="#FFFFFF"/>'
        content = content.replace('<svg ', f'<svg ', 1).replace('>', f'>{bg_rect}', 1)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    real_data = get_notion_data(notion_token, database_id)

    # 🚀 这里的命令进行了严格的引号包裹，修复背景、标题和格子隐身问题
    command = (
        f'github_heatmap notion '
        f'--notion_token "{notion_token}" '
        f'--database_id "{database_id}" '
        f'--date_prop_name "日期" '
        f'--value_prop_name "总时长" '
        f'--unit "分钟" '
        f'--year {current_year} '
        f'--me "残暴的邪神的学习热力图" '
        f'--without-type-name '
        f'--background-color "#FFFFFF" '
        f'--track-color "#EBEDF0" '
        f'--dom-color "#EBEDF0" '
        f'--text-color "#000000"'
    )
    
    print("🚀 正在生成热力图底板...")
    subprocess.run(command, shell=True, check=True)

    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        print("🎨 正在注入渐变色与标题数据...")
        process_svg_colors(svg_path, real_data, current_year)
        
        os.makedirs("study_heatmap", exist_ok=True)
        # 最终产出：study_heatmap/main.svg
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 任务完成！现在的图应该和你的 Keep 版本一样漂亮了。")

if __name__ == "__main__":
    main()
