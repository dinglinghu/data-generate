#!/usr/bin/env python3
"""
利用已采集的星座位置数据为可见子元任务添加卫星位置信息
充分利用constellation_data中的卫星位置数据
"""

import logging
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExistingDataEnhancer:
    """已有数据增强器"""
    
    def __init__(self):
        self.enhancement_stats = {
            "files_processed": 0,
            "tasks_enhanced": 0,
            "satellites_matched": 0,
            "geometric_analyses_added": 0
        }
    
    def enhance_all_collection_files(self):
        """增强所有采集文件"""
        logger.info("🚀 开始增强所有采集文件的卫星位置数据...")
        
        # 查找所有采集数据文件
        output_dir = Path("output/unified_collections")
        
        if not output_dir.exists():
            logger.error("❌ 输出目录不存在")
            return
        
        # 查找所有会话目录
        session_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
        
        for session_dir in session_dirs:
            logger.info(f"📁 处理会话: {session_dir.name}")
            self._enhance_session_files(session_dir)
        
        # 显示增强统计
        self._display_enhancement_stats()
    
    def _enhance_session_files(self, session_dir: Path):
        """增强单个会话的文件"""
        json_dir = session_dir / "json_data"
        
        if not json_dir.exists():
            logger.warning(f"⚠️ JSON数据目录不存在: {session_dir.name}")
            return
        
        # 查找原始数据文件（包含完整数据结构）
        original_files = list(json_dir.glob("*_original.json"))
        
        for original_file in original_files:
            logger.info(f"📊 增强文件: {original_file.name}")
            self._enhance_single_file(original_file)
    
    def _enhance_single_file(self, file_path: Path):
        """增强单个文件"""
        try:
            # 读取原始数据
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查数据结构
            if not self._validate_data_structure(data):
                logger.warning(f"⚠️ 文件数据结构不完整: {file_path.name}")
                return
            
            # 执行增强
            enhanced_data = self._enhance_data_with_satellite_positions(data)
            
            if enhanced_data:
                # 保存增强后的数据
                enhanced_file_path = file_path.parent / f"{file_path.stem}_enhanced.json"
                with open(enhanced_file_path, 'w', encoding='utf-8') as f:
                    json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ 增强完成: {enhanced_file_path.name}")
                self.enhancement_stats["files_processed"] += 1
            else:
                logger.warning(f"⚠️ 文件增强失败: {file_path.name}")
                
        except Exception as e:
            logger.error(f"❌ 处理文件失败 {file_path.name}: {e}")
    
    def _validate_data_structure(self, data: Dict[str, Any]) -> bool:
        """验证数据结构完整性"""
        required_keys = ["constellation_data", "visible_meta_tasks"]
        
        for key in required_keys:
            if key not in data:
                return False
        
        # 检查constellation_data结构
        constellation_data = data.get("constellation_data", {})
        if "satellites" not in constellation_data:
            return False
        
        # 检查visible_meta_tasks结构
        visible_meta_tasks = data.get("visible_meta_tasks", {})
        if "constellation_visible_task_sets" not in visible_meta_tasks:
            return False
        
        return True
    
    def _enhance_data_with_satellite_positions(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """为数据添加卫星位置信息"""
        try:
            # 创建数据副本
            enhanced_data = data.copy()
            
            # 提取卫星位置数据
            satellite_positions = self._extract_satellite_positions(data["constellation_data"])
            
            if not satellite_positions:
                logger.warning("⚠️ 没有找到卫星位置数据")
                return None
            
            # 增强可见元任务
            enhanced_visible_tasks = self._enhance_visible_meta_tasks(
                data["visible_meta_tasks"], satellite_positions, data.get("collection_time")
            )
            
            enhanced_data["visible_meta_tasks"] = enhanced_visible_tasks
            
            # 添加增强元数据
            enhanced_data["enhancement_metadata"] = {
                "enhancement_time": datetime.now().isoformat(),
                "enhancement_version": "v1.0",
                "satellite_positions_added": True,
                "geometric_analysis_added": True,
                "enhancement_source": "existing_constellation_data"
            }
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"❌ 数据增强失败: {e}")
            return None
    
    def _extract_satellite_positions(self, constellation_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """提取卫星位置数据"""
        satellite_positions = {}
        
        satellites = constellation_data.get("satellites", [])
        
        for satellite_info in satellites:
            satellite_id = satellite_info.get("satellite_id")
            position = satellite_info.get("position")
            
            if satellite_id and position:
                satellite_positions[satellite_id] = {
                    "position": position,
                    "payload_status": satellite_info.get("payload_status", {}),
                    "data_quality": satellite_info.get("data_quality", "unknown")
                }
        
        logger.info(f"📊 提取到 {len(satellite_positions)} 个卫星的位置数据")
        return satellite_positions
    
    def _enhance_visible_meta_tasks(self, visible_meta_tasks: Dict[str, Any], 
                                  satellite_positions: Dict[str, Dict[str, Any]],
                                  collection_time: str) -> Dict[str, Any]:
        """增强可见元任务数据"""
        enhanced_tasks = visible_meta_tasks.copy()
        
        constellation_task_sets = enhanced_tasks.get("constellation_visible_task_sets", {})
        
        for satellite_id, satellite_data in constellation_task_sets.items():
            # 获取对应的卫星位置数据
            satellite_position_data = satellite_positions.get(satellite_id)
            
            if not satellite_position_data:
                logger.debug(f"⚠️ 未找到卫星 {satellite_id} 的位置数据")
                continue
            
            self.enhancement_stats["satellites_matched"] += 1
            
            # 增强该卫星的所有可见任务
            missile_tasks = satellite_data.get("missile_tasks", {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get("visible_tasks", [])
                
                enhanced_visible_tasks = []
                
                for task in visible_tasks:
                    enhanced_task = self._enhance_single_visible_task(
                        task, satellite_id, satellite_position_data, collection_time
                    )
                    enhanced_visible_tasks.append(enhanced_task)
                    self.enhancement_stats["tasks_enhanced"] += 1
                
                missile_data["visible_tasks"] = enhanced_visible_tasks
        
        return enhanced_tasks
    
    def _enhance_single_visible_task(self, task: Dict[str, Any], satellite_id: str,
                                   satellite_position_data: Dict[str, Any],
                                   collection_time: str) -> Dict[str, Any]:
        """增强单个可见任务"""
        enhanced_task = task.copy()
        
        # 添加卫星位置信息
        satellite_position = {
            "satellite_id": satellite_id,
            "position_data": satellite_position_data["position"],
            "payload_status": satellite_position_data["payload_status"],
            "data_quality": satellite_position_data["data_quality"],
            "position_timestamp": satellite_position_data["position"].get("time"),
            "enhancement_source": "constellation_data"
        }
        
        # 添加任务时间信息
        if "start_time" in task and "end_time" in task:
            satellite_position["task_time_span"] = {
                "start_time": task["start_time"],
                "end_time": task["end_time"],
                "collection_time": collection_time
            }
        
        # 计算几何分析（如果有导弹位置数据）
        missile_position = task.get("missile_position")
        if missile_position:
            geometric_analysis = self._calculate_geometric_analysis(
                satellite_position_data["position"], missile_position
            )
            if geometric_analysis:
                satellite_position["geometric_analysis"] = geometric_analysis
                self.enhancement_stats["geometric_analyses_added"] += 1
        
        enhanced_task["satellite_position"] = satellite_position
        
        return enhanced_task
    
    def _calculate_geometric_analysis(self, satellite_position: Dict[str, Any],
                                    missile_position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """计算卫星-导弹几何分析"""
        try:
            # 提取卫星坐标（笛卡尔坐标）
            sat_x = satellite_position.get("x", 0)
            sat_y = satellite_position.get("y", 0)
            sat_z = satellite_position.get("z", 0)
            
            # 提取导弹坐标（从start_position）
            missile_start = missile_position.get("start_position", {}).get("position", {})
            
            # 尝试不同的坐标格式
            missile_coords = None
            
            if "latitude" in missile_start and "longitude" in missile_start:
                # 地理坐标转换为笛卡尔坐标（简化）
                lat = math.radians(missile_start["latitude"])
                lon = math.radians(missile_start["longitude"])
                alt = missile_start.get("altitude", 0) * 1000  # 转换为米
                
                # 简化的地理坐标到笛卡尔坐标转换
                earth_radius = 6371000  # 地球半径（米）
                r = earth_radius + alt
                
                missile_x = r * math.cos(lat) * math.cos(lon)
                missile_y = r * math.cos(lat) * math.sin(lon)
                missile_z = r * math.sin(lat)
                
                missile_coords = (missile_x / 1000, missile_y / 1000, missile_z / 1000)  # 转换为km
                
            elif "x" in missile_start and "y" in missile_start and "z" in missile_start:
                # 直接使用笛卡尔坐标
                missile_coords = (missile_start["x"], missile_start["y"], missile_start["z"])
            
            if not missile_coords:
                return None
            
            missile_x, missile_y, missile_z = missile_coords
            
            # 计算距离
            dx = sat_x - missile_x
            dy = sat_y - missile_y
            dz = sat_z - missile_z
            
            distance_km = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # 计算角度（简化计算）
            # 仰角：从导弹到卫星的仰角
            horizontal_distance = math.sqrt(dx**2 + dy**2)
            elevation_angle = math.degrees(math.atan2(dz, horizontal_distance))
            
            # 方位角：从导弹到卫星的方位角
            azimuth_angle = math.degrees(math.atan2(dy, dx))
            if azimuth_angle < 0:
                azimuth_angle += 360
            
            geometric_analysis = {
                "range_km": round(distance_km, 2),
                "elevation_angle_deg": round(elevation_angle, 2),
                "azimuth_angle_deg": round(azimuth_angle, 2),
                "calculation_method": "cartesian_coordinates",
                "satellite_position_km": {
                    "x": round(sat_x, 2),
                    "y": round(sat_y, 2),
                    "z": round(sat_z, 2)
                },
                "missile_position_km": {
                    "x": round(missile_x, 2),
                    "y": round(missile_y, 2),
                    "z": round(missile_z, 2)
                }
            }
            
            return geometric_analysis
            
        except Exception as e:
            logger.debug(f"⚠️ 几何分析计算失败: {e}")
            return None
    
    def _display_enhancement_stats(self):
        """显示增强统计信息"""
        stats = self.enhancement_stats
        
        print("\n" + "="*80)
        print("📊 数据增强统计报告")
        print("="*80)
        print(f"处理文件数: {stats['files_processed']}")
        print(f"增强任务数: {stats['tasks_enhanced']}")
        print(f"匹配卫星数: {stats['satellites_matched']}")
        print(f"几何分析数: {stats['geometric_analyses_added']}")
        print("="*80)

def analyze_enhanced_data():
    """分析增强后的数据"""
    logger.info("🔍 分析增强后的数据...")
    
    # 查找增强后的文件
    output_dir = Path("output/unified_collections")
    enhanced_files = []
    
    for session_dir in output_dir.iterdir():
        if session_dir.is_dir():
            json_dir = session_dir / "json_data"
            if json_dir.exists():
                enhanced_files.extend(json_dir.glob("*_enhanced.json"))
    
    if not enhanced_files:
        logger.warning("⚠️ 没有找到增强后的文件")
        return
    
    print(f"\n📋 增强数据分析报告:")
    print("="*60)
    
    total_enhanced_tasks = 0
    total_geometric_analyses = 0
    
    for enhanced_file in enhanced_files:
        try:
            with open(enhanced_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 分析增强效果
            file_stats = analyze_single_enhanced_file(data, enhanced_file.name)
            
            total_enhanced_tasks += file_stats["enhanced_tasks"]
            total_geometric_analyses += file_stats["geometric_analyses"]
            
            print(f"\n📁 {enhanced_file.name}:")
            print(f"   增强任务: {file_stats['enhanced_tasks']}")
            print(f"   几何分析: {file_stats['geometric_analyses']}")
            print(f"   卫星覆盖: {file_stats['satellites_with_data']}")
            
        except Exception as e:
            logger.error(f"❌ 分析文件失败 {enhanced_file.name}: {e}")
    
    print(f"\n📊 总计:")
    print(f"   总增强任务: {total_enhanced_tasks}")
    print(f"   总几何分析: {total_geometric_analyses}")
    print("="*60)

def analyze_single_enhanced_file(data: Dict[str, Any], filename: str) -> Dict[str, int]:
    """分析单个增强文件"""
    stats = {
        "enhanced_tasks": 0,
        "geometric_analyses": 0,
        "satellites_with_data": 0
    }
    
    visible_meta_tasks = data.get("visible_meta_tasks", {})
    constellation_task_sets = visible_meta_tasks.get("constellation_visible_task_sets", {})
    
    for satellite_id, satellite_data in constellation_task_sets.items():
        satellite_has_enhanced_data = False
        missile_tasks = satellite_data.get("missile_tasks", {})
        
        for missile_id, missile_data in missile_tasks.items():
            visible_tasks = missile_data.get("visible_tasks", [])
            
            for task in visible_tasks:
                if "satellite_position" in task:
                    stats["enhanced_tasks"] += 1
                    satellite_has_enhanced_data = True
                    
                    if "geometric_analysis" in task["satellite_position"]:
                        stats["geometric_analyses"] += 1
        
        if satellite_has_enhanced_data:
            stats["satellites_with_data"] += 1
    
    return stats

def main():
    """主函数"""
    print("="*80)
    print("🛰️ 利用已有数据增强可见子元任务的卫星位置信息")
    print("="*80)
    
    # 创建增强器
    enhancer = ExistingDataEnhancer()
    
    # 增强所有文件
    enhancer.enhance_all_collection_files()
    
    # 分析增强结果
    analyze_enhanced_data()
    
    print("\n✅ 数据增强完成！")
    print("💡 增强后的文件保存为 *_enhanced.json")

if __name__ == "__main__":
    main()
