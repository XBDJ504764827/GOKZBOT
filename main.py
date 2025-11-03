import os
import re
import aiohttp
from bs4 import BeautifulSoup
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from .database import get_db_session, User


async def get_steam_info(steam_id_input: str) -> dict | None:
    """根据输入的steamid，从steamid.io获取信息"""
    url = f"https://steamid.io/lookup/{steam_id_input}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                steam_id_64 = None
                steam_name = None

                # steamid.io 网页结构为 <dt>key</dt><dd>value</dd>
                # 查找 steamID64
                dt_steamid64 = soup.find('dt', string='steamID64')
                if dt_steamid64:
                    dd_steamid64 = dt_steamid64.find_next_sibling('dd')
                    if dd_steamid64:
                        # dd 标签内的文本是 "copy to clipboard 7656..."
                        steam_id_64 = dd_steamid64.text.strip().split()[-1]
                
                # 查找 name
                dt_name = soup.find('dt', string='name')
                if dt_name:
                    dd_name = dt_name.find_next_sibling('dd')
                    if dd_name:
                        steam_name = dd_name.text.strip()

                if steam_id_64 and steam_name:
                    return {"steam_id_64": steam_id_64, "name": steam_name}
                return None
    except Exception:
        return None


@register("GOKZBOT", "ShaWuXBDJ", "kz数据查询", "1.0.0")
class GOKZPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.db_session = get_db_session()

    @filter.command("bind")
    async def bind(self, event: AstrMessageEvent):
        """绑定你的steamid，例如 /bind <id> 或 /bind <id> -u vnl"""
        args = event.message_str.split()[1:]
        
        if not args:
            yield event.plain_result("用法: /bind <steamid> [-u <模式>]")
            return

        steam_id_input = args[0]
        mode = "kzt"
        valid_modes = ["kzt", "skz", "vnl"]

        # 解析 -u 参数
        if "-u" in args:
            try:
                mode_index = args.index("-u") + 1
                if mode_index < len(args) and args[mode_index] in valid_modes:
                    mode = args[mode_index]
                else:
                    yield event.plain_result(f"无效的模式。可用模式: {', '.join(valid_modes)}")
                    return
            except (ValueError, IndexError):
                yield event.plain_result("-u 参数使用错误。用法: /bind <steamid> -u <模式>")
                return

        qq_id = str(event.get_sender_id())
        existing_user = self.db_session.query(User).filter_by(qq_id=qq_id).first()

        if existing_user:
            yield event.plain_result(f"您已经绑定过 Steam 账户: {existing_user.steam_name} ({existing_user.steam_id_64})")
            return

        yield event.plain_result(f"正在查询 SteamID '{steam_id_input}'...")
        info = await get_steam_info(steam_id_input)

        if not info:
            yield event.plain_result(f"无法找到 SteamID '{steam_id_input}' 的信息，请检查输入。")
            return
        
        steam_id_64 = info["steam_id_64"]
        steam_name = info["name"]
        
        # 检查此 SteamID 是否已被其他人绑定
        steam_id_bound = self.db_session.query(User).filter_by(steam_id_64=steam_id_64).first()
        if steam_id_bound:
            yield event.plain_result(f"此 Steam 账户已被其他用户绑定。")
            return

        new_user = User(qq_id=qq_id, steam_id_64=steam_id_64, steam_name=steam_name, default_mode=mode)
        self.db_session.add(new_user)
        self.db_session.commit()
        
        yield event.plain_result(f"成功绑定 Steam 账户: {steam_name} ({steam_id_64})，默认查询模式: {mode.upper()}")

    @filter.command("info")
    async def info(self, event: AstrMessageEvent):
        """查询你绑定的Steam账户信息"""
        qq_id = str(event.get_sender_id())
        user = self.db_session.query(User).filter_by(qq_id=qq_id).first()

        if not user:
            yield event.plain_result("你还没有绑定 SteamID。请使用 /bind <steamid> 进行绑定。")
            return
        
        bind_time = user.created_at.strftime("%Y-%m-%d %H:%M:%S")
        
        msg = (
            f"Steam 名称: {user.steam_name}\n"
            f"SteamID64: {user.steam_id_64}\n"
            f"默认模式: {user.default_mode.upper()}\n"
            f"绑定时间: {bind_time}"
        )
        yield event.plain_result(msg)
