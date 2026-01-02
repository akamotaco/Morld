# 행동 시스템 정리

## 개요

현재 게임 내 행동은 크게 세 가지 레이어로 나뉩니다:
1. **UI 액션** - BBCode URL 클릭으로 발생 (MetaActionHandler)
2. **플레이어 명령** - PlayerSystem.RequestCommand()로 처리
3. **유닛 액션** - ActionSystem.ApplyAction()으로 처리

---

## 1. UI 액션 (MetaActionHandler)

BBCode `[url=action:param]` 클릭 시 처리되는 액션들.

### 네비게이션 액션
| 액션 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| `move` | `move:regionId:localId` | 위치 이동 | O |
| `back` | `back` | 이전 화면으로 | O |
| `confirm` | `confirm` | 확인 (back과 동일) | O |
| `done` | `done` | 완료 (back과 동일) | O |
| `toggle` | `toggle:toggleId` | 토글 펼침/접힘 | O |

### 인벤토리 액션
| 액션 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| `inventory` | `inventory` | 인벤토리 화면 표시 | O |
| `drop` | `drop:itemId` | 아이템 버리기 | O |
| `take` | `take:ground:itemId` | 바닥에서 줍기 | O |
| `take` | `take:unitId:itemId` | 유닛에서 가져오기 | O |
| `put` | `put:unitId:itemId` | 유닛에 넣기 | O |

### 아이템 메뉴 액션
| 액션 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| `item_ground_menu` | `item_ground_menu:itemId:count` | 바닥 아이템 메뉴 | O |
| `item_inv_menu` | `item_inv_menu:itemId:count` | 인벤토리 아이템 메뉴 | O |
| `item_unit_menu` | `item_unit_menu:unitId:itemId:count` | 유닛 아이템 메뉴 | O |
| `item_use` | `item_use:itemId` | 아이템 사용 | X (TODO) |
| `item_combine` | `item_combine:itemId` | 아이템 조합 | X (TODO) |
| `back_inventory` | `back_inventory` | 인벤토리로 돌아가기 | O |
| `back_unit` | `back_unit:unitId` | 유닛 화면으로 돌아가기 | O |

### 유닛 액션
| 액션 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| `look_unit` | `look_unit:unitId` | 유닛 살펴보기 | O |
| `action` | `action:actionType:unitId` | 유닛 대상 행동 실행 | O (ActionSystem 연동) |

### 시간 경과 액션
| 액션 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| `idle` | `idle:minutes` | 멍때리기 (시간 경과) | O |

---

## 2. 플레이어 명령 (PlayerSystem)

`RequestCommand(string cmd)` 형식으로 처리되는 명령들.

| 명령 | 형식 | 설명 | 구현 상태 |
|------|------|------|-----------|
| 이동 | `이동:regionId:localId` | 위치로 이동 스케줄 push | O |
| 휴식 | `휴식:minutes` | 시간만 경과 | O |

---

## 3. 유닛 액션 (ActionSystem)

`ApplyAction(user, action, targets)` 형식으로 처리되는 액션들.

### Self 액션 (대상 없음)
| 액션 ID | 설명 | 소요 시간 | 구현 상태 |
|---------|------|-----------|-----------|
| `rest` | 휴식 | 60분 | O (효과 TODO) |
| `sleep` | 수면 | 480분 | O (효과 TODO) |
| `wait` | 대기 | 15분 | O |

### 단일 대상 액션
| 액션 ID | 설명 | 소요 시간 | 구현 상태 |
|---------|------|-----------|-----------|
| `talk` | 대화 | - | X (TODO) |
| `trade` | 거래 | - | X (TODO) |
| `open` | 열기 (오브젝트) | - | X (TODO) |
| `examine` | 조사 | - | X (TODO) |

### 아이템 액션 (ApplyItemAction)
| 액션 ID | 설명 | 소요 시간 | 구현 상태 |
|---------|------|-----------|-----------|
| `pickup` | 줍기 | - | X (TODO) |
| `drop` | 버리기 | - | X (TODO) |
| `use` | 사용 | - | X (TODO) |
| `combine` | 조합 | - | X (TODO) |
| `give` | 주기 | - | X (TODO) |

---

## 4. 하드코딩된 행동 (DescribeSystem)

현재 `GetSituationText()`에서 하드코딩된 행동 목록:

```csharp
// 7. 행동 옵션
lines.Add("[color=yellow]행동:[/color]");
lines.Add("  [url=inventory]소지품 확인[/url]");
lines.Add("  [url=toggle:idle]▶ 멍때리기[/url][hidden=idle]");
lines.Add("    [url=idle:15]15분[/url]");
lines.Add("    [url=idle:30]30분[/url]");
lines.Add("    [url=idle:60]1시간[/url]");
lines.Add("    [url=idle:240]4시간[/url]");
lines.Add("  [/hidden=idle]");
```

### 하드코딩 행동 목록
| 행동 | 위치 | 데이터화 필요 |
|------|------|---------------|
| 소지품 확인 | GetSituationText | 플레이어 기본 행동 |
| 멍때리기 (15/30/60/240분) | GetSituationText | 시간 선택 옵션 |

---

## 5. 향후 개선 방향

### 데이터 기반 행동 정의
```json
{
  "playerActions": [
    {
      "id": "inventory",
      "name": "소지품 확인",
      "type": "ui",
      "always": true
    },
    {
      "id": "idle",
      "name": "멍때리기",
      "type": "toggle",
      "options": [
        {"label": "15분", "param": 15},
        {"label": "30분", "param": 30},
        {"label": "1시간", "param": 60},
        {"label": "4시간", "param": 240}
      ]
    }
  ]
}
```

### 유닛별 행동 정의
현재 `unit_data.json`의 `actions` 필드에서 정의:
```json
{
  "id": 1,
  "name": "철수",
  "actions": ["talk", "trade"]
}
```

### 아이템별 행동 정의
현재 `item_data.json`의 `actions` 필드에서 정의:
```json
{
  "id": 0,
  "name": "녹슨 열쇠",
  "actions": ["use"]
}
```

---

## 6. 액션 흐름도

```
사용자 클릭
    │
    ▼
MetaActionHandler.HandleAction(metaString)
    │
    ├─> UI 액션 (toggle, back, inventory 등)
    │       └─> TextUISystem 조작
    │
    ├─> 플레이어 명령 (move, idle)
    │       └─> PlayerSystem.RequestCommand()
    │               └─> 스케줄 Push / 시간 진행
    │
    └─> 유닛 액션 (action:type:unitId)
            └─> ActionSystem.ApplyAction()
                    └─> ActionResult 반환
                            └─> TextUISystem.ShowResult()
```
