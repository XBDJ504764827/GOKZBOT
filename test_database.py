#!/usr/bin/env python3
"""测试数据库连接和查询功能"""
from database import get_db_session, VnlMapTier
from collections import Counter

def test_database_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("测试数据库连接")
    print("=" * 60)
    
    try:
        with get_db_session() as db_session:
            # 查询表中的记录数
            count = db_session.query(VnlMapTier).count()
            print(f"✅ 数据库连接成功！")
            print(f"📊 vnlmaptier 表中共有 {count} 条记录")
            
            # 查询前10条记录
            print("\n前10条记录示例:")
            print("-" * 60)
            print(f"{'地图ID (id)':<15} {'等级 (tptier)':<15}")
            print("-" * 60)
            
            sample_records = db_session.query(VnlMapTier).limit(10).all()
            for record in sample_records:
                print(f"{record.id:<15} {record.tptier:<15}")
            
            # 统计每个tier的数量
            print("\n" + "=" * 60)
            print("各等级地图数量统计:")
            print("=" * 60)
            
            tier_results = db_session.query(VnlMapTier.tptier).all()
            tier_counts = Counter(tier[0] for tier in tier_results)
            
            for tier in sorted(tier_counts.keys()):
                count = tier_counts[tier]
                bar = "█" * (count // 10)  # 简单的条形图
                print(f"Tier {tier}: {count:>4} 个地图 {bar}")
            
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_map_id_query():
    """测试地图ID查询"""
    print("\n" + "=" * 60)
    print("测试地图ID查询功能")
    print("=" * 60)
    
    # 模拟一些地图ID
    test_map_ids = [1, 2, 3, 4, 5, 100, 200, 300]
    
    try:
        with get_db_session() as db_session:
            print(f"\n测试查询地图ID: {test_map_ids}")
            
            # 查询这些地图的等级
            tier_results = db_session.query(
                VnlMapTier.id, 
                VnlMapTier.tptier
            ).filter(VnlMapTier.id.in_(test_map_ids)).all()
            
            print(f"✅ 找到 {len(tier_results)} 个匹配的地图")
            print("\n匹配结果:")
            print("-" * 60)
            print(f"{'地图ID':<15} {'等级':<15}")
            print("-" * 60)
            
            for map_id, tier in tier_results:
                print(f"{map_id:<15} Tier {tier:<15}")
            
            # 统计tier分布
            if tier_results:
                tier_counts = Counter(tier[1] for tier in tier_results)
                print("\n等级分布:")
                for tier, count in sorted(tier_counts.items()):
                    print(f"  Tier {tier}: {count} 个地图")
            
            return True
            
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "🔍 GOKZBOT 数据库测试工具" + "\n")
    
    # 测试数据库连接
    if not test_database_connection():
        print("\n❌ 数据库连接测试失败，请检查数据库配置")
        return
    
    # 测试地图ID查询
    if not test_map_id_query():
        print("\n❌ 地图ID查询测试失败")
        return
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    main()

