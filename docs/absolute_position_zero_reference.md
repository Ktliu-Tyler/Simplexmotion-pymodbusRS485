# Absolute Position And Zero Reference

這份紀錄說明目前程式新增的「絕對移動」、「設定 0 點」與「斷電後座標恢復」功能。

## 重要結論

Simplex Motion 手冊對 `MotorPosition` 的描述是：

- 手冊 register `200/201`，Python code address `199`。
- 型別是 `int32`。
- 單位是 encoder counts，通常 `4096 counts/rev`。
- 上電時 `MotorPosition` 會 reset to zero。
- `Reset` mode 也會 reset `MotorPosition`。
- 使用者可以寫入這個 register 來改變目前座標參考。

所以程式可以做到：

- 把「目前軸的位置」設成 `0 deg`。
- 之後用 `10 deg`、`-30 deg`、`0 deg` 這種絕對座標移動。
- 在離開程式前記錄最後位置到本機 JSON 檔。
- 下次上電後，如果軸在斷電期間沒有被轉動，可以把上次記錄的位置寫回 `MotorPosition`，恢復軟體座標系。

但程式不能保證：

- 如果馬達斷電後被手轉、機構滑動、外力推動，程式無法知道真實角度。
- 這種情況要真正「一上電就知道在哪個角度」，需要 homing switch、index/reference sensor，或外部 absolute encoder。

## 新增檔案

| File | Purpose |
| --- | --- |
| `position_reference.py` | 儲存/讀取軟體位置參考紀錄 |
| `motor_state/position_reference.json` | 執行後產生，本機座標紀錄檔 |

`motor_state/position_reference.json` 會用 `COMx:slave_id` 分開記錄，例如 `COM3:2`。

## motor_control_menu.py 新增功能

執行範例：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 2
```

新增選單：

| Menu | Function |
| ---: | --- |
| 16 | Set zero point，將目前位置寫成 `0 deg` |
| 17 | Absolute position test，以目前 zero 為基準做絕對位置移動 |
| 18 | Restore saved position reference，把上次儲存的位置寫回 `MotorPosition` |

建議第一次測試流程：

1. 進入 menu `1` 確認狀態。
2. 進入 menu `2` 設定保守 ramp，例如 speed `60`、acc `120`、dec `120`。
3. 把軸移到你要定義的機械 0 點。
4. 進入 menu `16`，確認後把目前位置設成 `0 deg`。
5. 進入 menu `17`。
6. 先測 `10`、`0`、`-10` 這種小角度。

`17 Absolute position test` 裡的指令：

| Input | Meaning |
| --- | --- |
| number | 移動到絕對角度，例如 `10`、`-10`、`0` |
| `p` | 讀取目前角度 |
| `z` | 立刻把目前位置設為 0 |
| `r` | 恢復上次儲存的位置參考 |
| `b` / `q` | 回主選單 |

## 斷電後恢復座標

程式離開時會在 reset/disable 前儲存最後位置。下次上電後，如果你確定軸沒有在斷電期間被轉動，可以用：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\motor_control_menu.py" --port COM3 --slave 2 --restore-last-position
```

或進入主選單後選：

```text
18. Restore saved position reference
```

注意：restore 只會把儲存的 count 寫回 `MotorPosition`，不會讓馬達移動。它是假設「斷電期間軸沒有動」。如果軸可能被動過，不要 restore，請重新做 homing 或重新設定 0 點。

## position_control_com3.py 新增功能

執行範例：

```powershell
.\motionENV\Scripts\python.exe ".\SimplexMotion_Motor_Example_Using_PyModbus-master\SimplexMotion_Motor_Example_Using_PyModbus-master\position_control_com3.py" --port COM3 --slave 2 --speed 60 --acc 120 --dec 120
```

互動指令：

| Input | Meaning |
| --- | --- |
| number | 移動到絕對角度 |
| `p` | 讀取目前位置 |
| `z` | 將目前位置設定為 0 |
| `s` | 儲存目前位置紀錄 |
| `r` | 恢復上次儲存的位置參考 |
| `q` | 離開並 reset/disable |

啟動參數：

| Option | Meaning |
| --- | --- |
| `--no-reset` | 啟動時不 reset `MotorPosition` |
| `--restore-last-position` | 啟動時恢復上次儲存的位置參考 |
| `--zero-state-file PATH` | 指定位置紀錄檔 |

## 安全注意

- 設定 0 點前，請確保機構不會因失去 holding torque 而掉落或滑動。
- `Set zero` 會先進入 `Off mode`，再寫 `MotorPosition = 0`。
- 寫 `MotorPosition` 不會讓馬達移動，但會改變控制器認為的目前座標。
- 如果 restore 了錯誤的位置參考，之後的絕對移動會以錯誤座標執行。
- 真正需要每次上電自動找到機械 0 點時，下一步應該設定 homing。
