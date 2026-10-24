# 美团每日领券：待验证草稿

**尚未使用真实账号实测成功，默认不启用每日任务。** 目前只完成模拟响应的离线测试。公开参考项目的近期运行记录出现过授权过期，本草稿无法保证当前接口仍可用，也不能保证每天有券。

这是独立编写的 Python 标准库实现。仅参考 [heiko1877/meituan-auto-coupon](https://github.com/heiko1877/meituan-auto-coupon/blob/main/coupon.py) 的接口地址、请求字段与响应结构；参考仓库未提供许可证，没有复制其大段实现。

## 在自己的仓库中手动验证

1. 代码已准备在自己的 GitHub 仓库中。当前仓库为公开 fork；令牌只能放在 Actions Secrets，不能提交到文件中。
2. 在仓库 **Settings → Secrets and variables → Actions → Secrets** 添加 `MEITUAN_TOKEN`。不要把令牌写进代码、Issue、README 或聊天。
3. 此接口的 `token` 可能是客户端授权令牌，**不能假定任意网页版 Cookie 中的 token 可用**。需通过平台允许的自有客户端授权途径确认，不能沿用普通 Cookie 教程。令牌可能过期，一次授权不代表永久有效；本草稿不运行第三方授权组件，不绕过验证码、签名或风控。
4. 在 **Actions → Meituan daily coupon → Run workflow** 手动运行一次，并在美团核实券确实到账。`already_received` 仅表示接口返回 1014，不等于本次新增券。
5. 只有实际验证成功后，才在同一设置页的 **Variables** 添加 `ENABLE_DAILY_CLAIM`，值为 `true`。之后每日北京时间 10:17 尝试一次；GitHub 排程可能延迟。删除该变量或改为 `false` 即停止定时尝试。

## 结果与日志

仅打印固定状态和券数量，写入 Actions 的 Step summary；不打印令牌、券名、原始响应、服务端消息或异常内容，不写账号数据文件，也不发送第三方通知。

| 状态 | 退出码 | 含义 |
| --- | --- | --- |
| `success` | 0 | 返回非空 `data.couponList`，需在美团核实 |
| `already_received` | 0 | 接口表示已领过（1014） |
| `no_token` | 2 | 未配置令牌 |
| `empty` | 3 | 返回空券列表，本次未领到券 |
| `auth_failed` | 4 | 授权失败（401），需更新令牌 |
| `failed` | 5 | 接口或 HTTP 请求被拒绝 |
| `error` | 6 | 网络、响应结构或本地输出处理失败 |

失败会让 Actions 标记运行失败；是否收到 GitHub 通知取决于账号的 Actions 通知设置。代码不重试，不请求额外活动，不下单。

## 本地离线检查

```text
python -m unittest -v test_coupon
```

测试只使用合成数据，并禁止建立网络 socket。直接执行 `python coupon.py` 才会尝试发送一次真实领券请求；缺少令牌时立即以非零退出。
