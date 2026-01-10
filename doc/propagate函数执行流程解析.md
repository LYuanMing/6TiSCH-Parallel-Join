# propagate函数执行流程详细解析

## 函数概述
`propagate()` 函数在 `SimEngine/Connectivity.py` 的第107-340行定义。它模拟在一个时隙（slot）中数据帧的传播过程，包括传输、接收、冲突检测和ACK处理。

---

## 执行流程详细步骤

### 第一步：初始化阶段（第111-112行）

```python
asn        = self.engine.getAsn()
slotOffset = asn % self.settings.tsch_slotframeLength
```

**函数调用：**
- `self.engine.getAsn()` → 返回当前绝对时隙号（Absolute Slot Number）

**计算：**
- `asn`: 获取当前模拟的时隙编号
- `slotOffset`: 计算当前时隙在时隙帧中的偏移位置（`asn % 时隙帧长度`）

**作用：** 确定当前处理的时隙位置

---

### 第二步：收集传输和接收信息（第114-149行）

```python
transmissions_by_channel = {}
receivers_by_channel = {}

for mote in self.engine.motes:
    if mote.radio.state == d.RADIO_STATE_TX:
        # 处理发送者
    elif mote.radio.state == d.RADIO_STATE_RX:
        # 处理接收者
```

**遍历所有mote，按状态分类：**

#### 2.1 发送者处理（第121-138行）

**条件检查：**
- `mote.radio.state == d.RADIO_STATE_TX` → 检查mote是否处于发送状态

**创建传输字典：**
```python
thisTran = {
    u'channel': mote.radio.onGoingTransmission[u'channel'],  # 信道号
    u'tx_mote_id': mote.id,                                  # 发送者ID
    u'packet': mote.radio.onGoingTransmission[u'packet'],    # 数据包
    u'txTime': mote.tsch.clock.get_drift(),                  # 传输开始时间
    u'numACKs': 0,                                           # ACK计数（初始为0）
}
```

**函数调用：**
- `mote.tsch.clock.get_drift()` → 获取mote的时钟漂移（用于确定传输时间）

**存储：**
- 按 `channel` 分组，将传输信息存入 `transmissions_by_channel[channel]` 列表

#### 2.2 接收者处理（第141-145行）

**条件检查：**
- `mote.radio.state == d.RADIO_STATE_RX` → 检查mote是否处于接收状态

**存储：**
- 按 `channel` 分组，将接收者ID存入 `receivers_by_channel[channel]` 列表

---

### 第三步：处理无传输的监听者（第151-160行）

```python
for channel in set(receivers_by_channel.keys()) - set(transmissions_by_channel.keys()):
    for listener_id in receivers_by_channel[channel]:
        sentAck = self.engine.motes[listener_id].radio.rxDone(packet=None)
        assert sentAck is False
```

**计算：**
- `set(receivers_by_channel.keys()) - set(transmissions_by_channel.keys())` → 找出有监听者但没有传输的信道

**函数调用链：**
1. `self.engine.motes[listener_id].radio.rxDone(packet=None)`
   - 调用 `Radio.rxDone()` (第114-142行)
   - 设置 `radio.state = d.RADIO_STATE_OFF`
   - 更新统计：`_update_stats(u'idle_listen')` → 空闲监听统计
   - 调用 `mote.tsch.rxDone(packet=None, channel)` → 通知TSCH层
   - 返回 `is_acked` (False，因为没有收到包)

**作用：** 处理那些在监听但没有收到任何传输的mote，将其状态设为空闲监听

---

### 第四步：处理无监听者的传输（第162-168行）

```python
for channel in set(transmissions_by_channel.keys()) - set(receivers_by_channel.keys()):
    for t in transmissions_by_channel[channel]:
        self.engine.motes[t[u'tx_mote_id']].radio.txDone(False)
```

**计算：**
- `set(transmissions_by_channel.keys()) - set(receivers_by_channel.keys())` → 找出有传输但没有监听者的信道

**函数调用链：**
1. `self.engine.motes[tx_mote_id].radio.txDone(False)`
   - 调用 `Radio.txDone()` (第80-104行)
   - 设置 `radio.state = d.RADIO_STATE_OFF`
   - 更新统计：`_update_stats(u'tx_data')` 或 `_update_stats(u'tx_data_rx_ack')`
   - 调用 `mote.tsch.txDone(isACKed=False, channel)` → 通知TSCH层传输失败（无ACK）

**作用：** 处理那些发送了数据但没有接收者的传输，标记为未收到ACK

---

### 第五步：处理有传输和监听者的信道（第170-332行）

这是核心处理逻辑，对每个有传输和监听者的信道进行处理：

```python
for channel in set(transmissions_by_channel.keys()) & set(receivers_by_channel.keys()):
    for listener_id in receivers_by_channel[channel]:
        # 处理每个监听者
```

**计算：**
- `set(transmissions_by_channel.keys()) & set(receivers_by_channel.keys())` → 找出既有传输又有监听者的信道

#### 5.1 冲突检测和锁定传输（第174-240行）

**初始化变量：**
```python
lockon_transmission = None          # 锁定的传输
lockon_random_value = None          # 锁定传输的随机值
interfering_transmissions = []       # 干扰传输列表
detected_transmissions = 0           # 检测到的传输数量
```

##### 情况A：存在冲突（多个传输）（第182-248行）

```python
if len(transmissions_by_channel[channel]) > 1:
    for t in transmissions_by_channel[channel]:
        random_value = random.random()
        peamble_pdr = self.get_pdr(
            src_id=t[u'tx_mote_id'],
            dst_id=listener_id,
            channel=channel,
        )
```

**函数调用：**
- `random.random()` → 生成0-1之间的随机数，用于PDR判断
- `self.get_pdr(src_id, dst_id, channel)` → 获取前导码（preamble）的PDR值
  - 内部调用：`self.matrix.get_pdr(src_id, dst_id, channel)` (第533行)
  - 返回：从连接矩阵中获取的PDR值（0-1之间）

**前导码接收判断（第195-197行）：**
```python
if random_value > peamble_pdr:
    continue  # 前导码接收失败，跳过此传输
```

**计算逻辑：**
- 如果 `random_value > peamble_pdr`，表示前导码接收失败
- 否则，前导码接收成功，`detected_transmissions += 1`

**锁定最早传输（第203-216行）：**
```python
if lockon_transmission is None:
    lockon_transmission = t
    lockon_random_value = random_value
elif t[u'txTime'] < lockon_transmission[u'txTime']:
    interfering_transmissions += [lockon_transmission]
    lockon_transmission = t
    lockon_random_value = random_value
else:
    interfering_transmissions += [t]
```

**计算逻辑：**
- 如果还没有锁定传输，锁定第一个成功接收前导码的传输
- 如果新传输的时间更早（`txTime`更小），将之前的锁定传输加入干扰列表，锁定新传输
- 否则，将新传输加入干扰列表

**无接收情况（第219-224行）：**
```python
if lockon_transmission is None:
    sentAck = self.engine.motes[listener_id].radio.rxDone(packet=None)
    continue
```

**函数调用：**
- `radio.rxDone(packet=None)` → 处理空闲监听（同第三步）

**记录干扰日志（第227-240行）：**
```python
self.log(
    SimLog.LOG_PROP_INTERFERENCE,
    {
        u'_mote_id': listener_id,
        u'channel': channel,
        u'lockon_transmission': lockon_transmission[u'packet'],
        u'interfering_transmissions': [t[u'packet'] for t in interfering_transmissions]
    }
)
```

**计算带干扰的PDR（第244-248行）：**
```python
packet_pdr = self._compute_pdr_with_interference(
    listener_id=listener_id,
    lockon_transmission=lockon_transmission,
    interfering_transmissions=interfering_transmissions
)
```

**函数调用：** `_compute_pdr_with_interference()` (第365-433行)

**详细计算过程：**

1. **计算噪声功率（第379-381行）：**
   ```python
   noise_mW = self._dBm_to_mW(
       self.engine.motes[listener_id].radio.noisepower
   )
   ```
   - `noisepower`: 默认-105 dBm
   - `_dBm_to_mW(dBm)`: `10^(dBm/10)` → 将dBm转换为毫瓦

2. **计算信号功率（第385-392行）：**
   ```python
   signal_mW = self._dBm_to_mW(
       self.get_rssi(lockon_tx_mote_id, listener_id, channel)
   )
   signal_mW -= noise_mW
   if signal_mW < 0.0:
       return -10.0  # 信号低于噪声，返回低SINR
   ```
   - `get_rssi()`: 从连接矩阵获取RSSI值
   - `signal_mW`: 信号功率（毫瓦）= RSSI转换后的功率 - 噪声功率

3. **计算总干扰功率（第396-407行）：**
   ```python
   totalInterference_mW = 0.0
   for interfering_tran in interfering_transmissions:
       interference_mW = self._dBm_to_mW(
           self.get_rssi(interfering_tx_mote_id, listener_id, channel)
       )
       interference_mW -= noise_mW
       if interference_mW < 0.0:
           interference_mW = 0.0
       totalInterference_mW += interference_mW
   ```
   - 对每个干扰传输，计算其RSSI对应的功率
   - 减去噪声功率，累加得到总干扰功率

4. **计算SINR（第409行）：**
   ```python
   sinr_dB = self._mW_to_dBm(signal_mW / (totalInterference_mW + noise_mW))
   ```
   - SINR (dB) = `10 * log10(信号功率 / (总干扰功率 + 噪声功率))`
   - `_mW_to_dBm(mW)`: `10 * log10(mW)` → 将毫瓦转换为dBm

5. **计算干扰PDR（第414-423行）：**
   ```python
   noise_dBm = self.engine.motes[listener_id].radio.noisepower
   interference_rssi = self._mW_to_dBm(
       self._dBm_to_mW(sinr_dB + noise_dBm) +
       self._dBm_to_mW(noise_dBm)
   )
   interference_pdr = self._rssi_to_pdr(interference_rssi)
   ```
   - 将SINR转换为等效RSSI
   - `_rssi_to_pdr(rssi)`: 使用RSSI-PDR查找表（第446-491行）进行线性插值

6. **计算最终PDR（第427-432行）：**
   ```python
   lockon_pdr = self.get_pdr(lockon_tx_mote_id, listener_id, channel)
   returnVal = lockon_pdr * interference_pdr
   ```
   - 最终PDR = 锁定传输的PDR × 干扰PDR

##### 情况B：无冲突（单个传输）（第251-261行）

```python
elif len(transmissions_by_channel[channel]) == 1:
    detected_transmissions = 1
    lockon_random_value = random.random()
    lockon_transmission = transmissions_by_channel[channel][0]
    packet_pdr = self.get_pdr(
        src_id=lockon_transmission[u'tx_mote_id'],
        dst_id=listener_id,
        channel=channel
    )
```

**计算：**
- 只有一个传输，直接获取PDR，无需计算干扰
- `packet_pdr` = 从连接矩阵获取的PDR值

#### 5.2 接收成功判断（第274-315行）

```python
if lockon_random_value < packet_pdr:
    # 接收成功
else:
    # 接收失败
```

**计算逻辑：**
- 如果 `lockon_random_value < packet_pdr`，表示数据包接收成功
- 否则，接收失败（被干扰）

##### 接收成功处理（第276-298行）

```python
receivedAck = self.engine.motes[listener_id].radio.rxDone(
    packet=lockon_transmission[u'packet'],
)
```

**函数调用链：**
1. `radio.rxDone(packet)` (第114-142行)
   - 设置 `radio.state = d.RADIO_STATE_OFF`
   - 根据包类型更新统计：
     - 如果是单播且目标是自己：`_update_stats(u'rx_data_tx_ack')`
     - 否则：`_update_stats(u'rx_data')`
   - 调用 `mote.tsch.rxDone(packet, channel)` → 通知TSCH层
   - 返回 `is_acked` (True/False，表示是否发送了ACK)

**ACK丢失模拟（第284-290行）：**
```python
if receivedAck and self.settings.conn_simulate_ack_drop:
    pdr_of_return_link = self.get_pdr(
        src_id=listener_id,
        dst_id=lockon_transmission[u'tx_mote_id'],
        channel=channel
    )
    receivedAck = random.random() < pdr_of_return_link
```

**计算：**
- 如果启用了ACK丢失模拟，根据反向链路的PDR判断ACK是否丢失
- `receivedAck = random.random() < pdr_of_return_link` → 随机数小于PDR则ACK成功

**更新ACK计数（第292-298行）：**
```python
if receivedAck:
    lockon_transmission[u'numACKs'] += 1
```

##### 接收失败处理（第299-315行）

```python
receivedAck = self.engine.motes[listener_id].radio.rxDone(packet=None)
self.log(SimLog.LOG_PROP_DROP_LOCKON, {...})
assert receivedAck is False
```

**函数调用：**
- `radio.rxDone(packet=None)` → 处理空闲监听
- `self.log()` → 记录丢包日志

#### 5.3 通知发送者ACK状态（第319-332行）

```python
for t in transmissions_by_channel[channel]:
    if t[u'numACKs'] == 0:
        isACKed = False
    elif t[u'numACKs'] == 1:
        isACKed = True
    else:
        raise SystemError()  # 不应该有多个ACK
    
    self.engine.motes[t[u'tx_mote_id']].radio.txDone(isACKed)
```

**函数调用：**
- `radio.txDone(isACKed)` (第80-104行)
  - 设置 `radio.state = d.RADIO_STATE_OFF`
  - 更新统计信息
  - 调用 `mote.tsch.txDone(isACKed, channel)` → 通知TSCH层

**计算逻辑：**
- `numACKs == 0`: 未收到ACK → `isACKed = False`
- `numACKs == 1`: 收到ACK → `isACKed = True`
- `numACKs > 1`: 错误（不应该有多个ACK）

---

### 第六步：验证和调度（第334-340行）

```python
# 验证所有radio都已关闭
for mote in self.engine.motes:
    assert mote.radio.state == d.RADIO_STATE_OFF
    assert mote.radio.channel is None

# 调度下一次传播
self._schedule_propagate()
```

**验证：**
- 确保所有mote的radio状态为OFF
- 确保所有mote的channel为None

**函数调用：** `_schedule_propagate()` (第342-352行)

```python
self.engine.scheduleAtAsn(
    asn              = self.engine.getAsn() + 1,
    cb               = self.propagate,
    uniqueTag        = (None, u'Connectivity.propagate'),
    intraSlotOrder   = d.INTRASLOTORDER_PROPAGATE,
)
```

**计算：**
- `asn = self.engine.getAsn() + 1` → 下一个时隙
- 调度 `propagate` 函数在下一个时隙执行

---

## 关键函数调用总结

### 内部函数调用
1. `self.engine.getAsn()` → 获取当前ASN
2. `self.get_pdr(src_id, dst_id, channel)` → 获取PDR值
3. `self.get_rssi(src_id, dst_id, channel)` → 获取RSSI值
4. `self._compute_pdr_with_interference()` → 计算带干扰的PDR
5. `self._dBm_to_mW(dBm)` → dBm转毫瓦
6. `self._mW_to_dBm(mW)` → 毫瓦转dBm
7. `self._rssi_to_pdr(rssi)` → RSSI转PDR
8. `self._schedule_propagate()` → 调度下一次传播

### 外部函数调用
1. `mote.radio.rxDone(packet)` → 处理接收完成
   - 内部调用：`mote.tsch.rxDone(packet, channel)`
   - 内部调用：`radio._update_stats(stats_type)`
2. `mote.radio.txDone(isACKed)` → 处理发送完成
   - 内部调用：`mote.tsch.txDone(isACKed, channel)`
   - 内部调用：`radio._update_stats(stats_type)`
3. `mote.tsch.clock.get_drift()` → 获取时钟漂移
4. `self.engine.scheduleAtAsn()` → 调度事件
5. `self.log()` → 记录日志

---

## 数据流示例

假设场景：信道16上有2个传输（mote 1 → mote 3, mote 2 → mote 3），mote 3在监听

1. **收集阶段：**
   - `transmissions_by_channel[16] = [tran1, tran2]`
   - `receivers_by_channel[16] = [3]`

2. **冲突处理：**
   - mote 3检测到2个传输
   - 对每个传输计算前导码PDR
   - 锁定最早传输（假设tran1）
   - tran2加入干扰列表

3. **PDR计算：**
   - 计算tran1的信号功率
   - 计算tran2的干扰功率
   - 计算SINR
   - 计算最终PDR = lockon_pdr × interference_pdr

4. **接收判断：**
   - 生成随机数
   - 与packet_pdr比较
   - 成功则调用 `rxDone(packet)`，失败则调用 `rxDone(None)`

5. **ACK处理：**
   - 如果接收成功且发送了ACK，`numACKs += 1`
   - 通知发送者ACK状态

---

## 关键计算公式

1. **dBm转毫瓦：** `mW = 10^(dBm/10)`
2. **毫瓦转dBm：** `dBm = 10 * log10(mW)`
3. **信号功率：** `signal_mW = RSSI_mW - noise_mW`
4. **SINR：** `SINR_dB = 10 * log10(signal_mW / (interference_mW + noise_mW))`
5. **最终PDR：** `packet_pdr = lockon_pdr × interference_pdr`
6. **接收判断：** `接收成功 = (random_value < packet_pdr)`
