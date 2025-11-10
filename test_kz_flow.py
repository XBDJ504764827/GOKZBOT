#!/usr/bin/env python3
"""测试完整的 /kz 指令数据流程"""
import asyncio
from kz_stats import get_vnl_stats, create_stats_image
from database import get_db_session, VnlMapTier
from collections import Counter

async def test_vnl_flow(steam_id64: str):
    """测试VNL模式的完整流程
    
    Args:
        steam_id64: 玩家的 SteamID64
    """
    print("=" * 70)
    print(f"测试 VNL 模式数据流程 - SteamID64: {steam_id64}")
    print("=" * 70)
    
    # 步骤1: 从API获取玩家数据
    print("\n[步骤1] 从 KZTimer Global API 获取玩家数据...")
    stats = await get_vnl_stats(steam_id64)
    
    if not stats:
        print("❌ 无法获取玩家数据")
        return False
    
    print(f"✅ 成功获取玩家数据")
    print(f"   玩家名称: {stats.get('name')}")
    print(f"   总分: {stats.get('points')}")
    print(f"   排名: {stats.get('rank')}")
    print(f"   等级: {stats.get('level')}")
    print(f"   完成地图数: {stats.get('finishes')}")
    
    # 步骤2: 获取地图ID列表
    map_ids = stats.get("map_ids", [])
    print(f"\n[步骤2] 提取地图ID列表")
    print(f"   共获取到 {len(map_ids)} 个地图ID")
    if map_ids:
        print(f"   前10个地图ID: {map_ids[:10]}")
    
    # 步骤3: 从数据库查询地图等级
    print(f"\n[步骤3] 从数据库查询地图等级...")
    
    if not map_ids:
        print("   ⚠️  没有地图ID，跳过数据库查询")
        stats["tier_counts"] = {}
    else:
        try:
            with get_db_session() as db_session:
                # 查询地图等级
                tier_results = db_session.query(
                    VnlMapTier.id, 
                    VnlMapTier.tptier
                ).filter(VnlMapTier.id.in_(map_ids)).all()
                
                print(f"   ✅ 从数据库匹配到 {len(tier_results)} 个地图的等级信息")
                print(f"   匹配率: {len(tier_results)}/{len(map_ids)} ({len(tier_results)*100//len(map_ids) if map_ids else 0}%)")
                
                if tier_results:
                    # 统计每个tier的数量
                    tier_counts = Counter(tier[1] for tier in tier_results)
                    stats["tier_counts"] = dict(sorted(tier_counts.items()))
                    
                    print(f"\n   等级分布:")
                    for tier, count in sorted(tier_counts.items()):
                        print(f"      Tier {tier}: {count} 个地图")
                else:
                    print("   ⚠️  数据库中没有找到匹配的地图等级")
                    stats["tier_counts"] = {}
                    
        except Exception as e:
            print(f"   ❌ 数据库查询失败: {e}")
            import traceback
            traceback.print_exc()
            stats["tier_counts"] = {}
    
    # 步骤4: 生成图片
    print(f"\n[步骤4] 生成数据图片...")
    image_bytes = await create_stats_image(stats)
    
    if not image_bytes:
        print("   ❌ 图片生成失败")
        return False
    
    # 保存图片
    output_file = f"test_vnl_flow_{steam_id64}.png"
    with open(output_file, "wb") as f:
        f.write(image_bytes)
    
    print(f"   ✅ 图片生成成功！")
    print(f"   保存为: {output_file}")
    print(f"   图片大小: {len(image_bytes)} 字节")
    
    print("\n" + "=" * 70)
    print("✅ 完整流程测试成功！")
    print("=" * 70)
    
    return True

async def main():
    print("\n🔍 GOKZBOT /kz 指令完整流程测试\n")
    
    # 测试用的 SteamID64
    # 你可以替换成实际的 SteamID64 进行测试
    test_steam_id64 = "76561199295538824"  # 示例ID
    
    print(f"使用测试 SteamID64: {test_steam_id64}")
    print("(你可以在代码中修改这个ID来测试其他玩家)\n")
    
    success = await test_vnl_flow(test_steam_id64)
    
    if success:
        print("\n✅ 所有测试通过！")
        print("\n提示:")
        print("  1. 检查生成的图片文件")
        print("  2. 查看控制台输出的调试信息")
        print("  3. 确认地图等级统计是否正确")
    else:
        print("\n❌ 测试失败，请检查错误信息")

if __name__ == "__main__":
    asyncio.run(main())

