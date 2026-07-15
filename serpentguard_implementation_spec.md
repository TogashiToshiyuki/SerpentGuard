# SerpentGuard 実装仕様書

## 1. 文書情報

| 項目           | 内容                                                        |
| -------------- | ----------------------------------------------------------- |
| プロジェクト名 | SerpentGuard                                                |
| 副題           | AI-assisted preflight checker for Serpent input files       |
| 想定カテゴリ   | Developer Tools                                             |
| 対象           | Serpent 2系の代表的な入力構文                               |
| 実装言語       | Python 3.11以降                                             |
| UI             | StreamlitによるローカルWebアプリケーション                  |
| 開発方針       | 小さく完成させ、段階的に機能を追加する                      |
| 本文書の目的   | Codexに段階的に実装させるための要求仕様と作業手順を定義する |

---

## 2. プロジェクト概要

SerpentGuardは、Serpent Monte Carlo計算を開始する前に入力ファイルを検査し、入力ミスや設定上の要確認事項を提示する軽量なpreflight checkerである。

主な対象は次のとおりである。

- 重複定義
- 未定義オブジェクトの参照
- 単純なcell領域式の矛盾
- 対応可能な範囲における幾何学的overlap候補
- どのcellにも属さないundefined region候補
- detector設定の基本的不整合
- AIによる警告内容の説明と確認手順の提案

本ツールは、Serpent本体の入力検査、geometry plotter、計算実行を置き換えるものではない。
また、入力体系の物理的妥当性や安全性を保証するものではない。

---

## 3. 開発目標

### 3.1 最終的に実現する利用フロー

1. ユーザーがSerpent入力ファイルを選択する。
2. 必要に応じて解析目的を入力する。
3. `Run check`を押す。
4. ローカルで静的解析を行う。
5. エラー、警告、参考情報を一覧表示する。
6. 対応可能な単純形状について2次元の幾何学サンプリング結果を表示する。
7. ユーザーがAIへ送信されるJSONを確認する。
8. ユーザーが明示的に`Generate AI explanation`を押した場合だけAI APIを呼び出す。
9. AIがfindingsの意味、優先順位、確認方法を説明する。

### 3.2 MVPの成功条件

次のデモが一連の操作として成立することをMVP完成条件とする。

- 正常な入力では重大なエラーが表示されない。
- 未定義surfaceを参照する入力では該当行を示す。
- 同一名称の重複定義を検出する。
- 単純なcell領域式の論理矛盾を検出する。
- 単純な2次元体系でoverlapまたはundefined region候補を可視化する。
- AIなしでも静的解析機能が動作する。
- AIへ生のSerpent入力を送信せず、構造化されたfindingsのみを送る。
- AI呼び出し前に送信内容を画面で確認できる。

---

## 4. 想定ユーザー

- Serpentを利用する大学院生、研究者、技術者
- 入力ファイルの改変時に単純ミスを減らしたい利用者
- 複雑な体系で参照関係を見落としやすい利用者
- Serpent入力に習熟途中の利用者
- 計算資源を投入する前に簡易点検を行いたい利用者

---

## 5. アプリケーション形態

### 5.1 ローカルWebアプリケーション

UIにはStreamlitを使用する。

起動例：

```bash
streamlit run app.py
```

ブラウザから次のようなローカルURLへアクセスする。

```text
http://localhost:8501
```

Streamlitは内部的にはローカルPC上でHTTPプロセスを起動するが、本プロジェクトでは次の運用を前提とする。

- 外部サーバーへデプロイしない。
- インターネットへ公開しない。
- Serpent入力の静的解析はユーザーのPC内で完結する。
- AI説明機能を使用するときだけOpenAI APIへ限定的なJSONを送信する。
- AI機能を使用しない場合は、原則として外部通信を必要としない。

### 5.2 UIレイアウト

初期版は次の程度の単純な構成とする。

```text
┌──────────────────────────────┐
│ Upload Serpent input         │
│ Analysis purpose             │
│ Run check                    │
├──────────────────────────────┤
│ 2 Errors | 1 Warning | 3 Info│
├──────────────────────────────┤
│ Findings table               │
├──────────────────────────────┤
│ Geometry plot                │
├──────────────────────────────┤
│ AI explanation               │
└──────────────────────────────┘
```

#### 上部入力領域

- メイン入力ファイルのアップロード
- 補助ファイルのアップロード
- 解析目的の任意入力
- `Run check`ボタン

#### Summary領域

- Error件数
- Warning件数
- Review件数
- Info件数
- パースしたsurface、cell、material、detectorの件数

#### Findings table

表示項目：

| Severity | Rule ID | File | Line | Object | Message |
| -------- | ------- | ---- | ---: | ------ | ------- |

必要な操作：

- Severityによるフィルター
- Rule IDによるフィルター
- 行番号順または重大度順の並べ替え
- findingごとの詳細展開
- 根拠データのJSON表示

#### Geometry plot

- XY断面の2次元表示
- 正常領域
- overlap候補
- undefined region候補
- 使用したサンプリング解像度
- 対応外surfaceや除外cellの表示

#### AI explanation

- AIへ送信するJSONのプレビュー
- `Generate AI explanation`ボタン
- AIの要約
- 優先度付きfindings
- 推奨確認手順
- 制限事項
- APIエラー時の説明

---

## 6. 重要なプライバシー方針

初期版では次を必須要件とする。

- 静的解析はローカルで実施する。
- AIには原則としてfindingsのJSONだけ送る。
- 生入力送信は初期版では実装しない。
- AIへ送信する内容をUIに表示する。
- ユーザーが明示的にボタンを押した場合のみ送信する。
- APIキーをソースコード、Git履歴、ログへ保存しない。
- AI機能は任意機能とし、APIキーがなくてもアプリを利用できる。
- 送信JSONには、必要のないファイルパス、ユーザー名、核データライブラリの絶対パス等を含めない。
- AI送信前に、入力由来の自由記述文字列を最小化または匿名化する。

### 6.1 AIへ送信してよい情報

- オブジェクト数
- rule ID
- severity
- 短いfindingメッセージ
- 対象オブジェクト名
- 元入力内の相対行番号
- 幾何学サンプリングの統計値
- ユーザーが入力した解析目的
- detectorの限定的な構造化情報

### 6.2 AIへ送信しない情報

- 入力ファイル全文
- コメント全文
- 未公開の幾何学定義全文
- 材料組成全文
- 核種組成全文
- 絶対ファイルパス
- 環境変数
- APIキー
- Serpent実行ファイルの場所
- 核データライブラリの場所
- その他、静的解析結果の説明に不要な生データ

---

## 7. 参照するSerpent構文例

実物の構文例およびテストケースの基礎資料として、Serpent公式Wikiのexample input collectionを用いる。

- Collection of example input files
  [https://serpent.vtt.fi/mediawiki/index.php/Collection_of_example_input_files](https://serpent.vtt.fi/mediawiki/index.php/Collection_of_example_input_files)

同ページには、2D BWR、CANDU、VVER、PWR MOX/UOX、burnup、transient、benchmark等の複数の入力例が掲載されている。

### 7.1 利用方針

- 公式example inputを、実際のカード配置と構文表現を確認するために使用する。
- 公式example inputをそのまま完全対応させることをMVP要件にはしない。
- テストには、公式例から必要最小限の構文を抽出した小型fixtureを作成する。
- 問題を含むテスト入力は、公式例を直接破壊するのではなく、最小例を複製して意図的なミスを挿入する。
- 各fixtureについて、出典、改変内容、期待findingを記録する。
- ライセンスや再配布条件が不明確な場合、公式入力全文をリポジトリへ無断転載せず、取得手順や参照URLを記載する。
- 自動ダウンロード機能は初期版では必須としない。
- ネットワークに依存しないテストができるよう、リポジトリ内には独自作成した最小fixtureを置く。

### 7.2 最初に参照する例

MVPでは次の順番で構文を確認する。

1. 単純な2D assembly geometry
2. 2D PWR pin-cell burnup example
3. detectorを含むVVERまたはgroup constant generation例
4. includeによる複数ファイル構成を含む例

---

## 8. スコープ

### 8.1 初期対応カード

MVPで正式に対応するカード：

- `surf`
- `cell`
- `mat`

部分対応：

- `include`
- `det`
- `ene`
- `set`

認識のみ行う候補：

- `pin`
- `lat`

対応外カードはアプリを停止させず、`INFO` findingとして記録するか、unknown cardとして保持する。

### 8.2 初期対応surface

具体的なsurface keywordは、公式ドキュメントとexample inputを確認して確定する。MVPでは次の幾何形状に相当する少数のsurfaceのみを対象とする。

- 円柱
- 球
- 軸に平行な平面
- 直方体または矩形境界

すべてのSerpent surface型へ対応しない。

### 8.3 初期対応cell領域式

- signed surface reference
- 空白区切りのintersection
- `:`によるunion
- 丸括弧
- 単純なsurface名または数値ID

初期版では、次を完全対応しなくてよい。

- cell complement
- 深い入れ子
- transformed universe
- repeated structure
- latticeの完全展開
- 任意の3次元CSG
- Serpent本体と完全に同一な領域評価

---

## 9. 非目標

初期版では次を行わない。

- Serpent入力仕様全体の完全実装
- Serpent本体と同一のパーサーの再実装
- 任意形状に対する厳密な幾何学証明
- すべてのoverlapやundefined regionの保証付き検出
- 計算結果の妥当性評価
- 臨界性や安全性の判定
- 核データライブラリの完全検査
- depletion入力の完全検証
- 自動で入力ファイルを書き換える機能
- AIが生成した修正版を無確認で適用する機能
- 公開Webサービスとしての運用
- ユーザー認証
- データベース
- 複数ユーザー対応
- クラウド保存

---

## 10. アーキテクチャ

```text
Uploaded files
      │
      ▼
Local preprocessor
  - newline normalization
  - comment handling
  - include resolution
  - source location tracking
      │
      ▼
Pragmatic parser
  - card classification
  - limited AST
  - unknown-card preservation
      │
      ├─────────────────┐
      ▼                 ▼
Symbol table        Geometry representation
      │                 │
      ▼                 ▼
Static rules        2D sampling checker
      │                 │
      └────────┬────────┘
               ▼
         Findings JSON
               │
       ┌───────┴────────┐
       ▼                ▼
 Local UI/report   Optional AI reviewer
                         │
                  explicit user action
```

---

## 11. 推奨技術構成

### 11.1 必須

- Python 3.11または3.12
- Streamlit
- Pydantic
- NumPy
- matplotlib
- pytest
- OpenAI Python SDK
- Git
- GitHub

### 11.2 推奨開発ツール

- Ruff
- mypyまたはPyright
- pre-commit
- GitHub Actions

### 11.3 実装原則

- 単純な手書きパーサーから開始する。
- 初期段階では完全なformal grammarを作らない。
- 静的解析結果をAI出力より優先する。
- 対応外構文を推測で処理しない。
- 解析できない場合は、解析不能であることをfindingとして表示する。
- geometry checkerでは偽陽性・偽陰性の可能性を明記する。
- 例外を握り潰さない。
- 行番号、ファイル名、対象オブジェクトを可能な限り保持する。
- UIロジックと解析ロジックを分離する。
- AIなしでテスト可能な設計にする。

---

## 12. ディレクトリ構成

```text
serpentguard/
├── app.py
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .env.example
├── .pre-commit-config.yaml
├── src/
│   └── serpentguard/
│       ├── __init__.py
│       ├── models.py
│       ├── diagnostics.py
│       ├── preprocessor.py
│       ├── parser.py
│       ├── symbol_table.py
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── definitions.py
│       │   ├── references.py
│       │   ├── regions.py
│       │   └── detectors.py
│       ├── geometry/
│       │   ├── __init__.py
│       │   ├── surfaces.py
│       │   ├── regions.py
│       │   └── sampler.py
│       ├── ai/
│       │   ├── __init__.py
│       │   ├── payload.py
│       │   ├── reviewer.py
│       │   └── prompts.py
│       ├── reporting.py
│       └── cli.py
├── tests/
│   ├── fixtures/
│   ├── test_preprocessor.py
│   ├── test_parser.py
│   ├── test_rules_definitions.py
│   ├── test_rules_references.py
│   ├── test_rules_regions.py
│   ├── test_geometry.py
│   └── test_ai_payload.py
├── examples/
│   ├── README.md
│   ├── valid_minimal.inp
│   ├── duplicate_surface.inp
│   ├── undefined_surface.inp
│   ├── contradictory_cell.inp
│   ├── overlap_2d.inp
│   └── undefined_region_2d.inp
├── docs/
│   ├── specification.md
│   ├── supported_syntax.md
│   ├── supported_checks.md
│   ├── privacy.md
│   └── example_sources.md
└── .github/
    └── workflows/
        └── ci.yml
```

---

## 13. データモデル

Pydanticを用いて以下を定義する。

### 13.1 SourceLocation

```python
class SourceLocation(BaseModel):
    file_name: str
    line_start: int
    line_end: int
```

### 13.2 Surface

```python
class Surface(BaseModel):
    name: str
    surface_type: str
    parameters: list[float | str]
    location: SourceLocation
    raw_text: str
```

### 13.3 Cell

```python
class Cell(BaseModel):
    name: str
    universe: str
    material: str | None
    region_expression: str
    referenced_surfaces: list[str]
    location: SourceLocation
    raw_text: str
```

### 13.4 Material

```python
class Material(BaseModel):
    name: str
    density: float | None
    location: SourceLocation
    raw_text: str
```

### 13.5 Detector

```python
class Detector(BaseModel):
    name: str
    options: dict[str, list[str]]
    referenced_energy_grids: list[str]
    location: SourceLocation
    raw_text: str
```

### 13.6 UnknownCard

```python
class UnknownCard(BaseModel):
    keyword: str
    tokens: list[str]
    location: SourceLocation
    raw_text: str
```

### 13.7 ParsedModel

```python
class ParsedModel(BaseModel):
    surfaces: list[Surface]
    cells: list[Cell]
    materials: list[Material]
    detectors: list[Detector]
    unknown_cards: list[UnknownCard]
    source_files: list[str]
```

### 13.8 Finding

```python
class Finding(BaseModel):
    rule_id: str
    severity: Literal["ERROR", "WARNING", "REVIEW", "INFO"]
    title: str
    message: str
    location: SourceLocation | None
    object_type: str | None
    object_name: str | None
    evidence: dict[str, Any]
    confidence: Literal["high", "medium", "low"]
```

### 13.9 AnalysisReport

```python
class AnalysisReport(BaseModel):
    model_summary: dict[str, int]
    findings: list[Finding]
    geometry_summary: dict[str, Any] | None
    limitations: list[str]
```

---

## 14. Severity定義

### ERROR

静的に高い確度で不正と判断できる問題。

例：

- 未定義surface参照
- 未定義material参照
- 同一スコープ内の重大な重複定義
- 数値として解釈不能な必須引数
- include循環
- 解析を継続できない構文破損

### WARNING

誤設定の可能性が高いが、ツールの限定実装上、完全には断定しない問題。

例：

- 単純なcell領域式の矛盾
- overlap候補点
- undefined region候補
- detector範囲の不自然さ
- 対応可能な形状における空cell候補

### REVIEW

解析目的や高度なSerpent仕様に依存する確認事項。

例：

- detector bin数が極端に多い
- z方向binningがない
- 複雑すぎるcell式
- geometry checkerで一部のcellを除外した
- 対応外カードが解析へ影響する可能性

### INFO

補助情報。

例：

- 未使用surface
- 未使用material
- 対応外カード
- 幾何学チェックを省略した理由
- AIレビューが無効であること

---

## 15. 静的解析ルール

### SG001: Duplicate surface

同一名称のsurfaceが複数定義されている。

### SG002: Duplicate cell

同一名称のcellが複数定義されている。

### SG003: Duplicate material

同一名称のmaterialが複数定義されている。

### SG004: Undefined surface reference

cell領域式が未定義surfaceを参照している。

### SG005: Undefined material reference

cellが未定義materialを参照している。

### SG006: Unused surface

定義されたsurfaceが解析対象cellから参照されていない。

### SG007: Unused material

定義されたmaterialが解析対象cellで使用されていない。

### SG008: Contradictory signed surface

同一intersection項に同一surfaceの正負が含まれる。

例：

```text
-1 1
```

### SG009: Duplicate region condition

同じintersection項に同一のsigned surfaceが重複している。

### SG010: Excessively complex region expression

surface参照数、union数、括弧深さが設定閾値を超える。

### SG011: Unterminated block comment

ブロックコメントが終了していない。

### SG012: Missing include file

アップロード済みファイル群または指定したローカル範囲でinclude先が見つからない。

### SG013: Include cycle

include関係が循環している。

### SG014: Unsupported card

未知または未対応カードを検出した。

### SG015: Parser recovery used

不完全なカードを読み飛ばして解析を継続した。

---

## 16. Detectorチェック

MVPではdetector構文の完全理解を目指さない。
公式例と公式syntax documentationを参照しながら、対応できるoptionのみ増やす。

初期候補：

- detector名重複
- 未定義energy grid参照
- bin数が0以下
- 最小値が最大値以上
- bin総数が設定閾値を超える
- geometry bounding boxから完全に外れている
- 解析目的とbinningの不一致候補

解析目的に依存する内容は`REVIEW`とし、AIも断定してはならない。

---

## 17. Geometry checker

### 17.1 目的

厳密なCSG検証ではなく、単純な2次元体系において次を候補として検出する。

- どのcellにも属さない点
- 複数cellに属する点

### 17.2 初期方式

- XY断面
- 固定したz座標
- ユーザー指定の`xmin`, `xmax`, `ymin`, `ymax`
- 規則格子サンプリング
- 初期解像度は100 × 100
- UIで解像度を変更可能
- 対応surfaceのみで構成されるcellを評価
- 対応外surfaceを含むcellは判定対象から除外
- 除外したcellは明示する

### 17.3 点の分類

- 0 cell matches: undefined region candidate
- 1 cell matches: normal
- 2 or more cells match: overlap candidate
- unsupported or indeterminate: not evaluated

### 17.4 出力

- 2次元plot
- overlap候補数
- undefined候補数
- 代表座標
- 関与するcell名
- サンプリング範囲
- サンプリング解像度
- 除外cell
- 検出完全性を保証しない旨

### 17.5 制限

- 細い隙間を見逃す可能性がある。
- surface境界上の数値誤差がある。
- repeated geometryやlatticeを完全展開しない。
- 3次元形状を単一断面だけで評価する。
- Serpent本体のgeometry plotterの代替ではない。

---

## 18. AIレビュー

### 18.1 役割

AIは静的解析の代わりではなく、決定論的に生成されたfindingsを研究者向けに説明する。

生成内容：

- 全体要約
- 優先順位
- 各findingの意味
- 想定される影響
- 確認すべき箇所
- 修正の方向性
- 判断不能な事項
- ツールの限界

### 18.2 AI送信payload

例：

```json
{
  "schema_version": "1.0",
  "project": "SerpentGuard",
  "analysis_purpose": "Check a pin-cell model before a criticality calculation.",
  "model_summary": {
    "surfaces": 6,
    "cells": 5,
    "materials": 3,
    "detectors": 1
  },
  "findings": [
    {
      "rule_id": "SG004",
      "severity": "ERROR",
      "title": "Undefined surface reference",
      "object_type": "cell",
      "object_name": "fuel",
      "line": 24,
      "message": "The cell references surface 104, but no surface with that name was parsed.",
      "confidence": "high"
    }
  ],
  "geometry_summary": {
    "evaluated": true,
    "overlap_candidate_points": 14,
    "undefined_candidate_points": 0,
    "excluded_cells": []
  },
  "limitations": [
    "Only a limited subset of Serpent syntax was parsed.",
    "Geometry findings are based on 2D sampling."
  ]
}
```

### 18.3 AI応答schema

```json
{
  "summary": "One blocking reference error was detected.",
  "prioritized_findings": [
    {
      "rule_id": "SG004",
      "priority": 1,
      "explanation": "The cell region cannot be evaluated because the referenced surface was not found.",
      "suggested_checks": [
        "Check whether the surface ID was renamed.",
        "Check whether an include file is missing."
      ],
      "confidence": "high"
    }
  ],
  "limitations": [
    "This explanation does not establish the physical validity of the model."
  ]
}
```

### 18.4 AIへのシステム指示

- Serpentの完全な専門家であるかのように振る舞わない。
- findingsに含まれないエラーを断定しない。
- 行番号を捏造しない。
- 未対応構文の仕様を作らない。
- 静的解析結果と推測を区別する。
- 解析目的に依存する内容はreview recommendationとして表現する。
- 入力の完全な修正版を生成しない。
- 変更前にSerpent公式ドキュメントで確認すべき点を示す。
- 物理的妥当性、臨界安全、設計安全を保証しない。

---

## 19. エラー処理

### 19.1 入力エラー

- ファイルが空
- 文字コードを読めない
- ファイル数が上限を超える
- include先が不足
- 不正なカード
- パース不能

処理方針：

- アプリ全体をクラッシュさせない。
- 可能な場合は解析を継続する。
- 継続不能の場合は理由と位置を表示する。
- tracebackを通常UIへ露出しない。
- 開発モードでのみ詳細を表示する。

### 19.2 AI APIエラー

- APIキー未設定
- 認証失敗
- タイムアウト
- rate limit
- JSON schema不一致
- 応答欠落

処理方針：

- 静的解析結果を保持する。
- AI explanation部分だけ失敗表示にする。
- 自動再送信しない。
- ユーザー操作で再試行できる。
- 送信payloadを保持して確認できる。

---

## 20. テスト方針

### 20.1 ユニットテスト

- コメント除去
- 行番号保持
- カード分割
- `surf` parsing
- `cell` parsing
- `mat` parsing
- 重複検出
- 未定義参照
- 未使用定義
- signed surface矛盾
- geometry surface評価
- cell membership評価
- AI payloadから生入力が除外されていること

### 20.2 回帰テスト

公式example inputを参考にした最小fixtureを使用する。

各fixtureには次を記録する。

- 参照した公式例
- 抽出した構文
- 独自改変
- 期待するfinding
- 非対応部分

### 20.3 AIテスト

APIへ実通信せず、mock clientを使用する。

確認項目：

- 生入力がpayloadに含まれない。
- APIキーがログへ出ない。
- invalid JSON時に静的解析結果が失われない。
- 明示的ボタン操作なしではAPI呼び出しが発生しない。

### 20.4 受け入れfixture

| Fixture                     | 期待結果             |
| --------------------------- | -------------------- |
| `valid_minimal.inp`       | ERRORなし            |
| `duplicate_surface.inp`   | SG001                |
| `undefined_surface.inp`   | SG004                |
| `contradictory_cell.inp`  | SG008                |
| `overlap_2d.inp`          | overlap候補          |
| `undefined_region_2d.inp` | undefined region候補 |

---

## 21. CLI

GUIが主機能だが、解析コアの独立性確認のためCLIを持たせる。

```bash
serpentguard check examples/valid_minimal.inp
```

JSON出力：

```bash
serpentguard check examples/valid_minimal.inp --format json
```

終了コード：

- `0`: ERRORなし
- `1`: ERRORあり
- `2`: パースまたは実行不能

---

## 22. ロギング

- デフォルトはINFOレベル
- 生入力全文をログへ出さない
- APIキーを出さない
- AI payloadはユーザーがUIで確認できるが、通常ログには保存しない
- デバッグモードでも材料組成全文を不用意に記録しない
- ローカルファイルへの永続ログ保存は初期版では必須としない

---

## 23. READMEに必ず記載する免責

- SerpentGuard is an experimental assistant.
- It supports only a limited subset of Serpent syntax.
- It does not guarantee that a model is geometrically or physically correct.
- Geometry checks are sampling-based and may miss narrow overlaps or gaps.
- It does not replace Serpent's own input validation or geometry plotter.
- AI-generated explanations may be incomplete or incorrect.
- All findings and suggested changes must be reviewed by a qualified user.
- The tool must not be used as the sole basis for reactor safety or criticality-safety decisions.

---

## 24. 実装段階

### Phase 0: GitHub連携とリポジトリ初期化

完了条件：

- GitHubリポジトリが存在する。
- ローカルrepositoryとremoteが接続されている。
- 初期ブランチが`main`である。
- README、LICENSE、`.gitignore`、仕様書がコミットされている。
- GitHub Actionsの最小workflowが存在する。
- Codexがrepository内容を読み取れる。
- ブランチ運用方針を決める。

### Phase 1: プロジェクト基盤

完了条件：

- `pyproject.toml`
- `src` layout
- pytest
- Ruff
- Streamlitの空画面
- CLIの空コマンド
- CIでlintとtestが通る

### Phase 2: PreprocessorとParser

完了条件：

- コメント処理
- 行番号保持
- `surf`, `cell`, `mat`
- unknown card保持
- includeの限定処理
- parser tests

### Phase 3: 静的ルール

完了条件：

- SG001からSG015のうちMVP対象を実装
- findings JSON生成
- CLI表示
- fixture tests

### Phase 4: GUI

完了条件：

- アップロード
- 解析目的入力
- Run check
- Summary
- Findings table
- raw parsed data
- エラー表示

### Phase 5: Geometry checker

完了条件：

- 限定surface
- XY断面
- 規則格子
- overlap候補
- undefined候補
- matplotlib表示
- 明示的な制限表示

### Phase 6: AI payloadとプライバシー

完了条件：

- findingsのみからpayload生成
- 生入力が含まれない自動テスト
- payload preview
- 明示的ボタン
- APIキー安全管理

### Phase 7: AI explanation

完了条件：

- Structured JSON応答
- summary
- prioritized findings
- error handling
- mock tests
- AIなしでも動作

### Phase 8: デモ・ドキュメント・提出準備

完了条件：

- example inputs
- README
- architecture
- supported syntax
- privacy
- 3分デモ
- スクリーンショット
- Devpost用説明
- `/feedback` Session ID取得準備

---

