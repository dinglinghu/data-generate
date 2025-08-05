#!/usr/bin/env python3
"""
导弹池管理器 - 优化导弹创建性能
通过预创建导弹池，避免频繁的STK对象创建/删除操作
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MissilePoolItem:
    """导弹池项目"""
    missile_id: str
    stk_object: Any
    launch_position: Dict[str, float]
    target_position: Dict[str, float]
    trajectory_data: Optional[Dict[str, Any]]
    is_active: bool = False
    current_launch_time: Optional[datetime] = None
    flight_duration: int = 1800
    creation_time: datetime = None

class MissilePoolManager:
    """导弹池管理器 - 性能优化核心组件"""
    
    def __init__(self, stk_manager, config_manager, missile_manager):
        """初始化导弹池管理器"""
        self.stk_manager = stk_manager
        self.config_manager = config_manager
        self.missile_manager = missile_manager

        # 从配置文件获取导弹池配置
        pool_config = self.config_manager.config.get("missile_pool", {})
        self.pool_size = pool_config.get("pool_size", 30)  # 池大小
        self.active_limit = pool_config.get("active_limit", 5)  # 同时活跃导弹数限制
        self.default_flight_duration = pool_config.get("default_flight_duration", 1800)  # 默认飞行时间
        self.id_random_range = pool_config.get("id_random_range", [1000, 9999])  # ID随机数范围
        
        # 导弹池
        self.missile_pool: Dict[str, MissilePoolItem] = {}
        self.active_missiles: List[str] = []
        self.available_missiles: List[str] = []
        
        # 性能统计
        self.stats = {
            "pool_hits": 0,
            "pool_misses": 0,
            "creation_time_saved": 0.0
        }
        
        logger.info(f"导弹池管理器初始化完成，池大小: {self.pool_size}")
    
    async def initialize_pool(self) -> bool:
        """初始化导弹池 - 预创建所有导弹"""
        try:
            logger.info(f"🏊 开始初始化导弹池，预创建 {self.pool_size} 个导弹...")
            
            start_time = datetime.now()
            
            for i in range(self.pool_size):
                missile_id = f"PoolMissile_{i+1:03d}_{random.randint(self.id_random_range[0], self.id_random_range[1])}"
                
                # 生成随机位置
                launch_pos = self._generate_random_launch_position()
                target_pos = self._generate_random_target_position()
                
                # 创建STK导弹对象
                success = await self._create_pool_missile(missile_id, launch_pos, target_pos)
                
                if success:
                    self.available_missiles.append(missile_id)
                    logger.debug(f"   ✅ 池导弹创建成功: {missile_id}")
                else:
                    logger.warning(f"   ⚠️ 池导弹创建失败: {missile_id}")
            
            creation_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ 导弹池初始化完成！")
            logger.info(f"   成功创建: {len(self.available_missiles)}/{self.pool_size} 个导弹")
            logger.info(f"   初始化耗时: {creation_time:.2f}秒")
            
            return len(self.available_missiles) > 0
            
        except Exception as e:
            logger.error(f"❌ 导弹池初始化失败: {e}")
            return False
    
    async def _create_pool_missile(self, missile_id: str, launch_pos: Dict, target_pos: Dict) -> bool:
        """创建池中的导弹对象"""
        try:
            # 使用导弹管理器的创建逻辑，但不激活
            missile_config = {
                "missile_id": missile_id,
                "launch_position": launch_pos,
                "target_position": target_pos,
                "launch_time": datetime.now(),  # 临时时间，后续会调整
                "flight_duration": self.default_flight_duration  # 默认飞行时间
            }
            
            # 创建STK对象
            result = self.missile_manager.create_single_missile_target(missile_config)
            
            if result:
                # 获取STK对象
                try:
                    stk_object = self.stk_manager.scenario.Children.Item(missile_id)
                    
                    # 创建池项目
                    pool_item = MissilePoolItem(
                        missile_id=missile_id,
                        stk_object=stk_object,
                        launch_position=launch_pos,
                        target_position=target_pos,
                        trajectory_data=None,
                        is_active=False,
                        creation_time=datetime.now()
                    )
                    
                    self.missile_pool[missile_id] = pool_item
                    return True
                    
                except Exception as stk_error:
                    logger.warning(f"   STK对象获取失败: {stk_error}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"创建池导弹失败 {missile_id}: {e}")
            return False
    
    def get_missiles_for_collection(self, collection_time: datetime, count: int) -> List[Dict[str, Any]]:
        """为采集获取导弹（从池中激活）"""
        try:
            logger.info(f"🎯 从导弹池获取 {count} 个导弹用于采集...")
            
            start_time = datetime.now()
            
            # 确保有足够的可用导弹
            if len(self.available_missiles) < count:
                logger.warning(f"⚠️ 可用导弹不足: {len(self.available_missiles)}/{count}")
                count = len(self.available_missiles)
            
            selected_missiles = []
            
            for i in range(count):
                if not self.available_missiles:
                    break
                
                # 从可用列表中选择导弹
                missile_id = self.available_missiles.pop(0)
                pool_item = self.missile_pool[missile_id]
                
                # 激活导弹
                success = self._activate_missile(pool_item, collection_time)
                
                if success:
                    self.active_missiles.append(missile_id)
                    
                    # 生成导弹配置
                    missile_config = {
                        "missile_id": missile_id,
                        "launch_position": pool_item.launch_position,
                        "target_position": pool_item.target_position,
                        "launch_time": pool_item.current_launch_time,
                        "flight_duration": pool_item.flight_duration,
                        "collection_time": collection_time,
                        "from_pool": True
                    }
                    
                    selected_missiles.append(missile_config)
                    logger.debug(f"   ✅ 激活池导弹: {missile_id}")
                else:
                    # 激活失败，放回可用列表
                    self.available_missiles.append(missile_id)
                    logger.warning(f"   ⚠️ 激活池导弹失败: {missile_id}")
            
            selection_time = (datetime.now() - start_time).total_seconds()
            self.stats["pool_hits"] += len(selected_missiles)
            self.stats["creation_time_saved"] += selection_time * 10  # 估算节省的时间
            
            logger.info(f"✅ 成功从池中获取 {len(selected_missiles)} 个导弹")
            logger.info(f"   选择耗时: {selection_time:.3f}秒 (vs 创建耗时 ~{selection_time*10:.1f}秒)")
            
            return selected_missiles
            
        except Exception as e:
            logger.error(f"❌ 从导弹池获取导弹失败: {e}")
            return []
    
    def _activate_missile(self, pool_item: MissilePoolItem, collection_time: datetime) -> bool:
        """激活池中的导弹"""
        try:
            # 生成新的发射时间和飞行时间
            offset_range = [-300, 300]  # ±5分钟
            offset = random.randint(*offset_range)
            launch_time = collection_time + timedelta(seconds=offset)
            
            # 生成飞行时间
            duration_range = [1800, 2400]  # 30-40分钟
            flight_duration = random.randint(*duration_range)
            
            # 更新池项目
            pool_item.is_active = True
            pool_item.current_launch_time = launch_time
            pool_item.flight_duration = flight_duration
            
            # 更新STK对象的时间属性
            success = self._update_missile_timing(pool_item, launch_time, flight_duration)
            
            return success
            
        except Exception as e:
            logger.error(f"激活导弹失败 {pool_item.missile_id}: {e}")
            return False
    
    def _update_missile_timing(self, pool_item: MissilePoolItem, launch_time: datetime, flight_duration: int) -> bool:
        """更新导弹的时间属性"""
        try:
            # 使用导弹管理器的时间设置方法
            missile = pool_item.stk_object
            success = self.missile_manager._set_missile_time_period_correct(
                missile, launch_time, flight_duration
            )
            
            if success:
                logger.debug(f"   ⏰ 导弹时间更新成功: {pool_item.missile_id}")
                return True
            else:
                logger.warning(f"   ⚠️ 导弹时间更新失败: {pool_item.missile_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新导弹时间失败 {pool_item.missile_id}: {e}")
            return False
    
    def release_missiles(self, missile_ids: List[str]) -> None:
        """释放导弹回池中"""
        try:
            logger.info(f"🔄 释放 {len(missile_ids)} 个导弹回池中...")
            
            for missile_id in missile_ids:
                if missile_id in self.active_missiles:
                    # 从活跃列表移除
                    self.active_missiles.remove(missile_id)
                    
                    # 停用导弹
                    if missile_id in self.missile_pool:
                        pool_item = self.missile_pool[missile_id]
                        pool_item.is_active = False
                        pool_item.current_launch_time = None
                        
                        # 放回可用列表
                        self.available_missiles.append(missile_id)
                        logger.debug(f"   ✅ 导弹释放成功: {missile_id}")
            
            logger.info(f"✅ 导弹释放完成，可用导弹: {len(self.available_missiles)}")
            
        except Exception as e:
            logger.error(f"❌ 释放导弹失败: {e}")
    
    def _generate_random_launch_position(self) -> Dict[str, float]:
        """生成随机发射位置"""
        return {
            "lat": random.uniform(30.0, 50.0),
            "lon": random.uniform(100.0, 140.0),
            "alt": 0.0
        }
    
    def _generate_random_target_position(self) -> Dict[str, float]:
        """生成随机目标位置"""
        return {
            "lat": random.uniform(35.0, 45.0),
            "lon": random.uniform(-125.0, -70.0),
            "alt": 0.0
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        total_requests = self.stats["pool_hits"] + self.stats["pool_misses"]
        hit_rate = (self.stats["pool_hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "pool_size": self.pool_size,
            "available_missiles": len(self.available_missiles),
            "active_missiles": len(self.active_missiles),
            "pool_hits": self.stats["pool_hits"],
            "pool_misses": self.stats["pool_misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "time_saved": f"{self.stats['creation_time_saved']:.1f}秒"
        }
    
    def cleanup(self) -> None:
        """清理导弹池"""
        try:
            logger.info("🧹 清理导弹池...")
            
            # 清理所有STK对象
            for missile_id in self.missile_pool:
                try:
                    self.stk_manager.scenario.Children.Unload(missile_id)
                except:
                    pass
            
            # 清理内部状态
            self.missile_pool.clear()
            self.active_missiles.clear()
            self.available_missiles.clear()
            
            logger.info("✅ 导弹池清理完成")
            
        except Exception as e:
            logger.error(f"❌ 导弹池清理失败: {e}")
