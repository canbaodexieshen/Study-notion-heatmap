import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    print("🔍 正在连接 Notion 数据库并抓取真实时长数据...")
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
        if next_cursor: body["start_cursor"] = next_cursor
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read())
                for result in res.get("results", []):
                    props = result.get("properties", {})
                    # 严格读取“日期”和“总时长”
                    date_val = None
                    if props.get("日期") and props["日期"].get("date"):
                        date_val = props["日期"]["date"].get("start")
                    
                    val = 0
                    val_prop = props.get("总时长")
                    if val_prop:
                        ptype = val_prop.get("type")
                        if ptype == "formula":
                            f_data = val_prop.get("formula", {})
                            val = f_data.get("number") if f_data.get("type") == "number" else 0
                            if f_data.get("type") == "string":
                                match = re.search(r'(\d+(\.\d+)?)', str(f_data.get("string", "0")))
                                val = float(match.group(1)) if match else 0
                        elif ptype == "number":
                            val = val_prop.get("number") or 0
                    
                    if date_val and val > 0:
                        date_str = str(date_val).split("T")[0]
                        data_dict[date_str] = data_dict.get(date_str, 0) + val
                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            sys.exit(1)
    return data_dict

def interpolate_color(color1, color2, factor):
    """根据因子计算两个颜色之间的中间色"""
    factor = max(0.0, min(1.0, factor))
    c1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
    c2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
    res = [int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3)]
    return f"#{res[0]:02x}{res[1]:02x}{res[2]:02x}"

def process_svg_styling(file_path, data_dict, current_year):
    """注入渐变逻辑和修复文字统计"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 动态修正统计文字（将 2026: 0 分钟 替换为真实总和）
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 2. 对每个格子应用渐变算法
    def rect_replacer(match):
        rect_tag = match.group(0)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match: return rect_tag # 忽略非日期格子
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 渐变逻辑
        if val == 0:
            color = "#ebedf0" # 经典 GitHub 灰
        elif val <= 240:
            # 0~4小时：浅紫白 -> 天蓝
            color = interpolate_color("#E0E7FF", "#60A5FA", val / 240.0)
        elif val <= 480:
            # 4~8小时：天蓝 -> 深海蓝 (核心渐变)
            color = interpolate_color("#60A5FA", "#1E3A8A", (val - 240) / 240.0)
        else:
            # 8小时以上：春意绿 -> 深翠绿
            color = interpolate_color("#10B981", "#064E3B", min(1.0, (val - 480) / 240.0))
            
        return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)

    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    # 3. 强制背景修复：如果 SVG 没有背景矩形，则手动插入一个白色底层
    if 'id="background"' not in content:
        content = content.replace('<svg ', '<svg style="background-color:white;" ', 1)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    # 抓取数据
    real_data = get_notion_data(notion_token, database_id)

    # 🚀 生成底稿：这里我们先用 0 作为基础生成，保留所有轨道(Track)和标题
    # 关键：所有颜色参数必须用引号包裹，防止 # 号在 Shell 中被当做注释
    command = [
        "github_heatmap", "notion",
        "--notion_token", f"{notion_token}",
        "--database_id", f"{database_id}",
        "--date_prop_name", "日期",
        "--value_prop_name", "总时长",
        "--unit", "分钟",
        "--year", str(current_year),
        "--me", "残暴的邪神的学习热力图",
        "--without-type-name",
        "--background-color", "#FFFFFF",
        "--track-color", "#ebedf0", # 默认灰色方块
        "--dom-color", "#ebedf0",
        "--text-color", "#000000"
    ]
    
    print("🚀 正在调用引擎绘制完整热力图底稿...")
    subprocess.run(command, check=True)

    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        print("🎨 正在执行高阶渐变着色与统计注入...")
        process_svg_styling(svg_path, real_data, current_year)
        
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 绘图成功！请查看 study_heatmap/main.svg")

if __name__ == "__main__":
    main()
