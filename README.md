# 🍜 柳州地道螺蛳粉 • 在线自助点餐系统 (Liu Zhou Luosifen Online Ordering)

基于原生现代 Web 技术构建的柳州地道螺蛳粉移动端/桌面端全功能在线点餐系统。支持到店自取、外直送餐、辣度定制、加料自由搭配、外带餐盒计算与一键发送 WhatsApp 订单。

![在线点餐界面预览](preview.png)

---

## ✨ 系统特性

- 📱 **移动端优先设计**：针对 iOS / Android 手机端进行高度优化，流畅触控与底部模态交互。
- 🍜 **58 道全套地道菜品**：完整同步 Optimy POS 门店系统最新菜品分类、正宗命名与核定售价。
- 📸 **高清实物菜品大图**：58 道佳肴均配备门店高清实拍照片，支持本地高速加载与云端 CDN 双重容灾备份。
- 🌶️ **自由定制规格**：
  - 辣度必选（不辣 / 微辣 / 中辣 / 大辣）
  - 云吞/水饺做法（经典原汤 / 香脆酥炸）
  - 豪华加料配菜库（炸蛋、卤肥肠、牛腩、脱骨大猪脚、虎皮凤爪等）
  - 快捷口味备注（多放酸笋、少油、不要葱花、汤粉分开等）
- 💬 **WhatsApp 一键出单**：根据顾客选择的自取/外送时间、详细地址、选购餐点及规格备注，全自动格式化生成结构化订单，一键唤醒 WhatsApp 发送至店员收款手机号。
- ⚡ **离线秒开零白屏**：内置离线主数据与容灾降级机制，无网络或云端维护时依旧秒级加载。

---

## 📁 目录结构

```text
luosifen-order/
├── index.html        # 点餐前端主程序（包含完整现代 UI、菜单交互、规格计算与 WhatsApp 生成器）
├── menu_data.json    # 从 Optimy POS 导出的 58 道标准化商品与价格数据
├── preview.png       # 点餐系统移动端高保真预览图
├── deploy_order.bat  # Windows 一键自动推送到 GitHub 脚本
└── images/           # 58 道餐品高清实物大图 (JPG/JPEG)
    ├── S1.jpeg       # S1 原味螺蛳粉
    ├── S2.jpeg       # S2 煎蛋螺蛳粉
    ├── S3.jpeg       # S3 炸蛋螺蛳粉
    ├── D1.jpeg       # D1 炸蛋干捞粉
    ├── B1.jpeg       # B1 炒螺蛳粉
    ├── C1.jpeg       # C1 手工水饺
    ├── F01.jpeg      # F01 Justea
    └── ...
```

---

## 🚀 部署与访问

- **GitHub 仓库**: [zhilikam-design/laiwanluosifen-order](https://github.com/zhilikam-design/laiwanluosifen-order)
- **默认 GitHub Pages 访问链接**: [https://zhilikam-design.github.io/laiwanluosifen-order/](https://zhilikam-design.github.io/laiwanluosifen-order/)
- 支持绑定**自定义独立域名**（如 `order.laiwanluosifen.com`），顾客扫码点餐更专业、无第三方痕迹。