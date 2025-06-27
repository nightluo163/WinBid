#!/bin/bash
# 文件名: /root/WinBid/scripts/delete_old_logs.sh

# 日志存储目录
LOG_DIR="/root/scripts/output"

# 查找并删除15天前的日志文件
find "$LOG_DIR" -name "bid_log_*.log" -mtime +15 -exec rm -f {} \;

# 记录清理操作
echo "[$(date)] Deleted logs older than 15 days" >> "$LOG_DIR/cleanup_history.log"
