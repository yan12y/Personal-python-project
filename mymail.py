"""
这个模块定义了一个函数，用于发送QQ邮件。它可以用来在程序出现错误或需要通知用户时发送邮件。
@Time: 2024/10/1 9:45
@Author: ysh
@File: mymail.py
"""

import smtplib
from email.mime.text import MIMEText


def send_email(sender, receiver, password, subject, content):
    """
    这个方法用于发送QQ邮件。
    :param sender: 发送方邮箱
    :param receiver: 接收方邮箱
    :param password: 不是QQ密码，是使用授权码
    :param subject: 邮件主题
    :param content: 邮件内容
    :return:
    """
    msg = MIMEText(content)  # 邮件内容
    msg['Subject'] = subject  # 邮件主题
    msg['From'] = sender  # 发送方邮箱
    msg['To'] = receiver  # 接收方邮箱

    server = smtplib.SMTP('smtp.qq.com', 587)  # 邮件服务器
    server.starttls()  # 开启加密传输
    server.login(sender, password)  # 登录
    server.sendmail(sender, receiver, msg.as_string())  # 发送邮件
    server.quit()
