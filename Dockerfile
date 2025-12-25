FROM python:3.9-slim

WORKDIR /app

# 设置加速源并安装依赖
RUN pip install --no-cache-dir flask pandas openpyxl xlrd -i https://pypi.tuna.tsinghua.edu.cn/simple

# 拷贝核心文件
COPY app.py .
COPY templates/ ./templates/

EXPOSE 5000

# 运行 Web 应用
CMD ["python", "app.py"]
