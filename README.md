# GOKZBOT

一个功能全面的 AstrBot 插件，用于查询 GOKZ（KZ 模式）玩家数据。

## 功能特性

### 已实现功能

- **账号绑定** (`/bind <steamid> [-u 模式]`)
  - 支持绑定 SteamID、SteamID3、SteamID64
  - 支持三种游戏模式：kzt、skz、vnl
  - 自动验证 Steam 账号有效性

- **账号解绑** (`/unbind`)
  - 解除当前绑定的 Steam 账号

- **信息查询** (`/info` 或 `/info @某人`)
  - 查询自己或他人的绑定信息
  - 显示 Steam 名称、SteamID64、默认模式、绑定时间

- **KZ 数据查询** (`/kz` 或 `/kz @某人` 或 `/kz -u 模式`)
  - 查询玩家在 GOKZ 的统计数据
  - 支持 kzt、skz、vnl 三种模式
  - 以精美图片形式展示数据
  - 包含玩家头像、排名、积分、完成地图数等信息

### 待开发功能

- **最近记录查询** (`/pb`) - 查询玩家最近完成的地图数据
- **全局统计** (`/kzstats`) - 查询玩家的全局统计数据

## 数据源

- **kzt/skz 模式**: [kzgo.eu](https://kzgo.eu/)
- **vnl 模式**: [vnl.kz](https://vnl.kz/) 和 [KZTimer Global API](https://kztimerglobal.com/)

## 使用方法

1. 绑定你的 Steam 账号：
   ```
   /bind STEAM_1:0:123456789
   /bind 76561198083722517 -u vnl
   ```

2. 查询 KZ 数据：
   ```
   /kz              # 查询自己的数据（使用默认模式）
   /kz @某人        # 查询其他人的数据
   /kz -u skz       # 使用指定模式查询
   ```

3. 查看绑定信息：
   ```
   /info            # 查看自己的绑定信息
   /info @某人      # 查看其他人的绑定信息
   ```

## 技术栈

- Python 3.10+
- AstrBot 框架
- PostgreSQL 数据库
- aiohttp (异步 HTTP 请求)
- BeautifulSoup4 (网页解析)
- Pillow (图片生成)
- SQLAlchemy (数据库 ORM)

## 支持

[AstrBot 帮助文档](https://astrbot.app)
