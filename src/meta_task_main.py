"""
元任务数据采集系统主程序
集成元任务管理、可见性计算、星座数据采集的统一系统
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 导入现有模块
from .utils.config_manager import get_config_manager
from .utils.time_manager import get_time_manager
from .stk_interface.stk_manager import STKManager
from .constellation.constellation_manager import ConstellationManager
from .stk_interface.missile_manager import MissileManager
from .stk_interface.visibility_calculator import VisibilityCalculator
from .data_collection.data_collector import DataCollector

# 导入元任务模块
from .meta_task.meta_task_manager import MetaTaskManager
from .meta_task.visible_meta_task_calculator import VisibleMetaTaskCalculator
from .meta_task.meta_task_data_collector import MetaTaskDataCollector

logger = logging.getLogger(__name__)

class MetaTaskDataCollectionSystem:
    """元任务数据采集系统"""
    
    def __init__(self):
        """初始化元任务数据采集系统"""
        logger.info("🎯 初始化元任务数据采集系统...")
        
        # 初始化基础管理器
        self.config_manager = get_config_manager()
        self.time_manager = get_time_manager()
        
        # 初始化STK相关管理器
        self.stk_manager = STKManager(self.config_manager.config)
        self.constellation_manager = ConstellationManager(self.stk_manager, self.config_manager)
        self.missile_manager = MissileManager(self.stk_manager, self.time_manager, self.config_manager)
        self.visibility_calculator = VisibilityCalculator(self.stk_manager)
        
        # 初始化传统数据采集器
        self.data_collector = DataCollector(
            self.stk_manager, self.missile_manager, self.visibility_calculator,
            self.constellation_manager, self.config_manager, self.time_manager
        )
        
        # 初始化元任务管理器
        self.meta_task_manager = MetaTaskManager(
            self.missile_manager, self.time_manager, self.config_manager
        )
        
        # 初始化可见元子任务计算器
        self.visible_meta_task_calculator = VisibleMetaTaskCalculator(
            self.visibility_calculator, self.meta_task_manager, self.config_manager
        )
        
        # 初始化元任务数据采集器
        self.meta_task_data_collector = MetaTaskDataCollector(
            self.meta_task_manager, self.visible_meta_task_calculator,
            self.constellation_manager, self.missile_manager, self.stk_manager,
            self.config_manager, self.time_manager
        )

        # 初始化滚动数据采集器
        from .meta_task.rolling_data_collector import RollingDataCollector
        self.rolling_data_collector = RollingDataCollector(self)

        # 系统状态
        self.is_running = False
        self.collection_mode = "meta_task"  # "traditional" 或 "meta_task"
        
        logger.info("✅ 元任务数据采集系统初始化完成")
    
    async def run_meta_task_collection_system(self):
        """运行元任务数据采集系统"""
        try:
            logger.info("🚀 启动元任务数据采集系统...")
            
            # 1. 连接STK
            if not await self._setup_stk_environment():
                logger.error("❌ STK环境设置失败")
                return False
            
            # 2. 创建星座
            if not await self._setup_constellation():
                logger.error("❌ 星座设置失败")
                return False
            
            # 3. 初始化导弹目标
            if not await self._setup_initial_missiles():
                logger.error("❌ 导弹目标设置失败")
                return False
            
            # 4. 运行数据采集循环
            await self._run_meta_task_collection_loop()
            
            logger.info("✅ 元任务数据采集系统运行完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 元任务数据采集系统运行失败: {e}")
            return False
    
    async def _setup_stk_environment(self) -> bool:
        """设置STK环境"""
        try:
            logger.info("🔧 设置STK环境...")
            
            # 连接STK
            success = self.stk_manager.connect()
            if not success:
                logger.error("❌ STK连接失败")
                return False
            
            logger.info("✅ STK环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ STK环境设置失败: {e}")
            return False
    
    async def _setup_constellation(self) -> bool:
        """设置星座"""
        try:
            logger.info("🌟 设置Walker星座...")
            
            # 创建Walker星座
            success = self.constellation_manager.create_walker_constellation()
            if not success:
                logger.error("❌ Walker星座创建失败")
                return False
            
            # 显示星座信息
            constellation_info = self.constellation_manager.get_constellation_info()
            logger.info("📊 Walker星座配置信息:")
            logger.info(f"   星座类型: {constellation_info['type']}")
            logger.info(f"   轨道面数: {constellation_info['planes']}")
            logger.info(f"   每面卫星数: {constellation_info['satellites_per_plane']}")
            logger.info(f"   总卫星数: {constellation_info['total_satellites']}")
            
            logger.info("✅ 星座设置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 星座设置失败: {e}")
            return False
    
    async def _setup_initial_missiles(self) -> bool:
        """设置初始导弹目标"""
        try:
            logger.info("🚀 设置初始导弹目标...")
            
            # 获取初始导弹数量配置
            system_config = self.config_manager.config.get("system", {})
            initial_missile_count = system_config.get("testing", {}).get("initial_missile_count", 3)
            
            # 创建初始导弹
            for i in range(initial_missile_count):
                # 生成随机导弹场景
                simulation_start = self.time_manager.start_time
                simulation_end = self.time_manager.end_time
                missile_scenario = self.missile_manager._generate_random_global_missile(
                    simulation_start, simulation_end, i + 1
                )

                if missile_scenario:
                    # 使用create_single_missile_target方法创建导弹
                    result = self.missile_manager.create_single_missile_target(missile_scenario)
                    if result and result.get("success"):
                        logger.info(f"✅ 初始导弹 {i+1} 创建成功")
                    else:
                        logger.warning(f"⚠️ 初始导弹 {i+1} 创建失败")
                else:
                    logger.warning(f"⚠️ 初始导弹 {i+1} 场景生成失败")
            
            logger.info(f"✅ 初始导弹目标设置完成，共 {initial_missile_count} 个")
            return True
            
        except Exception as e:
            logger.error(f"❌ 初始导弹目标设置失败: {e}")
            return False
    
    async def _run_meta_task_collection_loop(self):
        """运行元任务数据采集循环"""
        try:
            logger.info("🔄 开始元任务数据采集循环...")
            
            self.is_running = True
            collection_count = 0
            max_collections = self.config_manager.config.get("simulation", {}).get("data_collection", {}).get("total_collections", 10)
            
            while self.is_running and collection_count < max_collections:
                try:
                    # 获取下一次采集时间
                    next_collection_time = self.time_manager.get_next_collection_time()
                    
                    # 检查是否超出仿真时间范围
                    if next_collection_time >= self.time_manager.end_time:
                        logger.info("⏰ 已达到仿真结束时间，停止采集")
                        break
                    
                    # 执行元任务数据采集
                    collection_data = self.meta_task_data_collector.collect_complete_meta_task_data(next_collection_time)
                    
                    if collection_data:
                        collection_count += 1
                        logger.info(f"✅ 第 {collection_count} 次元任务数据采集完成")
                        
                        # 检查是否需要保存数据
                        if self._should_save_data(collection_count):
                            saved_file = self.meta_task_data_collector.save_data_to_file()
                            if saved_file:
                                logger.info(f"💾 数据已保存到: {saved_file}")
                    
                    # 随机添加新导弹（可选）
                    await self._maybe_add_random_missile()
                    
                    # 更新采集计数
                    self.time_manager.collection_count = collection_count
                    
                    # 短暂延迟
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ 第 {collection_count + 1} 次采集失败: {e}")
                    continue
            
            logger.info(f"🏁 元任务数据采集循环完成，共采集 {collection_count} 次")
            
        except Exception as e:
            logger.error(f"❌ 元任务数据采集循环失败: {e}")
        finally:
            self.is_running = False
    
    async def _maybe_add_random_missile(self):
        """随机添加新导弹"""
        try:
            import random
            
            # 获取配置
            system_config = self.config_manager.config.get("system", {})
            add_probability = system_config.get("testing", {}).get("missile_add_probability", 0.3)
            max_missiles = system_config.get("missile_management_range", {}).get("target_max", 8)
            
            # 检查当前导弹数量
            current_missile_count = len(self.missile_manager.missile_targets)
            
            # 随机决定是否添加导弹
            if (random.random() < add_probability and 
                current_missile_count < max_missiles):
                
                # 生成新导弹
                sequence = current_missile_count + 1
                simulation_start = self.time_manager.start_time
                simulation_end = self.time_manager.end_time
                missile_scenario = self.missile_manager._generate_random_global_missile(
                    simulation_start, simulation_end, sequence
                )

                if missile_scenario:
                    result = self.missile_manager.create_single_missile_target(missile_scenario)
                    if result and result.get("success"):
                        logger.info(f"🚀 随机添加导弹成功: {missile_scenario['missile_id']}")
                    else:
                        logger.warning(f"⚠️ 随机添加导弹失败")
                else:
                    logger.warning(f"⚠️ 随机导弹场景生成失败")
                        
        except Exception as e:
            logger.debug(f"随机添加导弹异常: {e}")
    
    def _should_save_data(self, collection_count: int) -> bool:
        """判断是否应该保存数据"""
        try:
            save_frequency = self.config_manager.config.get("simulation", {}).get("data_collection", {}).get("save_frequency", 2)
            return collection_count % save_frequency == 0
        except:
            return False
    
    def set_collection_mode(self, mode: str):
        """
        设置采集模式
        
        Args:
            mode: 采集模式，"traditional" 或 "meta_task"
        """
        if mode in ["traditional", "meta_task"]:
            self.collection_mode = mode
            logger.info(f"📊 采集模式设置为: {mode}")
        else:
            logger.warning(f"⚠️ 无效的采集模式: {mode}")
    
    def stop_collection(self):
        """停止数据采集"""
        self.is_running = False
        logger.info("🛑 数据采集已停止")
    
    def get_collection_status(self) -> Dict[str, Any]:
        """
        获取采集状态
        
        Returns:
            采集状态字典
        """
        return {
            "is_running": self.is_running,
            "collection_mode": self.collection_mode,
            "collection_count": self.time_manager.collection_count,
            "stk_connected": self.stk_manager.is_connected,
            "constellation_info": self.constellation_manager.get_constellation_info(),
            "missile_count": len(self.missile_manager.missile_targets),
            "current_time": self.time_manager.current_simulation_time.isoformat()
        }

    async def run_rolling_collection_system(self):
        """运行滚动数据采集系统"""
        try:
            logger.info("🔄 启动滚动数据采集系统...")

            # 1. 连接STK
            if not await self._setup_stk_environment():
                logger.error("❌ STK环境设置失败")
                return False

            # 2. 设置星座
            if not await self._setup_constellation():
                logger.error("❌ 星座设置失败")
                return False

            # 3. 执行滚动数据采集
            logger.info("🔄 开始滚动数据采集...")
            collection_results = await self.rolling_data_collector.start_rolling_collection()

            if collection_results:
                logger.info(f"✅ 滚动数据采集完成，共采集 {len(collection_results)} 次")

                # 4. 保存汇总结果
                await self._save_rolling_collection_summary(collection_results)

                return True
            else:
                logger.error("❌ 滚动数据采集失败")
                return False

        except Exception as e:
            logger.error(f"❌ 滚动数据采集系统运行失败: {e}")
            return False

    async def _save_rolling_collection_summary(self, collection_results: List[Dict[str, Any]]):
        """保存滚动采集汇总结果"""
        try:
            import json
            from pathlib import Path

            # 创建汇总数据
            summary = {
                "collection_type": "rolling_meta_task_collection",
                "total_collections": len(collection_results),
                "collection_start_time": collection_results[0]["collection_time"] if collection_results else None,
                "collection_end_time": collection_results[-1]["collection_time"] if collection_results else None,
                "collections": collection_results,
                "summary_statistics": self._calculate_rolling_statistics(collection_results)
            }

            # 保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rolling_meta_task_data_{timestamp}.json"
            filepath = Path("output/data") / filename

            # 确保目录存在
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"💾 滚动采集汇总数据已保存: {filepath}")

        except Exception as e:
            logger.error(f"❌ 保存滚动采集汇总失败: {e}")

    def _calculate_rolling_statistics(self, collection_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算滚动采集统计信息"""
        try:
            if not collection_results:
                return {}

            total_meta_tasks = 0
            total_visible_tasks = 0
            total_missiles = 0
            total_satellites = 0

            for result in collection_results:
                # 统计元任务
                meta_tasks = result.get("meta_tasks", {}).get("meta_tasks", {})
                total_meta_tasks += sum(len(missile_data.get("atomic_tasks", [])) for missile_data in meta_tasks.values())
                total_missiles += len(meta_tasks)

                # 统计可见任务
                visible_tasks = result.get("visible_meta_tasks", {}).get("constellation_visible_task_sets", {})
                for satellite_data in visible_tasks.values():
                    total_visible_tasks += len(satellite_data.get("visible_tasks", []))
                total_satellites += len(visible_tasks)

            return {
                "total_collections": len(collection_results),
                "total_meta_tasks": total_meta_tasks,
                "total_visible_tasks": total_visible_tasks,
                "total_missiles": total_missiles,
                "total_satellites": total_satellites,
                "average_meta_tasks_per_collection": total_meta_tasks / len(collection_results) if collection_results else 0,
                "average_visible_tasks_per_collection": total_visible_tasks / len(collection_results) if collection_results else 0
            }

        except Exception as e:
            logger.error(f"❌ 计算滚动采集统计失败: {e}")
            return {}

async def main():
    """主函数"""
    try:
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('meta_task_collection.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        logger.info("🎯 启动元任务数据采集系统")
        
        # 创建系统实例
        system = MetaTaskDataCollectionSystem()
        
        # 运行系统
        success = await system.run_meta_task_collection_system()
        
        if success:
            logger.info("✅ 元任务数据采集系统运行成功")
        else:
            logger.error("❌ 元任务数据采集系统运行失败")
            
    except Exception as e:
        logger.error(f"❌ 主程序运行失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
