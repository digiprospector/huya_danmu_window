# ==============================================================================
# 导入所需模块
# ==============================================================================
import tkinter as tk
import asyncio
import json
import random
from playwright.async_api import async_playwright, Route, Page
import threading
import os
from config import config

# ==============================================================================
# 全局变量和常量定义
# ==============================================================================
# 用于在UI和弹幕抓取逻辑之间共享弹幕文本的全局变量
shared_danmu_text = "正在初始化弹幕..."

# 全局Tkinter root对象，以便在主线程中访问和关闭
tk_root = None

# 存储窗口位置状态的文件名
WINDOW_STATE_FILE = "window_state.json"


# ==============================================================================
# 窗口状态管理 (位置保存与加载)
# ==============================================================================
def save_window_state(root_obj):
    """保存窗口的当前位置到文件"""
    if root_obj:
        try:
            x = root_obj.winfo_x()
            y = root_obj.winfo_y()
            state = {"x": x, "y": y}
            with open(WINDOW_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
            print(f"窗口位置已保存: x={x}, y={y}")
        except Exception as e:
            print(f"保存窗口位置失败: {e}")

def load_window_state():
    """从文件加载窗口的上次位置"""
    if os.path.exists(WINDOW_STATE_FILE):
        try:
            with open(WINDOW_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                return state.get("x", 50), state.get("y", 50) # 提供默认值
        except (json.JSONDecodeError, Exception) as e:
            print(f"加载窗口位置文件失败: {e}")
    return 50, 50 # 默认位置


# ==============================================================================
# UI界面部分 (Tkinter)
# ==============================================================================
def create_draggable_overlay_window():
    """创建并运行可拖动的弹幕悬浮窗"""
    global shared_danmu_text, tk_root
    # 1. 初始化主窗口
    root = tk.Tk()
    tk_root = root # 将root对象赋值给全局变量，以便在其他地方访问
    root.title("实时信息叠加层 - 可拖动")
    
    # 2. 初始化拖动所需的变量
    # 用于存储鼠标按下时的初始 X 和 Y 坐标
    root._drag_x = 0
    root._drag_y = 0

    # --- 核心窗口设置（与之前相同）---
    root.overrideredirect(True)      # 无边框
    root.wm_attributes("-topmost", True) # 始终保持最前
    root.attributes("-alpha", 0.8)   # 半透明
    root.attributes("-transparentcolor", "black") # 背景透明键
    
    # 窗口初始大小和位置
    window_width = 1200
    window_height = 400
    
    # 加载上次保存的位置，如果不存在则使用默认值
    initial_x, initial_y = load_window_state()
    root.geometry(f"{window_width}x{window_height}+{initial_x}+{initial_y}") 
    
    # --- 3. 添加拖动事件绑定 ---

    # 鼠标左键按下时
    def start_drag(event):
        # 记录鼠标按下时，鼠标相对于窗口左上角的坐标
        root._drag_x = event.x
        root._drag_y = event.y

    # 鼠标左键按住拖动时
    def do_drag(event):
        # 计算新位置：
        # 屏幕鼠标绝对坐标 (root.winfo_pointerx()) 
        # 减去 鼠标按下时相对于窗口的坐标 (root._drag_x) 
        # 得到窗口左上角的新 X 坐标
        
        new_x = root.winfo_pointerx() - root._drag_x
        new_y = root.winfo_pointery() - root._drag_y
        
        # 移动窗口到新位置
        root.geometry(f"+{new_x}+{new_y}")

    # 将事件绑定到整个窗口
    root.bind('<Button-1>', start_drag) # 绑定鼠标左键按下事件
    root.bind('<B1-Motion>', do_drag)   # 绑定鼠标左键按住拖动事件
    
    # --- 4. 添加内容和实时更新（与之前相同）---
    realtime_label = tk.Label(
        root, 
        text="【可拖动信息框】\n请点击并拖动我", 
        font=("微软雅黑", 14, "bold"),
        fg="white", 
        bg="black", # 必须是透明色键设置的颜色
        justify=tk.LEFT,
        padx=10, 
        pady=10
    )
    # 使用 pack(fill='both', expand=True) 确保 Label 铺满整个窗口
    realtime_label.pack(fill='both', expand=True) 
    
    # 这一行很重要：它确保拖动事件也能在 Label 上触发
    realtime_label.bind('<Button-1>', start_drag)
    realtime_label.bind('<B1-Motion>', do_drag)

    # 定义更新函数
    def update_text():
        # 获取当前窗口的几何信息
        current_bottom = root.winfo_y() + root.winfo_height()

        # 1. 直接从共享变量读取文本并更新UI
        if realtime_label.cget("text") != shared_danmu_text:
            need_update_y = True
            if "【可拖动信息框】\n请点击并拖动我" == realtime_label.cget("text"):
                need_update_y = False
            realtime_label.config(text=shared_danmu_text)
            # 2. 强制更新UI以获取新的所需高度
            root.update_idletasks()

            # 3. 获取Label内容更新后所需的新高度
            new_height = realtime_label.winfo_reqheight()
            # 4. 计算新的顶部Y坐标，以保持窗口底部位置不变
            new_y = current_bottom - new_height
            # 5. 同时更新窗口的高度和位置
            if need_update_y:
                root.geometry(f"{root.winfo_width()}x{new_height}+{root.winfo_x()}+{new_y}")

        # 每 500ms 检查一次更新
        root.after(500, update_text)

    update_text()
    
    root.mainloop()

def on_closing():
    """当Tkinter窗口关闭时调用，用于保存位置并销毁窗口"""
    global tk_root
    if tk_root:
        save_window_state(tk_root)
        tk_root.destroy()
        tk_root = None # 清除全局引用

# ==============================================================================
# 弹幕抓取部分 (Playwright)
# ==============================================================================
# 全局浏览器实例，用于在程序退出时关闭
browser = None

# 用于在内存中保存最新的弹幕
danmu_history = []


# --- 弹幕处理常量 ---
DANMU_MAX_LINES = 10  # 悬浮窗中显示的最大弹幕行数
DANMU_MAX_WIDTH = 22  # 每行弹幕的最大字符宽度

async def handle_route(route: Route):
    """拦截和修改网络请求"""
    request = route.request
    resource_type = request.resource_type
    url = request.url

    # 1. 阻止加载图片、媒体等不必要的资源
    if resource_type in ["image", "media"] or ".flv" in url:
        await route.abort()
        return

    # 2. 找到目标JS文件并注入代码
    if ".js" in url:
        try:
            response = await route.fetch()
            original_body = await response.text()

            # 通过特征字符串定位JS文件
            if '手机绑定失败，请稍后重试！' in original_body and '直播间上锁了哟，需解锁后才能发言！' in original_body:
                print(f"成功定位到目标JS文件: {url}")
                
                # 虎牙的页面可能会覆盖 console.log，这里注入一段JS代码来重新绑定 console.log
                # 这是原始JS脚本中的一个关键技巧
                jscode = """
                try {
                    const iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    document.body.appendChild(iframe);
                    console.log = iframe.contentWindow.console.log.bind(window.console);
                    console.log('1111：js注入成功!');
                } catch (e) {
                    // 忽略错误
                }
                """
                modified_body = jscode + original_body
                
                # 注入代码以捕获弹幕消息
                modified_body = modified_body.replace(
                    '.prototype.__showMessage=function(e){',
                    '.prototype.__showMessage=function(e){console.log("0000：" + JSON.stringify(e));'
                )
                
                await route.fulfill(
                    status=200,
                    content_type="application/javascript",
                    body=modified_body
                )
            else:
                await route.continue_()
        except Exception:
            # 如果请求失败（例如，页面关闭时），则继续
            await route.continue_()
    else:
        await route.continue_()

def handle_console_message(msg):
    """处理浏览器控制台消息"""
    global danmu_history, shared_danmu_text
    text = msg.text
    if text.startswith("1111："):
        print(text.replace("1111：", ""))
    elif text.startswith("0000："):
        try:
            data_str = text.replace("0000：", "")
            obj = json.loads(data_str)
            # 根据JS中的对象结构提取信息
            # 确保 tUserInfo 和 sNickName 存在
            if obj and "tUserInfo" in obj and "sNickName" in obj["tUserInfo"]:
                username = obj.get("tUserInfo", {}).get("sNickName", "未知用户")
                content = obj.get("sContent", "")
                danmu_msg = f"{username}：　{content}"
                print(danmu_msg)

                # --- 在内存中管理弹幕历史并更新共享变量 ---
                # 将原始弹幕消息添加到历史记录中
                danmu_history.append(danmu_msg)
                # 仅保留最后10条原始弹幕
                danmu_history = danmu_history[-DANMU_MAX_LINES:]
                
                # 准备要写入文件的行，处理换行
                lines_to_write = []
                for msg in danmu_history:
                    if len(msg) > DANMU_MAX_WIDTH:
                        lines_to_write.extend([msg[i:i+DANMU_MAX_WIDTH] + "\n" for i in range(0, len(msg), DANMU_MAX_WIDTH)])
                    else:
                        lines_to_write.append(msg + "\n")
                # 在最后添加一行由空格组成的行
                lines_to_write.append('　' * DANMU_MAX_WIDTH + '\n')

                # 更新共享变量，让UI线程可以读取
                shared_danmu_text = "".join(lines_to_write)
        except (json.JSONDecodeError, KeyError):
            pass # 忽略解析错误

async def move_mouse_periodically(page: Page):
    """定期移动鼠标以防止页面休眠"""
    while True:
        try:
            await asyncio.sleep(60)
            if not page.is_closed():
                x = random.randint(1, 1000)
                y = random.randint(1, 500)
                await page.mouse.move(x, y)
        except asyncio.CancelledError:
            break
        except Exception:
            break

async def danmu_main(room_id):
    """使用Playwright启动浏览器并抓取弹幕"""
    global browser
    async with async_playwright() as p:
        try:
            # 原始脚本使用的是firefox，这里保持一致
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
                service_workers='block'
            )
            page = await context.new_page()

            page.on("console", handle_console_message)
            await page.route("**/*", handle_route)
            
            print("正在导航到虎牙直播间...")
            # 改成自己想看的主播直播地址
            await page.goto(f'https://www.huya.com/{room_id}')
            
            mouse_task = asyncio.create_task(move_mouse_periodically(page))
            
            # 保持脚本运行以持续接收弹幕
            await asyncio.Event().wait() # 永久等待，直到被取消

        except asyncio.CancelledError:
            print("弹幕抓取任务被取消...")
        except Exception as e:
            print(f"弹幕抓取任务出现错误: {e}")
        finally:
            print("正在关闭浏览器...")
            if 'mouse_task' in locals() and not mouse_task.done():
                mouse_task.cancel()
            if browser and browser.is_connected():
                await browser.close()

# ==============================================================================
# 主程序逻辑
# ==============================================================================
if __name__ == "__main__":
    print("程序启动...")
    
    # 从 config.py 中获取 room_id，提供默认值
    room_id = config.get("room_id", "617694")
    print(f"配置的直播间ID: {room_id}")
    
    # 包装函数，用于在UI线程中创建窗口并设置全局 tk_root
    def run_ui():
        create_draggable_overlay_window()

    # 在一个独立的线程中运行Tkinter的UI
    ui_thread = threading.Thread(target=run_ui) # 移除 daemon=True
    ui_thread.start()
    print("弹幕悬浮窗UI线程已启动...")

    # 在主线程中运行asyncio事件循环来抓取弹幕
    loop = asyncio.get_event_loop()
    danmu_task = loop.create_task(danmu_main(room_id))
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n收到退出信号 (Ctrl+C), 程序正在关闭...")
    finally:
        print("开始清理资源...")
        # 清理 asyncio 任务
        print("正在取消弹幕抓取任务...")
        danmu_task.cancel()
        try:
            # 等待任务完成取消
            loop.run_until_complete(danmu_task)
        except asyncio.CancelledError:
            pass # 任务被取消是预期的行为，忽略此异常
        
        # 清理 Tkinter UI
        if tk_root: # 检查窗口是否实际创建
            print("正在关闭UI窗口并保存位置...")
            # 在 Tkinter 线程中调度 on_closing 函数
            tk_root.after(0, on_closing)
            ui_thread.join(timeout=5) # 等待 UI 线程结束，设置超时
            if ui_thread.is_alive():
                print("警告: Tkinter UI 线程未能正常终止。")
        
        loop.close()
        print("程序已退出")
