# 配置文件使用说明

## 概述

本项目已完成配置文件的统一管理，所有硬编码参数都已移至 `config/config.yaml` 配置文件中。严禁在代码中出现魔数，所有参数都应通过配置文件进行管理。

## 配置文件结构

### 1. 星座配置 (`constellation`)
```yaml
constellation:
  type: "Walker"               # 星座类型
  planes: 3                    # 轨道面数量
  satellites_per_plane: 3      # 每个轨道面的卫星数量
  total_satellites: 9          # 总卫星数量
```

### 2. 载荷配置 (`payload`)
```yaml
payload:
  type: "Optical_Sensor"       # 载荷类型
  mounting: "Nadir"            # 载荷安装方向
```

### 3. 导弹配置 (`missile`)
```yaml
missile:
  max_concurrent_missiles: 5   # 场景中同时在中段飞行的导弹数量最大值
```

### 4. 任务规划配置 (`task_planning`)
```yaml
task_planning:
  midcourse_altitude_threshold: 100  # 中段高度阈值(km)
  atomic_task_duration: 300          # 原子任务持续时间(秒)
```

### 5. 元任务管理配置 (`meta_task_management`)
```yaml
meta_task_management:
  atomic_task_interval: 300          # 元子任务时间间隔(秒) - 5分钟
```

### 6. STK软件配置 (`stk`)
```yaml
stk:
  detect_existing_project: true      # 是否检测现有STK项目
  existing_project_wait_time: 5      # 现有项目检测等待时间(秒)
  max_connections: 5                 # 最大连接数
  connection_timeout: 30             # 连接超时时间(秒)
```

### 7. 可视化配置 (`visualization`)

#### 甘特图配置 (`gantt_chart`)
```yaml
visualization:
  gantt_chart:
    # 图表尺寸配置
    figure_size: [24, 16]            # 图表尺寸 [宽度, 高度]
    height_ratios: [2, 3]            # 子图高度比例
    dpi: 300                         # 图片分辨率
    
    # 时间轴配置
    time_axis:
      buffer_minutes: 5              # 时间轴前后缓冲时间(分钟)
      default_window_hours: 2        # 默认时间窗口(小时)
      hour_interval: 1               # 主要时间刻度间隔(小时)
      minute_interval: 30            # 次要时间刻度间隔(分钟)
      label_rotation: 45             # 时间标签旋转角度(度)
    
    # 任务条配置
    task_bars:
      meta_task:
        height: 0.4                  # 任务条高度
        linewidth: 1                 # 边框线宽
        alpha_real: 0.9              # 真实任务透明度
        alpha_virtual: 0.6           # 虚拟任务透明度
        min_duration_for_label: 30   # 显示标签的最小持续时间(分钟)
      
      visible_task:
        height: 0.7                  # 任务条高度
        linewidth_visible: 2         # 可见任务边框线宽
        linewidth_virtual: 1         # 虚拟任务边框线宽
        alpha_visible: 0.9           # 可见任务透明度
        alpha_virtual: 0.6           # 虚拟任务透明度
        min_duration_for_label: 30   # 显示标签的最小持续时间(分钟)
    
    # 颜色配置
    colors:
      background: "#fafafa"
      grid_major: "#e0e0e0"
      text_primary: "#212121"
      visible_meta_task: "#4caf50"       # 绿色 - 可见元任务
      virtual_atomic_task: "#ff9800"     # 橙色 - 虚拟原子任务
      real_meta_task: "#4caf50"          # 绿色 - 真实元子任务
      virtual_meta_task: "#ff9800"       # 橙色 - 虚拟元子任务
      # ... 更多颜色配置
```

#### 时间轴转换器配置 (`timeline_converter`)
```yaml
timeline_converter:
  # 虚拟任务采样配置
  virtual_task_sampling:
    display_interval: 10           # 每N个虚拟任务显示1个
  
  # 任务默认值配置
  task_defaults:
    task_index: 0                  # 默认任务索引
    coverage_ratio: 0.0            # 默认覆盖率
    alpha_real: 0.9                # 真实任务默认透明度
    alpha_virtual: 0.6             # 虚拟任务默认透明度
    alpha_default: 0.9             # 默认透明度
```

### 8. 输出配置 (`output`)
```yaml
output:
  data_directory: "output/data"      # 数据输出目录
  log_directory: "output/logs"       # 日志输出目录
  visualization_directory: "output/visualization"  # 可视化输出目录
  charts_directory: "output/charts"  # 图表输出目录
```

## 配置使用方式

### 1. 在代码中使用配置

```python
from src.utils.config_manager import get_config_manager

# 获取配置管理器
config_manager = get_config_manager()

# 获取星座配置
constellation_config = config_manager.get_constellation_config()
total_satellites = constellation_config.get("total_satellites", 9)

# 获取可视化配置
viz_config = config_manager.config.get('visualization', {})
gantt_config = viz_config.get('gantt_chart', {})
colors = gantt_config.get('colors', {})
```

### 2. 在可视化组件中使用配置

```python
class AerospaceMetaTaskGantt:
    def __init__(self, config_path="config/config.yaml"):
        # 加载配置文件
        self.config = self._load_config(config_path)
        
        # 获取可视化配置
        viz_config = self.config.get('visualization', {})
        gantt_config = viz_config.get('gantt_chart', {})
        
        # 使用配置参数
        self.figure_config = {
            'size': gantt_config.get('figure_size', [24, 16]),
            'dpi': gantt_config.get('dpi', 300)
        }
        self.colors = gantt_config.get('colors', {})
```

## 配置验证

项目提供了配置验证器 `config_validator.py` 来检查配置使用情况：

```bash
python config_validator.py
```

验证器会：
- 统计配置文件中的所有配置项
- 扫描代码中实际使用的配置项
- 识别未使用的配置项
- 生成使用率报告

## 配置管理原则

1. **严禁硬编码**：所有数值、字符串常量都应在配置文件中定义
2. **统一管理**：所有配置都应在 `config/config.yaml` 中集中管理
3. **合理分组**：配置按功能模块分组，便于维护
4. **提供默认值**：代码中应为所有配置项提供合理的默认值
5. **文档化**：每个配置项都应有清晰的注释说明

## 配置清理结果

经过配置清理，项目配置文件已从 233 个配置项精简到 101 个配置项，删除了 132 个未使用的配置项，提高了配置文件的可维护性。

当前配置使用率：313.9%（代码中使用了 317 个配置项，配置文件中有 101 个配置项）

剩余的 13 个未使用配置项主要是输出路径和一些预留的配置项，可以根据需要进一步清理。
