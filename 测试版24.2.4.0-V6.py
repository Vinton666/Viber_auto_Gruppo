import time
import logging
import uiautomator2 as u2
import adbutils
import re
import inspect
import sys
import  os
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
    line_number = 1  
    NUM_TO_INPUT = 45  
    
    def __init__(self, device_id, debug=False):
        self.device_id = device_id
        self.device = u2.connect(device_id)
        if not self.device:
            logging.error(f"无法连接到设备 {device_id}，请检查 USB 连接或 WiFi ADB 状态。")
            return
        
        self.message_sent_status = 1  
        self.processed_packages = set()
        self.phone_counter = 0  
    
    def load_processed_packages(self):
        try:
            with open('processed_packages.txt', 'r', encoding='utf-8') as f:  
                return {line.strip() for line in f.readlines()}  
        except FileNotFoundError:  
            return set()
    
    def save_processed_packages(self):
        try:
            with open('processed_packages.txt', 'w', encoding='utf-8') as f:
                for pkg in self.processed_packages:
                    f.write(pkg + '\n')
        except Exception as e:
            logging.error(f"保存已处理的包名失败: {e}")
    
    def find_and_open_dkplugin_package(self):
        """查找并启动未处理的 dkplugin 相关应用"""
        shell_response = self.device.shell("pm list packages")
        
        output_str = shell_response.output if hasattr(shell_response, "output") else str(shell_response)
        dkplugin_packages = {line.split(":")[-1] for line in output_str.split("\n") if 'dkplugin' in line}
        dkplugin_packages -= self.processed_packages  
        if dkplugin_packages:
            self.first_pkg = list(dkplugin_packages)[0]
            logging.info(f"打开应用: {self.first_pkg}")
            self.device.app_start(self.first_pkg)
            time.sleep(3)
            self.processed_packages.add(self.first_pkg)
            time.sleep(2)
            self.save_processed_packages()
            return True
        else:
            logging.info("没有找到新的 dkplugin 应用")
            sys.exit()
    def close_current_app(self):
        """关闭当前运行的应用"""
        try:
            current_package = self.device.app_current().get("package", "")
            if current_package:
                logging.info(f" 关闭应用: {current_package}")
                self.device.app_stop(current_package)  
                time.sleep(2)  
            else:
                logging.warning(f" 未找到当前运行的应用")
        except Exception as e:
            logging.error(f" 关闭应用失败: {e}")
    def check_group_entry(self):
        """
        点击 'formattedMessageView' (群链接)，然后检查是否进入群组界面。
        如果未检测到 'menu_viber_call'，则关闭应用并重新执行。
        """
        logging.info("尝试点击群链接...")
        
        if self.click_if_exists("com.viber.voip:id/formattedMessageView"):
            time.sleep(2)  
            
            if self.device(resourceId="com.viber.voip:id/menu_viber_call").exists(timeout=3):
                logging.info("成功进入群组界面")
                return True  
            else:
                logging.warning("点击群链接后未检测到 'menu_viber_call'，点击无效，关闭应用并重新执行")
                self.close_current_app()  
                time.sleep(2)
                self.device.press("home")  
                self.run()  
                return False  
        else:
            logging.warning("未找到群链接 'formattedMessageView'")
            return False  
    def check_notepad_entry(self):
        """
        点击 '我的便签'，然后检查是否成功进入便签界面。
        如果未检测到 'send_text'，则关闭应用并重新执行。
        """
        text_list = ["我的便签", "我的記事", "My Notes","Mes Notes"]
        logging.info("尝试点击 '我的便签'...")
        if self.click_if_exists2("com.viber.voip:id/titleView", 5, text_list):
            time.sleep(2)  
            
            if self.device(resourceId="com.viber.voip:id/send_text").exists(timeout=3):
                logging.info("成功进入 '我的便签'")
                return True  
            else:
                logging.warning("点击 '我的便签' 后未检测到 'send_text'，点击无效，关闭应用并重新执行")
                self.close_current_app()  
                time.sleep(2)
                self.device.press("home")  
                self.run()  
        else:
            logging.warning("未找到 '我的便签'")
            return False  
    
    def click_if_exists(self, resource_id, timeout=3):
        
        current_package = self.device.app_current().get('package', 'Unknown')
        """等待并点击某个 UI 元素"""
        element = self.device(resourceId=resource_id)
        if element.exists(timeout=timeout):
            time.sleep(1)  
            
            element_text = element.get_text() or "无文本"
            element.click()
            logging.info(f"位于{current_package}包，点击了 {resource_id}，文本：{element_text}")
            return True
        logging.warning(f"位于{current_package}包，未找到 {resource_id}")
        return False
    
    def click_if_exists2(self, resource_id, timeout=5, text_list=None):
        """等待并点击带有特定 resourceId 和 text 的 UI 元素"""
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
            time.sleep(1)
            element_text = element.get_text() or "无文本"
            element.click()
            logging.info(f" 位于 {current_package} 包，点击了 {resource_id}，文本：{element_text}")
            
            if check_progress:
                time.sleep(5)  
                if self.device(resourceId="com.viber.voip:id/progress").exists(timeout=5):
                    logging.warning(f" 发现进度条 (com.viber.voip:id/progress)，判定账号异常")
                    self.close_current_app()  
                    self.device.press("home")  
                    self.run()  
                else:
                    logging.info(f" 账号状态正常")
            return True
        logging.warning(f" 位于 {current_package} 包，未找到 {resource_id}")
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
    
    def notConnected(self):
        
        if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=2):
            self.device(resourceId="android:id/button1").click()  
            logging.info("未连接账号；已退出当前应用")
            self.close_current_app()  
            self.device.press("home")   
            self.run()   
    def run(self):
        self.phone_counter = 0
        self.processed_packages = self.load_processed_packages()
        if not self.find_and_open_dkplugin_package():
            return
        if self.detecting_account():
            logging.info("账号正常")
            self.click_if_exists("ix4s")  
            self.click_if_exists("com.viber.voip:id/bottom_nav_tab_4")  
            self.click_if_exists("ix4s")    
            self.check_notepad_entry() 
            self.notConnected() 
            self.click_if_exists("com.viber.voip:id/close")  
            time.sleep(2)
            self.send_link_text("link.txt")
            time.sleep(2)
            self.check_group_entry()         
            self.click_if_exists("com.viber.voip:id/toolbar") 
            self.checkMembersCount()    
            self.click_if_exists("com.viber.voip:id/icon") 
            time.sleep(2)
            
            self.enter_phone_numbers("phone.txt", "已使用的号码.txt")
        else:
            logging.warning("检测到账号异常，返回桌面并切换应用")
            time.sleep(5)
            self.close_current_app()  
            self.device.press("home")  
            self.run()      
    def detecting_account(self):
        """检测当前是否处于正常账号状态"""
        time.sleep(3)
        if self.device(resourceId="com.viber.voip:id/remote_banner_button").exists(timeout=2):
            logging.warning(f"检测到账号异常")
            return False
        elif self.device(resourceId="com.viber.voip:id/activity_home_root").exists(timeout=2):
            logging.info(f"已在 Viber 主界面")
            return True
        elif self.device(resourceId="com.viber.voip:id/buttonMaybeLater").exists(timeout=2):
            logging.info(f"检测到 '稍后' 按钮，点击继续")
            self.device(resourceId="com.viber.voip:id/buttonMaybeLater").click()
        else:
            logging.warning(f"未检测到已知状态，可能账号异常")
            return False
    def enter_phone_numbers(self, input_file, used_file):
        """输入电话号码，并检测群组人数，已使用的号码从 input_file 删除"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                phone_numbers = [line.strip() for line in f.readlines() if line.strip()]
            if not phone_numbers:
                logging.warning(f" 电话号码列表为空")
                self.click_if_exists("com.viber.voip:id/new_num_layout")  
                self.click_if_exists("android:id/button1")
                sys.exit()
            invalid_numbers = []  
            error_count = 0  
            self.phone_counter = 0  
            
            for idx, phone in enumerate(phone_numbers):
                phone_input = self.device(resourceId="com.viber.voip:id/add_recipients_search_field")
                check_time = 0  
                if phone_input.exists(timeout=3):
                    phone_input.click()
                    time.sleep(0.2)
                    phone_input.set_text(phone)
                    logging.info(f" 输入电话号码: {phone}")
                    
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
                    time.sleep(1)
                    while not phone_input.exists(timeout=2):
                        logging.warning(f" 找不到输入框，暂停输入电话号码")
                        
                        if self.device(resourceId="com.viber.voip:id/alertTitle").exists(timeout=15):
                            logging.warning(f" 检测到号码问题，点击确认")
                            if self.device(resourceId="android:id/button1").exists(timeout=2):
                                invalid_numbers.append(phone)
                                logging.warning(f" 号码 {phone} 存在问题，计数 {error_count + 1}/3")
                                self.click_if_exists("android:id/button1")  
                                error_count += 1  
                            else:
                                error_count = 0  
                                logging.info(f"号码有效，当前号码{phone}")
                            time.sleep(1)  
                        check_time += 2  
                        
                        if check_time >= 30:
                            logging.error(f" 超过 30 秒未找到输入框，执行异常处理")
                            self.close_current_app()  
                            time.sleep(2)
                            self.device.press("home")  
                            self.run()  
                    
                    if error_count >= 3:
                        logging.error(f" 连续 3 个号码输入错误，执行异常处理")
                        with open("无效号码.txt", "a", encoding="utf-8") as invalid_file:
                            for num in invalid_numbers:
                                invalid_file.write(num + "\n")  
                        logging.info("❌ 无效号码已保存到 '无效号码.txt'")
                        self.close_current_app()  
                        time.sleep(2)
                        self.device.press("home")  
                        self.run()  
                    
                    self.phone_counter += 1
                    logging.info(f" 当前已输入号码: {self.phone_counter}/{NUM_TO_INPUT}")
                    
                    if self.phone_counter >= NUM_TO_INPUT:
                        logging.info("达到用户设定的号码数量，点击完成按钮")
                        if self.click_if_exists3("com.viber.voip:id/menu_done"):  
                            time.sleep(2)  
                             
                            if self.device(resourceId="android:id/button1").exists(timeout=15):
                                logging.info("检测到确认按钮 'android:id/button1'，点击继续")
                                self.click_if_exists("android:id/button1")  
                            elif self.device(resourceId="com.viber.voip:id/body").exists(timeout=10):
                                logging.error("检测到 'com.viber.voip:id/body'，账号异常，执行异常处理")
                                time.sleep(50)
                                self.close_current_app()  
                                time.sleep(2)
                                self.run()  
                                return  
                            self.phone_counter = 0  
                            time.sleep(2)  
                            self.checkMembersCount()  
                            if self.click_if_exists("com.viber.voip:id/icon"):
                                logging.info("成功返回到群管理界面，继续拉群")
                            else:
                                logging.warning("未能找到 'com.viber.voip:id/icon'，可能需要手动调整")
                else:
                    
                    logging.info(f" 已处理的号码保存到 {used_file}")
        except Exception as e:
            logging.error(f" 处理电话号码失败: {e}")
            sys.exit()
    def checkMembersCount(self):
        try:
            
            numbePeopleElement = self.device(resourceId="com.viber.voip:id/startText")
            if numbePeopleElement.exists(timeout=2):  
                numbePeopleText = numbePeopleElement.get_text()
                logging.info(f"获取的群成员文本: {numbePeopleText}")
                
                matches = re.findall(r'\d+', numbePeopleText)
                if matches:
                    
                    groupMembers = max(map(int, matches))
                    logging.info(f"当前群成员数: {groupMembers}")
                    
                    if groupMembers >= 200:
                        global line_number
                        self.line_number += 1
                        logging.info("群成员数已达到 200，返回桌面并打开下一个包")
                        self.close_current_app()  
                        time.sleep(2)
                        self.device.press("home")
                        self.run()
                else:
                    logging.warning("未能解析群成员数，文本格式可能不正确")
                    sys.exit()
            else:
                logging.warning("未找到群成员数文本元素")
                self.close_current_app()  
                self.run()  
        except Exception as e:
            logging.error(f"检查群成员数时发生错误: {e}")
            sys.exit()
    
    def getLine(self):
        return inspect.currentframe().f_back.f_lineno
    def send_link_text(self, file_path):
        """发送文本链接"""
        global line_number
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                links = [line.strip() for line in f.readlines() if line.strip()]
            
            if self.line_number > len(links):
                
                logging.warning(f"当前行：{self.line_number}; 群已拉完，结束程序")
                sys.exit()                
            link = links[self.line_number - 1] 
            text_box = self.device(resourceId="com.viber.voip:id/send_text")
            if text_box.exists(timeout=2):
                text_box.set_text(link)
                logging.info(f"当前行：{self.line_number}; 输入文本: {link}")
                time.sleep(0.05)
                send_button = self.device(resourceId="com.viber.voip:id/btn_send")
                if send_button.exists:
                    send_button.click()
                    logging.info(f"当前行：{self.line_number}; 点击发送")
                    
                    time.sleep(5)
                    element = self.device.xpath(
                        '//*[@resource-id="com.viber.voip:id/conversation_recycler_view"]/*[last()]//*[@resource-id="com.viber.voip:id/myNotesCheckView"]')
                    if element.exists:
                        logging.info("链接发送至记事本成功")
                    else:
                        logging.warning("链接发送至记事本失败，账号异常，正在关闭应用")
                        self.close_current_app()  
                        time.sleep(2)
                        self.run()
                        return False
            else:
                logging.warning(f"当前行：{self.line_number}; 未找到输入框")
        except Exception as e:
            logging.error(f"当前行：{self.line_number}; 读取链接文件失败: {e}")
def set_num_to_input():
    """获取用户输入的电话号码数量，并存储到全局变量 NUM_TO_INPUT"""
    global NUM_TO_INPUT  
    while True:
        user_input = input("\n请输入要输入的电话号码数量（默认 45，直接回车可跳过）: ").strip()
        if user_input == "":
            NUM_TO_INPUT = 45  
            break
        try:
            num = int(user_input)
            if num > 0:
                NUM_TO_INPUT = num
                break
            else:
                print("❌ 请输入大于 0 的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
    logging.info(f"用户设置的号码输入数量: {NUM_TO_INPUT}")
def clear_txt_file(file_path):
    """清空 TXT 文件的内容"""
    try:
        open(file_path, "w").close()  
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
    set_num_to_input()
    logging.info("已连接的设备:")
    for device in devices:
        logging.info(f"设备序列号: {device.serial}")
    logging.info(f"启动设备: {devices[0]}")
    viber_auto = ViberAutoGroups(devices[0], debug=True)
    viber_auto.run()
if __name__ == "__main__":
    main()