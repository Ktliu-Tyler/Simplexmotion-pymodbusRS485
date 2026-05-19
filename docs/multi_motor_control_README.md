# multi_motor_control.py 操作說明

這支程式用來在同一條 SC/SM-Comboard RS485 bus 上控制多顆 Simplex Motion 馬達。

目前預設 slave id：

```text
1, 2, 3
```

之後增加到 6 顆時，改用：

```text
--slaves 1-6
```

## 重要觀念

同一條 RS485 bus 只會開啟一個 serial connection。程式會依序對不同 slave id 下指令：

```text
COM3 -> slave 1
COM3 -> slave 2
COM3 -> slave 3
```

這不是同時平行送指令。Modbus RTU / RS485 本來就是 master 輪詢每個 slave 的架構，這樣最穩定。

## 執行方式

目前 1 到 3 號馬達：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\multi_motor_control.py" --port COM3 --slaves 1-3
```

之後 1 到 6 號馬達：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\multi_motor_control.py" --port COM3 --slaves 1-6
```

如果只想控制指定幾顆：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\multi_motor_control.py" --port COM3 --slaves 1,3,5
```

## 啟動參數

| Option | Default | Meaning |
| --- | ---: | --- |
| `--port` | `COM3` | SC/SM-Comboard 的 COM port |
| `--slaves` | `1-3` | 要連線的 slave id |
| `--baudrate` | `57600` | Modbus RTU baudrate |
| `--timeout` | `0.5` | 每次 Modbus request timeout |
| `--speed` | `60` | 預設 ramp speed，deg/s |
| `--acc` | `120` | 預設 ramp acceleration，deg/s^2 |
| `--dec` | `120` | 預設 ramp deceleration，deg/s^2 |
| `--strict` | off | 指定的 slave 只要有一顆沒回應就停止 |
| `--debug` | off | 顯示 debug log |
| `--keep-enabled-on-exit` | off | 離開時不要自動 reset/disable |
| `--zero-state-file` | `motor_state/position_reference.json` | 軟體零點/位置紀錄檔 |

預設離開程式時會儲存每顆位置並送 `Reset/disable`，比較適合實驗桌測試。

## 主選單

```text
1. Show status all
2. Show status selected
3. Configure ramp selected
4. Set zero selected
5. Absolute position one motor
6. Absolute position group
7. Off selected
8. Reset/disable selected
9. Restore saved position reference selected
10. Set safe/common mode selected
11. Beep one motor
12. Read manual register selected
q. Quit
```

### 馬達選擇格式

選單問 `Slave id or all` 時，可以輸入：

| Input | Meaning |
| --- | --- |
| `all` | 所有已連線馬達 |
| `1` | 只選 slave 1 |
| `1,3` | 選 slave 1 和 3 |
| `1-3` | 選 slave 1、2、3 |

## 建議第一次測試流程

1. 只接 1 到 3 號馬達，確認每顆 slave id 不重複。
2. 執行 `multi_motor_control.py --port COM3 --slaves 1-3`。
3. 選 `1`，確認三顆都有狀態回傳。
4. 選 `3`，對 `all` 設定保守 ramp，例如 `60 / 120 / 120`。
5. 選 `4`，先對單顆例如 `1` 設定 0 點。
6. 選 `5`，控制單顆馬達做 `10`、`0`、`-10`。
7. 確定單顆穩定後，再用 `6` 做 group absolute position。

## 單顆絕對位置控制

選 menu `5` 後，指定 slave id，例如：

```text
Slave id [1]: 2
```

接著可以輸入：

| Input | Meaning |
| --- | --- |
| number | 絕對目標角度，例如 `10`、`0`、`-10` |
| `p` | 顯示該馬達狀態 |
| `z` | 將目前位置設為軟體 0 點 |
| `r` | 恢復上次儲存的位置參考 |
| `b` / `q` | 回主選單 |

## 多顆 group position

選 menu `6`，可以選擇同一目標或每顆不同目標。

同一目標範例：

```text
Slaves for group position, for example all or 1,3 [all]: all
Target input style: same or each [same]: same
Common absolute target deg [0.0]: 10
```

每顆不同目標範例：

```text
Slaves for group position, for example all or 1,3 [all]: 1-3
Target input style: same or each [same]: each
slave 1 target deg, blank to skip: 0
slave 2 target deg, blank to skip: 10
slave 3 target deg, blank to skip: -10
```

程式會先讓每顆進入 `PositionRamp` 並把 target 設成該馬達目前位置，避免切模式時跳動，然後再依序寫入各自 target。

## 軟體 0 點與斷電恢復

menu `4` 可以對單顆或多顆設定目前位置為 `0 deg`。

位置紀錄會存到：

```text
motor_state/position_reference.json
```

menu `9` 可以把上次儲存的位置寫回 `MotorPosition`。注意這只適用於斷電期間軸沒有移動的情況。如果機構會被推動、滑動或手轉，請改用 homing 或 absolute encoder。

## 安全注意

- 多顆馬達共用 24 V 電源時，電源電流要足夠，GND 必須共地。
- 每顆馬達 slave id 必須唯一。
- 先用單顆測穩，再做 group move。
- 第一次 group move 請用小角度，例如 `5` 或 `10 deg`。
- 不要在未知負載下使用高速/高加速度。
- 離開程式預設會 reset/disable 全部已連線馬達。
