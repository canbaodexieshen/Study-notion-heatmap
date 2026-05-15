import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    """【强力抓取层】确保即便公式列返回 null 也能通过逻辑解析拿到数字"""
    print("🔍 正在通过强力引擎抓取 51 条记录中的有效时长数据...")
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
                    
                    # 2. 提取时长 (针对公式列做了特殊强化)
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
            print(f"❌ 抓取失败，请检查机器人是否已分享给所有相关数据库: {e}")
            sys.exit(1)
    return data_dict

def inject_data_to_svg(file_path, data_dict, current_year):
    """【精准注入层】把拿到的真实数据强行涂抹到 SVG 格子上"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 修复标题下方的总时长显示
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({current_year}:\s*)[0\.]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 2. 格子上色逻辑 (使用 GitHub 官方标准绿色梯度)
    def rect_replacer(match):
        rect_tag = match.group(0)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match: return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 按照时长分配 GitHub 标准绿 (可以根据你的习惯调整阈值)
        if val == 0:
            color = "#EBEDF0" # 没学的日子
        elif val <= 120:
            color = "#9BE9A8" # 2小时内：浅绿
        elif val <= 300:
            color = "#40C463" # 2-5小时：中绿
        elif val <= 600:
            color = "#30A14E" # 5-10小时：深绿
        else:
            color = "#216E39" # 10小时以上：极深绿
            
        return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)

    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    current_year = datetime.datetime.now().year

    # 第一步：先用手工逻辑拿到那 51 条记录的真实数字
    real_data = get_notion_data(notion_token, database_id)
    print(f"✅ 抓取完成！共发现 {len(real_data)} 天有学习记录，累计 {int(sum(real_data.values()))} 分钟。")

    # 第二步：调用工具生成“空底板”
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
        "--track-color", "#EBEDF0",
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"
    ]
    subprocess.run(command, check=True)

    # 第三步：将真实数据注入 SVG
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        inject_data_to_svg(svg_path, real_data, current_year)
        
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 恭喜！数据已成功渲染，绿色格子应该已经出现了！")

if __name__ == "__main__":
    main()
