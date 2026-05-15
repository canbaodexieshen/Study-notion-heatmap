import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    """【数据层】确保 51 条记录被精准抓取"""
    print("🔍 正在通过 API 提取 Notion 真实时长数据...")
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
                    
                    # 1. 提取日期
                    date_val = None
                    date_prop = props.get("日期")
                    if date_prop and date_prop.get("date"):
                        date_val = date_prop["date"].get("start")
                    
                    # 2. 提取时长 (公式列兼容逻辑)
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
                                if match: val = float(match.group(1))
                        elif ptype == "number":
                            val = val_prop.get("number") or 0
                    
                    if date_val and val > 0:
                        date_str = str(date_val).split("T")[0]
                        data_dict[date_str] = data_dict.get(date_str, 0) + val
                
                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            sys.exit(1)
            
    total_found = int(sum(data_dict.values()))
    print(f"✅ 抓取完毕：共发现 {len(data_dict)} 天有学习记录，累计 {total_found} 分钟。")
    return data_dict

def process_svg_full_render(file_path, data_dict, current_year):
    """【渲染层】核心：强制铺设底板并上色"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 强制更新顶部总时长文本 (2026: XXX 分钟)
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 2. 全量格子处理逻辑
    def rect_replacer(match):
        rect_tag = match.group(0)
        # 提取格子中的日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag # 背景或其他非日期格子不处理
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 🎨 GitHub 官方色阶逻辑
        if val == 0:
            # 💡 核心修复：如果没有数据，强制上色为原生灰色，保证底板出现！
            color = "#EBEDF0" 
        elif val <= 120:
            color = "#9BE9A8" # 浅绿
        elif val <= 300:
            color = "#40C463" # 中绿
        elif val <= 600:
            color = "#30A14E" # 深绿
        else:
            color = "#216E39" # 极深绿
            
        # 替换或插入 fill 属性
        if 'fill=' in rect_tag:
            rect_tag = re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        else:
            rect_tag = rect_tag.replace('<rect ', f'<rect fill="{color}" ')
            
        # 确保鼠标悬停文字显示正确
        title_text = f"{date_str}: {int(val)} 分钟"
        rect_tag = re.sub(r'<title>.*?</title>', f'<title>{title_text}</title>', rect_tag)
        
        return rect_tag

    # 扫描整个 SVG，对每一个 <rect> 标签执行上面的逻辑
    new_content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    # 3. 强制背景修复：确保 SVG 容器有白色背景
    if 'style=' not in new_content:
        new_content = new_content.replace('<svg ', '<svg style="background-color:white;" ', 1)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    # 第一步：拿到真实数据
    real_data = get_notion_data(notion_token, database_id)

    # 第二步：调用工具生成 365 天的原生骨架
    # 哪怕工具读到的是 0 数据，它也会根据 --year 生成全年的方块位置
    command = [
        "github_heatmap", "notion",
        "--notion_token", str(notion_token),
        "--database_id", str(database_id),
        "--date_prop_name", "日期",
        "--value_prop_name", "总时长",
        "--unit", "分钟",
        "--year", str(current_year),
        "--me", "残暴的邪神的学习热力图",
        "--without-type-name",
        "--background-color", "#FFFFFF",
        "--track-color", "#EBEDF0", # 预设轨道颜色
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"
    ]
    
    print("🚀 正在生成原生热力图骨架...")
    subprocess.run(command, check=True)

    # 第三步：缝合数据，强制渲染底板
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        print("💉 正在执行全量底板铺设与数据注入...")
        process_svg_full_render(svg_path, real_data, current_year)
        
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 任务圆满完成！请查看 study_heatmap/main.svg")

if __name__ == "__main__":
    main()
