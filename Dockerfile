# 2026 世界杯比分预测 · Docker 镜像
FROM python:3.11-slim

WORKDIR /app

# 先装依赖（利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝代码
COPY . .

# 容器内监听 8000；运行时用 -p 6889:8000 映射
ENV PORT=8000
EXPOSE 8000

# 用 gunicorn 跑（比 Flask 开发服务器稳定）
# warmup.py 在导入时即触发首次预测构建，确保第一个请求不慢
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "app:app"]
