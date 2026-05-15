import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def get_notion_data(token, database_id):
    """【黑科技】直接调用 Notion 官方 API，完美解析函数属性，不依赖任何第三方瞎猜"""
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
                    
                    # 1. 精准提取日期
                    date_val = None
                    date_prop = props.get("日期")
                    if date_prop and date_prop.get("date"):
                        date_val = date_prop["date"].get("start")
                        
                    # 2. 精准提取时长 (专治各种 Formula 函数不服)
                    val = 0
                    val_prop = props.get("今日学习总时长(数字)")
                    if val_prop:
                        if val_prop.get("type") == "formula":
                            # 扒开 formula 的嵌套外衣拿到里面的 number
                            val = val_prop["formula"].get("number")
                        elif val_prop.get("type") == "number":
                            val = val_prop.get("number")
                    
                    val = val or 0 # 防止遇到空值报错
                    
                    # 存入我们的“真实数据库”字典
                    if date_val and val > 0:
                        date_str = date_val.split("T")[0]
                        data_dict[date_str] = data_dict.get(date_str, 0) + val
                        
                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")
        except Exception as e:
            print("❌ 官方 Notion API 请求失败，请检查 Secret:", e)
            sys.exit(1)
            
    print(f"✅ 成功获取了 {len(data_dict)} 天的有效学习记录！准备开始注入颜料...")
    return data_dict

def process_svg_colors(file_path, data_dict):
    """【神笔马良】将我们自己获取的真实数据，强行注入到那张空白的 SVG 画板中"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def rect_replacer(match):
        rect_tag = match.group(0)
        
        # 从画板的方块标签中找出日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag
            
        date_str = date_match.group(1)
        
        # 从我们的字典中查询出这一天真实的分钟数
        val = float(data_dict.get(date_str, 0))
        
        # 判定阶梯颜色
        if val == 0:
            color = "#EBEDF0"
        elif val < 240:
            color = "#D1D5DB"  # < 4小时：灰
        elif val < 480:
            color = "#3B82F6"  # 4~8小时：蓝
        else:
            color = "#10B981"  # > 8小时：绿
            
        # 强行给 SVG 换色
        rect_tag = re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)
        
        # 强行重写悬停提示，干掉原来的 0 分钟
        title_text = f"{val:g} 分钟" if val > 0 else "0 分钟"
        rect_tag = re.sub(r'<title>.*?</title>', f'<title>{date_str} {title_text}</title>', rect_tag)
        
        return rect_tag

    # 扫描并替换画板上所有的方块
    new_content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def main():
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        print("❌ 致命错误：未找到 NOTION_TOKEN 或 NOTION_DATABASE_ID！")
        sys.exit(1)

    # 1. 【破局点】我们自己去拿数据！
    real_data = get_notion_data(notion_token, database_id)

    current_year = datetime.datetime.now().year

    # 2. 让第三方工具当个没有感情的“空白画板生成器”
    command = f'github_heatmap notion --notion_token "{notion_token}" --database_id "{database_id}" --date_prop_name "日期" --value_prop_name "今日学习总时长(数字)" --unit "分钟" --year {current_year} --me "学习热力图" --without-type-name --background-color="#FFFFFF" --track-color="#EBEDF0" --special-color1="#CBE2F9" --special-color2="#8AB4F8" --dom-color="#EBEDF0" --text-color="#000000"'
    
    print("🚀 正在使唤工具生成基础格子画板...")
    try:
        subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print("✅ 基础画板生成完毕！")
    except subprocess.CalledProcessError:
        print("❌ 画板生成失败，但这不应该发生！")
        sys.exit(1)

    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        # 3. 强行把颜料泼上去
        process_svg_colors(svg_path, real_data)
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 学习热力图着色与数据注入完美完成！你可以去检阅了！")
    else:
        print("❌ 错误：未在 OUT_FOLDER 找到画板文件。")
        sys.exit(1)

if __name__ == "__main__":
    main()
