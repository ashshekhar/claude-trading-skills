---
layout: default
title: データの取り扱いとプライバシー
lang_peer: /en/privacy-data-handling/
permalink: /ja/privacy-data-handling/
---

# データの取り扱いとプライバシー

このガイドは、リポジトリのソースコードで確認できた挙動を説明します。
すべてのスキルや、別途インストールしたプロバイダー連携が同じデータ経路を
使うという保証ではありません。実行するスキルの指示と設定も確認してください。

## ローカルファイルと除外設定

リポジトリでは `.gitignore` を使い、ローカル設定や生成物・実行データを除外します。
対象には `.env` ファイル（`.env.example` を除く）、`.mcp.json`、`.cache/`、`logs/`、
`reports/`、`reviews/`、`.staging/`、`state/`、`*.log`、`*.tmp`、秘密鍵・証明書
ファイル（`*.pem`、`*.key`、`*.p12`、`*.pfx`、`id_rsa`、`id_ed25519`）が含まれます。
空の状態ディレクトリ用プレースホルダー2件、`state/journal/.gitkeep` と
`state/theses/.gitkeep` は追跡対象です。

常時実行のpre-commitガードはGit indexからステージ済みパスを取得し、現在の
`.gitignore` と照合したうえで、上記のローカル／機微パスを個別にも拒否します。
`git add -f` による強制追加も拒否します。このガードは、設定済みpre-commit hookを
インストールした場合、または手動実行した場合に限り動作します。`.gitignore` や
クライアント側hookでは、すでにコミットされた秘密情報を除去したり、サーバー側の
制約を強制したりできません。

## ローカルデータと外部サービス

| データ／操作 | ローカルでの処理 | 外部への送信 |
| --- | --- | --- |
| リポジトリソースと利用者が指定したファイル | 実行したスキル／スクリプトが読み取ります。無視対象フォルダのファイルも、別途アップロード／送信しない限りローカルに残ります。 | プロンプトやAPIリクエストは、選択された内容を設定済みサービスへ送る場合があります。スキルごとの入力とプロバイダー設定を確認してください。 |
| Financial Modeling Prep (FMP) | スクリプトが選択されたendpointとパラメーターからリクエストを構成します。 | 銘柄コード、日付、期間、FMP認証情報が含まれる場合があります。現在の多くのclientはAPI keyをheaderで送りますが、一部の旧endpointはquery parameterを使います。 |
| FINVIZ | スクリーナーコードが指定条件からfilterを構成します。 | FINVIZへのURL／requestにスクリーニング条件、テーマ、表示形式、銘柄コードが含まれる場合があります。 |
| Alpaca | ポートフォリオコードはRESTまたはインストール済みMCP serverを通じて、口座、保有、資産、価格、履歴を取得します。 | REST requestはAPI key IDとsecretをheaderに含み、保有銘柄、数量、口座評価額を明らかにする場合があります。このガイドのために確認したリポジトリソースには読み取りrequestと注文templateがあり、直接注文を送信するcallはありません。別途インストールしたMCP serverの権限は異なる場合があります。 |
| Web検索 | 呼び出し元のスキルが指示と利用者の依頼から検索queryを作ります。 | 検索文はhostアプリが提供する検索providerへ送られます。providerは利用者の環境に依存します。 |
| GitHub | Git操作とGitHub CLIは、利用者が設定したaccountと選択したrepositoryの内容を使います。 | pushやPR作成を行う場合、選択したcommit、Issue本文、PR本文がGitHubへ送信されます。ローカルの非公開データをcommitしないでください。 |

プロバイダーの挙動、account設定、保持期間はproviderとhostアプリが管理します。
このリポジトリからそれらの設定を独立に検証することはできません。

## セッションログminer

`skills/skill-idea-miner/scripts/mine_session_logs.py` の既定値は次のとおりです。

- `~/.claude/projects/` 配下で、最終更新時刻が直近7日以内の `*.jsonl` を、5つの
  project名allowlistに基づいて読み取ります。
- 外部user message、assistantのtool名と入力、一部tool error出力、timestampを解析します。
  sidechain entryは読み飛ばします。
- 現在の作業ディレクトリから見た `reports/raw_candidates.yaml` に、集計値、上限付きの
  signal sample、project label、生成候補、合成session labelを書き込みます。
- ローカルの `claude` CLIがあり、`--dry-run` を指定していない場合は、`claude -p` に
  promptを渡します。promptには集計signal、skill名、上限付きerror／automation／pattern
  sample、設定project名、最大5件のuser message sample（各200文字まで）が含まれます。
  signal sampleはsignalごとに最大3件、各100文字までです。

`--project` は既定allowlistを1つのproject名に置き換えます。
`--lookback-days` は期間を変更し、`--output-dir` はreportの保存先を変更します。
これらのoptionは読み取り範囲を広げたり、`reports/` 以外へ書き込んだりできます。
実行前にコマンドと保存先を確認してください。`--dry-run` が省略するのはLLM呼び出しだけです。
一致するログがなくても、ローカルログを読み、ローカルreport（空reportを含む）を書きます。
CLI provider、account、保持設定はこのリポジトリから見えないため、`claude` のpromptを
外部へ送ってよいaccountか確認してください。

### 限定的なマスキング

prompt作成、report保存、候補filterの前に、minerは認識しやすい一部パターンを隠します。
対象は`FMP_API_KEY`のようなprovider名付きも含むAPI key、access token、secret、passwordなどの
credential assignment、Bearer／Basic形式、いくつかの一般的なprovider token prefix、メール
アドレス、SSN形式、account／order／customer／user／portfolio／phone／tax IDのlabel直後の値です。
構造化されたcredential／identifier fieldはkey名でも判定して伏せます。providerの標準出力・標準
エラーや候補titleはlogに書かず、reportのsession名はローカル連番に置き換えます。

これは限定的なpattern filterであり、完全なPII検出や匿名化ではありません。氏名、住所、
自由記述の金融情報、符号化された値、labelのない値、新しいcredential形式などを見逃すことが
あります。reportをローカルで確認してから共有してください。session由来データを外部modelへ
送れない場合は、LLM abstractionを実行しないでください。`--dry-run` もローカル読取・書込は
行い、外部呼び出しだけを省略します。

## ログの保持期間

skill generationの日次／週次pipelineとskill improvement pipelineは、log rotation stepまで実行が
進んだ際に、30日を超える`logs/*.log`を削除します。定期実行ではないため、pipelineを実行しない
場合やstepに到達しない場合は30日を超えてファイルが残ることがあります。`logs/`内のJSON状態／backlog file、report、
`~/.claude/projects/` のClaude Code session logはrotation対象ではありません。これらには
スクリプトで定めた保持期間がありません。

## `state/theses/` のバックアップと復旧

backupはrepositoryの外に保存し、filesystem permissionを限定してください。このdirectoryは
Gitで無視されるため、中身はrepository backupに含まれません。repository rootから、macOS／Linux
のshellで次のようにtimestamp付きarchiveを作れます。

```sh
umask 077
repo_root="$PWD"
backup_dir="$HOME/private-backups/claude-trading-skills"
mkdir -p "$backup_dir"
backup="$backup_dir/state-theses-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$backup" -C "$repo_root" state/theses
```

復旧時は、現在のstateへ上書きする前に別directoryへ展開して確認します。

```sh
backup="/path/to/state-theses-YYYYMMDD-HHMMSS.tar.gz"
restore_dir="$(mktemp -d)"
tar -xzf "$backup" -C "$restore_dir"
find "$restore_dir/state/theses" -type f -print
```

復旧したfileを確認後、必要なfileだけを `state/theses/` に戻します。未確認archiveを現在の
stateへ直接展開しないでください。合成データだけを使う一時directoryでのarchive／restore testは
次で実行できます: `python3 -m pytest scripts/tests/test_state_theses_backup.py -q`。

## 脆弱性報告とサポート対象

[SECURITY.md](https://github.com/tradermonty/claude-trading-skills/blob/main/SECURITY.md)を参照してください。このrepositoryは非公開連絡先を公開しておらず、
GitHubのprivate vulnerability reportingが有効かも確認できていません。サポート対象versionの
一覧も公開していません。対象versionを問い合わせる場合はtagまたはcommit SHAを指定してください。
default branchや古いcommitへのサポートを推定しないでください。
