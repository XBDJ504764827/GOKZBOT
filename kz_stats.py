import aiohttp
import io
import os
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

# 定义字体缓存路径
FONT_CACHE_DIR = os.path.join(os.path.dirname(__file__), '.font_cache')
FONT_URL = 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
FONT_FILE = os.path.join(FONT_CACHE_DIR, 'NotoSansCJKsc-Regular.otf')


async def get_kzgo_stats(steam_id: str, mode: str) -> dict | None:
    """Fetches player stats from kzgo.eu."""
    url = f"https://kzgo.eu/players/{steam_id}?{mode}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                player_card = soup.find("div", class_="player-card")
                if not player_card:
                    return None

                stats = {"source": "kzgo.eu", "mode": mode}

                # Player name and avatar
                name_tag = player_card.find("h1")
                img_tag = player_card.find("img")
                
                if name_tag:
                    stats["name"] = name_tag.text.strip()
                else:
                    stats["name"] = "Unknown"
                    
                if img_tag and img_tag.get("src"):
                    stats["avatar_url"] = img_tag["src"]
                else:
                    stats["avatar_url"] = ""

                # Rank and Points
                rank_div = player_card.find("div", class_="rank")
                if rank_div:
                    rank_h2 = rank_div.find("h2")
                    rank_p = rank_div.find("p")
                    stats["rank"] = rank_h2.text.strip() if rank_h2 else "Unranked"
                    stats["points"] = rank_p.text.strip().replace("points", "").strip() if rank_p else "0"
                else:
                    stats["rank"] = "Unranked"
                    stats["points"] = "0"
                
                # Other stats from the table
                stats_table = soup.find("table", class_="table-player")
                if stats_table:
                    rows = stats_table.find_all("tr")
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) == 2:
                            key = cols[0].text.strip().lower().replace(" ", "_")
                            value = cols[1].text.strip()
                            stats[key] = value

                return stats
    except aiohttp.ClientError:
        return None
    except Exception:
        return None


def get_vnl_level(points: int) -> str:
    """根据积分返回VNL等级"""
    if points >= 600000:
        return "Legend"
    elif points >= 400000:
        return "Master"
    elif points >= 300000:
        return "Pro"
    elif points >= 250000:
        return "Semipro"
    elif points >= 200000:
        return "Expert+"
    elif points >= 180000:
        return "Expert"
    elif points >= 160000:
        return "Expert-"
    elif points >= 140000:
        return "Skilled+"
    elif points >= 120000:
        return "Skilled"
    elif points >= 100000:
        return "Skilled-"
    elif points >= 80000:
        return "Regular+"
    elif points >= 70000:
        return "Regular"
    elif points >= 60000:
        return "Regular-"
    elif points >= 40000:
        return "Casual+"
    elif points >= 30000:
        return "Casual"
    elif points >= 20000:
        return "Casual-"
    elif points >= 10000:
        return "Amateur+"
    elif points >= 5000:
        return "Amateur"
    elif points >= 2000:
        return "Amateur-"
    elif points >= 1000:
        return "Beginner+"
    elif points >= 500:
        return "Beginner"
    elif points >= 1:
        return "Beginner-"
    else:
        return "New"


async def get_vnl_stats(steam_id64: str) -> dict | None:
    """Fetches player stats for vnl mode from kztimerglobal and vnl.kz APIs.

    从 KZTimer Global API 获取玩家完成的所有地图记录，
    每条记录包含 map_id (地图ID) 和 points (该地图获得的分数)。
    """
    records_url = f"https://kztimerglobal.com/api/v2.0/records/top?steamid64={steam_id64}&stage=0&modes_list_string=kz_vanilla&limit=10000&has_teleports=true"
    profile_url = f"https://vnl.kz/api/v1/profiles?steamids={steam_id64}"
    ranking_url = f"https://kztimerglobal.com/api/v2.0/rankings?steamid64={steam_id64}&mode=kz_vanilla&has_teleports=true"

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Fetch records for points and map_ids
            records = []
            try:
                print(f"[DEBUG] 正在从 KZTimer Global API 获取玩家记录...")
                async with session.get(records_url) as response:
                    if response.status == 200:
                        records = await response.json()
                        print(f"[DEBUG] 成功获取 {len(records)} 条记录")
                    else:
                        print(f"[DEBUG] API返回状态码: {response.status}")
            except (aiohttp.ClientError, Exception) as e:
                print(f"[ERROR] 获取记录失败: {e}")
                pass  # Continue with empty records

            # Calculate total points and finishes from records
            # 每条记录的 points 字段是该地图的分数，总分是所有地图分数之和
            total_points = sum(record.get('points', 0) for record in records)
            finishes = len(records)

            # 提取所有地图ID，这些ID将用于在数据库中查询地图等级
            map_ids = [record.get('map_id') for record in records if record.get('map_id') is not None]
            print(f"[DEBUG] 总分: {total_points}, 完成地图数: {finishes}, 地图ID数量: {len(map_ids)}")

            # Fetch ranking data
            rank = "N/A"
            try:
                async with session.get(ranking_url) as ranking_response:
                    if ranking_response.status == 200:
                        ranking_data = await ranking_response.json()
                        if ranking_data and len(ranking_data) > 0:
                            rank = str(ranking_data[0].get('points_rank', 'N/A'))
            except (aiohttp.ClientError, Exception):
                pass  # Use N/A if ranking fetch fails

            # Fetch profile for name and avatar - 使用 Steam API 作为备选
            stats = {}
            player_name = "N/A"
            avatar_url = ""
            
            # 首先尝试从 vnl.kz 获取
            try:
                async with session.get(profile_url) as profile_response:
                    if profile_response.status == 200:
                        profile_data = await profile_response.json()
                        if profile_data and len(profile_data) > 0:
                            player_name = profile_data[0].get("name", "N/A")
                            avatar_url = profile_data[0].get("avatarfull", "")
            except (aiohttp.ClientError, Exception):
                pass
            
            # 如果 vnl.kz 没有获取到，尝试从 records 中获取
            if player_name == "N/A" and records:
                player_name = records[0].get("player_name", "N/A")
            
            # 如果还是没有，尝试从 Steam API 获取
            if player_name == "N/A" or not avatar_url:
                try:
                    steam_api_url = f"https://steamcommunity.com/profiles/{steam_id64}?xml=1"
                    async with session.get(steam_api_url) as steam_response:
                        if steam_response.status == 200:
                            from lxml import etree
                            xml_data = await steam_response.text()
                            root = etree.fromstring(xml_data.encode())
                            if player_name == "N/A":
                                name_elem = root.find(".//steamID")
                                if name_elem is not None and name_elem.text:
                                    player_name = name_elem.text
                            if not avatar_url:
                                avatar_elem = root.find(".//avatarFull")
                                if avatar_elem is not None and avatar_elem.text:
                                    avatar_url = avatar_elem.text
                except Exception:
                    pass
            
            stats["name"] = player_name
            stats["avatar_url"] = avatar_url

            # Calculate level
            level = get_vnl_level(total_points)

            # Assemble stats dictionary
            stats.update({
                "source": "vnl.kz",
                "mode": "vnl",
                "points": total_points,
                "rank": rank,
                "level": level,
                "finishes": finishes,
                "wrs": "N/A",
                "map_ids": map_ids
            })
            
            return stats
    except Exception:
        return None

def _find_font() -> str:
    """Tries to find a usable TTF font on Windows, Linux, or macOS."""
    font_paths = [
        # Linux fonts - 优先使用支持中文的字体
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # 文泉驿正黑
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
        "/usr/share/fonts/truetype/arphic/uming.ttc",  # AR PL UMing
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Droid Sans Fallback
        # Windows fonts
        "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei (supports Chinese)
        "C:/Windows/Fonts/simhei.ttf",  # SimHei
        "C:/Windows/Fonts/simsun.ttc",  # SimSun
        "C:/Windows/Fonts/arial.ttf",  # Arial
        # Linux fonts - 其他字体
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        # macOS fonts
        "/System/Library/Fonts/PingFang.ttc",  # PingFang (supports Chinese)
        "/System/Library/Fonts/STHeiti Medium.ttc",  # STHeiti
        "/Library/Fonts/Arial.ttf",
        # 缓存的字体
        FONT_FILE,
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return "default"  # Pillow will use its built-in bitmap font


async def _download_font() -> bool:
    """下载中文字体到缓存目录"""
    try:
        # 如果字体已经存在，不需要下载
        if os.path.exists(FONT_FILE):
            return True
        
        # 创建缓存目录
        os.makedirs(FONT_CACHE_DIR, exist_ok=True)
        
        # 下载字体文件（使用更稳定的源）
        font_url = "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf"
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(font_url) as response:
                if response.status == 200:
                    font_data = await response.read()
                    with open(FONT_FILE, 'wb') as f:
                        f.write(font_data)
                    return True
        return False
    except Exception as e:
        print(f"下载字体失败: {e}")
        return False

async def create_stats_image(stats: dict) -> bytes | None:
    """Creates an image from the player's stats."""
    try:
        # 根据是否有tier数据动态调整图片高度
        tier_counts = stats.get("tier_counts", {})
        has_tier_data = bool(tier_counts)

        # 计算需要的高度
        base_height = 200  # 基础高度（头部信息）
        tier_height = 0
        if has_tier_data:
            # 每个tier一行，每行30像素
            tier_height = len(tier_counts) * 30 + 40  # 40是标题和间距

        width = 500
        height = base_height + tier_height

        # 背景色
        bg_color = (24, 25, 28)
        image = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(image)

        # Load font
        try:
            font_path = _find_font()
            # 如果没有找到系统字体，尝试下载
            if font_path == "default":
                await _download_font()
                font_path = _find_font()

            if font_path == "default":
                font_regular = ImageFont.load_default()
                font_bold = ImageFont.load_default()
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()
            else:
                font_regular = ImageFont.truetype(font_path, 16)
                font_bold = ImageFont.truetype(font_path, 22)
                font_large = ImageFont.truetype(font_path, 28)
                font_small = ImageFont.truetype(font_path, 14)
        except (IOError, OSError):
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Fetch and add avatar with rounded corners
        avatar_url = stats.get("avatar_url")
        avatar_size = 80
        if avatar_url:
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(avatar_url) as response:
                        if response.status == 200:
                            avatar_data = await response.read()
                            avatar_image = Image.open(io.BytesIO(avatar_data))
                            avatar_image = avatar_image.resize((avatar_size, avatar_size))

                            # Create rounded corners mask
                            mask = Image.new('L', (avatar_size, avatar_size), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

                            # Apply mask and paste
                            output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
                            output.paste(avatar_image, (0, 0))
                            output.putalpha(mask)

                            image.paste(output, (20, 20), output)
            except Exception:
                pass  # Skip avatar if fetch fails

        # Colors
        text_color = (255, 255, 255)
        highlight_color = (100, 200, 255)
        level_color = (255, 215, 0)  # 金色
        secondary_color = (180, 180, 180)
        tier_bar_color = (60, 60, 80)
        tier_text_color = (200, 200, 220)

        # Draw player name (大字体，醒目)
        player_name = stats.get("name", "N/A")
        name_x = 120
        draw.text((name_x, 25), player_name, font=font_large, fill=text_color)

        # Draw level (等级，金色显示)
        level_value = stats.get('level', '')
        if level_value:
            level_text = f"[{level_value}]"
            draw.text((name_x, 60), level_text, font=font_bold, fill=level_color)

        # Draw rank and points
        rank_value = stats.get('rank', 'N/A')
        points_value = stats.get('points', 'N/A')

        rank_text = f"排名: #{rank_value}" if rank_value != "N/A" else "排名: N/A"
        points_text = f"总分: {points_value:,}" if isinstance(points_value, int) else f"总分: {points_value}"

        draw.text((name_x, 95), rank_text, font=font_regular, fill=highlight_color)
        draw.text((name_x, 120), points_text, font=font_regular, fill=text_color)

        # Draw mode badge (右上角)
        mode_text = f"{stats.get('mode', 'N/A').upper()}"
        draw.text((width - 80, 25), mode_text, font=font_bold, fill=highlight_color)

        # Draw separator line
        separator_y = 160
        draw.line([(20, separator_y), (width - 20, separator_y)], fill=secondary_color, width=2)

        # Draw stats based on source
        y_offset = separator_y + 20

        if stats["source"] == "kzgo.eu":
            # Display kzgo.eu stats
            stats_to_display = [
                ("完成地图", stats.get('maps_completed', 'N/A')),
                ("世界纪录", stats.get('world_records', 'N/A')),
                ("平均分", stats.get('average', 'N/A')),
            ]

            for i, (label, value) in enumerate(stats_to_display):
                draw.text((20, y_offset + i * 30), f"{label}:", font=font_regular, fill=secondary_color)
                draw.text((200, y_offset + i * 30), str(value), font=font_regular, fill=text_color)

        elif stats["source"] == "vnl.kz":
            # Display vnl stats
            finishes = stats.get('finishes', 'N/A')
            draw.text((20, y_offset), f"完成地图总数: {finishes}", font=font_bold, fill=text_color)

            # Display tier distribution (每个tier一行，带进度条样式)
            if tier_counts:
                y_offset += 40
                draw.text((20, y_offset), "各等级地图完成情况:", font=font_regular, fill=secondary_color)
                y_offset += 30

                # 找出最大值用于计算进度条长度
                max_count = max(tier_counts.values()) if tier_counts else 1
                bar_max_width = 350

                for tier, count in sorted(tier_counts.items()):
                    # 绘制tier标签
                    tier_label = f"Tier {tier}"
                    draw.text((20, y_offset), tier_label, font=font_regular, fill=tier_text_color)

                    # 绘制进度条背景
                    bar_x = 100
                    bar_y = y_offset + 2
                    bar_height = 18
                    draw.rectangle(
                        [(bar_x, bar_y), (bar_x + bar_max_width, bar_y + bar_height)],
                        fill=tier_bar_color,
                        outline=secondary_color
                    )

                    # 绘制进度条填充
                    if max_count > 0:
                        bar_width = int((count / max_count) * bar_max_width)
                        if bar_width > 0:
                            # 根据tier等级使用不同颜色
                            if tier <= 2:
                                fill_color = (100, 200, 100)  # 绿色 - 简单
                            elif tier <= 4:
                                fill_color = (100, 150, 255)  # 蓝色 - 中等
                            elif tier <= 6:
                                fill_color = (255, 200, 100)  # 橙色 - 困难
                            else:
                                fill_color = (255, 100, 100)  # 红色 - 极难

                            draw.rectangle(
                                [(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)],
                                fill=fill_color
                            )

                    # 绘制数量文本
                    count_text = f"{count}"
                    draw.text((bar_x + bar_max_width + 10, y_offset), count_text, font=font_regular, fill=text_color)

                    y_offset += 30
            else:
                y_offset += 30
                draw.text((20, y_offset), "暂无等级数据", font=font_small, fill=secondary_color)

        # Add footer
        footer_text = f"数据来源: {stats['source']}"
        draw.text((20, height - 25), footer_text, font=font_small, fill=secondary_color)

        # Save image to a bytes buffer
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return img_byte_arr
    except Exception as e:
        # Log the error for debugging
        print(f"Error creating stats image: {e}")
        return None
