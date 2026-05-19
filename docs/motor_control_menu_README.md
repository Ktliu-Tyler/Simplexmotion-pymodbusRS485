# motor_control_menu.py 操作說明

這份文件專門說明如何使用互動式主程式：

```text
SimplexMotion_Motor_Example_Using_PyModbus-master/
  SimplexMotion_Motor_Example_Using_PyModbus-master/
    motor_control_menu.py
```

此程式用來透過 `COM3`、Modbus RTU、RS485 控制 Simplex Motion 馬達，並用選單方式切換常用測試模式。

## 1. 啟動方式

從專案根目錄執行：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 1
```

如果要用較保守的預設 ramp 參數啟動：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 1 --speed 60 --acc 120 --dec 120
```

## 2. 啟動參數

| 參數 | 預設值 | 說明 |
| --- | ---: | --- |
| `--port` | `COM3` | Windows COM port |
| `--slave` | `1` | 馬達 Modbus address |
| `--baudrate` | `57600` | Modbus RTU baud rate |
| `--speed` | `90` | 預設 ramp speed，單位 deg/s |
| `--acc` | `180` | 預設 ramp acceleration，單位 deg/s^2 |
| `--dec` | `180` | 預設 ramp deceleration，單位 deg/s^2 |
| `--allow-dangerous-modes` | 關閉 | 允許特殊/高風險 mode |

查詢說明：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --help
```

## 3. 建議第一次測試流程

第一次接一顆馬達時，建議照這個順序：

```text
1  Show status
2  Configure ramp speed/acc/dec
3  Position ramp test
```

在 `2` 裡面建議先輸入：

```text
Ramp speed max deg/s: 60
Ramp acceleration deg/s^2: 120
Ramp deceleration deg/s^2: 120
```

在 `3` position 測試裡先輸入小角度：

```text
10
-10
0
```

如果運動方向、角度、聲音、震動都正常，再逐步提高速度或角度。

## 4. 主選單功能

啟動成功後會看到：

```text
==== Simplex Motion Test Menu ====
1. Show status
2. Configure ramp speed/acc/dec
3. Position ramp test
4. Speed ramp test
5. Freewheel mode
6. Reset/disable motor
7. Off mode
8. Beep
9. Read manual register
10. List modes
11. Set common mode by value
12. Set raw/advanced mode
13. Manual turn check (Off mode)
14. Neutral angle monitor (Off + live position)
15. Torque control test
q. Quit
```

## 5. 選單詳細說明

### 1. Show status

讀取目前馬達狀態，包含：

| 項目 | 說明 |
| --- | --- |
| Mode | 目前操作模式 |
| Position | 目前位置，單位 degrees |
| Speed | 目前速度，單位 deg/s |
| Ramp speed max | 目前 ramp 最高速度 |
| Ramp acc/dec max | 目前 ramp 加速度/減速度 |
| Torque max | 目前 torque limit |
| PID | Kp/Ki/Kd |

建議每次剛連線先執行 `1`，確認通訊正常。

### 2. Configure ramp speed/acc/dec

設定 position ramp / speed ramp 會用到的速度與加減速度限制。

保守測試建議：

| 狀況 | speed | acc | dec |
| --- | ---: | ---: | ---: |
| 第一次空載 | 30-60 | 60-120 | 60-120 |
| 空載穩定後 | 60-180 | 120-360 | 120-360 |
| 有機構但未知負載 | 15-60 | 30-120 | 30-120 |

單位：

```text
speed: deg/s
acc:   deg/s^2
dec:   deg/s^2
```

### 3. Position ramp test

切換到：

```text
MODE_POSITION_RAMP = 21
```

這是建議優先使用的 position control 模式，因為有 ramp 控制，會限制速度與加減速度。

進入後可以輸入絕對目標角度：

```text
10
-10
0
90
```

回到主選單：

```text
b
```

注意：這裡輸入的是「絕對位置」，不是每次增加多少。例如先輸入 `10`，再輸入 `20`，馬達會從 10 度移到 20 度，不是再加 20 度。

### 4. Speed ramp test

切換到：

```text
MODE_SPEED_RAMP = 33
```

輸入目標速度，單位是 `deg/s`：

```text
90
-90
0
```

回到主選單：

```text
b
```

離開 speed ramp test 時，程式會先寫入 `0` 速度。

程式進入 speed ramp test 時會先做三件事：

1. 設定 `TargetSelect = 0`，也就是 target source 使用 register。
2. 設定 `TargetFilter = 0`，避免數位 target 被額外濾波。
3. 先把 `TargetInput` 寫成 32-bit 的 `0`，再切到 speed ramp mode。

注意：`TargetInput` 在手冊中是 `int32`，佔兩個 register `450/451`。Speed target 也必須用 32-bit 方式寫入。如果只寫單一 register，可能會寫到高 16-bit，造成目標值被放大 `65536` 倍而暴衝。

### 5. Freewheel mode

切換到：

```text
MODE_FREEWHEEL = 19
```

用途：

- 讓馬達軸可以自由轉動
- 檢查機構是否卡住
- 手動轉軸確認方向或機構阻力

注意：Freewheel 不是純粹「完全斷電」。依手冊描述，freewheel 允許馬達自由轉動到 `RampSpeedMax`，若速度超過限制，馬達仍可能用 `MotorTorqueMax` 進行減速抑制。因此如果剛從 speed mode 切過來、軸還沒完全停、或速度估測有雜訊，可能出現短暫抖動。

目前程式進入 freewheel 前會先：

1. 設定 `TargetSelect=Register`。
2. 將 speed target 寫成 32-bit `0`。
3. 等待 `0.5 s`。
4. 讀取目前速度。
5. 如果速度仍大於 `30 deg/s`，不進入 freewheel，改成 `Reset`。
6. 若速度已接近 0，先切 `Off`，再切 `Freewheel` 並回讀確認 mode。

如果進入 freewheel 後仍持續震動，建議改用：

```text
6  Reset/disable motor
```

或：

```text
7  Off mode
```

如果要重新控制馬達，再選 `3` position ramp 或 `4` speed ramp。

如果你的目的是「用手轉軸檢查機構阻力」，請優先用選單 `13 Manual turn check (Off mode)`，不要用 freewheel。

### 6. Reset/disable motor

切換到：

```text
MODE_RESET = 1
```

用途：

- reset running data
- disable motor
- 通常離開程式前也會自動做一次

注意：Reset 可能會讓目前位置參考歸零，測試 position control 前要知道這件事。

### 7. Off mode

切換到：

```text
MODE_OFF = 0
```

用途：

- Stop / disable motor
- 讓馬達停止輸出控制

### 8. Beep

使用馬達 beep 功能。

輸入 duration，例如：

```text
300
```

代表 beep `300 ms`。

### 9. Read manual register

讀取手冊上的 register number。

範例：

```text
Manual register number: 400
```

代表讀取 `<Mode>` register。

注意：手冊使用 register number，例如 `400`；Python 程式內部會自動轉成 Modbus zero-based address，也就是 `399`。

### 10. List modes

列出常用測試 mode 與一些特殊 mode。

### 11. Set common mode by value

手動輸入常用 mode value。

常用值：

| Mode | 說明 |
| ---: | --- |
| 0 | Off |
| 1 | Reset |
| 5 | Quickstop |
| 19 | Freewheel |
| 21 | Position ramp |
| 33 | Speed ramp |
| 35 | Speed low ramp |
| 60 | Beep |
| 70 | Homing |

這個選項只允許常用測試 mode。

### 12. Set raw/advanced mode

允許輸入更底層的 mode value。

預設會阻擋下列 mode：

| Mode | 說明 | 為什麼阻擋 |
| ---: | --- | --- |
| 6 | Firmware | 進入 firmware update mode |
| 7 | Factory | 會重設參數 |
| 9 | Store | 寫入 flash |
| 10 | PWM | open loop，沒有 ramp |
| 20 | Position | position 無 ramp |
| 32 | Speed | speed 無 ramp |
| 40 | Torque | torque mode 需要額外限制 |

若真的要允許：

```powershell
--allow-dangerous-modes
```

### 13. Manual turn check (Off mode)

這個選項會：

1. 設定 `TargetSelect=Register`。
2. 將 speed target 寫成 0。
3. 切到 `MODE_OFF = 0`。
4. 回讀確認 mode。

用途：

- 用手轉馬達軸，檢查機構阻力。
- 檢查皮帶、滑台、軸承、齒輪是否卡住。
- 避免 freewheel 的超速抑制干擾手感。

如果機構有垂直負載、彈簧、重物或儲能，切 Off 前要先扶住機構。

### 14. Neutral angle monitor (Off + live position)

這是目前最接近「空檔模式」的測試選項。

它會：

1. 設定 `TargetSelect=Register`。
2. 將 speed target 寫成 0。
3. 切到 `MODE_OFF = 0`。
4. 連續讀取 `MotorPosition` 和 `MotorSpeed`。

用途：

- 馬達不 hold position。
- 馬達不進行 freewheel speed limit 抑制。
- 可以用手推/轉馬達。
- 同時在畫面上讀目前角度。

進入後快捷鍵：

| Key | 功能 |
| --- | --- |
| `q` | 回主選單 |
| `b` | 回主選單 |
| `z` | 將目前位置 reference reset 成 0 |

注意：這個模式只能關掉「控制器主動出力」。馬達本身是永久磁鐵馬達，未出力時仍然會有 cogging torque / 磁力段落感，這種機械/磁性阻力無法靠 Off mode 完全消除。

### 15. Torque control test

這是 torque mode 的專用安全測試入口，對應：

```text
MODE_TORQUE = 40
```

官方手冊重點：

| 手冊 register | 程式 address | 名稱 | 單位/用途 |
| ---: | ---: | --- | --- |
| 203 | 202 | `MotorTorque` | 目前量測 torque，單位 `mNm` |
| 204 | 203 | `MotorTorqueMax` | torque limit，單位 `mNm` |
| 351 | 350 | `RampSpeedMax` | torque mode 的 speed limit |
| 400 | 399 | `Mode` | 寫入 `40` 進入 torque mode |
| 450/451 | 449 | `TargetInput` | `int32` target register pair |
| 452 | 451 | `TargetSelect` | `0 = Register` |
| 462/463 | 461 | `TargetPresent` | regulator 實際 target |

注意：手冊 register 是 1-based 顯示；程式使用的 Modbus address 是手冊編號減 1。這和 speed/position control 目前使用的對照一致。

Torque target 單位特別注意：

- `MotorTorqueMax` 是 `mNm`，這是 torque limit。
- `MotorTorque` 回讀也是 `mNm`。
- 但 torque mode 的 `TargetInput` 不是 mNm。
- 手冊說 torque mode 的 `TargetInput` 使用 signed 16-bit scale，`+32767` / `-32767` 代表馬達最大 torque range。
- 雖然 target scale 是 signed 16-bit，仍然要寫進 32-bit `TargetInput` register pair `450/451`。

因此程式讓你輸入「raw torque scale 的百分比」，不是直接輸入 Nm。預設測試會把每次 torque command 當作短脈衝，時間到會自動回到 target `0`：

```text
1    -> +1% of raw torque target scale
-1   -> -1% of raw torque target scale
5    -> +5% of raw torque target scale
0    -> zero torque target
```

進入 torque test 時，程式會先：

1. 設定 `TargetSelect = Register`。
2. 寫入 torque target raw `0`。
3. 設定 `MotorTorqueMax`，預設 `30 mNm`。
4. 設定 `RampSpeedMax`，預設 `15 deg/s`。
5. 切到 `MODE_TORQUE = 40`。
6. 回讀確認 mode。

啟動參數：

```powershell
--torque-limit-mnm 30
--torque-speed-limit 15
--torque-percent-limit 2
--torque-pulse-seconds 0.5
```

安全限制：

- 沒有 `--allow-dangerous-modes` 時，`MotorTorqueMax` 超過 `200 mNm` 會被擋住。
- 沒有 `--allow-dangerous-modes` 時，target percent 超過 `+/-2%` 會被擋住。
- 每次 torque command 只會維持預設 `0.5 s`，然後自動寫回 target `0`。
- 每次 torque pulse 期間，程式會監看 torque / speed。
- 如果 speed 或 torque 超出安全範圍，程式會寫 target `0` 並 reset。

第一次 torque 測試建議：

```text
15
Torque limit MotorTorqueMax in mNm: 30
Torque mode speed limit deg/s: 15
torque target % > 0.5
torque target % > 0
torque target % > -0.5
torque target % > 0
torque target % > b
```

不要一開始輸入 `2` 以上。Torque mode 沒有 position/speed ramp 的那種直覺保護，空載時幾 mNm 就可能讓馬達快速加速。

如果輸入某個 torque percent 後看到：

```text
WARNING: speed exceeded torque-mode safety limit.
Writing torque target 0 and resetting motor now.
```

這是程式的保護機制，不是馬達自己重啟。代表該 torque command 對目前空載/負載條件已經太大，下一次請降低 target percent、降低 pulse duration，或降低 `MotorTorqueMax`。

## 6. 結束程式

在主選單輸入：

```text
q
```

程式會嘗試：

1. 設定 `MODE_RESET`
2. 關閉 serial connection

如果馬達行為異常，不要只依賴軟體退出，直接切掉馬達電源會更快。

## 7. 常見測試建議

### Position control 最小測試

```text
1
2
speed = 60
acc = 120
dec = 120
3
10
-10
0
b
q
```

### Speed control 最小測試

```text
1
2
speed = 60
acc = 120
dec = 120
4
90
0
-90
0
b
q
```

### 機構阻力確認

```text
5
```

然後手動輕轉馬達軸，確認機構沒有卡住。

如果手轉時 freewheel 會震動，改用：

```text
13
```

也就是 `Manual turn check (Off mode)`。

如果你想一邊手推一邊讀角度，改用：

```text
14
```

也就是 `Neutral angle monitor (Off + live position)`。

### Torque control 最小測試

```text
15
30
15
0.5
0
-0.5
0
b
```

其中前兩個輸入分別是：

```text
MotorTorqueMax = 30 mNm
RampSpeedMax = 15 deg/s
```

## 8. 故障排除

### 連不上 COM port

先確認：

```powershell
.\motionENV\Scripts\python.exe -m serial.tools.list_ports
```

確認 `COM3` 是否存在。如果不是 `COM3`，啟動時改成實際 port：

```powershell
--port COMx
```

### 有 COM port 但讀不到馬達

檢查：

- 馬達是否有 24 V 供電
- GND 是否共地
- slave address 是否為 `1`
- baud rate 是否為 `57600`
- A/B 是否接反

### 馬達動太快或震動

降低：

```text
speed
acc
dec
```

建議退回：

```text
speed = 30
acc = 60
dec = 60
```

如果 speed ramp 測試時輸入很小的速度，馬達卻突然高速轉動，先停止測試並確認目前程式已修正為 32-bit 寫入 `TargetInput`。修正後 `raw = 43` 會寫成兩個 register：

```text
[0, 43]
```

而不是只把 `43` 寫到第一個 register。

### Position target 跑太遠

確認你輸入的是絕對位置，不是相對位移。

例如：

```text
10 -> 去 10 度
20 -> 去 20 度
0  -> 回 0 度
```

不是：

```text
10 -> 加 10 度
20 -> 再加 20 度
```

### Read manual register 輸入 0 會怎樣

手冊 register number 從 1 以上開始。程式內部會把手冊 register 減 1，轉成 Modbus zero-based address。

例如：

```text
Manual register 400 -> Modbus address 399
```

所以不能輸入 `0`。目前程式已加入保護，輸入小於 1 的數字會提示錯誤，不會再讓程式崩潰。

## 9. 相關文件

| 文件 | 內容 |
| --- | --- |
| `README.md` | 專案總覽 |
| `docs/rs485_wiring_record.md` | 接線紀錄 |
| `docs/position_control_run_record.md` | position control 測試紀錄 |
| `docs/simplexmotor_modes_and_functions.md` | mode 與函式總覽 |
