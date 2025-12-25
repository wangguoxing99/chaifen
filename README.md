# Excel 智能拆分系统 v3.0

基于 Flask + Pandas + Docker 构建的自动化采购报表拆分工具。

## 核心功能
* **多 Sheet 支持**：上传后可自由切换不同的工作表。
* **自定义基准列**：手动指定用于拆分的“数量”列。
* **动态保留列**：支持从原表中勾选最多 10 个需要保留的列。
* **整数单位判定**：自动提取单位，自定义哪些单位需按整数逻辑拆分。
* **自动化流水线**：集成 GitHub Actions，推送即构建镜像。

## 本地运行
1. 构建：`docker build -t excel-splitter .`
2. 运行：`docker run -d -p 5000:5000 excel-splitter`
3. 访问：`http://localhost:5000`

docker run -d -p 5000:5000 \
  -e APP_USER=myuser \
  -e APP_PASSWORD=mypassword \
  --name excel-app your-image-name
