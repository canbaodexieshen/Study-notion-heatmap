import os
import subprocess
import datetime
import sys

def main():
    # 1. 获取 Notion 配置
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    if not notion_token or not database_id:
        print("❌ 错误：未找到 NOTION_TOKEN 或 NOTION_DATABASE_ID，请检查环境变量设置！")
        sys.exit(1)

    # 2. 设定基础信息
    current_year = datetime.datetime.now().year
    title = "残暴的邪神的学习热力图"
    
    # 3. 构造原生 github_heatmap 命令
    # 配置说明：
    # --track-color: #EBEDF0 (对应图片中无数据时的浅灰色方块)
    # --special-color1/2: 使用标准 GitHub 绿色系
    command = [
        "github_heatmap", "notion",
        "--notion_token", notion_token,
        "--database_id", database_id,
        "--date_prop_name", "日期",
        "--value_prop_name", "总时长",
        "--unit", "分钟",
        "--year", str(current_year),
        "--me", title,
        "--without-type-name",
        "--background-color", "#FFFFFF",
        "--track-color", "#EBEDF0",  # 标准灰色底块
        "--special-color1", "#9BE9A8", # 浅绿色
        "--special-color2", "#216E39", # 深绿色
        "--dom-color", "#EBEDF0",
        "--text-color", "#000000"      # 黑色标题与文字
    ]

    print(f"🚀 正在调用原生引擎生成热力图：{title}...")
    
    # 4. 执行命令
    try:
        # 使用列表形式调用 subprocess 可以完美处理带空格的参数和 # 号颜色值
        subprocess.run(command, check=True)
        print("✅ 热力图 SVG 生成成功！")
    except subprocess.CalledProcessError as e:
        print(f"❌ 绘图引擎执行失败，请检查 Notion 权限或网络连接。")
        sys.exit(1)

    # 5. 文件整理
    svg_source = "OUT_FOLDER/notion.svg"
    target_dir = "study_heatmap"
    target_file = f"{target_dir}/main.svg"

    if os.path.exists(svg_source):
        os.makedirs(target_dir, exist_ok=True)
        # 如果目标文件已存在则先删除，确保更新
        if os.path.exists(target_file):
            os.remove(target_file)
        os.rename(svg_source, target_file)
        print(f"🎉 任务完成！生成的图片已保存至: {target_file}")
    else:
        print(f"⚠️ 警告：未在输出目录找到 notion.svg，请确认 github_heatmap 是否正常运行。")

if __name__ == "__main__":
    main()
