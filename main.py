import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
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
        try:
            args = event.message_str.split()[1:]
            if len(args) != 1:
                yield event.plain_result("用法: /bind <steamid>")
                return

            steam_id = args[0]
            # The following line will deliberately fail to trigger the debug log.
            qq_id = str(event.sender['user_id'])

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
        except AttributeError:
            logger.error("【GOKZBOT】在获取用户信息时捕获到 AttributeError。这是预期的调试步骤。")
            logger.info("【GOKZBOT】'event' 对象的可用属性列表如下:")
            logger.info(dir(event))
            yield event.plain_result(
                "插件调试：无法获取用户信息。请查看机器人后台日志，找到【GOKZBOT】开头的日志，并将“可用属性列表”下面的那行内容发给我，以便进行最终修复。"
            )
        except IndexError:
            # This happens when user sends just "/bind"
            yield event.plain_result("用法: /bind <steamid>")
        except Exception as e:
            logger.error(f"【GOKZBOT】在 bind 命令中发生未知错误: {e}")
            yield event.plain_result("插件出现未知内部错误，请检查机器人后台日志。")
