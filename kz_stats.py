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
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                player_card = soup.find("div", class_="player-card")
                if not player_card:
                    return None

                stats = {"source": "kzgo.eu", "mode": mode}

                # Player name and avatar
                stats["name"] = player_card.find("h1").text.strip()
                stats["avatar_url"] = player_card.find("img")["src"]

                # Rank and Points
                rank_div = player_card.find("div", class_="rank")
                if rank_div:
                    stats["rank"] = rank_div.find("h2").text.strip()
                    stats["points"] = rank_div.find("p").text.strip().replace("points", "").strip()
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
    except Exception:
        return None


async def get_vnl_stats(steam_id64: str) -> dict | None:
    """Fetches player stats for vnl mode from kztimerglobal and vnl.kz APIs."""
    records_url = f"https://kztimerglobal.com/api/v2.0/records/top?steamid64={steam_id64}&stage=0&modes_list_string=kz_vanilla&limit=10000&has_teleports=true"
    profile_url = f"https://vnl.kz/api/v1/profiles?steamids={steam_id64}"
    
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch records for points and map_ids
            async with session.get(records_url) as response:
                if response.status != 200:
                    records = [] # Assume no records if API fails
                else:
                    records = await response.json()
            
            # Calculate total points and finishes from records
            total_points = sum(record.get('points', 0) for record in records)
            finishes = len(records)
            map_ids = [record.get('map_id') for record in records if record.get('map_id') is not None]

            # Fetch profile for name and avatar
            stats = {}
            async with session.get(profile_url) as profile_response:
                if profile_response.status == 200:
                    profile_data = await profile_response.json()
                    if profile_data and len(profile_data) > 0:
                        stats["name"] = profile_data[0].get("name", "N/A")
                        stats["avatar_url"] = profile_data[0].get("avatarfull", "")
                    else:
                        # Fallback name from records if profile API fails
                        stats["name"] = records[0].get("player_name", "N/A") if records else "N/A"
                        stats["avatar_url"] = ""
                else:
                    stats["name"] = records[0].get("player_name", "N/A") if records else "N/A"
                    stats["avatar_url"] = ""

            # Assemble stats dictionary
            stats.update({
                "source": "vnl.kz",
                "mode": "vnl",
                "points": total_points,
                "rank": str(total_points), # Using points as rank for vnl
                "finishes": finishes,
                "wrs": "N/A", # This API doesn't provide WR count.
                "map_ids": map_ids
            })
            
            return stats
    except Exception:
        return None

def _find_font() -> str:
    """Tries to find a usable TTF font on a Linux system."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return path
    return "default"  # Pillow will use its built-in bitmap font

async def create_stats_image(stats: dict) -> bytes | None:
    """Creates an image from the player's stats."""
    try:
        # Create a background
        width, height = 400, 250  # Increased height
        bg_color = (24, 25, 28)  # Dark grey
        image = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Load font
        try:
            font_path = _find_font()
            if font_path == "default":
                font_regular = ImageFont.load_default()
                font_bold = ImageFont.load_default()
            else:
                font_regular = ImageFont.truetype(font_path, 15)
                font_bold = ImageFont.truetype(font_path, 18)
        except IOError:
            # Fallback to default font if the specified one isn't found
            font_regular = ImageFont.load_default()
            font_bold = ImageFont.load_default()

        # Fetch and add avatar
        avatar_url = stats.get("avatar_url")
        if avatar_url:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        avatar_image = Image.open(io.BytesIO(avatar_data))
                        avatar_image = avatar_image.resize((64, 64))
                        image.paste(avatar_image, (15, 15))

        # Colors
        text_color = (255, 255, 255)
        highlight_color = (153, 102, 255) # Purple

        # Draw text
        draw.text((95, 15), stats.get("name", "N/A"), font=font_bold, fill=text_color)
        
        rank_text = f"Rank: {stats.get('rank', 'N/A')}"
        points_text = f"Points: {stats.get('points', 'N/A')}"
        draw.text((95, 45), rank_text, font=font_regular, fill=highlight_color)
        draw.text((95, 65), points_text, font=font_regular, fill=text_color)
        
        # Draw stats based on source
        y_offset = 100
        if stats["source"] == "kzgo.eu":
            completions = f"Completions: {stats.get('maps_completed', 'N/A')}"
            wr = f"World Records: {stats.get('world_records', 'N/A')}"
            draw.text((15, y_offset), completions, font=font_regular, fill=text_color)
            draw.text((15, y_offset + 20), wr, font=font_regular, fill=text_color)
        elif stats["source"] == "vnl.kz":
            finishes = f"Finishes: {stats.get('finishes', 'N/A')}"
            draw.text((15, y_offset), finishes, font=font_regular, fill=text_color)
            
            tier_counts = stats.get("tier_counts")
            if tier_counts:
                tier_texts = [f"T{tier}: {count}" for tier, count in tier_counts.items()]
                
                # Display up to 5 tiers per line to fit
                line1 = "  ".join(tier_texts[:5])
                line2 = "  ".join(tier_texts[5:10])
                draw.text((15, y_offset + 25), line1, font=font_regular, fill=text_color)
                if line2:
                    draw.text((15, y_offset + 50), line2, font=font_regular, fill=text_color)
            else:
                 draw.text((15, y_offset + 25), "No TP tier data found.", font=font_regular, fill=text_color)

        # Save image to a bytes buffer
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        return img_byte_arr
    except Exception:
        return None
