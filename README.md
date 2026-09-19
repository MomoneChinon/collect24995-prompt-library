# collect24995 Prompt Library

从 X 账号 [@collect24995](https://x.com/collect24995) 抓取的 AI 生图提示词静态库。  
自编顺序 ID：`0`–`9999`。供自动化任务用稳定 JSON 拉取，不依赖聊天接口爬虫。

## 自动化拉取（推荐）

部署到 GitHub Pages 后（见下方），直接 HTTP GET：

| 路径 | 说明 |
|------|------|
| `/data/prompts.json` | 全部提示词 |
| `/data/latest.json` | 当前最大 `id` 的一条 |
| `/data/by-id/<id>.json` | 指定 ID |
| `/data/index.json` | id → status id 索引 |
| `/data/used_keys.json` | 已收录的 `main:reply` 去重键 |

示例：

```bash
curl -sL https://momonechinon.github.io/collect24995-prompt-library/data/latest.json
curl -sL https://momonechinon.github.io/collect24995-prompt-library/data/by-id/0.json
```

每条字段：`id`, `main_status_id`, `reply_status_id`, `main_url`, `reply_url`, `posted_at`, `captured_at`, `raw_prompt`。

## 本地预览（Deno）

```bash
deno task start
# http://127.0.0.1:8000/
```

## 更新抓取（独立 Python 爬虫，Yahoo 实时检索）

```bash
# 抓取并追加新提示词到 data/prompts.json，同步 public/data
python3 crawler/update_library.py
# 或
deno task update
```

去重键：`main_status_id:reply_status_id`。ID 递增到 9999 封顶。

## GitHub Pages

仓库已带 Actions：推送到 `main` 后部署 `public/` 目录。  
设置：Settings → Pages → Source = GitHub Actions。

线上（Deno Deploy + KV）：`https://collect24995-prompt-library.momonechinon.deno.net/`

备用 GitHub Pages（静态 JSON）：`https://momonechinon.github.io/collect24995-prompt-library/`
