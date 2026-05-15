# YouTube + Gemini 自动监控与摘要（PushPlus + ClawBot 双推送版）

## 功能
1. 监控 YouTube 频道 RSS 更新
2. 使用 Gemini 自动生成中文摘要
3. 同时支持 PushPlus 和 ClawBot 推送
4. 支持 GitHub Actions 每 10 分钟自动运行
5. 自动记录已处理视频，避免重复推送

## GitHub Secrets
在仓库 Settings → Secrets and variables → Actions 中添加：

- GEMINI_API_KEY（必填）
- PUSHPLUS_TOKEN（可选）
- CLAWBOT_WEBHOOK（可选）

两个推送渠道可同时启用，也可以只配置其中一个。

## ClawBot
默认发送 JSON：
- title
- content
- text

如果你的 ClawBot 接口字段不同，请修改 main.py 中 send_clawbot() 函数。

## 本地运行
```bash
pip install -r requirements.txt
python main.py
```
