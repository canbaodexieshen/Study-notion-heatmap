import os
import subprocess
import datetime
import re
import sys
import urllib.request
import json


# =========================
# Notion 数据获取
# =========================
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

                    # ======================
                    # 日期
                    # ======================
                    date_prop = props.get("日期")

                    if not date_prop:
                        continue

                    if not date_prop.get("date"):
                        continue

                    date_str = date_prop["date"]["start"].split("T")[0]

                    # ======================
                    # 总时长
                    # ======================
                    value = 0

                    total_prop = props.get("总时长")

                    if total_prop:

                        ptype = total_prop.get("type")

                        if ptype == "number":
                            value = total_prop.get("number") or 0

                        elif ptype == "formula":

                            formula = total_prop.get("formula", {})

                            if formula.get("type") == "number":
                                value = formula.get("number") or 0

                            elif formula.get("type") == "string":

                                text = str(formula.get("string", ""))

                                match = re.search(r"(\d+(\.\d+)?)", text)

                                if match:
                                    value = float(match.group(1))

                    # ======================
                    # 累加同一天
                    # ======================
                    if value > 0:
                        data_dict[date_str] = data_dict.get(date_str, 0) + value

                has_more = res.get("has_more", False)
                next_cursor = res.get("next_cursor")

        except Exception as e:
            print(f"❌ Notion 数据获取失败: {e}")
            sys.exit(1)

    total_minutes = int(sum(data_dict.values()))

    print(f"✅ 成功读取 {len(data_dict)} 天数据")
    print(f"✅ 累计时长 {total_minutes} 分钟")

    return data_dict


# =========================
# GitHub 原生色阶
# =========================
def get_color(value):

    if value <= 0:
        return "#ebedf0"

    elif value <= 120:
        return "#9be9a8"

    elif value <= 300:
        return "#40c463"

    elif value <= 600:
        return "#30a14e"

    else:
        return "#216e39"


# =========================
# SVG 修复核心
# =========================
def process_svg(svg_path, data_dict, current_year):

    print("🎨 正在渲染 GitHub 风格热力图...")

    with open(svg_path, "r", encoding="utf-8") as f:
        svg = f.read()

    total_minutes = int(sum(data_dict.values()))

    # =========================
    # 修复顶部总时长
    # =========================
    svg = re.sub(
        rf"{current_year}:\s*\d+\s*分钟",
        f"{current_year}: {total_minutes} 分钟",
        svg
    )

    # =========================
    # rect 处理
    # =========================
    rect_pattern = r'<rect\b[^>]*/>'

    def replace_rect(match):

        rect_tag = match.group(0)

        # 找日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', rect_tag)

        if not date_match:
            return rect_tag

        date_str = date_match.group(1)

        value = float(data_dict.get(date_str, 0))

        color = get_color(value)

        # 替换 fill
        if 'fill="' in rect_tag:

            rect_tag = re.sub(
                r'fill="[^"]*"',
                f'fill="{color}"',
                rect_tag
            )

        else:

            rect_tag = rect_tag.replace(
                "<rect ",
                f'<rect fill="{color}" ',
                1
            )

        # title
        title = f"{date_str}: {int(value)} 分钟"

        if "<title>" in rect_tag:

            rect_tag = re.sub(
                r'<title>.*?</title>',
                f'<title>{title}</title>',
                rect_tag
            )

        else:

            rect_tag = rect_tag.replace(
                "/>",
                f'><title>{title}</title></rect>'
            )

        return rect_tag

    svg = re.sub(rect_pattern, replace_rect, svg)

    # =========================
    # SVG 背景
    # =========================
    if "<svg" in svg and "background-color" not in svg:

        svg = svg.replace(
            "<svg ",
            '<svg style="background-color:white;" ',
            1
        )

    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print("✅ SVG 渲染完成")


# =========================
# 主程序
# =========================
def main():

    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    current_year = datetime.datetime.now().year

    if not notion_token:
        print("❌ 缺少 NOTION_TOKEN")
        sys.exit(1)

    if not database_id:
        print("❌ 缺少 NOTION_DATABASE_ID")
        sys.exit(1)

    # =========================
    # 获取真实数据
    # =========================
    real_data = get_notion_data(
        notion_token,
        database_id
    )

    # =========================
    # 生成热力图骨架
    # =========================
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

        "--year",
        str(current_year),

        "--unit",
        "分钟",

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

    print("🚀 正在生成热力图骨架...")

    try:
        subprocess.run(command, check=True)

    except subprocess.CalledProcessError as e:
        print(f"❌ github_heatmap 执行失败: {e}")
        sys.exit(1)

    # =========================
    # SVG 路径
    # =========================
    svg_path = "OUT_FOLDER/notion.svg"

    if not os.path.exists(svg_path):

        print("❌ 未找到生成的 SVG 文件")
        sys.exit(1)

    # =========================
    # 强制渲染 GitHub 风格
    # =========================
    process_svg(
        svg_path,
        real_data,
        current_year
    )

    # =========================
    # 输出目录
    # =========================
    os.makedirs("study_heatmap", exist_ok=True)

    final_path = "study_heatmap/main.svg"

    os.replace(svg_path, final_path)

    print("🎉 热力图生成成功")
    print(f"📁 输出文件: {final_path}")


if __name__ == "__main__":
    main()
