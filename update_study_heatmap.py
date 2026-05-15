import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    """【已定型】数据抓取部分（保持不动）"""
    print("🔍 正在从 Notion 提取 51 条真实学习记录...")
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
                    date_val = None
                    if props.get("日期") and props["日期"].get("date"):
                        date_val = props["日期"]["date"].get("start")
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

def inject_github_style(file_path, data_dict, current_year):
    """【核心融合层】将原生灰色小方块与数据格子合并"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 强制更新顶部总时长（2026: XXX 分钟）
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 2. 遍历所有方块进行“地毯式上色”
    def rect_replacer(match):
        rect_tag = match.group(0)
        # 寻找日期属性 data-date="YYYY-MM-DD" 或在 title 里的日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        
        if not date_match:
            return rect_tag # 如果不是日期方块（如背景），保持原样

        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 🎨 核心颜色逻辑
        if val == 0:
            # 💡 这里就是你想要的“原生样式灰色边小框”
            # 统一使用 GitHub 官方背景灰 #EBEDF0
            color = "#EBEDF0"
        elif val <= 120:
            color = "#9BE9A8" # 浅绿
        elif val <= 300:
            color = "#40C463" # 中绿
        elif val <= 600:
            color = "#30A14E" # 深绿
        else:
            color = "#216E39" # 极深绿
            
        # 强行替换或插入 fill 属性，确保每个格子都有颜色
        if 'fill=' in rect_tag:
            rect_tag = re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        else:
            rect_tag = rect_tag.replace('<rect ', f'<rect fill="{color}" ')
            
        # 优化鼠标悬停显示的文字
        title_text = f"{date_str}: {int(val)} 分钟"
        rect_tag = re.sub(r'<title>.*?</title>', f'<title>{title_text}</title>', rect_tag)
        
        return rect_tag

    # 全量替换所有 <rect> 标签
    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    # 3. 强制背景补丁：确保 SVG 画布本身是白色的，衬托出灰格子
    if 'background-color' not in content:
        content = content.replace('<svg ', '<svg style="background-color:white;" ', 1)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    # 第一步：精准抓取数据
    real_data = get_notion_data(notion_token, database_id)
    print(f"📊 抓取完毕：发现 {len(real_data)} 天的学习记录，累计 {sum(real_data.values())} 分钟。")

    # 第二步：调用原生工具生成“全量底稿”
    # 注意：我们这里设置 --track-color 为原生灰，确保工具生成所有方块的占位符
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
        "--track-color", "#EBEDF0",  # 显式指定原生灰色底
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"
    ]
    
    print("🎨 正在生成原生热力图骨架...")
    subprocess.run(command, check=True)

    # 第三步：缝合数据与样式
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        print("💉 正在注入灰色小方块与绿色数据格子...")
        inject_github_style(svg_path, real_data, current_year)
        
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 恭喜！完美版热力图已完成：study_heatmap/main.svg")

if __name__ == "__main__":
    main()
