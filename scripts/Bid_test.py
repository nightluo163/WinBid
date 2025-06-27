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

keyword_main = ["培训", "竞赛", "赋能", "会务", "营销"]
keyword_list = ["交流活动", "辅助服务", "训战", "会议活动", "会议服务", "会展", "论坛", "实战", "服务支撑", "服务提质", "客户价值提升", "训练营"]
keyword_list = keyword_main + keyword_list
not_list = ["租赁", "设备采购", "办公室", "材料", "培训中心"]
# not_list = not_list + keyword_main

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

key = os.getenv("BID_WIN")
# key_test = os.getenv("BID_TEST")
# key_ot = os.getenv("BID_OT")

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

# class WeComWebhookOT:  
#     BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
#     def __init__(self):
#         self.webhook_key = key_ot
#         if not self.webhook_key:
#             logger.error("未检测到环境变量 WECOM_WEBHOOK_KEY_TEST")
#             raise ValueError("缺失密钥")

#     def send_text(self, content: str) -> dict:
#         payload = {"msgtype": "text", "text": {"content": content}}
#         try:
#             response = requests.post(
#                 self.BASE_URL.format(key=self.webhook_key),
#                 json=payload,
#                 timeout=60
#             )
#             response.raise_for_status()
#             return response.json()
#         except Exception as e:
#             logger.error(f"消息发送失败: {str(e)}")
#             return {"errcode": -1, "errmsg": "请求异常"}
            
def ct_search(keyword, start_time):
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    home_url = "https://caigou.chinatelecom.com.cn"
    try:
        home_response = session.get(home_url)
        home_response.raise_for_status()

    except Exception as e:
            logger.error(f"阳光采购网，主页请求失败: {str(e)}")
            return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }

    payload_type = ["xi9s", "e2no", "e3erht", "ru7of", "e8vif", "ds3fd2s", "f1f7e", "n0eves", "ow7t", "th4gie", "s1x5e"]
    type_list = ["6", "1", "3", "4", "5", "14", "3", "7", "2", "8", "7"]
    
    api_url = "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew"
    bid_list = []
    for i in range(len(payload_type)):
        type = payload_type[i]
        type_id = type_list[i]
        payload = {
            "title": keyword,
            "pageSize": 10,
            "pageNum": 1,
            "type": type,
            "creatorName": "",
            "provinceCode": ""
        }

        try:
            response = session.post(
                url=api_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()              
            data = response.json()
            data_list = data['data']['list']
            for list in data_list:
                format_str = "%Y-%m-%d %H:%M:%S"
                bid_time = datetime.strptime(list['createDate'], format_str)
                if bid_time >= start_time.replace(tzinfo=None):
                    bid = {
                        "标题": list['docTitle'],
                        "类型": list['docType'],
                        "链接":  f"{home_url}/DeclareDetails?id={list['docId']}&type={type_id}&docTypeCode={list['docTypeCode']}&securityViewCode={list['securityViewCode']}"
                    }
                    bid_list.append(bid)
                else:
                    break

        except requests.exceptions.HTTPError as e:
            logger.error(f"阳光采购网，API请求失败: 状态码 {response.status_code}, 响应内容: {response.text}")
            return None
    
    return bid_list
    
def tower_search(keyword, start_time):
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    home_url = "http://www.tower.com.cn/#/purAnnouncement?name=more&purchaseNoticeType=2&activeIndex=0"
    try:
        home_response = session.get(home_url)
        home_response.raise_for_status()

    except Exception as e:
            logger.error(f"铁塔，主页请求失败: {str(e)}")
            return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }

    type_list = ["2", "45"]
    docType_list = ["采购公告", "候选人及结果公示"]
    
    api_url = "http://www.tower.com.cn/supportal/v1/obp-notice/query-notice"
    bid_list = []
    for i in range(len(type_list)):
        type_id = type_list[i]
        docType = docType_list[i]
        payload = {
            "noticeTitle": keyword,
            "purchaseNoticeType": type_id,
            "orgName":"",
            "times":"",
            "transformationField":"",
            "conversionMethod":"",
            "current":1,
            "size":20
        }

        try:
            response = session.post(
                url=api_url,
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
                
            data = response.json()
            
            data_list = data['data']['records']
            for list in data_list:
                format_str = "%Y-%m-%d %H:%M:%S"
                bid_time = datetime.strptime(list['createTime'], format_str)
                if bid_time >= start_time.replace(tzinfo=None):
                    bid = {
                        "标题": list['noticeTitle'],
                        "类型": docType,
                        "链接":  f"http://www.tower.com.cn/#/noticeDetail?id={list['noticeId']}"
                    }
                    bid_list.append(bid)
                else:
                    break

        except requests.exceptions.HTTPError as e:
            logger.error(f"铁塔，API请求失败: 状态码 {response.status_code}, 响应内容: {response.text}")
            return None
        
    return bid_list
    

def lambda_handler(event, context):
    """Lambda入口函数"""
    logger.info("【调试】函数开始执行")
    webhook = WeComWebhook()
    # webhook_test = WeComWebhookTest()
    # webhook_ot = WeComWebhookOT()
    logger.info("【调试】Webhook初始化成功")
    try:
        utc_now = datetime.now(timezone.utc)
        beijing_time = utc_now.astimezone(timezone(timedelta(hours=8)))        
        end_time = beijing_time - timedelta(minutes=15)
        start_time = beijing_time - timedelta(minutes=75)
        logger.info(f"start_time: {start_time}")
        logger.info(f"end_time: {end_time}")
        # send_test = webhook_test.send_text(f"重启，必胜！\n {beijing_time}")
        # send_ot = webhook_ot.send_text(f"测试消息！\n {beijing_time}")
        logger.info(f"重启，必胜！\n {beijing_time}")
        
        bid_total = []
        while beijing_time >= start_time:
            # start_time = beijing_time - timedelta(minutes=15)
            # logger.info(f"start_time: {start_time}")
            for keyword in keyword_list:
                result_1 = ct_search(keyword, start_time)
                result_2 = tower_search(keyword, start_time)
                result = result_1 + result_2
                message = ''
                for msg in result:
                    if msg not in bid_total:
                        if any(notword in msg['标题'] for notword in not_list):
                            logger.info(f"msg['标题']：{msg['标题']}")
                            continue
                        else:
                            bid_total.append(msg)
                            message = message + f"【标题】{msg['标题']}\n【类型】{msg['类型']}\n【链接】{msg['链接']}\n\n"
                
                if message != '':
                    message = message[:-2]
                    result = webhook.send_text(message)
                    # result_test = webhook_test.send_text(message)
                    # result_ot = webhook_ot.send_text(message)
                    logger.info(f"关键词：{keyword}\n消息详情：{message}")
                    logger.info(f"【调试】发送结果: {json.dumps(result)}")
                else:
                    logger.info(f"关键词：{keyword}\n消息详情：no")
                    continue
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            break

        now_time = beijing_time.strftime("%Y-%m-%d %H:%M:%S")
        # time_send = webhook_test.send_text(f"归零，更新！\n{now_time}")
        logger.info(f"归零，更新！\n{now_time}")
    
    except Exception as e:
        logger.error(f"全局异常: {str(e)}")
        # error_send = webhook.send_text(f"全局异常: {str(e)}")
        # error_send = webhook_test.send_text(f"全局异常: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
if __name__ == "__main__":
    func = lambda_handler("", "")
