import time
import logging
import uiautomator2 as u2
import adbutils
import re
import inspect
import sys

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ViberAutoGroups:

    # 初始化，链接手机
    def __init__(self, device_id, debug=False):
        self.device_id = device_id
        self.device = u2.connect(device_id)
        if not self.device:
            logging.error(f"当前行：{self.getLine()};无法连接到设备 {device_id}，请检查 USB 连接或 WiFi ADB 状态。")
            return

        self.debug = debug
        self.message_sent_status = 1  # 默认消息状态为 1（成功）

        self.processed_packages = set()
        self.phone_counter = 0  # 记录输入号码的次数

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
            logging.error(f"当前行：{self.getLine()};保存已处理的包名失败: {e}")

    # 如果id存在，则延迟5秒 点击
    def click_if_exists(self, resource_id, timeout=5):

        # 获取当前应用包名
        current_package = self.device.app_current().get('package', 'Unknown')

        """等待并点击某个 UI 元素"""
        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)  # 避免点击太快导致失败

            # 获取元素的文本
            element_text = element.get_text() or "无文本"

            element.click()
            logging.info(f"当前行：{self.getLine()};位于{current_package}包，点击了 {resource_id}，文本：{element_text}")
            return True
        logging.warning(f"当前行：{self.getLine()};位于{current_package}包，未找到 {resource_id}")
        return False

    # 重复id的时候，输入索引
    def click_if_exists2(self, resource_id, timeout=5, text_list=None):
        """等待并点击带有特定 resourceId 和 text 的 UI 元素"""
        # 获取当前应用包名
        # current_package = self.device.app_current().get('package', 'Unknown')


        for text in text_list:
            self.click_text_view_if_exists(resource_id, text)

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
            logging.info(f"当前行：{self.getLine()}; 位于 {current_package} 包，点击了 {resource_id}，文本：{element_text}")

            # 如果启用了 `check_progress`，点击后等待 5 秒，并检查进度条
            if check_progress:
                time.sleep(5)  # 等待 5 秒，确保 UI 更新

                if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=2):
                    logging.warning(f"当前行：{self.getLine()}; 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                    self.handle_account_exception()  # 处理账号异常
                    return False  # 账号异常，终止操作
                else:
                    logging.info(f"当前行：{self.getLine()}; 账号状态正常")

            return True
        logging.warning(f"当前行：{self.getLine()}; 位于 {current_package} 包，未找到 {resource_id}")
        return False

    def click_text_view_if_exists(self, id, text, timeout=5):
        """通过文本和类名查找并点击 UI 元素"""
        element = self.device(resourceId=id, text=text)
        if element.exists(timeout=timeout):
            element.click()
            logging.info(f"点击了文本为 '{text}' 且类名为 '{id}' 的控件")
            return True
        logging.warning(f"未找到文本为 '{text}' 且类名为 '{id}' 的控件")
        return False

    # 判断未连接方案
    def notConnected(self):
        # 判断有没有“未连接“
        if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=2):
            time.sleep(2)  # 避免点击过快导致失败
            self.device(resourceId="android:id/button1").click()  # 点击确定元素
            logging.info("未连接账号；已退出当前应用")
            # self.device.app_current().app_stop(self.first_pkg)   # 获取当前运行的应用信息 关闭指定包
            self.device.press("home")   #回到主界面
            self.run()   #重新执行run



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
            logging.info(f"当前行：{self.getLine()};打开应用: {self.first_pkg}")
            self.device.app_start(self.first_pkg)
            time.sleep(3)
            self.processed_packages.add(self.first_pkg)
            time.sleep(2)
            self.save_processed_packages()
            return True
        else:
            logging.info("当前行：{self.getLine()};没有找到新的 dkplugin 应用")
            return False

    def close_current_app(self):
        """关闭当前运行的应用"""
        try:
            current_package = self.device.app_current().get("package", "")
            if current_package:
                logging.info(f"当前行：{self.getLine()}; 关闭应用: {current_package}")
                self.device.app_stop(current_package)  # 关闭应用
                time.sleep(2)  # 确保应用完全退出
            else:
                logging.warning(f"当前行：{self.getLine()}; 未找到当前运行的应用")
        except Exception as e:
            logging.error(f"当前行：{self.getLine()}; 关闭应用失败: {e}")

    def run(self):
        self.phone_counter = 0
        self.processed_packages = self.load_processed_packages()
        #
        # if not self.find_and_open_dkplugin_package():
        #     return

        if self.detecting_account():
            logging.info("账号正常")
            self.click_if_exists("ix4s")  # 可能会出现广告
            self.click_if_exists("com.viber.voip:id/bottom_nav_tab_4")  # 点击更多
            self.click_if_exists("ix4s")    # 可能会出现广告
            text_list = ["我的便签", "我的記事", "Mes Notes"]            # 便签：多个语言
            self.click_if_exists2("com.viber.voip:id/titleView", 5, text_list)  # 点击“我的记事”
            self.notConnected() # 判断未连接情况
            self.click_if_exists("com.viber.voip:id/close")  # 輕觸该按钮，即可关闭提醒
            time.sleep(2)
            self.send_link_text("link.txt") # 输入群链接
            self.click_if_exists("com.viber.voip:id/formattedMessageView") # 点击群链接
            self.click_if_exists("com.viber.voip:id/toolbar") # 点击群名字
            self.checkMembersCount()    # 检测群人数
            self.click_if_exists("com.viber.voip:id/icon") # 邀请参与者
            self.click_if_exists("com.viber.voip:id/top_2_frame")   # 点击参与者
            self.enter_phone_numbers("phone.txt", "已使用的号码.txt")
        else:
            logging.warning("检测到账号异常，返回桌面并切换应用")
            self.close_current_app()  # 关闭应用
            self.device.press("home")
            if self.find_and_open_dkplugin_package():
                self.run()

    def detecting_account(self):
        """检测当前是否处于正常账号状态"""
        if self.device(resourceId="com.viber.voip:id/remote_banner_button").exists(timeout=2):
            logging.warning(f"当前行：{self.getLine()};检测到账号异常")
            return False
        elif self.device(resourceId="com.viber.voip:id/activity_home_root").exists(timeout=2):
            logging.info(f"当前行：{self.getLine()};已在 Viber 主界面")
            return True
        elif self.device(resourceId="com.viber.voip:id/buttonMaybeLater").exists(timeout=2):
            logging.info(f"当前行：{self.getLine()};检测到 '稍后' 按钮，点击继续")
            self.device(resourceId="com.viber.voip:id/buttonMaybeLater").click()
            time.sleep(3)
            return True
        else:
            logging.warning(f"当前行：{self.getLine()};未检测到已知状态，可能账号异常")
            return False

    # def notepadCheckAccountStatus(self):
    #     # 方法1: 直接使用 instance=-1
    #     icon = self.d(resourceId="com.viber.voip:id/statusView", instance=-1)
    #     # 方法2: 获取列表后取末尾
    #     # icons = d(resourceId="com.app:id/icon").all()
    #     # icon = icons[-1] if icons else None
    #     if icon.exists:
    #         icon.screenshot()  # 截取图标 ‌二进制数据
    #         # icon.screenshot("icon.png")
    #     else:
    #         logging.error(f"当前行：{self.getLine()};没找到图标")


    def enter_phone_numbers(self, input_file, used_file):
        """输入电话号码，并检测群组人数，已使用的号码从 input_file 删除"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                phone_numbers = [line.strip() for line in f.readlines() if line.strip()]

            if not phone_numbers:
                logging.warning(f"当前行：{self.getLine()};电话号码列表为空")
                return

            # 清空已使用号码文件
            with open(used_file, "w", encoding="utf-8") as used_f:
                used_f.truncate(0)

            # 遍历所有电话号码
            for idx, phone in enumerate(phone_numbers):
                # 当phone.txt没号码的时候，点击完成
                with open(input_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line.strip():  # 读取第一行并去除空格、换行符
                        print("文件有内容")
                    else:
                        print("文件为空")
                        self.click_if_exists3("com.viber.voip:id/menu_done")
                        # 终止程序
                        sys.exit()

                phone_input = self.device(resourceId="com.viber.voip:id/add_recipients_search_field")

                if phone_input.exists(timeout=5):
                    phone_input.click()
                    time.sleep(0.2)
                    phone_input.set_text(phone)
                    time.sleep(0.2)
                    logging.info(f"当前行：{self.getLine()};输入电话号码: {phone}")
                    time.sleep(0.2)
                    with open(used_file, "a", encoding="utf-8") as used_f:# 将已使用的号码添加到 '已使用的号码.txt'
                        used_f.write(phone + '\n')
                    # 从原始文件中移除当前号码
                    with open(input_file, "r+", encoding="utf-8") as f:
                        lines = f.readlines()
                        f.seek(0)
                        f.truncate()
                        for line in lines:
                            if line.strip() != phone:
                                f.write(line)
                    time.sleep(0.2)
                    self.click_if_exists("com.viber.voip:id/new_num_layout")

                    if self.device(resourceId="android:id/button1").exists(timeout=2):
                        logging.warning(f"当前行：{self.getLine()};号码 {phone} 存在问题，跳过")
                        txt_list = ["确定"]  # 便签：多个语言
                        self.click_if_exists2("android:id/button1", 5, txt_list)  # 点击“我的记事”
                        continue
                else:
                    logging.warning(f"当前行：{self.getLine()};找不到输入框，跳过 {phone}")

                # self.click_if_exists("com.viber.voip:id/top_2_frame")

                # 每输入 15 个号码后，点击完成并进行确认
                self.phone_counter += 1
                if self.phone_counter >= 15:
                    # 点击完成并确认
                    if self.click_if_exists3("com.viber.voip:id/menu_done"):   #点击确定
                        time.sleep(1)  # 等待界面更新
                        self.click_if_exists("android:id/button1")
                        self.phone_counter = 0  # 计数器归零

                        # 确保回到正确的界面，继续拉人
                        time.sleep(2)  # 稍作等待，确保页面刷新

                        self.checkMembersCount()    # 检测群人数

                        if self.click_if_exists("com.viber.voip:id/icon"):
                            logging.info("成功返回到群管理界面，继续拉群")
                        else:
                            logging.warning("未能找到 'com.viber.voip:id/icon'，可能需要手动调整")

            logging.info(f"当前行：{self.getLine()};已处理的号码保存到 {used_file}")
        except Exception as e:
            print(f"错误内容：{e}")
            # logging.error(f"当前行：{self.getLine()};处理电话号码失败: {e}")

    # # 判断有没有200个成员
    # def checkMembersCount(self):
    #     # 获取指定id的文本；然后根据正则获取数字；判断有没有200个成员；满足200就退出程序
    #     numbePeopleText = self.device(resourceId="com.viber.voip:id/startText").text
    #     groupMembers = re.search(r'\((\d+)\)', numbePeopleText)
    #     if self.groupMembers >= 200:
    #         sys.exit()

    def checkMembersCount(self):
        try:
            # 获取文本内容
            numbePeopleElement = self.device(resourceId="com.viber.voip:id/startText")

            if numbePeopleElement.exists(timeout=2):  # 确保元素存在
                numbePeopleText = numbePeopleElement.get_text()
                logging.info(f"获取的群成员文本: {numbePeopleText}")

                # 使用正则表达式提取所有数字
                matches = re.findall(r'\d+', numbePeopleText)
                if matches:
                    # 取出最大值，防止提取到错误的数字（比如时间、ID 等）
                    groupMembers = max(map(int, matches))
                    logging.info(f"当前群成员数: {groupMembers}")

                    # 如果成员数达到 200，则退出程序
                    if groupMembers >= 200:
                        logging.info("群成员数已达到 200，返回桌面并打开下一个包")

                        # 返回桌面
                        self.device.press("home")
                        time.sleep(2)

                        # 重新执行 run 方法，进入新的群并发送第二个群链接
                        self.run()

                else:
                    logging.warning("未能解析群成员数，文本格式可能不正确")

            else:
                logging.warning("未找到群成员数文本元素")
        except Exception as e:
            logging.error(f"检查群成员数时发生错误: {e}")

    # 获取当前行
    def getLine(self):
        return inspect.currentframe().f_back.f_lineno

    def send_link_text(self, file_path):
        """发送文本链接"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                links = [line.strip() for line in f.readlines() if line.strip()]

            for link in links:
                text_box = self.device(resourceId="com.viber.voip:id/send_text")
                if text_box.exists(timeout=2):
                    text_box.set_text(link)
                    logging.info(f"当前行：{self.getLine()};输入文本: {link}")
                    time.sleep(0.05)

                    send_button = self.device(resourceId="com.viber.voip:id/btn_send")
                    if send_button.exists:
                        send_button.click()
                        logging.info(f"当前行：{self.getLine()};点击发送")
                        time.sleep(2)
                        element = self.device.xpath(
                            '//*[@resource-id="com.viber.voip:id/conversation_recycler_view"]/*[last()]//*[@resource-id="com.viber.voip:id/myNotesCheckView"]')

                        if element.exists:
                            logging.info("Found myNotesCheckView")
                        else:
                            logging.warning("myNotesCheckView not found in the last child")
                            time.sleep(2)
                            self.device.press("home")
                            time.sleep(2)
                            self.run()
                            time.sleep(2)
                            return False
                else:
                    logging.warning(f"当前行：{self.getLine()};未找到输入框")
        except Exception as e:
            logging.error(f"当前行：{self.getLine()};读取链接文件失败: {e}")

def clear_txt_file(file_path):
    """清空 TXT 文件的内容"""
    try:
        open(file_path, "w").close()  # 直接用 w 模式打开并关闭，文件内容会被清空
        print(f"文件 {file_path} 已清空。")
    except Exception as e:
        print(f"清空文件 {file_path} 失败: {e}")

def main():
    clear_txt_file("processed_packages.txt")
    clear_txt_file("已使用的号码.txt")
    devices = adbutils.adb.device_list()
    if not devices:
        logging.error("没有检测到任何设备，请检查连接状态。")
        return

    logging.info("已连接的设备:") 
    for device in devices:
        logging.info(f"设备序列号: {device.serial}")

    logging.info(f"启动设备: {devices[0]}")  
    viber_auto = ViberAutoGroups(devices[0], debug=True)
    viber_auto.run()

if __name__ == "__main__":
    main()
