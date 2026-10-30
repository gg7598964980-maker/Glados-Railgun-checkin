# Glados自动签到

> 基于 GitHub Actions 的 GLaDOS 自动签到工具，支持多账号与多通道推送（PushDeer / Server酱）。

## 文件结构

```shell
│  checkin.py          # 签到主脚本
│  logging_config.py   # 日志配置（北京时间、[I/W/E] 短标签）
│  requirements.txt    # Python 依赖
│
├─.github
│  └─workflows
│          gladosCheck.yml   # Actions 配置文件
```

## 食用方式

### 注册 GLaDOS 账号

注册地址：<https://glados.space/landing/0A58E-NV28S-6U3QV-33VMG>

- 我的邀请码：[`0A58E-NV28S-6U3QV-33VMG`](https://0a58e-nv28s-6u3qv-33vmg.glados.space)
- 我的优惠码（9 折）：[`DEVILSTORE`](https://0a58e-nv28s-6u3qv-33vmg.glados.space)

### Fork 本仓库

![图片加载失败](imgs/1.png)

### 配置 Secrets

跳转至自己仓库的 `Settings` → `Secrets and variables` → `Action`，按需添加以下 `repository secret`：

#### 3.1 GLADOS_COOKIES（必填）

对应 GLaDOS 账号 Cookie 中的有效部分，获取方式：

- 在 GLaDOS 签到页面按 `F12`，切换到 `Network` 页面下，刷新
- 点击第一个请求，在 `Request Headers` 下找到 `Cookie`，右键复制其值即可

  > 参考格式：`koa:sess=eyJ1c2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxAwMH0=; koa:sess.sig=xJkOxxxxxxxxxxxxxxxtnM;`

- 多账号请在 `COOKIES` 中添加多个 cookies，中间使用 `&` 连接即可（例如：`c1&c2&c3`）

也可以分别添加账号 Secret：`GLADOS_COOKIES`（第 1 个账号）以及可选的 `GLADOS_COOKIES_2`、`GLADOS_COOKIES_3`、`GLADOS_COOKIES_4`、`GLADOS_COOKIES_5`。工作流会按顺序拼接这些 Secret；未使用的账号 Secret 可留空。

![图片加载失败](imgs/2.png)
![图片加载失败](imgs/3.png)

#### 3.2 自动兑换规则

工作流每天按北京时间 **00:18** 和 **09:18** 运行签到。自动兑换规则如下：

- 仅对 200G 套餐账号自动兑换；10GB 套餐账号不会自动兑换。
- 当 200G 账号剩余会员时间大于 0 且不超过 1 天时，使用当前积分能兑换的最高档位：

  | 档位 | 积分要求 | 兑换天数 |
  |---|---:|---:|
  | `plan500` | 500 积分 | 100 天 |
  | `plan200` | 200 积分 | 30 天 |
  | `plan100` | 100 积分 | 10 天 |

- 不足 100 积分时跳过；每个账号每次工作流运行最多尝试兑换一次。
- 旧版 `GLADOS_EXCHANGE_PLAN` Secret 已不再使用，可以删除以免混淆。当前自动兑换由上述规则控制；如果不希望任何账号自动兑换，需要停用或修改本仓库中的自动兑换规则。

#### 3.3 手机推送（非必填）

支持多个推送后端，可在 `Settings`→`Secrets and variables`→`Action` 中按需配置，**任一后端配置后即会推送，支持同时配置多个（都发）**：

- **PushDeer**：添加 `repository secret` 命名为 `PUSHDEER_SENDKEY`，其值对应 PushDeer key（[获取地址](https://www.pushdeer.com/product.html)）。
- **Server酱**：添加 `repository secret` 命名为 `SERVERCHAN_SENDKEY`，其值对应 Server酱 SendKey（[获取地址](https://sct.ftqq.com/)）。

### Star 本仓库

![图片加载失败](imgs/4.png)

## 更新日志

- **2026-01**: 重构代码，添加日志输出方便定位，支持新版网址，支持配置积分兑换策略。
- **2026-04**: 优化代码逻辑与日志输出，支持 `glados.network`、`glados.cloud` 和[新版域名](https://railgun.info)，在 `GLADOS_COOKIES` 中添加新版域名下的 cookies 即可使用。
- **2026-09**: 设备平台自适应重试（无需手动配置 UA 即可自动恢复签到）；网络层自动重试与退避，降低 CI 网络抖动导致的误报失败；日志时间统一为北京时间，定时任务调整为北京时间每天 2 次并避开整点高峰。
- **2026-10**: 日志级别短标签 `[I]/[W]/[E]`；推送兼容 Server酱；工作流支持通过五个独立 Secret 配置最多 5 个账号；定时任务设为北京时间 00:18 和 09:18；仅在 200G 账号会员剩余不超过 1 天时按积分余额兑换最高档位。

## 问题排查与定位

大家可以通过查询 Actions 中的 running checkin 日志快速定位问题，有其他问题提交 issue。

  <img width="1684" height="844" alt="image" src="https://github.com/user-attachments/assets/45348a5f-43e4-45f5-8fdf-ce84d343b30d" />

## 声明

本项目不保证稳定运行与更新，因 GitHub 相关规定可能会删库，请注意备份。
