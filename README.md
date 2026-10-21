# 콘솔 가계부

수입·지출을 JSONL 파일에 저장하는 Python CLI입니다. 거래 추가·조회·수정·삭제·검색, 월별 요약, 예산·카테고리 관리와 CSV 가져오기·내보내기를 지원합니다.

## 실행

Python 3.10 이상이 필요합니다. 표준 라이브러리만 사용하므로 별도 패키지를 설치하지 않습니다. `budget_app/`이 있는 프로젝트 루트에서 실행합니다. 아래 셸 예시는 Bash 기준입니다.

```bash
python -m budget_app --help
python -m budget_app --data-dir ./sample-data category list
python -m budget_app --data-dir ./sample-data add
python -m budget_app --data-dir ./sample-data list --limit 3
```

`--data-dir`는 실행할 명령 **앞에** 지정합니다. 생략하면 현재 작업 폴더 기준 `./data`를 사용합니다. 상대 경로인 CSV 입력·출력 경로도 현재 작업 폴더 기준입니다.

명령 없이 실행하거나 `--help`를 요청하면 도움말만 출력합니다. 모든 명령·하위 명령에 `--help`가 있으며 도움말·명령 누락·옵션 구문 및 형식 오류에서는 데이터 폴더를 생성하지 않습니다. 카테고리 등록 여부와 CSV 내용 검사는 데이터 폴더를 준비한 뒤 수행합니다.

```bash
python -m budget_app category add --help
python -m budget_app budget set --help
python -m budget_app import --help
python -m budget_app export --help
```

## 명령 사용법

### 거래 추가·목록

`add`는 날짜 → 타입 → 카테고리 → 금액 → 메모 → 태그 순서로 입력받습니다. 카테고리 입력 전에 등록 목록을 보여주며 필수 값이 잘못되면 해당 필드만 다시 입력받습니다.

```text
날짜(YYYY-MM-DD): 2024-01-15
타입(income/expense): expense
카테고리: food
금액(양수 정수): 15000
메모(선택): 점심
태그(쉼표로 구분, 없으면 엔터): meal,lunch
```

저장이 끝나면 생성된 ID를 출력합니다. 메모·태그는 엔터로 생략할 수 있습니다. 날짜·타입·카테고리·금액 입력은 앞뒤 공백을 제거하며, 메모는 원문을 유지하고 태그는 쉼표로 나눠 각 항목의 공백을 제거합니다.

```bash
python -m budget_app --data-dir ./sample-data add
python -m budget_app --data-dir ./sample-data list
python -m budget_app --data-dir ./sample-data list --limit 3
```

`list --limit N`은 양수 정수를 받으며 기본값은 `20`입니다. 날짜 내림차순, 같은 날짜는 ID 문자열 오름차순으로 출력합니다.

각 거래 행의 출력 형식은 다음과 같습니다.

```text
ID | 날짜 | 타입 | 카테고리 | 금액 | 메모 | 태그
```

거래가 없으면 `거래 내역이 없습니다.`를 출력합니다.

### 거래 수정·삭제

수정은 **옵션 방식**입니다. 아래 `TX-...`는 `add` 또는 `list`에서 확인한 실제 거래 ID로 바꿉니다.

```bash
python -m budget_app --data-dir ./sample-data update --id TX-... --date 2024-01-20 --amount 18000
python -m budget_app --data-dir ./sample-data update --id TX-... --memo "" --tags ""
python -m budget_app --data-dir ./sample-data delete --id TX-...
```

`update`는 `--id`와 함께 `--date`, `--type`, `--category`, `--amount`, `--memo`, `--tags` 중 하나 이상이 필요합니다. 생략한 필드는 유지하며 빈 문자열의 메모·태그는 비웁니다. ID는 변경할 수 없고 날짜가 바뀌면 정렬 위치도 바뀝니다.

`delete --id`는 지정한 거래 한 건을 삭제합니다. 없는 ID를 수정·삭제하면 오류와 목록 확인 힌트를 출력하고 코드 `1`로 종료합니다.

### 거래 검색

```bash
python -m budget_app --data-dir ./sample-data search --from 2024-01-01 --to 2024-01-31
python -m budget_app --data-dir ./sample-data search --category food --type expense --q 점심 --tag meal
```

| 옵션 | 조건 |
| --- | --- |
| `--from`, `--to` | 해당 날짜 포함, 한쪽 날짜만 지정 가능 |
| `--category` | 등록된 카테고리 이름과 정확히 일치 |
| `--type` | `income` 또는 `expense` |
| `--q` | 메모에 포함된 부분 문자열 |
| `--tag` | 태그 한 개와 정확히 일치 |

여러 조건은 모두 만족해야 하며 시작일은 종료일보다 늦을 수 없습니다. 문자열은 대소문자를 구분하고 공백을 자동으로 정리하지 않습니다. 빈 카테고리·검색어·태그는 거부하며 `--tag`는 쉼표로 분리하지 않습니다.

조건이 없으면 전체 거래를 조회합니다. 검색에는 건수 제한이 없으며 최신순으로 출력합니다. 결과가 없으면 안내 문구와 코드 `0`으로 종료합니다.

### 월별 요약·예산

```bash
python -m budget_app --data-dir ./sample-data summary --month 2024-01 --top 3
python -m budget_app --data-dir ./sample-data budget set --month 2024-01 --amount 500000
python -m budget_app --data-dir ./sample-data budget show --month 2024-01
```

- `summary`는 `--month YYYY-MM`이 필수이며 양수 정수 `--top N`의 기본값은 `5`입니다.
- 총수입·총지출·잔액과 지출 카테고리 TOP N을 출력합니다. 잔액은 총수입에서 총지출을 뺀 정수이며 음수도 표시합니다.
- 지출 합계 내림차순, 동률이면 카테고리 이름 오름차순입니다. 수입은 지출 순위에 포함하지 않습니다.
- `budget set/show`는 `--month`가 필수이며 `set`에는 양수 정수 `--amount`도 필요합니다. 같은 월 재설정은 해당 월의 금액만 바꿉니다.
- 예산 사용률은 `총지출 / 예산 * 100`이며 소수점 한 자리로 반올림합니다. 수입을 빼지 않으며 실제 지출이 예산보다 클 때 초과 금액과 경고를 출력합니다.
- 예산과 같은 지출에는 경고하지 않습니다. 표시가 `100.0%`로 반올림되어도 실제로 초과했다면 경고합니다. 경고의 종료 코드는 `0`입니다.
- 거래가 없는 달에도 예산 상태를 표시합니다. 거래가 없거나 수입만 있는 달은 설정된 예산의 사용률을 `0.0%`로 표시하며, 수입만 있으면 지출 없음도 안내합니다. 예산이 없으면 미설정 안내를 출력합니다.

### 카테고리

```bash
python -m budget_app --data-dir ./sample-data category list
python -m budget_app --data-dir ./sample-data category add
python -m budget_app --data-dir ./sample-data category remove
```

추가·삭제는 카테고리명을 대화형으로 입력받습니다. 이름의 앞뒤 공백을 제거하고 대소문자를 구분합니다. 빈 이름·중복 이름 추가는 거부하며, 없는 이름이나 거래에서 사용하는 카테고리는 삭제할 수 없습니다.

## 저장 위치와 형식

유효한 데이터 명령을 처음 실행하면 저장 폴더와 없는 파일을 생성합니다. 기존 파일은 덮어써서 초기화하지 않습니다. 카테고리 파일이 비어 있으면 `food`, `transport`, `rent`, `salary`, `etc`를 채웁니다. 마지막 카테고리를 삭제한 경우에도 다음 데이터 명령에서 기본값이 다시 생성됩니다.

각 파일은 UTF-8 JSONL이며 한 줄에 JSON 객체 하나를 저장합니다.

| 파일 | 저장 내용 예시 |
| --- | --- |
| `transactions.jsonl` | `{"id":"TX-1","type":"expense","date":"2024-01-15","amount":15000,"category":"food","memo":"점심","tags":["meal"]}` |
| `categories.jsonl` | `{"name":"food"}` |
| `budgets.jsonl` | `{"month":"2024-01","amount":500000}` |

거래 필드는 다음과 같습니다. `TX-1`은 형식 설명용 예시이며 CLI는 `TX-` 뒤에 UUID의 32자리 식별자를 붙여 ID를 생성합니다.

| 필드 | 조건 |
| --- | --- |
| `id` | 비어 있지 않은 유일한 문자열, 수정 불가 |
| `type` | `income` 또는 `expense` |
| `date` | 실제 `YYYY-MM-DD` 날짜 |
| `amount` | 양수 정수, 0·음수·소수·불리언 거부 |
| `category` | 등록된 카테고리 이름 |
| `memo` | 문자열, 기본값 `""` |
| `tags` | 문자열 배열, 기본값 `[]` |

거래 파일 자체의 정렬을 유지합니다. 행 형식·필드 값·정렬 순서가 손상되면 파일과 행 번호가 있는 오류를 출력합니다.

추가·수정·삭제와 카테고리·예산 저장은 같은 폴더의 임시 파일에 쓴 뒤 입력·출력 파일을 닫고 `os.replace()`로 교체합니다. 처리 실패 시 원본을 유지하고 임시 파일을 정리합니다. 쓰기는 단일 프로세스 사용을 전제로 하며 파일 잠금은 없습니다.

거래를 변경할 때마다 파일 전체를 재작성합니다. CSV 가져오기도 정상 행마다 이 방식을 사용하므로 대량 가져오기 시간은 입력 건수와 기존 거래 수에 따라 증가합니다.

## CSV 형식과 처리 정책

### 스키마

```csv
date,type,category,amount,memo,tags
2024-01-15,expense,food,15000,"점심, 커피","meal,lunch"
2024-01-31,income,salary,3000000,월급,
```

| 열 | 필수 | 값 |
| --- | --- | --- |
| `date` | 예 | 실제 `YYYY-MM-DD` 날짜 |
| `type` | 예 | `income`, `expense` |
| `category` | 예 | 등록된 카테고리 이름 |
| `amount` | 예 | 양수 정수 문자열 |
| `memo` | 아니오 | 문자열 |
| `tags` | 아니오 | 쉼표로 구분한 태그 |

입력은 UTF-8이며 BOM도 허용합니다. 헤더 순서는 바꿀 수 있고 선택 열은 헤더에서 생략할 수 있습니다. 헤더에 포함한 열은 빈 값도 셀 개수에 맞게 작성합니다. 완전히 빈 줄은 무시합니다.

쉼표·줄바꿈이 있는 셀은 큰따옴표로 감싸고, 셀 안의 큰따옴표는 `""`로 씁니다. CSV 작성기·판독기가 인용을 처리합니다. 태그는 셀 안에서 다시 쉼표로 나누며 빈 항목은 제외합니다.

### 가져오기

```bash
python -m budget_app --data-dir ./sample-data import --from ./input.csv
```

행마다 새 ID를 생성합니다. CSV에 ID 열을 넣지 않습니다. 같은 파일을 재가져오면 별도 거래가 추가되며 내용 중복은 제거하지 않습니다.

| 입력 상태 | 처리 |
| --- | --- |
| 정상 행 | 정렬을 유지해 건별 저장 |
| 잘못된 날짜·타입·금액·카테고리, 셀 개수 오류 | 행 번호·원인·힌트 출력 후 건너뜀 |
| 필수 열 누락·중복·알 수 없는 열·빈 파일 | 헤더 오류로 거래 저장 전에 중단 |
| 헤더만 있는 파일 | `imported=0, skipped=0`, 정상 종료 |
| 읽기·인코딩·CSV 구문·저장 오류 | 즉시 중단하고 실제 반영·건너뜀 건수 안내 |

오류 행 번호는 레코드의 **마지막 물리 행 번호**입니다. 여러 줄 메모나 빈 줄이 있으면 레코드 순번과 다를 수 있습니다.

정상적으로 파일 끝까지 처리하면 `[완료] imported=N, skipped=M`을 출력합니다. 건너뛴 행이 있으면 코드 `2`, 없으면 `0`입니다. 읽기·저장 오류로 중단하면 코드 `1`이며 앞서 저장한 거래는 유지합니다. 헤더 오류의 종료 코드는 `2`입니다. 중단 예외에는 건수와 마지막으로 읽은 CSV 행을 포함합니다.

### 내보내기

```bash
python -m budget_app --data-dir ./sample-data export --out ./january.csv --month 2024-01
python -m budget_app --data-dir ./sample-data export --out ./period.csv --from 2024-01-01 --to 2024-01-31
```

`--out`과 월 또는 시작일·종료일 한 쌍이 필요합니다. 월·기간은 함께 사용할 수 없으며 양 끝 날짜를 포함합니다. 시작일은 종료일보다 늦을 수 없습니다. 출력의 부모 폴더는 이미 있어야 합니다.

헤더는 `date,type,category,amount,memo,tags` 순서로 고정하며 최신순으로 출력합니다. ID는 제외합니다. 결과가 없어도 헤더를 저장하고 `0건`으로 안내합니다.

기존 출력 파일이 있으면 전체 작성이 끝난 뒤 교체합니다. 읽기·쓰기·교체 실패 시 기존 출력을 보존합니다. 내부 JSONL 파일과 같은 출력 경로는 상대 경로·심볼릭 링크·하드 링크를 포함해 거부합니다.

## 오류와 종료 코드

오류는 표준 오류로 원인과 `[힌트]`를 출력하며 스택트레이스를 출력하지 않습니다. CSV의 건너뛴 행은 `[건너뜀]`으로 안내합니다.

| 코드 | 의미 |
| --- | --- |
| `0` | 정상 처리·도움말·빈 조회·예산 미설정·예산 초과 경고 |
| `2` | 입력·헤더 검증 오류 또는 오류 행을 건너뛰고 마친 가져오기 |
| `1` | 없는 거래 ID·삭제 불가능한 카테고리·저장 데이터 손상·파일 작업 실패·입력 종료 등 |
| `130` | `Ctrl+C`로 취소 |

명령 직후 `echo $?`로 종료 코드를 확인할 수 있습니다. `add`의 잘못된 필수 입력은 재입력하므로 최종 저장에 성공하면 코드 `0`입니다.

목록은 `--limit`까지만 읽습니다. 검색·요약·내보내기와 거래 저장은 파일 끝까지 검사합니다. 검색 중 뒤쪽 손상을 발견하면 이미 출력한 행이 있을 수 있습니다. 요약은 읽기가 끝난 후 출력하며 내보내기는 읽기가 끝난 후 파일을 교체합니다.

## 사용자 확인 절차

아래 내용은 사용자가 실행할 절차와 기대 결과입니다. 문서는 소스와 정적으로 대조했으며 빌드·테스트·프로그램 실행 결과는 아직 확인하지 않았습니다.

### 정상·오류·재실행 후 영속성

기존 데이터와 다른 **비어 있는 `./check-data` 경로**를 사용합니다. 프로젝트 루트에 다음 내용으로 `check.csv`를 직접 만듭니다.

```csv
date,type,category,amount,memo,tags
2024-01-15,expense,food,15000,"점심, 커피","meal,lunch"
2024-01-31,income,salary,3000000,월급,
2024-02-30,expense,food,1000,날짜 오류,
```

```bash
python -m budget_app --data-dir ./check-data import --from ./check.csv
echo $?
python -m budget_app --data-dir ./check-data list
python -m budget_app --data-dir ./check-data budget set --month 2024-01 --amount 10000
python -m budget_app --data-dir ./check-data summary --month 2024-01
python -m budget_app --data-dir ./check-data search --q 점심 --tag meal
python -m budget_app --data-dir ./check-data export --out ./check-output.csv --month 2024-01
```

| 확인 | 기대 결과 |
| --- | --- |
| 가져오기 | 날짜 오류 행 안내, `imported=2, skipped=1`, 코드 `2` |
| 목록 | 1월 31일 수입 다음 1월 15일 지출 |
| 요약 | 수입 `3000000`, 지출 `15000`, 잔액 `2985000`, 사용률 `150.0%`, `5000원` 초과 경고 |
| 검색 | 점심 메모와 `meal` 태그가 있는 지출 1건 |
| 내보내기 | 헤더와 정상 거래 2건, 코드 `0` |
| 재실행 | 터미널을 닫고 같은 작업 폴더·`--data-dir`로 `list`, `budget show --month 2024-01`을 다시 실행하면 2건과 예산 `10000원` 유지 |

다음 확인은 위 결과를 확인한 뒤 수행합니다.

| 확인 | 실행·기대 결과 |
| --- | --- |
| 대화형 추가·재입력 | `add`에서 잘못된 날짜·0 금액을 먼저 입력한 뒤 올바른 값으로 바꾸면 현재 필드 재입력 후 저장 ID 출력 |
| 일부 수정 | 실제 ID에 `update --id TX-... --amount 18000`을 적용하면 ID·다른 필드는 유지 |
| 날짜 재배치 | `--date`를 바꾼 뒤 `list`에서 최신순·같은 날짜 ID 순서 유지 |
| 선택 값 비우기 | `update --id TX-... --memo "" --tags ""` 후 메모·태그가 비어 있음 |
| 삭제 | 실제 ID를 `delete --id`로 삭제하면 해당 거래만 사라지고 재실행 후에도 유지 |
| 없는 ID | `delete --id missing`은 코드 `1`과 힌트, 나머지 데이터 유지 |
| 카테고리 보호 | `category remove`에 사용 중인 이름을 입력하면 코드 `1`로 차단 |
| 빈 월 | `summary --month 2030-01`은 거래 없음·예산 미설정 안내와 코드 `0` |
| 인자 오류 | `list --limit 0`, `summary --month 2024-13`, `export --out x.csv --from 2024-01-01`은 코드 `2` |

마지막 인자 오류 확인에 새 `--data-dir ./not-created-check`를 지정하면 해당 폴더는 생성되지 않아야 합니다.

### 대용량 스트리밍 확인

아래 코드는 임시 폴더에 정렬된 JSONL을 직접 만들어 초기 데이터 준비 시간을 줄입니다. 애플리케이션의 추가 명령으로 대량 파일을 만드는 코드는 아닙니다.

```bash
python - <<'PY'
import json
import tracemalloc
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from budget_app.cli import main
from budget_app.repositories import TransactionRepository, initialize_stores
from budget_app.services import summarize_month

with TemporaryDirectory() as folder:
    data_dir = Path(folder)
    initialize_stores(data_dir)
    repository = TransactionRepository(data_dir)
    for count in (10000, 100000):
        with repository.path.open("w", encoding="utf-8") as output:
            for index in range(count):
                record = dict(
                    id=f"TX-{index:06d}", type="expense", date="2024-01-15",
                    amount=1, category="food", memo="", tags=[],
                )
                output.write(json.dumps(record) + "\n")
        listing = StringIO()
        with redirect_stdout(listing):
            assert main(["--data-dir", str(data_dir), "list", "--limit", "3"]) == 0
        assert len(listing.getvalue().splitlines()) == 3
        tracemalloc.start()
        assert summarize_month("2024-01", repository) == (0, count, {"food": count})
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"거래={count}건, 집계 중 최대 메모리={peak}바이트")
PY
```

두 크기 모두 목록 3건과 정확한 합계를 확인합니다. 카테고리 수가 같은 경우 거래 수가 10배로 늘어도 집계 메모리가 거래 수에 비례해 증가하지 않는지 비교합니다. 메모리 수치는 실행 환경에 따라 달라 고정 통과값을 두지 않습니다.

### 저장 실패·원본 보존 확인

아래 코드는 임시 데이터에서 파일 교체 실패를 주입합니다. JSONL·CSV 원본 보존과 임시 파일 정리, 가져오기 중단 전 반영을 확인합니다.

```bash
python - <<'PY'
import csv
import os
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_app.cli import main
from budget_app.models import Transaction
from budget_app.repositories import (
    CSV_FIELDS, BudgetStore, CategoryStore, TransactionRepository, initialize_stores,
)
from budget_app.services import export_transactions
from budget_app.validators import parse_date

with TemporaryDirectory() as folder:
    root = Path(folder)
    data_dir = root / "data"
    initialize_stores(data_dir)
    transactions, categories, budgets = (
        TransactionRepository(data_dir), CategoryStore(data_dir), BudgetStore(data_dir),
    )
    first = Transaction(
        id="TX-A", type="expense", date=parse_date("2024-01-15"), amount=100, category="food",
    )
    transactions.insert(first)
    budgets.save({"2024-01": 1000})
    output = root / "output.csv"
    output.write_bytes(b"keep original")
    original = {path: path.read_bytes() for path in data_dir.glob("*.jsonl")}
    actions = (
        lambda: transactions.insert(replace(first, id="TX-B")),
        lambda: transactions.update(replace(first, amount=200)),
        lambda: transactions.delete(first.id),
        lambda: categories.save([*categories.load(), "custom"]),
        lambda: budgets.save({"2024-01": 2000}),
        lambda: export_transactions(output, categories, transactions, month="2024-01"),
    )
    with patch("budget_app.repositories.os.replace", side_effect=OSError("교체 실패")):
        for action in actions:
            try:
                action()
            except OSError:
                pass
            else:
                raise AssertionError("교체 실패가 전달되지 않았습니다.")
            assert all(path.read_bytes() == content for path, content in original.items())
            assert output.read_bytes() == b"keep original"
            assert not list(root.rglob(".*.tmp"))

    source = root / "input.csv"
    with source.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_FIELDS)
        writer.writerows([["2024-01-15", "expense", "food", "50", "", ""]] * 2)
    real_replace = os.replace
    saved = []

    def fail_second(temporary, destination):
        if Path(destination) == transactions.path and saved:
            raise OSError("두 번째 거래 교체 실패")
        real_replace(temporary, destination)
        if Path(destination) == transactions.path:
            saved.append(transactions.path.read_bytes())

    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr), patch(
        "budget_app.repositories.os.replace", side_effect=fail_second,
    ):
        code = main(["--data-dir", str(data_dir), "import", "--from", str(source)])
    assert code == 1 and "imported=1, skipped=0" in stderr.getvalue()
    assert "[완료]" not in stdout.getvalue()
    assert transactions.path.read_bytes() == saved[0]
    assert not list(root.rglob(".*.tmp"))

    broken = transactions.path.read_bytes() + b"{broken}\n"
    transactions.path.write_bytes(broken)
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = main(["--data-dir", str(data_dir), "summary", "--month", "2024-01"])
    assert code == 1 and stdout.getvalue() == ""
    assert "[오류]" in stderr.getvalue() and "[힌트]" in stderr.getvalue()
    assert transactions.path.read_bytes() == broken
    assert not list(root.rglob(".*.tmp"))

print("저장 실패·부분 반영 확인 완료")
PY
```

## 코드 구성

| 파일 | 역할 |
| --- | --- |
| `budget_app/__main__.py` | CLI 호출과 프로세스 종료 코드 전달 |
| `budget_app/cli.py` | 명령 해석·대화형 입력·결과 출력 |
| `budget_app/services.py` | 검증·집계·가져오기 등 업무 처리 |
| `budget_app/repositories.py` | JSONL·CSV 입출력·정렬·임시 파일 교체 |
| `budget_app/models.py` | 불변 `Transaction` dataclass와 생성 시 검증 |
| `budget_app/validators.py` | 입력값 검사·변환 |
| `budget_app/errors.py` | 원인·힌트를 담는 예외 |
| `budget_app/decorators.py` | CLI 공통 오류 처리 데코레이터 |
| `budget_app/__init__.py` | 패키지 정의 |

거래 조회는 제너레이터로 한 건씩 읽습니다. 서비스·저장소는 직접 입력하거나 출력하지 않으며, `@handle_errors`가 예외를 메시지·종료 코드로 바꿉니다. 함수·모델에는 타입 힌트를 사용합니다.
