import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    """【数据抓取层】忽略工具限制，直接从 API 提取最真实的函数列数字"""
    print("🔍 正在通过 Notion API 提取 51 条真实学习记录...")
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
        body = {"start_cursor": next_cursor} if next_cursor else {}
        req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read())
                for result in res.get("results", []):
                    props = result.get("properties", {})
                    
                    # 提取日期
                    date_val = None
                    if props.get("日期") and props["日期"].get("date"):
                        date_val = props["日期"]["date"].get("start")
                    
                    # 提取时长 (兼容函数列返回的各种格式)
                    val = 0
                    val_prop = props.get("总时长")
                    if val_prop:
                        ptype = val_prop.get("type")
                        if ptype == "formula":
                            f_data = val_prop.get("formula", {})
                            if f_data.get("type") == "number":
                                val = f_data.get("number") or 0
                            elif f_data.get("type") == "string":
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
            print(f"❌ 抓取失败: {e}")
            sys.exit(1)
    return data_dict

def surgery_inject_svg(file_path, data_dict, current_year):
    """【外科手术注入】在原生 SVG 骨架上精准填色并修改统计文字"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复原生 SVG 顶部的统计数字 (把 "2026: 0 分钟" 改成真实总数)
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 2. 对每个 <rect> 格子进行精准填色
    # 原生工具生成的格子包含日期信息，我们根据这个日期匹配数据
    def rect_replacer(match):
        rect_tag = match.group(0)
        # 从格子中提取日期 YYYY-MM-DD
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 严格执行 GitHub 标准绿色阶梯
        if val == 0:
            color = "#EBEDF0" # 灰色
        elif val <= 120:
            color = "#9BE9A8" # 浅绿
        elif val <= 300:
            color = "#40C463" # 中绿
        elif val <= 600:
            color = "#30A14E" # 深绿
        else:
            color = "#216E39" # 极深绿
            
        # 替换 fill 属性
        rect_tag = re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        # 顺便把鼠标悬停的标题也改了
        rect_tag = re.sub(r'<title>.*?</title>', f'<title>{date_str} {int(val)} 分钟</title>', rect_tag)
        return rect_tag

    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    # 步骤 1: 独立抓取数据
    real_data = get_notion_data(notion_token, database_id)
    print(f"📊 数据抓取成功：共计 {len(real_data)} 天有数据，总时长 {int(sum(real_data.values()))} 分钟")

    # 步骤 2: 调用原生工具生成全灰色的“原生底稿”
    # 注意：这里我们故意让它生成一张“0数据”的图，目的是要它的排版和文字
    command = [
        "github_heatmap", "notion",
        "--notion_token", notion_token,
        "--database_id", database_id,
        "--date_prop_name", "日期",
        "--value_prop_name", "总时长",
        "--unit", "分钟",
        "--year", str(current_year),
        "--me", "残暴的邪神的学习热力图",
        "--without-type-name",
        "--background-color", "#FFFFFF",
        "--track-color", "#EBEDF0", # 灰色底色
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"
    ]
    
    print("🎨 正在生成原生样式底稿...")
    subprocess.run(command, check=True)

    # 步骤 3: 注入真实数据
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        print("💉 正在向原生底稿注入真实数据...")
        surgery_inject_svg(svg_path, real_data, current_year)
        
        # 整理输出
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 完美！现在你可以去查看 study_heatmap/main.svg 了，样式和数据都对了。")

if __name__ == "__main__":
    main()
