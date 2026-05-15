import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json

# ================= 配置区 =================
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
YEAR = datetime.datetime.now().year
JSON_FILE = "study_data.json"
TITLE = "残暴的邪神的学习热力图"
# ==========================================

def get_and_save_notion_data():
    """第一步：从 Notion 提取数据并保存为本地 JSON"""
    print(f"🔍 正在从 Notion 提取 {YEAR} 年的真实数据...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
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
            
    # 保存为本地 JSON 文件，供 github_heatmap 绘图使用
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f)
    
    print(f"✅ 数据提取成功！已保存至 {JSON_FILE}，共 {len(data_dict)} 条有效记录。")
    return data_dict

def draw_heatmap_generic():
    """第二步：利用 github_heatmap 的 generic 模式绘图"""
    print("🚀 正在调用 github_heatmap 通用模式绘制底板...")
    
    # 注意：这里改用 generic 子命令，指定 --json_file
    command = [
        "github_heatmap", "generic",
        "--json_file", JSON_FILE,
        "--year", str(YEAR),
        "--me", TITLE,
        "--unit", "分钟",
        "--without-type-name",
        "--background-color", "#FFFFFF",
        "--track-color", "#EBEDF0",  # 显式指定灰色方块
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"
    ]
    
    try:
        subprocess.run(command, check=True)
        print("🎨 原生底板（The Track）已成功铺设。")
    except subprocess.CalledProcessError as e:
        print(f"❌ 绘图引擎执行失败: {e}")
        sys.exit(1)

def apply_color_gradient(data_dict):
    """第三步：在原生底板上精准注入渐变色和统计文字"""
    print("💉 正在执行最终的渐变色注入...")
    svg_path = "OUT_FOLDER/notion.svg"
    if not os.path.exists(svg_path):
        # 尝试通用模式可能的默认路径
        svg_path = "OUT_FOLDER/generic.svg" 
    
    if not os.path.exists(svg_path):
        print("❌ 未找到生成的 SVG 文件，请检查 OUT_FOLDER 目录。")
        return

    with open(svg_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新顶部统计文字
    total_minutes = int(sum(data_dict.values()))
    content = re.sub(rf'({YEAR}:\s*)[0\.\d]+(\s*分钟)', rf'\g<1>{total_minutes}\g<2>', content)

    # 渐变插值辅助函数
    def interpolate(c1, c2, f):
        c1_v = [int(c1[i:i+2], 16) for i in (1, 3, 5)]
        c2_v = [int(c2[i:i+2], 16) for i in (1, 3, 5)]
        res = [int(c1_v[i] + (c2_v[i] - c1_v[i]) * f) for i in range(3)]
        return f"#{res[0]:02x}{res[1]:02x}{res[2]:02x}"

    def rect_replacer(match):
        rect_tag = match.group(0)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)
        if not date_match: return rect_tag
            
        date_str = date_match.group(1)
        val = float(data_dict.get(date_str, 0))
        
        if val == 0:
            color = "#EBEDF0" # 无数据日期的标准灰
        elif val <= 240:
            color = interpolate("#E0E7FF", "#93C5FD", val / 240.0)
        elif val <= 480:
            color = interpolate("#60A5FA", "#1E3A8A", (val - 240) / 240.0)
        else:
            color = interpolate("#10B981", "#064E3B", min(1.0, (val - 480) / 240.0))
            
        return re.sub(r'fill="[^"]+"', f'fill="{color}"', rect_tag)

    content = re.sub(r'<rect\b[^>]*>.*?</rect>', rect_replacer, content, flags=re.DOTALL)
    
    # 强制背景层
    if 'style=' not in content:
        content = content.replace('<svg ', '<svg style="background-color:white;" ', 1)

    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # 移动文件
    os.makedirs("study_heatmap", exist_ok=True)
    os.replace(svg_path, "study_heatmap/main.svg")
    print("🎉 任务圆满完成！请查看 study_heatmap/main.svg")

def main():
    # 检查环境变量
    if not NOTION_TOKEN or not DATABASE_ID:
        print("❌ 错误：环境变量未配置！")
        return

    # 执行三步走方案
    data = get_and_save_notion_data()
    draw_heatmap_generic()
    apply_color_gradient(data)

if __name__ == "__main__":
    main()
