import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json


# ==========================================
# 从 Notion 获取真实数据
# ==========================================
def get_notion_data(token, database_id):

    print("🔍 正在读取 Notion 数据...")

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

        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as response:

                res = json.loads(response.read())

                for result in res.get("results", []):

                    props = result.get("properties", {})

                    # ==========================
                    # 日期属性
                    # ==========================
                    date_prop = props.get("日期")

                    if not date_prop:
                        continue

                    if not date_prop.get("date"):
                        continue

                    date_str = date_prop["date"]["start"].split("T")[0]

                    # ==========================
                    # 总时长属性
                    # ==========================
                    total_prop = props.get("总时长")

                    value = 0

                    if total_prop:

                        ptype = total_prop.get("type")

                        # 数字属性
                        if ptype == "number":

                            value = total_prop.get("number") or 0

                        # 公式属性
                        elif ptype == "formula":

                            formula = total_prop.get("formula", {})

                            ftype = formula.get("type")

                            # 公式输出 number
                            if ftype == "number":

                                value = formula.get("number") or 0

                            # 公式输出 string
                            elif ftype == "string":

                                text = str(formula.get("string", ""))

                                match = re.search(
                                    r"(\d+(\.\d+)?)",
                                    text
                                )

                                if match:
                                    value = float(match.group(1))

                    # ==========================
                    # 累加同一天数据
                    # ==========================
                    if value > 0:

                        data_dict[date_str] = (
                            data_dict.get(date_str, 0) + value
                        )

                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")

        except Exception as e:

            print(f"❌ Notion 数据获取失败: {e}")
            sys.exit(1)

    total_minutes = int(sum(data_dict.values()))

    print(f"✅ 成功读取 {len(data_dict)} 天数据")
    print(f"✅ 累计时长 {total_minutes} 分钟")

    return data_dict


# ==========================================
# 修复 SVG 空白格子
# ==========================================
def process_svg(svg_path):

    print("🎨 正在修复热力图空白格子...")

    with open(svg_path, "r", encoding="utf-8") as f:
        svg = f.read()

    # ==========================================
    # 给没有 fill 的 rect 自动补灰色
    # ==========================================
    def fix_rect(match):

        rect_tag = match.group(0)

        # 已经有 fill（说明已有数据颜色）
        if 'fill="' in rect_tag:
            return rect_tag

        # 没有 fill -> 补 GitHub 原生灰色
        rect_tag = rect_tag.replace(
            "<rect ",
            '<rect fill="#ebedf0" ',
            1
        )

        return rect_tag

    svg = re.sub(
        r'<rect\b[^>]*/>',
        fix_rect,
        svg
    )

    # ==========================================
    # 强制 SVG 白色背景
    # ==========================================
    if "background-color" not in svg:

        svg = svg.replace(
            "<svg ",
            '<svg style="background-color:white;" ',
            1
        )

    # ==========================================
    # 保存 SVG
    # ==========================================
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print("✅ SVG 修复完成")


# ==========================================
# 主程序
# ==========================================
def main():

    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    current_year = datetime.datetime.now().year

    # ==========================================
    # 环境变量检查
    # ==========================================
    if not notion_token:

        print("❌ 缺少环境变量 NOTION_TOKEN")
        sys.exit(1)

    if not database_id:

        print("❌ 缺少环境变量 NOTION_DATABASE_ID")
        sys.exit(1)

    # ==========================================
    # 验证 Notion 数据
    # （确保数据真实存在）
    # ==========================================
    get_notion_data(
        notion_token,
        database_id
    )

    # ==========================================
    # 调用 github_heatmap
    # ==========================================
    command = [
        "github_heatmap",
        "notion",

        "--notion_token",
        notion_token,

        "--database_id",
        database_id,

        "--date_prop_name",
        "日期",

        "--value_prop_name",
        "总时长",

        "--unit",
        "分钟",

        "--year",
        str(current_year),

        "--me",
        "残暴的邪神的运动热力图",

        "--without-type-name",

        "--background-color",
        "#ffffff",

        "--track-color",
        "#ebedf0",

        "--dom-color",
        "#ebedf0",

        "--text-color",
        "#000000"
    ]

    print("🚀 正在生成 GitHub 热力图...")

    try:

        subprocess.run(
            command,
            check=True
        )

    except subprocess.CalledProcessError as e:

        print(f"❌ github_heatmap 执行失败: {e}")
        sys.exit(1)

    # ==========================================
    # github_heatmap 输出路径
    # ==========================================
    svg_path = "OUT_FOLDER/notion.svg"

    if not os.path.exists(svg_path):

        print("❌ 未找到生成的 SVG 文件")
        sys.exit(1)

    # ==========================================
    # 修复空白格子
    # ==========================================
    process_svg(svg_path)

    # ==========================================
    # 输出最终文件
    # ==========================================
    os.makedirs(
        "study_heatmap",
        exist_ok=True
    )

    final_path = "study_heatmap/main.svg"

    if os.path.exists(final_path):
        os.remove(final_path)

    os.replace(
        svg_path,
        final_path
    )

    print("🎉 热力图生成成功")
    print(f"📁 输出文件: {final_path}")


# ==========================================
# 程序入口
# ==========================================
if __name__ == "__main__":
    main()
