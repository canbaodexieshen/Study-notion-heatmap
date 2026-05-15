import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    print("🔍 正在启动原生引擎，直接读取 Notion 数据库...")
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    data_dict = {}
    has_more = True
    next_cursor = None
    debug_counter = 0 # 只打印前两行的详情，帮你抓虫！
    
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
                    
                    # 💡 自动容错装甲：忽略列名前后的隐形空格！
                    date_prop = None
                    val_prop = None
                    for key, value in props.items():
                        if key.strip() == "日期":
                            date_prop = value
                        elif key.strip() == "今日学习总时长(数字)":
                            val_prop = value
                            
                    # 1. 提取日期（全类型兼容）
                    date_val = None
                    if date_prop:
                        if date_prop.get("type") == "date" and date_prop.get("date"):
                            date_val = date_prop["date"].get("start")
                        elif date_prop.get("type") == "title" and date_prop.get("title"):
                            # 万一日期属性被设置成了标题
                            date_val = date_prop["title"][0].get("plain_text")
                            
                    # 2. 提取数值
                    val = 0
                    if val_prop:
                        if val_prop.get("type") == "formula":
                            val = val_prop["formula"].get("number")
                        elif val_prop.get("type") == "number":
                            val = val_prop.get("number")
                    
                    # 防御空值
                    val = val or 0
                    
                    # --- 🚨 X光透视仪：打印前两条数据的真面目 ---
                    if debug_counter < 2:
                        print("\n=== 🕵️‍♂️ 深度侦察：读取到的原始数据样本 ===")
                        print(f"你的 Notion 真实列名有: {list(props.keys())}")
                        print(f"当前行提取的日期: {date_val}")
                        print(f"当前行提取的时长: {val}")
                        print("=========================================\n")
                        debug_counter += 1
                    
                    # 存入字典
                    if date_val and val > 0:
                        # 确保提取 YYYY-MM-DD
                        date_str = str(date_val).split("T")[0][:10]
                        data_dict[date_str] = data_dict.get(date_str, 0) + val
                        
                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")
        except Exception as e:
            print("❌ 官方 Notion API 请求失败:", e)
            sys.exit(1)
            
    print(f"✅ 成功获取了 {len(data_dict)} 天的有效学习记录！准备开始注入颜料...")
    return data_dict

def process_svg_colors(file_path, data_dict):
    """将我们自己获取的真实数据，强行注入 SVG 画板"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def rect_replacer(match):
        rect_tag = match.group(0)
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 色阶判定
        if val == 0:
            color = "#EBEDF0"
        elif val < 240:
            color = "#D1D5DB"  # 灰
        elif val < 480:
            color = "#3B82F6"  # 蓝
        else:
            color = "#10B981"  # 绿
            
        # 换色并修改悬停文字
        rect_tag = re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        title_text = f"{val:g} 分钟" if val > 0 else "0 分钟"
        rect_tag = re.sub(r'<title>.*?</title>', f'<title>{date_str} {title_text}</title>', rect_tag)
        
        return rect_tag

    new_content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        print("❌ 致命错误：未找到 NOTION_TOKEN 或 NOTION_DATABASE_ID！")
        sys.exit(1)

    # 1. 自己拿数据
    real_data = get_notion_data(notion_token, database_id)

    current_year = datetime.datetime.now().year

    # 2. 生成底板
    command = f'github_heatmap notion --notion_token "{notion_token}" --database_id "{database_id}" --date_prop_name "日期" --value_prop_name "今日学习总时长（数字）" --unit "分钟" --year {current_year} --me "学习热力图" --without-type-name --background-color="#FFFFFF" --track-color="#EBEDF0" --special-color1="#CBE2F9" --special-color2="#8AB4F8" --dom-color="#EBEDF0" --text-color="#000000"'
    
    print("🚀 正在生成基础格子画板...")
    try:
        subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print("✅ 基础画板生成完毕！")
    except subprocess.CalledProcessError:
        print("❌ 画板生成失败！")
        sys.exit(1)

    # 3. 强行上色
    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        process_svg_colors(svg_path, real_data)
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 学习热力图着色与数据注入完美完成！")
    else:
        print("❌ 错误：未找到画板文件。")
        sys.exit(1)

if __name__ == "__main__":
    main()
