# 6TiSCH 多网络并行组网模拟器扩展

## 概述

本扩展在原有的6TiSCH模拟器基础上增加了对多网络并行组网的支持，能够模拟多个6TiSCH网络同时运行并相互干扰的情况。

## 主要特性

### 1. 多网络并行模拟
- 支持同时运行多个独立的6TiSCH网络
- 每个网络有独立的节点集合和配置
- 网络间可以有时间偏移（ASN偏移）

### 2. 精细时间粒度
- 支持纳秒级时间精度（默认1ms）
- 比原有slot级别更精细的时间控制
- 支持精确时间调度事件

### 3. 跨网络干扰模拟
- 自动检测网络间频道冲突
- 动态调整受干扰频道的PDR
- 可配置干扰惩罚系数

### 4. 向后兼容
- 完全兼容原有的单网络模拟
- 现有配置文件无需修改即可运行

## 架构设计

### 核心组件

#### MultiNetworkEngine
多网络模拟引擎的核心类，继承自原有的`DiscreteEventEngine`。

**主要方法：**
- `add_network()`: 添加新的网络实例
- `schedule_at_precise_time()`: 精确时间调度
- `run()`: 运行多网络模拟

#### NetworkInstance
表示单个6TiSCH网络实例。

**属性：**
- `network_id`: 网络唯一标识
- `asn_offset`: ASN时间偏移
- `motes`: 网络中的节点列表
- `connectivity`: 网络的连接性模型

### 时间管理

#### 全局时间 vs 本地时间
- **全局时间**: 整个模拟器的纳秒级时间戳
- **本地时间**: 每个网络相对于自己起始时间的ASN

#### 时间转换
```python
# 全局ASN -> 网络本地ASN
local_asn = network.get_local_asn(global_asn)

# 网络本地ASN -> 全局ASN
global_asn = network.get_global_asn(local_asn)
```

### 干扰模型

#### 干扰检测
系统自动检测哪些频道被多个网络同时使用：

```python
def _check_cross_network_interference(self, network_id, local_asn):
    interference_channels = set()
    for channel, using_networks in self.network_channels.items():
        if network_id in using_networks and len(using_networks) > 1:
            # 检查其他网络是否同时活跃
            for other_net_id in using_networks:
                if other_net_id != network_id:
                    # 计算时间同步窗口
                    if abs(other_local_asn - local_asn) < 2:
                        interference_channels.add(channel)
    return interference_channels
```

#### 干扰惩罚
受干扰的频道PDR会按比例降低：

```python
interference_penalty = 0.3  # 30% PDR降低
new_pdr = current_pdr * (1 - interference_penalty)
```

## 配置参数

### 多网络配置

```json
{
    "settings": {
        "regular": {
            "multi_num_networks": 2,
            "multi_network_spacing_slots": 100,
            "multi_interference_penalty": 0.3,
            "time_resolution_ns": 1000000,
            "net_0_num_motes": 10,
            "net_1_num_motes": 10
        }
    }
}
```

**参数说明：**
- `multi_num_networks`: 网络数量
- `multi_network_spacing_slots`: 网络间时间间隔（slots）
- `multi_interference_penalty`: 干扰惩罚系数（0-1）
- `time_resolution_ns`: 时间分辨率（纳秒）
- `net_X_num_motes`: 第X个网络的节点数

### 组合参数
支持以下参数的组合测试：
- `multi_num_networks`: [2, 3, 4]
- `multi_network_spacing_slots`: [50, 100, 200]

## 使用方法

### 1. 配置文件
创建多网络配置文件 `config_multi_network.json`：

```json
{
    "version": 0,
    "execution": {
        "numCPUs": 1,
        "numRuns": 10
    },
    "settings": {
        "combination": {
            "multi_num_networks": [2, 3],
            "multi_network_spacing_slots": [50, 100, 200]
        },
        "regular": {
            "exec_numMotes": 20,
            "multi_num_networks": 2,
            "multi_network_spacing_slots": 100,
            "multi_interference_penalty": 0.3,
            "time_resolution_ns": 1000000,
            "net_0_num_motes": 10,
            "net_1_num_motes": 10
        }
    }
}
```

### 2. 运行模拟
```bash
# 使用专用脚本
python bin/run_multi_network.py

# 或使用原有脚本
python bin/runSim.py --config=config_multi_network.json
```

### 3. 查看结果
模拟结果保存在 `simData/` 目录中，与单网络模拟格式相同。

## 性能优化

### 内存优化
- 网络实例按需创建
- 连接性矩阵共享基础数据
- 事件队列使用堆结构优化查找

### 时间优化
- 跨网络事件使用优先队列
- slot级别事件批量处理
- 干扰检测缓存结果

### 可扩展性
- 支持动态添加/删除网络
- 模块化设计便于功能扩展
- 向后兼容保证现有代码可用

## 测试和验证

### 单元测试
运行测试：
```bash
python -m pytest tests/test_multi_network_engine.py -v
```

### 功能测试
1. **基本功能**: 多网络初始化和时间管理
2. **干扰模拟**: 跨网络频道冲突检测
3. **性能测试**: 大规模网络并发性能
4. **兼容性**: 确保单网络模式正常工作

## 扩展开发

### 添加新的干扰模型
继承 `MultiNetworkEngine` 并重写 `_apply_interference_penalty()` 方法：

```python
class CustomMultiNetworkEngine(MultiNetworkEngine):
    def _apply_interference_penalty(self, network, interference_channels):
        # 自定义干扰逻辑
        pass
```

### 自定义时间同步
重写时间管理方法：

```python
def get_network_time_offset(self, network_id):
    # 返回网络的时间偏移
    return custom_offset
```

### 集成新的协议
扩展 `NetworkInstance` 以支持新的协议栈组件。

## 故障排除

### 常见问题

1. **内存不足**: 减少网络数量或增加系统内存
2. **性能慢**: 调整 `time_resolution_ns` 或减少并发网络数
3. **配置错误**: 检查JSON格式和参数名称
4. **兼容性问题**: 确保使用正确的Python版本和依赖

### 调试技巧

1. 启用详细日志：设置 `"logging": "all"`
2. 检查网络状态：添加调试打印网络信息
3. 性能分析：使用Python的 `cProfile` 模块

## 未来发展

### 计划功能
1. **动态网络管理**: 运行时添加/删除网络
2. **高级干扰模型**: 基于距离和功率的干扰计算
3. **频谱优化**: 智能频道分配算法
4. **移动性支持**: 节点在网络间移动

### 研究方向
1. **大规模网络**: 支持数百个并发网络
2. **实时模拟**: 与实际硬件集成
3. **机器学习优化**: 使用AI优化网络配置

## 参考文献

1. IEEE 802.15.4-2015 TSCH标准
2. RFC 8180 - Minimal 6TiSCH Configuration
3. RFC 8480 - 6TiSCH 6top Protocol
4. "Simulating 6TiSCH Networks" - Municio et al., 2019

---

*本文档描述了6TiSCH多网络并行组网模拟器的设计和使用方法。如有问题，请参考源代码或提交Issue。*