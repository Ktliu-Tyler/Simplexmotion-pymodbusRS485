# change_slave_id.py 操作說明

這份文件說明如何使用獨立程式修改 Simplex Motion 馬達的 Modbus slave id，並保存到非揮發記憶體。

程式位置：

```text
SimplexMotion_Motor_Example_Using_PyModbus-master/
  SimplexMotion_Motor_Example_Using_PyModbus-master/
    change_slave_id.py
```

## 1. 重要注意事項

- 修改 slave id 時，最好一次只接一顆馬達。
- 如果多顆馬達還是同一個 slave id，請先斷開其他馬達。
- slave id 合法範圍是 `1..126`。
- 預設通訊參數仍是 `57600 baud`、Even parity、8 data bits、1 stop bit。
- 修改後程式會執行 `Store` 保存，再執行 `Reset` 讓新 id 生效。

## 2. Register 對照

手冊使用的 register number 和程式使用的 Modbus address 差一格：

```text
程式 address = 手冊 register number - 1
```

本功能用到：

| 手冊 register | 程式 address | 名稱 | 用途 |
| ---: | ---: | --- | --- |
| 50 | 49 | `Address` | Modbus slave id |
| 400 | 399 | `Mode` | 寫入 `9` Store、`1` Reset |

## 3. 基本指令

例如目前馬達 id 是 `1`，要改成 `2`：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 1 --target 2
```

程式會要求你輸入：

```text
CHANGE
```

才會真的執行修改。

如果你確認要直接執行，不想互動確認：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 1 --target 2 --yes
```

## 4. 執行流程

程式會依序做：

1. 用 `--current` 指定的 id 連線。
2. 讀取 `Address` register，確認目前設定。
3. 將 `Address` register #50 寫成 `--target`。
4. 寫入 `Mode = 9`，也就是 `Store`，保存到非揮發記憶體。
5. 寫入 `Mode = 1`，也就是 `Reset`，讓新 id 生效。
6. 用新的 `--target` id 重新連線驗證。
7. 回讀 `Address` register，確認已是新 id。

成功時會看到類似：

```text
Slave id change completed and verified.
```

## 5. 常用範例

### 1 改成 2

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 1 --target 2
```

### 2 改成 3

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 2 --target 3
```

### 開 debug log

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\change_slave_id.py" --port COM3 --current 1 --target 2 --debug
```

## 6. 修改後如何使用

例如改成 id `2` 後，主控選單要用：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 2
```

## 7. 失敗時怎麼辦

如果程式顯示驗證失敗：

1. 先重新上電馬達。
2. 用新 id 試著連線，例如 `--slave 2`。
3. 如果新 id 不通，再用原本 id 試。
4. 確認同一條 RS485 上沒有兩顆馬達使用同一個 id。
5. 確認 A/B、GND、24V 電源都正常。

如果你不確定目前 id 是多少，先一次只接一顆馬達，逐一用 `1..126` 掃描會比較安全；目前尚未寫自動掃描工具。

## 8. 安全建議

- 修改 id 時不要同時讓馬達運轉。
- 修改前可先在主選單選 `6 Reset/disable motor`。
- 只改通訊 id，不會改馬達控制參數。
- 但因為會執行 `Store`，請避免在其他參數剛被誤改時立刻執行這個工具。
