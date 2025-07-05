import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import re
import io
import sys
import time
from logging.handlers import RotatingFileHandler
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote
from fake_useragent import UserAgent
  
with open('scripts/bid.json', 'r', encoding='utf-8') as f:
    bid = json.load(f) 
    keyword_main = bid["keyword"]["main"]
    keyword_others = bid["keyword"]["others"]
    keyword_list = keyword_main + keyword_others
    not_list = bid["keyword"]["not"]

key = os.getenv("key_main")
key_test = os.getenv("key_test")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 确保日志目录存在
log_dir = "scripts/output"
os.makedirs(log_dir, exist_ok=True)  # 自动创建目录

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建文件处理器（输出到scripts/output/bid_log.log）
log_file = os.path.join(log_dir, "bid_log.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 保留控制台输出（可选）
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

# 替换FileHandler为RotatingFileHandler（保留3个备份，每个10MB）
file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=3,
    encoding='utf-8'
)

# 配置重试策略
retry_strategy = Retry(
    total=5,                              # 总尝试次数（含首次请求）[2,4](@ref)
    backoff_factor=1,                     # 指数退避间隔：{backoff_factor} * 2^(n-1)秒[4,5](@ref)
    status_forcelist=[500, 502, 503, 504],# 遇到这些状态码自动重试[3,5](@ref)
    allowed_methods=["GET", "POST"]       # 仅对指定HTTP方法重试[4](@ref)
)

try:
    response = requests.get("https://api.ipify.org", timeout=10)
    logger.info(f"当前代理IP: {response.text}")
except Exception as e:
    logger.info(f"代理请求失败: {e}")
    
class WeComWebhook:  
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    def __init__(self):
        self.webhook_key = key
        if not self.webhook_key:
            logger.error("未检测到环境变量 WECOM_WEBHOOK_KEY")
            raise ValueError("缺失密钥")

    def send_text(self, content: str) -> dict:
        payload = {"msgtype": "text", "text": {"content": content}}
        try:
            response = requests.post(
                self.BASE_URL.format(key=self.webhook_key),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"消息发送失败: {str(e)}")
            return {"errcode": -1, "errmsg": "请求异常"}

class WeComWebhookTest:  
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    def __init__(self):
        self.webhook_key = key_test
        if not self.webhook_key:
            logger.error("未检测到环境变量 WECOM_WEBHOOK_KEY_TEST")
            raise ValueError("缺失密钥")

    def send_text(self, content: str) -> dict:
        payload = {"msgtype": "text", "text": {"content": content}}
        try:
            response = requests.post(
                self.BASE_URL.format(key=self.webhook_key),
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"消息发送失败: {str(e)}")
            return {"errcode": -1, "errmsg": "请求异常"}

def get_random_user_agent():
    ua = UserAgent()
    return ua.random
    
def zgyz_search(keyword, start_time):
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    home_url = "https://www.chinapost.com.cn"
    try:
        home_response = session.get(home_url)
        home_response.raise_for_status()

    except Exception as e:
            logger.error(f"中国邮政，主页请求失败: {str(e)}")
            return None

    headers = {
        'User-Agent': get_random_user_agent(),
        'Content-Type': 'application/json;charset=UTF-8',
    }
    
    api_url = f"https://iframe.chinapost.com.cn/jsp/util/Search.jsp?community=ChinaPostJT&lucenelist=1813902036&q={quote(keyword, encoding='utf-8')}"
    bid_list = []
    try:
        response = session.post(
            url=api_url,
            headers=headers,
            timeout=60
        )
        
        response.raise_for_status()              
        data = response.json()
        logger.info(f"data！\n {data}")
        data_list = data['data'][:10]
        for list in data_list:
            format_str = "%Y-%m-%d"
            bid_time = datetime.strptime(list['time'], format_str)
            if bid_time == start_time:
                bid = {
                    "标题": list['title'],
                    "链接":  f"{home_url}{list['url']}"
                }
                bid_list.append(bid)
            else:
                break

    except requests.exceptions.HTTPError as e:
        logger.error(f"中国邮政，API请求失败: 状态码 {response.status_code}, 响应内容: {response.text}")
        return None
    
    return bid_list
    
def lambda_handler(event, context):
    """Lambda入口函数"""
    logger.info("【调试】函数开始执行")
    webhook = WeComWebhook()
    webhook_test = WeComWebhookTest()
    logger.info("【调试】Webhook初始化成功")
    
    utc_now = datetime.now(timezone.utc)
    beijing_time = utc_now.astimezone(timezone(timedelta(hours=8)))        
    end_time = beijing_time + timedelta(hours=5.1)
    logger.info(f"end_time: {end_time}")
    send_test = webhook_test.send_text(f"重启，必胜！\n {beijing_time}")
    logger.info(f"重启，必胜！\n {beijing_time}")

    start_time = beijing_time - timedelta(days=2)
    start_time = start_time.date()
    # start_time = beijing_time.date()
    logger.info(f"start_time: {start_time}")

    bid_total = []
    while beijing_time <= end_time:
        try:
            for keyword in keyword_list:
                result = zgyz_search(keyword, start_time)
                message = ''
                for msg in result:
                    if msg not in bid_total:
                        if any(notword in msg['标题'] for notword in not_list):
                            logger.info(f"msg['标题']：{msg['标题']}")
                            continue
                        else:
                            bid_total.append(msg)
                            message = message + f"【标题】{msg['标题']}\n【链接】{msg['链接']}\n\n"
                
                if message != '':
                    message = message[:-2]
                    result = webhook.send_text(message)
                    result_test = webhook_test.send_text(message)
                    # logger.info(f"【调试】发送结果: {json.dumps(result)}")
                    # logger.info(f"【调试】发送结果: {json.dumps(result_test)}")
                    time.sleep(10)
                else:
                    time.sleep(10)
                    continue
        except Exception as e:
            logger.error(f"全局异常: {str(e)}")
            error_send = webhook_test.send_text(f"全局异常: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
            
        if len(bid_total) >= 20:
            bid_total = bid_total[-6:]
            
        beijing_time = datetime.now(timezone(timedelta(hours=8)))

    now_time = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
    time_send = webhook_test.send_text(f"归零，更新！\n{now_time}")
    logger.info(f"归零，更新！\n{now_time}")
    
if __name__ == "__main__":
    func = lambda_handler("", "")
