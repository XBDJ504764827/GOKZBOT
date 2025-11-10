#!/usr/bin/env python3
"""测试图片生成功能"""
import asyncio
from kz_stats import create_stats_image

async def test_vnl_image():
    """测试VNL模式的图片生成"""
    # 模拟VNL模式的数据
    test_stats = {
        "source": "vnl.kz",
        "mode": "vnl",
        "name": "TestPlayer",
        "avatar_url": "",  # 可以留空测试无头像情况
        "rank": "1234",
        "points": 156789,
        "level": "Expert",
        "finishes": 245,
        "tier_counts": {
            1: 45,
            2: 52,
            3: 48,
            4: 38,
            5: 32,
            6: 20,
            7: 10
        }
    }
    
    print("正在生成VNL模式测试图片...")
    image_bytes = await create_stats_image(test_stats)
    
    if image_bytes:
        with open("test_vnl_output.png", "wb") as f:
            f.write(image_bytes)
        print("✅ VNL模式图片生成成功！保存为 test_vnl_output.png")
    else:
        print("❌ VNL模式图片生成失败")

async def test_kzt_image():
    """测试KZT模式的图片生成"""
    # 模拟KZT模式的数据
    test_stats = {
        "source": "kzgo.eu",
        "mode": "kzt",
        "name": "TestPlayer",
        "avatar_url": "",
        "rank": "567",
        "points": "12345",
        "maps_completed": "150",
        "world_records": "5",
        "average": "82.5"
    }
    
    print("正在生成KZT模式测试图片...")
    image_bytes = await create_stats_image(test_stats)
    
    if image_bytes:
        with open("test_kzt_output.png", "wb") as f:
            f.write(image_bytes)
        print("✅ KZT模式图片生成成功！保存为 test_kzt_output.png")
    else:
        print("❌ KZT模式图片生成失败")

async def main():
    print("=" * 50)
    print("开始测试图片生成功能")
    print("=" * 50)
    
    await test_vnl_image()
    print()
    await test_kzt_image()
    
    print()
    print("=" * 50)
    print("测试完成！")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())

