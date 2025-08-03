# STK卫星星座数据采集系统

基于STK软件结合Python代码进行卫星星座数据生成的项目，严格按照ADK官网文档要求实现。

## 项目概述

本项目是一个航天领域STK轨道仿真与任务规划软件专家系统，用于基于大模型强化学习（RLHF）场景下的数据集采集工作。

### 主要功能

1. **Walker星座创建与配置**
   - 支持多轨道面Walker星座
   - 精确的轨道参数计算
   - 载荷传感器配置

2. **导弹目标管理**
   - 随机生成全球发射和落点位置
   - 弹道轨迹计算
   - 动态导弹数量控制

3. **数据采集系统**
   - 卫星位置和姿态数据
   - 载荷参数采集
   - 导弹轨迹信息
   - 可见性时间窗口计算

4. **统一时间管理**
   - 严格使用仿真时间
   - 禁止系统时间依赖
   - 随机时间间隔生成

## 系统架构

```
├── main.py                 # 主程序入口
├── config/
│   └── config.yaml        # 统一配置文件
├── src/
│   ├── utils/             # 工具模块
│   │   ├── config_manager.py    # 配置管理器
│   │   └── time_manager.py      # 时间管理器
│   ├── stk_interface/     # STK接口模块
│   │   ├── stk_manager.py       # STK管理器
│   │   ├── missile_manager.py   # 导弹管理器
│   │   └── visibility_calculator.py  # 可见性计算器
│   ├── constellation/     # 星座管理模块
│   │   └── constellation_manager.py  # 星座管理器
│   └── data_collection/   # 数据采集模块
│       └── data_collector.py    # 数据采集器
└── output/               # 输出目录
    ├── data/            # 数据文件
    ├── logs/            # 日志文件
    └── visualization/   # 可视化文件
```

## 配置说明

### Walker星座配置
```yaml
constellation:
  type: "Walker"
  planes: 3                    # 轨道面数量
  satellites_per_plane: 3      # 每个轨道面的卫星数量
  total_satellites: 9          # 总卫星数量
  reference_satellite:
    altitude: 1800             # 轨道高度(km)
    inclination: 51.856        # 轨道倾角(度)
    eccentricity: 0.0          # 轨道偏心率
    arg_of_perigee: 12         # 近地点幅角(度)
    raan_offset: 24            # 升交点赤经偏移(度)
    mean_anomaly_offset: 180   # 平近点角偏移(度)
```

### 载荷配置
```yaml
payload:
  type: "Optical_Sensor"
  mounting: "Nadir"            # 载荷安装方向：天底方向
  sensor_pattern: "Conic"      # 传感器模式：锥形
  inner_cone_half_angle: 66.1  # 内锥半角(度)
  outer_cone_half_angle: 85.0  # 外锥半角(度)
  pointing:
    azimuth: 0.0              # 指向方位角(度)
    elevation: 90.0           # 指向俯仰角(度)
  constraints_range:
    min_range: 0              # 最小距离(km)
    max_range: 5000           # 最大距离(km)
```

### 导弹配置
```yaml
missile:
  max_concurrent_missiles: 5   # 同时在飞行的导弹数量阈值
  launch_interval_range: [300, 1800]  # 发射时间间隔范围(秒)
  global_launch_positions:
    lat_range: [-60, 60]      # 发射位置纬度范围
    lon_range: [-180, 180]    # 发射位置经度范围
  global_target_positions:
    lat_range: [-60, 60]      # 目标位置纬度范围
    lon_range: [-180, 180]    # 目标位置经度范围
```

## 安装和运行

### 环境要求
- Windows操作系统
- STK 12软件
- Python 3.8+

### 安装步骤

1. 克隆项目
```bash
git clone <repository_url>
cd data-generate
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置STK
   - 确保STK 12已安装并可正常运行
   - 检查COM接口可用性

4. 运行系统
```bash
python main.py
```

## 数据采集流程

1. **建立STK仿真场景**
   - 连接STK软件
   - 创建或检测现有场景

2. **初始化仿真时间**
   - 设置开始和结束时刻
   - 配置统一时间管理器

3. **创建Walker星座**
   - 根据配置创建卫星
   - 配置载荷传感器

4. **数据采集循环**
   - 随机时间间隔采集数据
   - 随机添加导弹目标
   - 计算可见性时间窗口
   - 定期保存数据

5. **数据输出**
   - JSON格式保存
   - 文件名包含时间段信息
   - 每10次采集保存一次

## 输出数据格式

```json
{
  "metadata": {
    "collection_start_time": "2025-07-26T04:00:00",
    "collection_end_time": "2025-07-26T08:00:00",
    "total_collections": 50,
    "constellation_info": {...},
    "simulation_config": {...}
  },
  "data_snapshots": [
    {
      "collection_time": "2025-07-26T04:05:30",
      "simulation_progress": 2.3,
      "satellites": [...],
      "missiles": [...],
      "visibility": [...]
    }
  ]
}
```

## 注意事项

1. **时间管理**
   - 严格禁止使用系统时间
   - 必须使用配置的仿真时间
   - 通过偏移量计算使用时刻

2. **STK连接**
   - 确保STK软件正常运行
   - 检查COM接口权限
   - 处理连接异常情况

3. **数据质量**
   - 验证轨道参数合理性
   - 检查可见性计算结果
   - 监控数据采集状态

## 参考资料

- STK官方文档
- ADK官网文档
- 参考项目：https://github.com/dinglinghu/icbm_warning

## 许可证

本项目遵循相关开源许可证。
