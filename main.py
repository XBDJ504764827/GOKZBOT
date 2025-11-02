import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from .database import get_db_session, User

@register("GOKZBOT", "ShaWuXBDJ", "kz数据查询", "1.0.0")
class GOKZPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        data_dir = os.path.join("data", "plugins", "GOKZBOT")
        self.db_session = get_db_session(data_dir)

    @filter.command("bind")
    async def bind(self, event: AstrMessageEvent):
        """绑定你的steamid，例如 /bind steamid"""
        args = event.message_str.split()[1:]
        if len(args) != 1:
            yield event.plain_result("用法: /bind <steamid>")
            return

        steam_id = args[0]
        qq_id = str(event.sender.id)

        user = self.db_session.query(User).filter_by(qq_id=qq_id).first()
        if user:
            user.steam_id = steam_id
            msg = f"你的 SteamID 已更新为: {steam_id}"
        else:
            new_user = User(qq_id=qq_id, steam_id=steam_id)
            self.db_session.add(new_user)
            msg = f"成功绑定 SteamID: {steam_id}"

        self.db_session.commit()
        yield event.plain_result(msg)
