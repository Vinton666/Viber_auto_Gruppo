import time
import datetime
import logging
import uiautomator2 as u2
import adbutils
import re
import inspect
import sys
import os

"""
Author: Lucas
Version: 1.0
"""
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
class ViberAutoGroups:
    line_number = 1  
    PULL_NUMBER = 15 
    SEARCH_NOT_FOUND_COUNT = 0  
    
    def __init__(self, device_id, debug=False):
        self.device_id = device_id
        self.device = u2.connect(device_id)
        if not self.device:
            logging.error(f"当前行：{self.getLine()};无法连接到设备 {device_id}，请检查 USB 连接或 WiFi ADB 状态。")
            return
        self.message_sent_status = 1  
        self.processed_packages = set()
        self.phone_counter = 0  
    
    def load_processed_packages(self):
        try:
            with open('processed_packages.txt', 'r', encoding='utf-8') as f:  
                create_if_not_exists(["已操作账号.txt"])
                return {line.strip() for line in f.readlines()}  
        except FileNotFoundError:  
            return set()
    
    def save_processed_packages(self):
        try:
            with open('processed_packages.txt', 'w', encoding='utf-8') as f:
                for pkg in self.processed_packages:
                    f.write(pkg + '\n')
        except Exception as e:
            logging.error(f"当前行：{self.getLine()};保存已处理的包名失败: {e}")
    
    def click_if_exists(self, resource_id, timeout=0.2):
        
        current_package = self.device.app_current().get('package', 'Unknown')
        """等待并点击某个 UI 元素"""
        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)
            element_text = element.get_text() or "无文本"
            element.click()
            logging.info(f"当前行：{self.getLine()};位于{current_package}包，点击了 {resource_id}，文本：{element_text}")
            return True
        logging.warning(f"当前行：{self.getLine()};位于{current_package}包，未找到 {resource_id}")
        return False
    
    def click_if_exists2(self, resource_id, timeout=2, text_list=None):
        """等待并点击带有特定 resourceId 和 text 的 UI 元素"""
        for text in text_list:
            self.click_text_view_if_exists(resource_id, text)
    def click_if_exists3(self, resource_id, timeout=2, check_progress=False):
        """
        等待并点击某个 UI 元素。
        如果 `check_progress=True`，则点击后等待 5 秒，并检查 `com.viber.voip:id/progress` 是否存在。
        如果 `com.viber.voip:id/progress` 存在，则判定账号异常。
        """
        current_package = self.device.app_current().get('package', 'Unknown')
        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)
            element_text = element.get_text() or "无文本"
            element.click()
            logging.info(f"当前行：{self.getLine()}; 位于 {current_package} 包，点击了 {resource_id}，文本：{element_text}")
            
            if check_progress:
                time.sleep(5)  
                if self.device(resourceId="com.viber.voip:id/progress").exists(3):
                    logging.warning(f"当前行：{self.getLine()}; 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                    
                    self.device.press("home")  
                    self.run()  
                else:
                    logging.error(f"当前行：{self.getLine()}; 账号状态正常")
            return True
        logging.warning(f"当前行：{self.getLine()}; 位于 {current_package} 包，未找到 {resource_id}")
        return False
    def click_text_view_if_exists(self, id, text, timeout=2):
        """通过文本和类名查找并点击 UI 元素"""
        element = self.device(resourceId=id, text=text)
        if element.exists(timeout=timeout):
            element.click()
            
            return True
        logging.warning(f"未找到文本为 '{text}' 且类名为 '{id}' 的控件")
        return False
    
    def notConnected(self):
        if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=2):
            self.device(resourceId="android:id/button1").click()  
            logging.error("未连接账号；已退出当前应用")
            self.device.press("home")   
            self.run()
    
    def find_and_open_dkplugin_package(self):
        """查找并启动未处理的 dkplugin 相关应用"""
        shell_response = self.device.shell("pm list packages")
        output_str = shell_response.output if hasattr(shell_response, "output") else str(shell_response)
        dkplugin_packages = {line.split(":")[-1] for line in output_str.split("\n") if 'dkplugin' in line}
        dkplugin_packages -= self.processed_packages  
        if dkplugin_packages:
            self.first_pkg = list(dkplugin_packages)[0]
            logging.info(f"当前行：{self.getLine()};打开应用: {self.first_pkg}")
            self.device.app_start(self.first_pkg)
            time.sleep(2)
            self.processed_packages.add(self.first_pkg)
            time.sleep(1)
            self.save_processed_packages()
            return True
        else:
            logging.error("当前行：{self.getLine()};没有找到新的 dkplugin 应用; 程序停止")
            sys.exit()

    def close_current_app(self):
        """关闭当前运行的应用"""
        try:
            current_package = self.device.app_current().get("package", "")
            if current_package:
                logging.error(f"当前行：{self.getLine()}; 关闭应用: {current_package}")
                self.device.app_stop(current_package)  
                time.sleep(1)  
            else:
                logging.error(f"当前行：{self.getLine()}; 未找到当前运行的应用")
        except Exception as e:
            logging.error(f"当前行：{self.getLine()}; 关闭应用失败: {e}")
    def append_account_to_file(self, text, file_path="已操作账号.txt"):
        """将设备获取的账号信息追加到指定文件"""
        try:
            account_text = text
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"{account_text}\n")
            logging.info(f"账号 {account_text} 已成功记录")
            return True
        except FileNotFoundError:
            logging.error(f"文件路径不存在：{file_path}")
        except PermissionError:
            logging.error(f"无写入权限：{file_path}")
        except Exception as e:
            logging.error(f"记录失败：{str(e)}")
        return False
    def run(self):
        global SEARCH_NOT_FOUND_COUNT
        self.phone_counter = 0

        self.processed_packages = self.load_processed_packages()
        if not self.find_and_open_dkplugin_package():
            return
        if self.detecting_account():
            logging.info("账号正常")
            self.click_if_exists("ix4s")  
            self.click_if_exists("com.viber.voip:id/btn_close")    
            self.click_if_exists("com.viber.voip:id/bottom_nav_tab_4")  
            self.click_if_exists("ix4s")    
            self.click_if_exists("com.viber.voip:id/btn_close")    
            self.append_account_to_file(self.device(resourceId="com.viber.voip:id/toolbar_custom_subtitle").get_text())   
            text_list = ["我的便签", "我的記事", "Mes Notes"]            
            self.click_if_exists2("com.viber.voip:id/titleView", 5, text_list)  
            self.click_if_exists("com.viber.voip:id/btn_close")    
            self.notConnected()
            time.sleep(2)
            self.click_if_exists("com.viber.voip:id/close")  
            self.click_if_exists("com.viber.voip:id/btn_close")
            time.sleep(1)
            self.send_link_text("link.txt") 
            self.click_if_exists("com.viber.voip:id/btn_close")
            time.sleep(2)
            self.click_if_exists("com.viber.voip:id/formattedMessageView") 
            self.click_if_exists("com.viber.voip:id/btn_close")    
            self.click_if_exists("com.viber.voip:id/toolbar") 
            self.click_if_exists("com.viber.voip:id/btn_close")    
            self.checkMembersCount()
            self.click_if_exists("com.viber.voip:id/addParticipantsItem") 
            self.click_if_exists("com.viber.voip:id/top_2_frame")   
            self.enter_phone_numbers("phone.txt", "已使用的号码.txt")
            if self.device(resourceId="com.viber.voip:id/share_group_link_explanation").exists(timeout=2):
               logging.warning("当前可能是建群账号拉取===方法后")
               self.SEARCH_NOT_FOUND_COUNT += 1
               logging.warning(f"找不到搜索框次数：{self.SEARCH_NOT_FOUND_COUNT}")
               if self.SEARCH_NOT_FOUND_COUNT >= 5:
                   logging.warning("当前可能是建群账号拉取")
                   self.device.press("home")  
                   self.run()  
            else:
                self.SEARCH_NOT_FOUND_COUNT = 0
        else:
            logging.warning("检测到账号异常，返回桌面并切换应用")
            self.device.press("home")
            self.run()      
    def detecting_account(self):
        """检测当前是否处于正常账号状态"""
        time.sleep(3)
        if self.device(resourceId="com.viber.voip:id/remote_banner_button").exists(timeout=2):
            logging.warning(f"当前行：{self.getLine()};检测到账号异常")
            return False
        elif self.device(resourceId="com.viber.voip:id/activity_home_root").exists(timeout=2):
            logging.warning(f"当前行：{self.getLine()};已在 Viber 主界面")
            return True
        elif self.device(resourceId="com.viber.voip:id/buttonMaybeLater").exists(timeout=2):
            logging.warning(f"当前行：{self.getLine()};检测到 '稍后' 按钮，点击继续")
            self.device(resourceId="com.viber.voip:id/buttonMaybeLater").click()
        else:
            logging.warning(f"当前行：{self.getLine()};未检测到已知状态，可能账号异常")
            return False

    def enter_phone_numbers(self, input_file, used_file):
        """输入电话号码，并检测群组人数，已使用的号码从 input_file 删除"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                phone_numbers = [line.strip() for line in f.readlines() if line.strip()]
            if not phone_numbers:
                logging.warning(f"当前行：{self.getLine()};电话号码列表为空")
                self.click_if_exists("com.viber.voip:id/new_num_layout") 
                self.click_if_exists("android:id/button1")
                sys.exit()
            
            with open(used_file, "w", encoding="utf-8") as used_f:
                used_f.truncate(0)
            error_count = 0
            for idx, phone in enumerate(phone_numbers):
                with open(input_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    if first_line.strip():  
                        self.click_if_exists("android:id/button1")
                        if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                            logging.warning(
                                f"当前行：{self.getLine()}; 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                            self.close_current_app()  
                            self.device.press("home")  
                            self.run()
                        
                    else:
                        logging.warning("电话号码文件为空")
                        self.click_if_exists3("com.viber.voip:id/menu_done")
                        self.click_if_exists("android:id/button1")
                        sys.exit()
                
                phone_input = self.device(resourceId="com.viber.voip:id/add_recipients_search_field")
                if phone_input.exists(timeout=1):
                    phone_input.click()
                    time.sleep(0.2)
                    phone_input.set_text(phone)
                    logging.info(f"当前行：{self.getLine()};输入电话号码: {phone}")
                    with open(used_file, "a", encoding="utf-8") as used_f:
                        used_f.write(phone + '\n')
                    with open(input_file, "r+", encoding="utf-8") as f:
                        lines = f.readlines()
                        f.seek(0)
                        f.truncate()
                        for line in lines:
                            if line.strip() != phone:
                                f.write(line)
                    time.sleep(0.2)
                    self.click_if_exists("com.viber.voip:id/new_num_layout")
                    if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                        time.sleep(15)
                        if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                            logging.warning(
                                f"当前行：{self.getLine()}; 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                            self.append_account_to_file(phone, "异常底料.txt")
                            self.close_current_app()  
                            self.device.press("home")  
                            self.run()  
                        elif self.device(resourceId="com.viber.voip:id/alertTitle").exists(5):
                            error_count += 1  
                            self.append_account_to_file(phone, "异常底料.txt")
                            logging.warning(f"当前行：{self.getLine()}; 号码 {phone} 存在问题，计数 {error_count}")
                            self.click_if_exists("android:id/button1")  
                        elif self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                            logging.warning(
                                f"当前行：{self.getLine()}; 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                            self.append_account_to_file(phone, "异常底料.txt")
                            self.close_current_app()  
                            self.device.press("home")  
                            self.run()
                    if error_count >= 3:
                        logging.warning("不是viber大于3次")
                        logging.error(f"当前行：{self.getLine()}; 连续 3 个号码输入错误，执行异常处理")
                        self.append_account_to_file(phone, "异常底料.txt")
                        time.sleep(0.2)
                        self.device.press("home")  
                        if self.find_and_open_dkplugin_package():  
                            self.run()  
                        return  
                else:
                    logging.warning(f"当前行：{self.getLine()};找不到输入框，跳过 {phone}")
                    return
                self.click_if_exists("com.viber.voip:id/top_2_frame")
                self.phone_counter += 1
                if self.phone_counter >= PULL_NUMBER:
                    
                    if self.click_if_exists3("com.viber.voip:id/menu_done"):   
                        time.sleep(1)  
                        self.click_if_exists("android:id/button1")
                        self.phone_counter = 0
                        time.sleep(1)  
                        self.checkMembersCount()    
                        if self.click_if_exists("com.viber.voip:id/icon"):
                            logging.info("成功返回到群管理界面，继续拉群")
                        else:
                            logging.warning("未能找到 'com.viber.voip:id/icon'，可能需要手动调整")
                            self.close_current_app()  
                            self.device.press("home")  
                            self.run()  
            logging.info(f"当前行：{self.getLine()};已处理的号码保存到 {used_file}")
            error_count = 0
        except Exception as e:
            logging.error(f"错误内容：{e}")
    def checkMembersCount(self):
        try:
            numbePeopleElement = self.device(resourceId="com.viber.voip:id/startText")
            if numbePeopleElement.exists(timeout=3):  
                numbePeopleText = numbePeopleElement.get_text()
                
                matches = re.findall(r'\d+', numbePeopleText)
                if matches:
                    groupMembers = max(map(int, matches))
                    logging.info(f"当前群成员数: {groupMembers}")
                    if groupMembers >= 200:
                        global line_number
                        self.line_number += 1
                        logging.info("群成员数已达到 200，返回桌面并打开下一个包")
                        time.sleep(0.2)
                        self.close_current_app()  
                        time.sleep(1)
                        self.device.press("home")
                        self.run()
                else:
                    logging.warning("未能解析群成员数，文本格式可能不正确")
            else:
                logging.warning("未找到群成员数文本元素")
        except Exception as e:
            logging.error(f"检查群成员数时发生错误: {e}")
    
    def getLine(self):
        return inspect.currentframe().f_back.f_lineno
    def send_link_text(self, file_path):
        """发送文本链接"""
        global line_number
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                links = [line.strip() for line in f.readlines() if line.strip()]
            if self.line_number > len(links):
                logging.error(f"当前行：{self.line_number}; 群已拉完，结束程序")
                sys.exit()
            link = links[self.line_number - 1]
            text_box = self.device(resourceId="com.viber.voip:id/send_text")
            if text_box.exists(timeout=0.5):
                text_box.set_text(link)
                time.sleep(0.05)
                send_button = self.device(resourceId="com.viber.voip:id/btn_send")
                if send_button.exists:
                    send_button.click()
                    logging.info(f"当前行：{self.line_number}; 点击发送")
                    time.sleep(5)
                    element = self.device.xpath(
                        '//*[@resource-id="com.viber.voip:id/conversation_recycler_view"]/*[last()]//*[@resource-id="com.viber.voip:id/myNotesCheckView"]')
                    if element.exists:
                        logging.info("Found myNotesCheckView")
                    else:
                        logging.error("myNotesCheckView not found in the last child")
                        self.device.press("home")
                        time.sleep(0.2)
                        self.run()
                        time.sleep(0.8)
                        return False
            else:
                logging.warning(f"当前行：{self.line_number}; 未找到输入框")
        except Exception as e:
            logging.error(f"当前行：{self.line_number}; 读取链接文件失败: {e}")
def rename_file_with_timestamp(file_path):
    try:
        
        base_name, file_ext = os.path.splitext(file_path)
        dir_path = os.path.dirname(file_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{base_name}_{timestamp}{file_ext}"
        new_path = os.path.join(dir_path, new_name)
        os.rename(file_path, new_path)
        logging.info(f"文件重命名成功：{file_path} -> {new_path}")
        return new_path
    except FileNotFoundError:
        logging.error(f"文件不存在：{file_path}")
    except PermissionError:
        logging.error(f"权限不足，无法重命名：{file_path}")
    except Exception as e:
        logging.error(f"重命名失败：{e}")
def create_if_not_exists(filenames):
    results = []
    current_dir = os.getcwd()
    for filename in filenames:
        file_path = os.path.join(current_dir, filename)
        if os.path.exists(file_path):
            results.append(f"已存在: {filename}")
        else:
            try:
                with open(file_path, 'w') as f:  
                    pass
                results.append(f"已创建: {filename}")
            except Exception as e:
                results.append(f"创建失败: {filename} ({str(e)})")
    return results
PULL_NUMBER = 15
def update_pull_number():
    global PULL_NUMBER
    while True:
        user_input = input("请输入每次拉取人数;正整数（回车使用默认值15）: ").strip()
        if not user_input:
            logging.info(f"使用默认值{PULL_NUMBER}")
            return
        try:
            num = int(user_input)
            if num > 0:
                PULL_NUMBER = num
                logging.info(f"每次拉取人数已更新为: {PULL_NUMBER}")
                return
            else:
                logging.error("错误：请输入大于0的正整数！")
        except ValueError:
            logging.error("错误：输入内容非数字，请重新输入！")
def main():
    rename_file_with_timestamp("processed_packages.txt")
    rename_file_with_timestamp("已使用的号码.txt")
    rename_file_with_timestamp("已操作账号.txt")
    results = create_if_not_exists(["已使用的号码.txt", "processed_packages.txt", "phone.txt", "link.txt", "异常底料.txt"])
    logging.info(results)
    devices = adbutils.adb.device_list()
    if not devices:
        logging.error("没有检测到任何设备，请检查连接状态。")
        return
    logging.info("已连接的设备:")
    for device in devices:
        logging.info(f"设备序列号: {device.serial}")
    update_pull_number()
    logging.info(f"启动设备: {devices[0]}")
    viber_auto = ViberAutoGroups(devices[0], debug=True)
    viber_auto.run()
if __name__ == "__main__":
    main()