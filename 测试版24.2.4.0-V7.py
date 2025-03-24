import sys
import time
import logging
import os
import re
import inspect
import threading
import uiautomator2 as u2
import adbutils
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout, QTextEdit, QLineEdit, QComboBox

# 📌 **日志配置**
app_name = os.path.splitext(os.path.basename(__file__))[0]
log_filename = f"{app_name}_{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ViberAutoGroups:
    line_number = 1  # 默认读取第 1 行
    # 定义全局变量
    NUM_TO_INPUT = None  # 默认未初始化

    # 初始化，链接手机
    def __init__(self, device_id, debug=False):
        self.device_id = device_id
        self.device = u2.connect(device_id)
        self.phone_file = phone_file
        self.link_file = link_file
        self.log_callback = log_callback  # 日志回调函数，用于 GUI 显示日志
        if not self.device:
            self.log(f"无法连接到设备 {device_id}，请检查 USB 连接或 WiFi ADB 状态。")
            return

        self.message_sent_status = 1  # 默认消息状态为 1（成功）
        self.processed_packages = set()
        self.phone_counter = 0  # 记录输入号码的次数

    def log(self, message, error=False):
        """ 统一日志记录，支持 GUI 显示 """
        if error:
            logging.error(message)
        else:
            logging.info(message)
        if self.log_callback:
            self.log_callback(message)

    # 加载读取的包
    def load_processed_packages(self):
        try:
            with open('processed_packages.txt', 'r', encoding='utf-8') as f:  # 读取已处理的包名文件
                return {line.strip() for line in f.readlines()}  # 返回一个去重后的包名集合
        except FileNotFoundError:  # 文件未找到时返回空集合
            return set()

    # 保存已处理的包
    def save_processed_packages(self):
        try:
            with open('processed_packages.txt', 'w', encoding='utf-8') as f:
                for pkg in self.processed_packages:
                    f.write(pkg + '\n')
        except Exception as e:
            logging.error(f"保存已处理的包名失败: {e}")

    # 找到对应dp插件包 并打开
    def find_and_open_dkplugin_package(self):
        """查找并启动未处理的 dkplugin 相关应用"""
        shell_response = self.device.shell("pm list packages")
        # 适配不同版本的 uiautomator2
        output_str = shell_response.output if hasattr(shell_response, "output") else str(shell_response)
        dkplugin_packages = {line.split(":")[-1] for line in output_str.split("\n") if 'dkplugin' in line}
        dkplugin_packages -= self.processed_packages  # 过滤已处理的包
        if dkplugin_packages:
            self.first_pkg = list(dkplugin_packages)[0]
            self.log(f"打开应用: {self.first_pkg}")
            self.device.app_start(self.first_pkg)
            time.sleep(1)
            self.processed_packages.add(self.first_pkg)
            time.sleep(1)
            self.save_processed_packages()
            return True
        else:
            self.log("没有找到新的 dkplugin 应用")
            sys.exit()

    def close_current_app(self):
        """关闭当前运行的应用"""
        try:
            current_package = self.device.app_current().get("package", "")
            if current_package:
                self.log(f" 关闭应用: {current_package}")
                self.device.app_stop(current_package)  # 关闭应用
                time.sleep(2)  # 确保应用完全退出
            else:
                logging.warning(f" 未找到当前运行的应用")
        except Exception as e:
            logging.error(f" 关闭应用失败: {e}")

    def check_group_entry(self):
        """
        点击 'formattedMessageView' (群链接)，然后检查是否进入群组界面。
        如果未检测到 'menu_viber_call'，则关闭应用并重新执行。
        """
        self.log("尝试点击群链接...")

        # 尝试点击群链接
        if self.click_if_exists("com.viber.voip:id/formattedMessageView"):
            time.sleep(2)  # 等待群组界面加载

            # 检测是否成功进入群组
            if self.device(resourceId="com.viber.voip:id/menu_viber_call").exists(timeout=3):
                self.log("成功进入群组界面")
                return True  # 进入成功，继续后续操作
            else:
                logging.warning("点击群链接后未检测到 'menu_viber_call'，点击无效，关闭应用并重新执行")
                self.close_current_app()  # 关闭当前应用
                time.sleep(2)
                self.device.press("home")  # 返回桌面
                self.run()  # 重新执行流程
                return False  # 终止当前操作
        else:
            logging.warning("未找到群链接 'formattedMessageView'")
            return False  # 终止当前操作

    def check_notepad_entry(self):
        """
        点击 '我的便签'，然后检查是否成功进入便签界面。
        如果未检测到 'send_text'，则关闭应用并重新执行。
        """
        text_list = ["我的便签", "我的記事", "Mes Notes"]  # 兼容多语言
        self.log("尝试点击 '我的便签'...")

        if self.click_if_exists2("com.viber.voip:id/titleView", 5, text_list):
            time.sleep(2)  # 等待页面加载
            # 检测是否成功进入便签界面
            if self.device(resourceId="com.viber.voip:id/send_text").exists(timeout=3):
                self.log("成功进入 '我的便签'")
                return True  # 进入成功
            else:
                logging.warning("点击 '我的便签' 后未检测到 'send_text'，点击无效，关闭应用并重新执行")
                self.close_current_app()  # 关闭当前应用
                time.sleep(2)
                self.device.press("home")  # 返回桌面
                self.run()  # 重新执行流程
        # else:
        #     logging.warning("未找到 '我的便签'")
        #     return False  # 终止当前操作

    def click_if_exists(self, resource_id,timeout=0.2):

        # 获取当前应用包名
        current_package = self.device.app_current().get('package', 'Unknown')

        """等待并点击某个 UI 元素"""
        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)  # 避免点击太快导致失败

            # 获取元素的文本
            element_text = element.get_text() or "无文本"

            element.click()
            self.log(f"位于{current_package}包，点击了 {resource_id}，文本：{element_text}")
            return True
        logging.warning(f"位于{current_package}包，未找到 {resource_id}")
        return False

    # 重复id的时候，输入索引
    def click_if_exists2(self, resource_id, timeout=5, text_list=None):
        """等待并点击带有特定 resourceId 和 text 的 UI 元素"""
        # 获取当前应用包名
        # current_package = self.device.app_current().get('package', 'Unknown')

        for text in text_list:
            if self.click_text_view_if_exists(resource_id, text):
                return True



    def click_if_exists3(self, resource_id, timeout=5, check_progress=False):
        """
        等待并点击某个 UI 元素。
        如果 `check_progress=True`，则点击后等待 5 秒，并检查 `com.viber.voip:id/progress` 是否存在。
        如果 `com.viber.voip:id/progress` 存在，则判定账号异常。
        """

        current_package = self.device.app_current().get('package', 'Unknown')

        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)  # 避免点击太快导致失败

            # 获取元素的文本
            element_text = element.get_text() or "无文本"

            element.click()
            self.log(f" 位于 {current_package} 包，点击了 {resource_id}，文本：{element_text}")

            # 如果启用了 `check_progress`，点击后等待 5 秒，并检查进度条
            if check_progress:
                time.sleep(5)  # 等待 5 秒，确保 UI 更新

                if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                    logging.warning(f" 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                    self.close_current_app()  # 关闭应用
                    self.device.press("home")  # 回到主界面
                    self.run()  # 重新执行run
                else:
                    self.log(f" 账号状态正常")
            return True
        logging.warning(f" 位于 {current_package} 包，未找到 {resource_id}")
        return False

    def click_text_view_if_exists(self, id, text, timeout=5):
        """通过文本和类名查找并点击 UI 元素"""
        element = self.device(resourceId=id, text=text)
        if element.exists(timeout=timeout):
            element.click()
            self.log(f"点击了文本为 '{text}' 且类名为 '{id}' 的控件")
            return True
        logging.warning(f"未找到文本为 '{text}' 且类名为 '{id}' 的控件")
        return False

    # 判断未连接方案
    def notConnected(self):
        # 判断有没有“未连接“
        if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=2):
            self.device(resourceId="android:id/button1").click()  # 点击确定元素
            self.log("未连接账号；已退出当前应用")
            self.close_current_app()  # 关闭应用
            self.device.press("home")   #回到主界面
            self.run()   #重新执行run

    def run(self):
        self.phone_counter = 0
        self.processed_packages = self.load_processed_packages()
        if not self.find_and_open_dkplugin_package():
            return

        if self.detecting_account():
            self.log(f"🚀 设备 {self.device_id} 开始执行")
            self.log(f"📂 号码文件: {self.phone_file}")
            self.log(f"📂 群链接文件: {self.link_file}")
            self.log("账号正常")
            self.click_if_exists("ix4s")  # 可能会出现广告
            self.click_if_exists("com.viber.voip:id/bottom_nav_tab_4")  # 点击更多
            self.click_if_exists("ix4s")    # 可能会出现广告
            self.check_notepad_entry() #点击"我的便签", "我的記事", "Mes Notes"
            self.notConnected() # 判断未连接情况
            self.click_if_exists("com.viber.voip:id/close")  # 輕觸该按钮，即可关闭提醒
            time.sleep(2)
            self.send_link_text("link.txt") # 输入群链接
            # 避免在便签，点击出右侧栏
            time.sleep(2)
            # self.click_if_exists("com.viber.voip:id/formattedMessageView") # 点击群链接
            self.check_group_entry()         # 点击群链接，如果点击不成功则重新执行run
            self.click_if_exists("com.viber.voip:id/toolbar") # 点击群名字
            self.checkMembersCount()    # 检测群人数
            self.click_if_exists("com.viber.voip:id/icon") # 邀请参与者
            self.click_if_exists("com.viber.voip:id/top_2_frame")   # 点击参与者
            self.enter_phone_numbers("phone.txt", "已使用的号码.txt")
        else:
            logging.warning("检测到账号异常，返回桌面并切换应用")
            time.sleep(3)
            self.close_current_app()  # 关闭应用
            self.device.press("home")  #返回桌面
            self.run()      #重新执行循环

    # def detecting_account(self):
    #     """检测当前是否处于正常账号状态"""
    #     time.sleep(3)
    #     if self.device(resourceId="com.viber.voip:id/remote_banner_button").exists(timeout=2):
    #         logging.warning(f"检测到账号异常")
    #         return False
    #     elif self.device(resourceId="com.viber.voip:id/activity_home_root").exists(timeout=2):
    #         self.log(f"已在 Viber 主界面")
    #         return True
    #     elif self.device(resourceId="com.viber.voip:id/buttonMaybeLater").exists(timeout=2):
    #         self.log(f"检测到 '稍后' 按钮，点击继续")
    #         time.sleep(0.5)
    #         self.device(resourceId="com.viber.voip:id/buttonMaybeLater").click()
    #     else:
    #         logging.warning(f"未检测到已知状态，可能账号异常")
    #         return False
    #
    # def enter_phone_numbers(self, input_file, used_file):
    #     """输入电话号码，并检测群组人数，已使用的号码从 input_file 删除"""
    #     try:
    #         with open(input_file, "r", encoding="utf-8") as f:
    #             phone_numbers = [line.strip() for line in f.readlines() if line.strip()]
    #         if not phone_numbers:
    #             logging.warning(f" 电话号码列表为空")
    #             self.click_if_exists("com.viber.voip:id/new_num_layout")  # 确定拉人
    #             self.click_if_exists("android:id/button1")
    #             sys.exit()
    #
    #         error_count = 0  # 记录连续出现弹窗的次数
    #         self.phone_counter = 0  # 初始化号码计数器
    #
    #         # 遍历所有电话号码
    #         for idx, phone in enumerate(phone_numbers):
    #             phone_input = self.device(resourceId="com.viber.voip:id/add_recipients_search_field")
    #             # **如果找不到输入框，暂停输入，并持续检测 alertTitle**
    #             check_time = 0  # 记录等待时间
    #             while not phone_input.exists(timeout=2):
    #                 logging.warning(f" 找不到输入框，暂停输入电话号码")
    #
    #                 # **持续检测是否出现 `alertTitle`**
    #                 if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=2):
    #                     logging.warning(f" 检测到 `alertTitle`，点击确认")
    #                     self.click_if_exists("android:id/button1")  # 点击确认
    #                     time.sleep(2)  # 等待 UI 更新
    #                 check_time += 2  # 计时
    #                 # **如果超过 15 秒仍然没有输入框，执行异常处理**
    #                 if check_time >= 15:
    #                     logging.error(f" 超过 15 秒未找到输入框，执行异常处理")
    #                     self.close_current_app()  # 关闭应用
    #                     time.sleep(2)
    #                     self.device.press("home")  # 返回桌面
    #                     self.run()  # 重新执行流程
    #
    #             if phone_input.exists(timeout=3):
    #                 phone_input.click()
    #                 time.sleep(0.2)
    #                 phone_input.set_text(phone)
    #                 self.log(f" 输入电话号码: {phone}")
    #
    #                 # 记录号码到 '已使用的号码.txt'
    #                 with open(used_file, "a", encoding="utf-8") as used_f:
    #                     used_f.write(phone + '\n')
    #
    #                 # 从原始文件中移除当前号码
    #                 with open(input_file, "r+", encoding="utf-8") as f:
    #                     lines = f.readlines()
    #                     f.seek(0)
    #                     f.truncate()
    #                     for line in lines:
    #                         if line.strip() != phone:
    #                             f.write(line)
    #
    #                 time.sleep(0.2)
    #                 self.click_if_exists("com.viber.voip:id/new_num_layout")
    #                 # **增加号码计数**
    #                 self.phone_counter += 1
    #                 self.log(f" 当前已输入号码: {self.phone_counter}/{NUM_TO_INPUT}")
    #
    #                 # **每输入 N 个号码后，点击完成并进行确认**
    #                 if self.phone_counter >= NUM_TO_INPUT:
    #                     self.log("达到用户设定的号码数量，点击完成按钮")
    #                     if self.click_if_exists3("com.viber.voip:id/menu_done"):  # **点击完成**
    #                         time.sleep(2)  # **等待界面更新**
    #                         # **检查 `android:id/button1` 和 `com.viber.voip:id/body`**
    #                         if self.device(resourceId="android:id/button1").exists(timeout=3):
    #                             self.log("检测到确认按钮 'android:id/button1'，点击继续")
    #                             self.click_if_exists("android:id/button1")  # **确认**
    #                             self.close_current_app()  # 关闭应用
    #                             self.device.press("home")
    #                             self.run()
    #                         elif self.device(resourceId="com.viber.voip:id/body").exists(timeout=15):
    #                             logging.error("检测到 'com.viber.voip:id/body'，账号异常，执行异常处理")
    #                             self.close_current_app()  # **关闭应用**
    #                             time.sleep(2)
    #                             self.device.press("home")  # **返回桌面**
    #                             self.run()  # **重新执行流程**
    #                             return  # **终止当前流程**
    #
    #                         self.phone_counter = 0  # **重置计数器**
    #                         time.sleep(2)  # **确保页面刷新**
    #                         self.checkMembersCount()  # **检测群人数**
    #                         time.sleep(2)
    #                         self.run()
    #
    #             else:
    #                 logging.warning(f" 找不到输入框，跳过 {phone}")
    #
    #             self.click_if_exists("com.viber.voip:id/top_2_frame")  # 继续下一个步骤
    #
    #         self.log(f" 已处理的号码保存到 {used_file}")
    #
    #     except Exception as e:
    #         logging.error(f" 处理电话号码失败: {e}")
    #         sys.exit()
    #
    # def checkMembersCount(self):
    #     try:
    #         # 获取文本内容
    #         numbePeopleElement = self.device(resourceId="com.viber.voip:id/startText")
    #
    #         if numbePeopleElement.exists(timeout=2):  # 确保元素存在
    #             numbePeopleText = numbePeopleElement.get_text()
    #             self.log(f"获取的群成员文本: {numbePeopleText}")
    #
    #             # 使用正则表达式提取所有数字
    #             matches = re.findall(r'\d+', numbePeopleText)
    #             if matches:
    #                 # 取出最大值，防止提取到错误的数字（比如时间、ID 等）
    #                 groupMembers = max(map(int, matches))
    #                 self.log(f"当前群成员数: {groupMembers}")
    #
    #                 # 如果成员数达到 200，则退出程序
    #                 if groupMembers >= 200:
    #                     global line_number
    #                     self.line_number += 1
    #                     self.log("群成员数已达到 200，返回桌面并打开下一个包")
    #                     # 返回桌面
    #                     time.sleep(2)
    #                     self.close_current_app()  # 关闭应用
    #                     time.sleep(2)
    #                     self.device.press("home")
    #                     self.run()# 重新执行 run 方法，进入新的群并发送第二个群链接
    #
    #             else:
    #                 logging.warning("未能解析群成员数，文本格式可能不正确")
    #                 sys.exit()
    #
    #         else:
    #             logging.warning("账号可能封禁，更换下一个账号")
    #             self.close_current_app()  # 关闭应用
    #             time.sleep(1)
    #             self.run()
    #     except Exception as e:
    #         logging.error(f"检查群成员数时发生错误: {e}")
    #         sys.exit()
    #
    # # 获取当前行
    # def getLine(self):
    #     return inspect.currentframe().f_back.f_lineno
    #
    # def send_link_text(self, file_path):
    #     """发送文本链接"""
    #     global line_number
    #     try:
    #         with open(file_path, "r", encoding="utf-8") as f:
    #             links = [line.strip() for line in f.readlines() if line.strip()]
    #
    #         # 检查是否超出文件行数
    #         if self.line_number > len(links):
    #             # logging.warning(f"当前行：{self.line_number}; 超出文件行数，无法读取更多数据")
    #             logging.warning(f"当前行：{self.line_number}; 群已拉完，结束程序")
    #             # 终止程序
    #             sys.exit()
    #
    #         # 读取指定行
    #         link = links[self.line_number - 1]
    #
    #         text_box = self.device(resourceId="com.viber.voip:id/send_text")
    #         if text_box.exists(timeout=2):
    #             text_box.set_text(link)
    #             self.log(f"当前行：{self.line_number}; 输入文本: {link}")
    #             time.sleep(0.05)
    #             send_button = self.device(resourceId="com.viber.voip:id/btn_send")
    #             if send_button.exists:
    #                 send_button.click()
    #                 self.log(f"当前行：{self.line_number}; 点击发送")
    #                 # 需要多等一会儿，这个元素显示不会这么快
    #                 time.sleep(3)
    #                 element = self.device.xpath(
    #                     '//*[@resource-id="com.viber.voip:id/conversation_recycler_view"]/*[last()]//*[@resource-id="com.viber.voip:id/myNotesCheckView"]')
    #                 if element.exists:
    #                     self.log("链接发送至记事本成功")
    #                 else:
    #                     logging.warning("链接发送至记事本失败，账号异常，正在关闭应用")
    #                     self.close_current_app()  # 关闭应用
    #                     time.sleep(2)
    #                     self.run()
    #                     return False
    #         else:
    #             logging.warning(f"当前行：{self.line_number}; 未找到输入框")
    #     except Exception as e:
    #         logging.error(f"当前行：{self.line_number}; 读取链接文件失败: {e}")


class ViberBotGUI(QWidget):
    def __init__(self):
        super().__init__()

        # **窗口初始化**
        self.setWindowTitle("Viber 自动群管理")
        self.setGeometry(100, 100, 600, 500)

        self.layout = QVBoxLayout()

        # **设备选择**
        self.device_label = QLabel("选择设备:")
        self.device_combo = QComboBox()
        self.refresh_devices()
        self.layout.addWidget(self.device_label)
        self.layout.addWidget(self.device_combo)

        # **文件选择**
        self.phone_label = QLabel("选择电话号码文件 (phone.txt):")
        self.phone_button = QPushButton("📂 选择文件")
        self.phone_button.clicked.connect(self.select_phone_file)
        self.layout.addWidget(self.phone_label)
        self.layout.addWidget(self.phone_button)

        self.link_label = QLabel("选择群链接文件 (link.txt):")
        self.link_button = QPushButton("📂 选择文件")
        self.link_button.clicked.connect(self.select_link_file)
        self.layout.addWidget(self.link_label)
        self.layout.addWidget(self.link_button)

        # **输入号码数量**
        self.num_label = QLabel("每次输入的号码数量 (默认 45):")
        self.num_input = QLineEdit("45")
        self.layout.addWidget(self.num_label)
        self.layout.addWidget(self.num_input)

        # **日志显示**
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.layout.addWidget(self.log_box)

        # **运行按钮**
        self.run_button = QPushButton("🚀 开始运行")
        self.run_button.clicked.connect(self.start_bot)
        self.layout.addWidget(self.run_button)

        self.setLayout(self.layout)

        # **变量**
        self.phone_file = ""
        self.link_file = ""

    # **刷新设备列表**
    def refresh_devices(self):
        self.device_combo.clear()
        devices = adbutils.adb.device_list()
        for device in devices:
            self.device_combo.addItem(device.serial)

    # **选择电话号码文件**
    def select_phone_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 phone.txt", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.phone_file = file_path
            self.phone_label.setText(f"📂 号码文件: {file_path}")

    # **选择群链接文件**
    def select_link_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择 link.txt", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.link_file = file_path
            self.link_label.setText(f"📂 群链接文件: {file_path}")

    # **日志更新**
    def update_log(self, message):
        self.log_box.append(message)

    # **运行脚本**
    def start_bot(self):
        device_id = self.device_combo.currentText()
        if not device_id:
            self.update_log("❌ 请选择设备！")
            return

        num_to_input = self.num_input.text().strip()
        if not num_to_input.isdigit():
            self.update_log("❌ 请输入有效的电话号码数量！")
            return

        ViberAutoGroups.NUM_TO_INPUT = int(num_to_input)

        if not self.phone_file or not self.link_file:
            self.update_log("❌ 请选择 phone.txt 和 link.txt 文件！")
            return

        self.update_log(f"🚀 设备 {device_id} 开始运行！")

        bot = ViberAutoGroups(device_id, self.phone_file, self.link_file, self.update_log)
        threading.Thread(target=bot.run, daemon=True).start()


# **主程序**
if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = ViberBotGUI()
    gui.show()
    sys.exit(app.exec_())
