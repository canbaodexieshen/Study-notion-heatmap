import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

def interpolate_color(color1, color2, factor):
    """【色彩魔法引擎】根据学习时长的百分比，计算出最完美的渐变色"""
    # 确保因子在 0 到 1 之间
    factor = max(0.0, min(1.0, factor))
    # 将十六进制颜色拆解为 RGB 数值
    c1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
    c2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
    # 按比例混合颜色
    c3 = [int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3)]
    # 重新组合成十六进制颜色代码
    return f"#{c3[0]:02x}{c3[1]:02x}{c3[2]:02x}"

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
                    
                    date_prop = None
                    val_prop = None
                    for key, value in props.items():
                        if "日期" in key or "Date" in key:
                            date_prop = value
                        elif key == "总时长":
                            val_prop = value
                            
                    # 1. 提取日期
                    date_val = None
                    if date_prop:
                        if date_prop.get("type") == "date" and date_prop.get("date"):
                            date_val = date_prop["date"].get("start")
                        elif date_prop.get("type") == "title" and date_prop.get("title"):
                            date_val = date_prop["title"][0].get("plain_text")
                            
                    # 2. 提取数值
                    val = 0
                    if val_prop:
                        ptype = val_prop.get("type")
                        if ptype == "formula":
                            f_data = val_prop.get("formula", {})
                            f_type = f_data.get("type")
                            
                            if f_type == "number":
                                num_val = f_data.get("number")
                                if num_val is not None:
                                    val = num_val
                            elif f_type == "string":  
                                raw_str = f_data.get("string")
                                if raw_str is not None:
                                    try:
                                        val = float(raw_str)
                                    except (ValueError, TypeError):
                                        match = re.search(r'(\d+(\.\d+)?)', str(raw_str))
                                        if match:
                                            val = float(match.group(1))
                        elif ptype == "number":
                            val = val_prop.get("number")
                        elif ptype == "rollup": 
                            r_data = val_prop.get("rollup", {})
                            if r_data.get("type") == "number":
                                val = r_data.get("number")
                            elif r_data.get("type") == "array" and len(r_data.get("array", [])) > 0:
                                val = r_data["array"][0].get("number", 0)
                    
                    val = val or 0
                    
                    if date_val and val > 0:
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
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    def rect_replacer(match):
        rect_tag = match.group(0)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 🔥 核心：高级色彩渐变逻辑
        if val == 0:
            color = "#EBEDF0" # 原生浅灰底板
        elif val < 240:
            # 0~4小时阶梯：浅灰(#E5E7EB) 到 深灰(#9CA3AF)
            factor = val / 240.0
            color = interpolate_color("#E5E7EB", "#9CA3AF", factor)
        elif val < 480:
            # 4~8小时阶梯：浅蓝(#93C5FD) 到 宝石蓝(#1D4ED8)
            factor = (val - 240) / 240.0
            color = interpolate_color("#93C5FD", "#1D4ED8", factor)
        else:
            # 8小时以上阶梯：薄荷绿(#6EE7B7) 到 墨绿(#047857)
            # 我们设定12小时(720分钟)为满色，超过12小时统一显示最深的墨绿色
            factor = min((val - 480) / 240.0, 1.0)
            color = interpolate_color("#6EE7B7", "#047857", factor)
            
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

    real_data = get_notion_data(notion_token, database_id)
    current_year = datetime.datetime.now().year

    # 我们通过指定圆润的样式颜色，生成最美观的底板（让 GitHub 原生工具只管排版和画格子）
    command = f'github_heatmap notion --notion_token "{notion_token}" --database_id "{database_id}" --date_prop_name "日期" --value_prop_name "总时长" --unit "分钟" --year {current_year} --me "学习热力图" --without-type-name --background-color="#FFFFFF" --track-color="#EBEDF0" --special-color1="#CBE2F9" --special-color2="#8AB4F8" --dom-color="#EBEDF0" --text-color="#000000"'
    
    print("🚀 正在生成基础格子画板...")
    subprocess.run(command, shell=True, check=True, capture_output=True)

    svg_path = "OUT_FOLDER/notion.svg"
    if os.path.exists(svg_path):
        process_svg_colors(svg_path, real_data)
        os.makedirs("study_heatmap", exist_ok=True)
        os.replace(svg_path, "study_heatmap/main.svg")
        print("🎉 高级渐变色学习热力图着色完成！")
    else:
        print("❌ 错误：未在 OUT_FOLDER 找到画板文件。")

if __name__ == "__main__":
    main()
