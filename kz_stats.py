import aiohttp
import io
import os
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont


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


async def get_vnl_stats(steam_id64: str) -> dict | None:
    """Fetches player stats for vnl mode from kztimerglobal and vnl.kz APIs."""
    records_url = f"https://kztimerglobal.com/api/v2.0/records/top?steamid64={steam_id64}&stage=0&modes_list_string=kz_vanilla&limit=10000&has_teleports=true"
    profile_url = f"https://vnl.kz/api/v1/profiles?steamids={steam_id64}"
    ranking_url = f"https://kztimerglobal.com/api/v2.0/rankings?steamid64={steam_id64}&mode=kz_vanilla&has_teleports=true"
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Fetch records for points and map_ids
            records = []
            try:
                async with session.get(records_url) as response:
                    if response.status == 200:
                        records = await response.json()
            except (aiohttp.ClientError, Exception):
                pass  # Continue with empty records
            
            # Calculate total points and finishes from records
            total_points = sum(record.get('points', 0) for record in records)
            finishes = len(records)
            map_ids = [record.get('map_id') for record in records if record.get('map_id') is not None]

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

            # Fetch profile for name and avatar
            stats = {}
            try:
                async with session.get(profile_url) as profile_response:
                    if profile_response.status == 200:
                        profile_data = await profile_response.json()
                        if profile_data and len(profile_data) > 0:
                            stats["name"] = profile_data[0].get("name", "N/A")
                            stats["avatar_url"] = profile_data[0].get("avatarfull", "")
                        else:
                            stats["name"] = records[0].get("player_name", "N/A") if records else "N/A"
                            stats["avatar_url"] = ""
                    else:
                        stats["name"] = records[0].get("player_name", "N/A") if records else "N/A"
                        stats["avatar_url"] = ""
            except (aiohttp.ClientError, Exception):
                stats["name"] = records[0].get("player_name", "N/A") if records else "N/A"
                stats["avatar_url"] = ""

            # Assemble stats dictionary
            stats.update({
                "source": "vnl.kz",
                "mode": "vnl",
                "points": total_points,
                "rank": rank,
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
        # Windows fonts
        "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei (supports Chinese)
        "C:/Windows/Fonts/simhei.ttf",  # SimHei
        "C:/Windows/Fonts/arial.ttf",  # Arial
        # Linux fonts
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        # macOS fonts
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return "default"  # Pillow will use its built-in bitmap font

async def create_stats_image(stats: dict) -> bytes | None:
    """Creates an image from the player's stats."""
    try:
        # Create a background with better dimensions
        width, height = 450, 300
        bg_color = (24, 25, 28)
        image = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Load font
        try:
            font_path = _find_font()
            if font_path == "default":
                font_regular = ImageFont.load_default()
                font_bold = ImageFont.load_default()
                font_small = ImageFont.load_default()
            else:
                font_regular = ImageFont.truetype(font_path, 14)
                font_bold = ImageFont.truetype(font_path, 20)
                font_small = ImageFont.truetype(font_path, 12)
        except (IOError, OSError):
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Fetch and add avatar with rounded corners
        avatar_url = stats.get("avatar_url")
        if avatar_url:
            try:
                timeout = aiohttp.ClientTimeout(total=5)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(avatar_url) as response:
                        if response.status == 200:
                            avatar_data = await response.read()
                            avatar_image = Image.open(io.BytesIO(avatar_data))
                            avatar_image = avatar_image.resize((70, 70))
                            
                            # Create rounded corners mask
                            mask = Image.new('L', (70, 70), 0)
                            mask_draw = ImageDraw.Draw(mask)
                            mask_draw.ellipse((0, 0, 70, 70), fill=255)
                            
                            # Apply mask and paste
                            output = Image.new('RGBA', (70, 70), (0, 0, 0, 0))
                            output.paste(avatar_image, (0, 0))
                            output.putalpha(mask)
                            
                            image.paste(output, (15, 15), output)
            except Exception:
                pass  # Skip avatar if fetch fails

        # Colors
        text_color = (255, 255, 255)
        highlight_color = (153, 102, 255)
        secondary_color = (180, 180, 180)
        mode_color = (100, 200, 255)

        # Draw player name and mode badge
        player_name = stats.get("name", "N/A")
        draw.text((100, 20), player_name, font=font_bold, fill=text_color)
        
        mode_text = f"[{stats.get('mode', 'N/A').upper()}]"
        draw.text((100, 50), mode_text, font=font_small, fill=mode_color)
        
        # Draw rank and points
        rank_value = stats.get('rank', 'N/A')
        points_value = stats.get('points', 'N/A')
        
        rank_text = f"Rank: #{rank_value}" if rank_value != "N/A" else "Rank: N/A"
        points_text = f"Points: {points_value}"
        
        draw.text((100, 70), rank_text, font=font_regular, fill=highlight_color)
        draw.text((100, 92), points_text, font=font_regular, fill=text_color)
        
        # Draw separator line
        draw.line([(15, 120), (width - 15, 120)], fill=secondary_color, width=1)
        
        # Draw stats based on source
        y_offset = 135
        if stats["source"] == "kzgo.eu":
            # Display kzgo.eu stats
            stats_to_display = [
                ("Maps Completed", stats.get('maps_completed', 'N/A')),
                ("World Records", stats.get('world_records', 'N/A')),
                ("Average", stats.get('average', 'N/A')),
            ]
            
            for i, (label, value) in enumerate(stats_to_display):
                draw.text((15, y_offset + i * 25), f"{label}:", font=font_regular, fill=secondary_color)
                draw.text((200, y_offset + i * 25), str(value), font=font_regular, fill=text_color)
                
        elif stats["source"] == "vnl.kz":
            # Display vnl stats
            finishes = stats.get('finishes', 'N/A')
            draw.text((15, y_offset), "Finishes:", font=font_regular, fill=secondary_color)
            draw.text((200, y_offset), str(finishes), font=font_regular, fill=text_color)
            
            # Display tier distribution
            tier_counts = stats.get("tier_counts")
            if tier_counts:
                draw.text((15, y_offset + 30), "Tier Distribution:", font=font_regular, fill=secondary_color)
                
                tier_texts = [f"T{tier}: {count}" for tier, count in tier_counts.items()]
                
                # Display tiers in rows of 6
                for row_idx in range(0, len(tier_texts), 6):
                    row_text = "  ".join(tier_texts[row_idx:row_idx + 6])
                    draw.text((15, y_offset + 55 + row_idx // 6 * 20), row_text, font=font_small, fill=text_color)
            else:
                draw.text((15, y_offset + 30), "No tier data available", font=font_small, fill=secondary_color)

        # Add footer
        footer_text = f"Data from {stats['source']}"
        draw.text((15, height - 25), footer_text, font=font_small, fill=secondary_color)

        # Save image to a bytes buffer
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return img_byte_arr
    except Exception as e:
        # Log the error for debugging
        print(f"Error creating stats image: {e}")
        return None
