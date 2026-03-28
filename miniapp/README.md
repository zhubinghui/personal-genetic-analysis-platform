# 微信小程序端

基于 [Taro 4.x](https://taro-docs.jd.com/) + React + TypeScript 开发，可同时编译为微信小程序和 H5。

## 页面结构

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `pages/index` | 历史检测列表 / 空状态引导 |
| 登录 | `pages/login` | 微信一键登录（wx.login → code2session） |
| 知情同意 | `pages/consent` | 首次登录必须同意 |
| 上传/检测 | `pages/upload` | Beta CSV 上传 / 购买套餐 |
| 报告 | `pages/report` | 分析进度轮询 + 结果可视化 |
| 我的 | `pages/profile` | 账号、订阅、退出 |

## 开发环境搭建

```bash
cd miniapp
npm install
npm run dev:weapp     # 编译为微信小程序，输出到 dist/
```

用**微信开发者工具**打开 `dist/` 目录进行预览和调试。

## 环境变量

在 `miniapp/` 根目录创建 `.env.development` 和 `.env.production`：

```bash
# .env.development（本地开发，指向 ngrok 或局域网 IP）
TARO_APP_API_BASE=https://your-ngrok-url.ngrok-free.app

# .env.production（生产环境，必须 HTTPS 且已在微信公众平台备案）
TARO_APP_API_BASE=https://api.yourdomain.com
```

## 微信公众平台配置

在 [微信公众平台](https://mp.weixin.qq.com) 完成以下配置：

1. **AppID / AppSecret** → 填入后端 `.env`：
   ```
   WECHAT_MINIAPP_APP_ID=wx...
   WECHAT_MINIAPP_APP_SECRET=...
   ```

2. **服务器域名白名单**（request 合法域名）：
   ```
   https://api.yourdomain.com
   ```

3. **uploadFile 合法域名**（文件上传）：
   ```
   https://api.yourdomain.com
   ```

## 登录流程说明

```
小程序端                    后端
  │                          │
  ├─ wx.login()              │
  │  ← code                  │
  │                          │
  ├─ POST /auth/wechat-miniapp/login { code }
  │                          │
  │                     调用腾讯 API
  │               jscode2session → openid
  │                          │
  │                   查找/创建用户
  │                          │
  │  ← { access_token }      │
  │                          │
  ├─ 后续所有请求携带 Bearer token（与 Web 端完全一致）
```

## 与 Web 端共享的后端 API

小程序端复用全部后端 API，无需为小程序单独开发接口。唯一新增的接口：

```
POST /api/v1/auth/wechat-miniapp/login
Body: { "code": "wx.login() 返回的临时 code" }
Return: { "access_token": "...", "token_type": "bearer" }
```
