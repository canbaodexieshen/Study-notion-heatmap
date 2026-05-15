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
                                val = f_data.get("number")
                            elif f_type == "string" and f_data.get("string"):  
                                try:
                                    val = float(f_data.get("string"))
                                except (ValueError, TypeError):
                                    match = re.search(r'(\d+(\.\d+)?)', str(f_data.get("string")))
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
            
    print(f"✅ 成功获取了 {len(data_dict)} 天的有效记录！")
    return data_dict

def interpolate_color(color1, color2, factor):
    """🎨 核心色彩引擎：根据完成度在两个Hex颜色之间生成平滑渐变"""
    factor = max(0.0, min(1.0, factor))
    c1 = [int(color1[i:i+2], 16) for i in (1, 3, 5)]
    c2 = [int(color2[i:i+2], 16) for i in (1, 3, 5)]
    res = [int(c1[i] + (c2[i] - c1[i]) * factor) for i in range(3)]
    return f"#{res[0]:02x}{res[1]:02x}{res[2]:02x}"

def process_svg_colors(file_path, data_dict, current_year):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 🔧 修复左上角的“总时长”统计，使其精准显示真实的分钟数
    total_minutes = sum(data_dict.values())
    # 匹配类似 "2026: 0 分钟" 或 "2026: 0.0 分钟" 并替换为真实时长
    content = re.sub(
        rf'({current_year}:\s*)[0\.]+(\s*分钟)',
        rf'\g<1>{int(total_minutes)}\g<2>',
        content
    )

    def rect_replacer(match):
        rect_tag = match.group(0)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match:
            return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        # 🌈 渐变色彩逻辑分配
        if val == 0:
            color = "#EBEDF0"  # 空白打卡为标准灰色底
        elif val <= 240:  # 0~4小时：浅紫白 -> 浅蓝
            factor = val / 240.0
            color = interpolate_color("#f0f9ff", "#7dd3fc", factor)
        else:  # >4小时：浅蓝 -> 深蓝/绿（可自定义）
            factor = min((val - 240) / 120.0, 1.0)  # 假设最多到6小时（360分钟）
            color = interpolate_color("#7dd3fc", "#0ea5e9", factor)
        
        # 替换 fill 属性
        return re.sub(r'fill="[^"]*"', f'fill="{color}"', rect_tag)

    # 用正则替换所有 rect 标签
    content = re.sub(r'<rect[^>]*>', rect_replacer, content)

    # 保存处理后的 SVG
    output_path = file_path.replace(".svg", f"_processed_{current_year}.svg")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ SVG 热力图已生成：{output_path}")
    return output_path

# 🚀 主程序入口
if __name__ == "__main__":
    # ⚙️ 配置参数（请替换为你的 Notion Token 和 Database ID）
    NOTION_TOKEN = "your_notion_token_here"
    DATABASE_ID = "your_database_id_here"
    SVG_TEMPLATE_PATH = "template.svg"  # 请确保当前目录有这个模板文件

    # 自动获取当前年份
    current_year = datetime.datetime.now().year

    # 获取数据
    data = get_notion_data(NOTION_TOKEN, DATABASE_ID)

    # 处理 SVG
    if os.path.exists(SVG_TEMPLATE_PATH):
        processed_svg = process_svg_colors(SVG_TEMPLATE_PATH, data, current_year)
        print(f"🎉 完成！打开 {processed_svg} 查看你的热力图！")
    else:
        print(f"❌ 找不到模板文件：{SVG_TEMPLATE_PATH}，请确保它存在。")
