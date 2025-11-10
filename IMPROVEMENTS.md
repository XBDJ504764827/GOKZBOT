# /kz 指令功能改进说明

## 📋 改进概述

本次改进主要针对 `/kz` 指令的图片生成功能，参考 `text.jpg` 的样式，重新设计了数据展示方式。

## 🎨 图片样式改进

### 1. 布局优化
- **动态高度**: 根据 tier 数据自动调整图片高度
- **更大的字体**: 提高可读性
- **圆形头像**: 80x80 像素的圆形玩家头像
- **清晰的层次**: 头部信息 + 分隔线 + 详细数据

### 2. 显示内容

#### 头部区域
- **玩家名称**: 大字体显示（28px）
- **等级标识**: 金色显示等级（如 Expert, Master）
- **排名**: 蓝色高亮显示
- **总分**: 格式化显示（带千位分隔符）
- **模式标识**: 右上角显示 KZT/SKZ/VNL

#### VNL 模式详细数据
- **完成地图总数**: 粗体显示
- **各等级地图分布**: 
  - 每个 Tier 一行
  - 带进度条的可视化显示
  - 根据难度使用不同颜色：
    - Tier 1-2: 绿色（简单）
    - Tier 3-4: 蓝色（中等）
    - Tier 5-6: 橙色（困难）
    - Tier 7+: 红色（极难）
  - 显示具体数量

## 🔧 技术改进

### 1. 数据流程优化

```
API 获取 → 提取 map_id → 数据库匹配 tier → 统计分布 → 绘制图片
```

#### 详细步骤：

1. **API 数据获取**
   - 从 `https://kztimerglobal.com/api/v2.0/records/top` 获取玩家完成的所有地图记录
   - 每条记录包含：`map_id`（地图ID）、`points`（该地图分数）

2. **地图ID提取**
   - 从所有记录中提取 `map_id` 列表
   - 过滤掉 `None` 值

3. **数据库匹配**
   - 在 `vnlmaptier` 表中查询：
     - `id` 字段对应 API 返回的 `map_id`
     - `tptier` 字段是地图等级（1-7）
   - 使用 SQLAlchemy 的 `filter().in_()` 批量查询

4. **统计分布**
   - 使用 `Counter` 统计每个 tier 的数量
   - 排序后存入 `stats["tier_counts"]`

5. **图片绘制**
   - 根据 tier 数量动态调整图片高度
   - 绘制进度条和数量标签

### 2. 错误处理增强

- **数据库查询异常**: 捕获并记录，继续执行但不显示 tier 数据
- **API 请求失败**: 详细的日志输出，便于调试
- **调试信息**: 添加 `[DEBUG]` 和 `[ERROR]` 标签的日志

### 3. 代码改进

#### main.py
```python
# 改进的数据库查询
tier_results = db_session.query(
    VnlMapTier.id,      # 地图ID
    VnlMapTier.tptier   # 地图等级
).filter(VnlMapTier.id.in_(map_ids)).all()

# 统计每个tier的数量
tier_counts = Counter(tier[1] for tier in tier_results)
stats["tier_counts"] = dict(sorted(tier_counts.items()))
```

#### kz_stats.py
```python
# 动态计算图片高度
tier_counts = stats.get("tier_counts", {})
tier_height = len(tier_counts) * 30 + 40
height = base_height + tier_height

# 绘制带颜色的进度条
for tier, count in sorted(tier_counts.items()):
    # 根据tier选择颜色
    if tier <= 2:
        fill_color = (100, 200, 100)  # 绿色
    elif tier <= 4:
        fill_color = (100, 150, 255)  # 蓝色
    # ...
```

## 🧪 测试工具

提供了三个测试脚本：

### 1. `test_database.py`
测试数据库连接和查询功能
```bash
python3 test_database.py
```

### 2. `test_image_generation.py`
测试图片生成功能（使用模拟数据）
```bash
python3 test_image_generation.py
```

### 3. `test_kz_flow.py`
测试完整的数据流程（从API到图片生成）
```bash
python3 test_kz_flow.py
```

## 📊 数据库表结构

### vnlmaptier 表
```sql
CREATE TABLE vnlmaptier (
    id INTEGER PRIMARY KEY,      -- 地图ID（对应API的map_id）
    tptier INTEGER              -- 地图等级（1-7）
);
```

## 🎯 使用示例

```bash
# 查询自己的数据（使用默认模式）
/kz

# 查询 VNL 模式数据
/kz -u vnl

# 查询其他人的数据
/kz @某人

# 查询其他人的 VNL 数据
/kz @某人 -u vnl
```

## 📝 注意事项

1. **数据库连接**: 确保 PostgreSQL 数据库可访问
2. **API 限流**: KZTimer Global API 可能有请求限制
3. **字体支持**: 自动下载中文字体，首次运行可能较慢
4. **调试模式**: 查看控制台输出的 `[DEBUG]` 信息

## 🔍 调试信息

运行时会输出详细的调试信息：
- `[DEBUG]` 正常的调试信息
- `[ERROR]` 错误信息
- 包括：API 请求状态、数据库查询结果、tier 统计等

## 📈 后续优化建议

1. **缓存机制**: 缓存玩家数据，减少 API 请求
2. **异步优化**: 并行处理多个 API 请求
3. **图片美化**: 添加更多视觉元素（渐变、阴影等）
4. **数据验证**: 更严格的数据完整性检查

