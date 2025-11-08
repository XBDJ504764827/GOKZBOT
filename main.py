import aiohttp
from bs4 import BeautifulSoup
from collections import Counter
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from .database import get_db_session, User, init_db, VnlMapTier
from .kz_stats import get_kzgo_stats, get_vnl_stats, create_stats_image


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


def parse_bind_args(cmd_args: list) -> tuple[str | None, str, str | None]:
    """解析绑定命令的参数"""
    if not cmd_args:
        return None, "kzt", "用法: /bind <steamid> [-u <模式>]"

    mode = "kzt"
    valid_modes = {"kzt", "skz", "vnl"}
    
    # Check if the last argument is a mode and if there are preceding arguments for the steamid
    if len(cmd_args) > 1 and cmd_args[-1] in valid_modes:
        potential_mode = cmd_args[-1]
        steam_id_parts = cmd_args[:-1]
        
        # To be more robust, we can assume the user of `-u` is now gone,
        # so the second to last argument shouldn't be `-u`.
        # However, the framework might just remove '-u' and keep the arguments.
        # Let's handle the case where the framework removes '-u' but leaves a gap or not.
        # The simplest robust way is to assume the last part is the mode if it matches.
        
        mode = potential_mode
        steam_id_input = " ".join(steam_id_parts)
    else:
        # If only one arg, or last arg is not a mode, treat all as steamid
        steam_id_input = " ".join(cmd_args)

    return steam_id_input, mode, None


@register("GOKZBOT", "ShaWuXBDJ", "kz数据查询", "1.0.4")
class GOKZPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        init_db()

    @filter.command("bind")
    async def bind(
        self,
        event: AstrMessageEvent,
        args=None,
        kwargs=None,
        extra_args=None,
        extra_kwargs=None,
    ):
        """绑定你的steamid，例如 /bind <id> 或 /bind <id> -u vnl"""
        cmd_args = []
        # Consolidate args
        if args is not None:
            if isinstance(args, (list, tuple)):
                cmd_args.extend(args)
            else:
                cmd_args.append(args)

        # Consolidate extra_args
        if extra_args is not None:
            if isinstance(extra_args, (list, tuple)):
                cmd_args.extend(extra_args)
            else:
                cmd_args.append(extra_args)

        # Fallback to message_str if no args were passed via parameters
        if not cmd_args:
            cmd_args = event.message_str.split()[1:]

        steam_id_input, mode, error_msg = parse_bind_args(cmd_args)

        if error_msg:
            yield event.plain_result(error_msg)
            return

        qq_id = str(event.get_sender_id())
        with get_db_session() as db_session:
            existing_user = db_session.query(User).filter_by(qq_id=qq_id).first()

            if existing_user and existing_user.steam_id_64:
                yield event.plain_result(f"您已经绑定过 Steam 账户: {existing_user.steam_name} ({existing_user.steam_id_64})")
                return

            info = await get_steam_info(steam_id_input)

            if not info:
                yield event.plain_result(f"无法找到 SteamID '{steam_id_input}' 的信息，请检查输入。")
                return
            
            steam_id_64 = info["steam_id_64"]
            steam_name = info["name"]
            
            # 检查此 SteamID 是否已被其他人绑定
            steam_id_bound = (
                db_session.query(User)
                .filter(User.steam_id_64 == steam_id_64, User.qq_id != qq_id)
                .first()
            )
            if steam_id_bound:
                yield event.plain_result(f"此 Steam 账户已被其他用户绑定。")
                return

            if not existing_user:
                # New user
                new_user = User(
                    qq_id=qq_id,
                    steam_id=steam_id_input,
                    steam_id_64=steam_id_64,
                    steam_name=steam_name,
                    default_mode=mode,
                )
                db_session.add(new_user)
            else:
                # Existing user, re-binding
                existing_user.steam_id = steam_id_input
                existing_user.steam_id_64 = steam_id_64
                existing_user.steam_name = steam_name
                existing_user.default_mode = mode

            db_session.commit()

            yield event.plain_result(
                f"成功绑定 Steam 账户: {steam_name} ({steam_id_64})，默认查询模式: {mode.upper()}"
            )

    @filter.command("unbind")
    async def unbind(
        self,
        event: AstrMessageEvent,
        args=None,
        kwargs=None,
        extra_args=None,
        extra_kwargs=None,
    ):
        """解除当前绑定的 SteamID 并删除用户数据"""
        if kwargs is None:
            kwargs = {}

        qq_id = str(event.get_sender_id())

        with get_db_session() as db_session:
            user = db_session.query(User).filter_by(qq_id=qq_id).first()

            if not user or not user.steam_id_64:
                yield event.plain_result("你还没有绑定 SteamID。")
                return

            previous_name = user.steam_name
            previous_steam_id64 = user.steam_id_64

            db_session.delete(user)
            db_session.commit()

            yield event.plain_result(
                f"已成功删除 Steam 账户绑定: {previous_name} ({previous_steam_id64})。"
            )

    @filter.command("info")
    async def info(
        self,
        event: AstrMessageEvent,
        args=None,
        kwargs=None,
        extra_args=None,
        extra_kwargs=None,
    ):
        """查询你绑定的Steam账户信息"""
        qq_id = str(event.get_sender_id())
        if kwargs is None:
            kwargs = {}
 
        with get_db_session() as db_session:
            user = db_session.query(User).filter_by(qq_id=qq_id).first()
 
            if not user or not user.steam_id_64:
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

    @filter.command("kz")
    async def kz(
        self,
        event: AstrMessageEvent,
        args=None,
        kwargs=None,
        extra_args=None,
        extra_kwargs=None,
    ):
        """查询指定玩家的KZ数据, 默认查询自己。用法: /kz [-u <模式>] [@某人]"""
        # --- Argument Parsing ---
        cmd_args = []
        if args is not None:
            if isinstance(args, (list, tuple)):
                cmd_args.extend(args)
            else:
                cmd_args.append(args)
        if extra_args is not None:
            if isinstance(extra_args, (list, tuple)):
                cmd_args.extend(extra_args)
            else:
                cmd_args.append(extra_args)
        if not cmd_args and event.message_str.strip() != "/kz":
             cmd_args = event.message_str.split()[1:]

        target_qq_id = str(event.get_sender_id())
        # Check for mentions
        if hasattr(event, "mentions") and event.mentions:
            target_qq_id = str(event.mentions[0].id)

        mode_override = None
        # The argument parsing here is tricky because AstrBot might pass mentions
        # as part of the text arguments. We'll look for -u and the next argument.
        if "-u" in cmd_args:
            try:
                mode_index = cmd_args.index("-u")
                if mode_index + 1 < len(cmd_args):
                    potential_mode = cmd_args[mode_index + 1]
                    if potential_mode in ["kzt", "skz", "vnl"]:
                        mode_override = potential_mode
            except (ValueError, IndexError):
                # This can happen if parsing fails, just ignore for now.
                pass
        
        # --- Database Lookup ---
        with get_db_session() as db_session:
            user = db_session.query(User).filter_by(qq_id=target_qq_id).first()
            if not user or not user.steam_id_64:
                yield event.plain_result("无法查询, 未绑定 SteamID。请使用 /bind 绑定。")
                return
            
            mode = mode_override or user.default_mode or "kzt"
            steam_id = user.steam_id
            steam_id64 = user.steam_id_64

        # --- Data Fetching ---
        stats = None
        yield event.plain_result(f"正在查询 {mode.upper()} 模式数据...")
        if mode in ["kzt", "skz"]:
            stats = await get_kzgo_stats(steam_id, mode)
        elif mode == "vnl":
            stats = await get_vnl_stats(steam_id64)
            if stats:
                map_ids = stats.get("map_ids", [])
                if map_ids:
                    # Query the database for tiers
                    tiers = db_session.query(VnlMapTier.tptier).filter(VnlMapTier.id.in_(map_ids)).all()
                    if tiers:
                        tier_counts = Counter(tier[0] for tier in tiers)
                        stats["tier_counts"] = dict(sorted(tier_counts.items()))

        else:
            valid_modes = ["kzt", "skz", "vnl"]
            yield event.plain_result(f"无效的模式。可用模式: {', '.join(valid_modes)}")
            return
            
        if not stats:
            yield event.plain_result("未能查询到玩家数据，请检查绑定的 SteamID 或稍后再试。")
            return
            
        # --- Image Generation ---
        image_bytes = await create_stats_image(stats)
        
        if not image_bytes:
            yield event.plain_result("生成玩家数据图时出错。")
            return

        yield event.image_result(image_bytes)
