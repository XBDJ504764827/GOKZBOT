from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .utils.db import get_user_bindings, save_user_bindings


@register("gokz", "GOKZBOT", "一个GOKZ插件", "1.0.0")
class GOKZPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化"""
        logger.info("GOKZ 插件已加载")

    @filter.command("kz_bind", "绑定SteamID", "将你的QQ号与SteamID绑定", ["/kz_bind <steamid>"])
    async def bind_steamid(self, event: AstrMessageEvent):
        """绑定SteamID"""
        args = event.get_plain_text().strip().split()
        if len(args) != 1:
            yield event.reply("用法: /kz_bind <steamid>")
            return

        steam_id = args[0]
        user_id = event.get_user_id()

        bindings = get_user_bindings()
        bindings[str(user_id)] = steam_id
        save_user_bindings(bindings)

        yield event.reply(f"绑定成功！您的QQ已与SteamID: {steam_id} 绑定。")

    async def terminate(self):
        """插件卸载"""
        logger.info("GOKZ 插件已卸载")
