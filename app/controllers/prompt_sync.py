#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提示词同步控制器
负责将提示词从辅助窗口同步到主窗口的AI视图
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import time
import json
import traceback

class PromptSync(QObject):
    """提示词同步管理器，负责将提示词从输入区同步到AI视图"""
    
    # 信号定义
    prompt_synced = pyqtSignal(str)  # 提示词同步成功信号
    response_collected = pyqtSignal(str, list)  # 回复收集完成信号，参数: prompt_id, responses
    
    # 轮询参数
    INITIAL_WAIT_TIME = 5000  # 初始等待时间（毫秒）
    POLLING_INTERVAL = 2000   # 轮询间隔时间（毫秒）
    STABILITY_THRESHOLD = 3   # 内容稳定阈值（连续几次内容相同视为稳定）
    MAX_WAIT_TIME = 60000     # 最大等待时间（毫秒）
    
    def __init__(self):
        super().__init__()
        self.db_manager = None
        # self.ai_views = [] # 不再使用列表存储多个AIView
        self.ai_view_container = None # 存储单个AIView容器实例
        
        self.current_prompt_id = None
        self.current_prompt_text = None
        self.collected_responses = []
        
        # 轮询相关状态 - 使用 AI key 作为字典键
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_responses)
        self.poll_start_time = None
        self.pending_views = set() # 存储待处理的 AI key
        self.previous_responses = {} # 存储上一次响应 {ai_key: response_text}
        self.stability_counter = {} # 存储稳定计数 {ai_key: count}
    
    def set_db_manager(self, db_manager):
        """设置数据库管理器"""
        self.db_manager = db_manager
    
    def register_ai_view(self, ai_view_container):
        """注册AI视图容器
        
        Args:
            ai_view_container (AIView): AI视图容器实例
        """
        # if ai_view not in self.ai_views:
        #     self.ai_views.append(ai_view)
        if self.ai_view_container is None:
            self.ai_view_container = ai_view_container
        elif self.ai_view_container != ai_view_container:
            print("警告：尝试注册不同的 AIView 容器。只支持一个容器。")

    def unregister_ai_view(self, ai_view_container):
        """取消注册AI视图容器
        
        Args:
            ai_view_container (AIView): AI视图容器实例
        """
        # if ai_view in self.ai_views:
        #     self.ai_views.remove(ai_view)
        if self.ai_view_container == ai_view_container:
            self.ai_view_container = None
            self._stop_polling() # 容器移除时停止轮询
        else:
            print("警告：尝试取消注册未注册的 AIView 容器。")
            
    def sync_prompt(self, prompt_text):
        """将提示词同步到所有AI视图
        
        Args:
            prompt_text (str): 提示词文本
            
        Returns:
            bool: 是否成功开始同步过程
        """
        try:
            print("="*50)
            print("开始处理sync_prompt函数调用...")
            print(f"提示词长度: {len(prompt_text)}字符")
            print(f"提示词前100字符: {prompt_text[:100]}...")
            
            # 检查AI视图容器是否可用
            if not self.ai_view_container:
                print("错误: 没有注册的AI视图容器，无法同步提示词")
                print("AI视图容器对象: None")
                return False
                
            print(f"AI视图容器类型: {type(self.ai_view_container).__name__}")
            
            # 生成唯一的提示词ID（基于时间戳）
            self.current_prompt_id = str(int(time.time() * 1000))
            self.current_prompt_text = prompt_text
            print(f"生成的提示词ID: {self.current_prompt_id}")
            
            # 清空上次收集结果
            self.collected_responses = []
            self.previous_responses = {}
            self.stability_counter = {}
            self.pending_views = set()
            print("已清空上次收集的结果和状态")
            
            # 检查AI视图容器中是否有活动的视图
            if not hasattr(self.ai_view_container, 'ai_web_views'):
                print("错误: AI视图容器没有ai_web_views属性")
                print(f"容器可用属性: {dir(self.ai_view_container)}")
                return False
                
            # 获取活动视图
            active_views = self.ai_view_container.ai_web_views
            print(f"活动视图类型: {type(active_views)}")
            
            if not active_views:
                print("警告: AI视图容器中没有活动的AI视图")
                return False
                
            # 视图数量检查
            view_count = len(active_views) if hasattr(active_views, '__len__') else '未知'
            print(f"活动视图数量: {view_count}")
            
            # 发送提示词到所有活动视图
            success_count = 0
            error_count = 0
            
            for ai_key, web_view in active_views.items():
                try:
                    print(f"正在发送提示词到视图 {ai_key}...")
                    
                    # 验证web_view对象
                    if not hasattr(web_view, 'fill_prompt'):
                        print(f"错误: 视图 {ai_key} 没有fill_prompt方法")
                        error_count += 1
                        continue
                    
                    try:
                        # 添加保护性处理以防止崩溃
                        print(f"  尝试发送到 {ai_key}，提示词长度: {len(prompt_text)}字符")
                        
                        # 使用更安全的方法发送提示词（尝试单独捕获这一步的异常）
                        web_view.fill_prompt(prompt_text)
                        print(f"  -> fill_prompt调用成功")
                        
                        # 更新状态
                        self.pending_views.add(ai_key)
                        self.stability_counter[ai_key] = 0
                        self.previous_responses[ai_key] = None
                        
                        print(f"  -> 成功发送至 {getattr(web_view, 'ai_name', 'Unknown')} (Key: {ai_key})")
                        success_count += 1
                    except Exception as fill_err:
                        print(f"  -> fill_prompt调用失败: {str(fill_err)}")
                        error_count += 1
                        # 继续处理其他视图
                        continue
                    
                except Exception as e:
                    error_count += 1
                    print(f"  -> 发送至视图 {ai_key} 时出错: {str(e)}")
                    print(traceback.format_exc())
            
            # 汇总发送结果
            print(f"提示词发送完成: 成功 {success_count}, 失败 {error_count}")
            
            if success_count == 0:
                print("错误: 没有成功发送到任何AI视图")
                return False
                
            # 发射同步信号
            print("发送prompt_synced信号...")
            self.prompt_synced.emit(self.current_prompt_id)
            
            # 开始轮询检查响应
            print("启动轮询检查...")
            self._start_polling()
            
            print("sync_prompt函数处理完成")
            print("="*50)
            return True
            
        except Exception as e:
            print(f"sync_prompt函数执行出错: {str(e)}")
            print(traceback.format_exc())
            print("="*50)
            return False
    
    def _start_polling(self):
        """开始轮询检查响应"""
        if not self.pending_views:
             print("没有待处理的视图，不启动轮询。")
             return
             
        print(f"启动响应轮询，初始等待 {self.INITIAL_WAIT_TIME}ms...")
        self.poll_start_time = time.time()
        self.poll_timer.start(self.INITIAL_WAIT_TIME) # 首次延迟执行
        
    def _stop_polling(self):
        """停止轮询"""
        if self.poll_timer.isActive():
            print("停止响应轮询。")
            self.poll_timer.stop()
            self.poll_start_time = None
    
    def _poll_responses(self):
        """轮询所有AI视图的响应"""
        # 检查是否超时
        elapsed_time = (time.time() - self.poll_start_time) * 1000
        if elapsed_time > self.MAX_WAIT_TIME:
            print(f"轮询超时（超过 {self.MAX_WAIT_TIME}ms），强制结束收集。")
            self._finalize_collection()
            return
        
        # 如果是首次执行（由INITIAL_WAIT_TIME触发），切换到常规间隔
        if self.poll_timer.interval() == self.INITIAL_WAIT_TIME:
             print(f"初始等待结束，切换到轮询间隔 {self.POLLING_INTERVAL}ms。")
             self.poll_timer.setInterval(self.POLLING_INTERVAL)

        if not self.pending_views:
            print("所有视图响应已收集或稳定，停止轮询。")
            self._finalize_collection()
            return

        if not self.ai_view_container:
             print("AI视图容器丢失，停止轮询。")
             self._stop_polling()
             return

        print(f"轮询检查响应，剩余待处理视图: {len(self.pending_views)}")
        # 遍历所有注册的视图
        # for view_idx, ai_view in enumerate(self.ai_views):
        #     if view_idx in self.pending_views:
        #          self._check_view_response(view_idx, ai_view)
        active_views = self.ai_view_container.ai_web_views
        for ai_key in list(self.pending_views): # 使用list复制，因为集合可能在迭代中修改
            if ai_key in active_views:
                web_view = active_views[ai_key]
                self._check_view_response(ai_key, web_view)
            else:
                # 如果视图不再活动（可能被用户关闭或切换），从待处理中移除
                print(f"视图 {ai_key} 不再活动，从轮询中移除。")
                self.pending_views.remove(ai_key)
                # 可以选择记录一个默认失败状态
                # self.collected_responses.append({"url": f"view_{ai_key}_removed", "reply": "视图已移除"})

        # 如果检查后所有视图都完成，则结束
        if not self.pending_views:
            self._finalize_collection()

    # def _check_view_response(self, view_idx, ai_view):
    def _check_view_response(self, ai_key, web_view):
        """检查单个AI视图的响应并处理稳定性"""
        
        # 定义响应回调
        def response_callback(result):
            if not result:
                print(f"视图 {ai_key} ({web_view.ai_name}) 获取响应失败。")
                # 考虑是否需要重试或标记为失败
                # 如果连续失败，也可以移除
                # self.pending_views.remove(ai_key)
                return

            # 提取回复内容，如果 result 或 reply 不存在则为空字符串
            reply_content = result.get('reply', '') if result else ''
            
            # 检查内容是否稳定
            # previous_reply = self.previous_responses.get(view_idx)
            previous_reply = self.previous_responses.get(ai_key)
            
            # 打印调试信息
            # print(f"  检查视图 {ai_key}: 当前 '{reply_content[:30]}...', 上次 '{str(previous_reply)[:30]}...', 稳定计数: {self.stability_counter.get(ai_key, 0)}")

            if reply_content and reply_content == previous_reply:
                # 内容未变，增加稳定计数
                # self.stability_counter[view_idx] += 1
                self.stability_counter[ai_key] += 1
                # print(f"  视图 {ai_key} 内容未变，稳定计数: {self.stability_counter[ai_key]}")
                
                # 检查是否达到稳定阈值
                # if self.stability_counter[view_idx] >= self.STABILITY_THRESHOLD:
                if self.stability_counter[ai_key] >= self.STABILITY_THRESHOLD:
                    # 回复已稳定，从待处理列表中移除
                    # if view_idx in self.pending_views:
                    #     self.pending_views.remove(view_idx)
                    if ai_key in self.pending_views:
                        self.pending_views.remove(ai_key)
                    
                    # 添加到已收集的响应中
                    self.collected_responses.append(result)
                    print(f"视图 {ai_key} ({web_view.ai_name}) 的回复已稳定，URL: {result.get('url', '')}")
            else:
                # 内容变化，重置稳定计数
                # self.stability_counter[view_idx] = 0
                self.stability_counter[ai_key] = 0
                # 更新上一次的响应内容
                # self.previous_responses[view_idx] = reply_content
                self.previous_responses[ai_key] = reply_content
                # print(f"  视图 {ai_key} 内容变化，重置稳定计数。")
        
        # 获取视图的响应
        # ai_view.get_prompt_response(response_callback) # Error was here
        web_view.get_prompt_response(response_callback) # Call on the AIWebView instance
    
    def _finalize_collection(self):
        """完成收集并保存结果"""
        # 停止轮询
        self._stop_polling()
        
        # 如果还有未完成的视图（因超时或错误导致未稳定），收集它们当前的状态
        if self.pending_views:
            print(f"有 {len(self.pending_views)} 个视图的回复未稳定或获取失败，使用当前状态或记录失败")
            
            if not self.ai_view_container:
                print("无法收集最终状态，AI视图容器丢失。")
                self._save_responses() # 尝试保存已有的
                return

            active_views = self.ai_view_container.ai_web_views
            pending_keys_list = list(self.pending_views) # 复制一份keys用于迭代
            collected_count = 0
            total_pending = len(pending_keys_list)

            # 定义最终回调
            def final_callback(key, result):
                nonlocal collected_count
                if result:
                    self.collected_responses.append(result)
                    print(f"  最终收集: 视图 {key} 成功, URL: {result.get('url', '')}")
                else:
                     # 记录失败状态
                     url = f"view_{key}_timeout_or_error"
                     if key in active_views:
                         url = active_views[key].url().toString() # 尝试获取最后URL
                     self.collected_responses.append({"url": url, "reply": "回复未在规定时间内稳定或获取失败"})
                     print(f"  最终收集: 视图 {key} 失败或超时")
                
                # 从待处理列表中移除 (理论上在调用此回调前已移除，但再次确保)
                if key in self.pending_views:
                    self.pending_views.remove(key)
                
                collected_count += 1
                # 如果所有最终视图都已处理，保存结果
                if collected_count == total_pending:
                    self._save_responses()
            
            print(f"开始收集 {total_pending} 个未稳定视图的最终状态...")
            for key in pending_keys_list:
                if key in active_views:
                    web_view = active_views[key]
                    print(f"  -> 请求 {key} ({web_view.ai_name}) 的最终状态...")
                    web_view.get_prompt_response(lambda res, k=key: final_callback(k, res))
                else:
                    # 如果视图在此期间消失了
                    print(f"  -> 视图 {key} 在最终收集中已不存在。")
                    final_callback(key, None) # 记录为失败

            # 添加一个短超时以防万一JS调用不返回
            QTimer.singleShot(5000, lambda: self._ensure_final_save(total_pending, collected_count))

        else:
            # 所有视图都已稳定，直接保存结果
            self._save_responses()

    def _ensure_final_save(self, total_pending, collected_count):
        """确保在最终收集中所有回调都已执行或超时后保存"""
        if collected_count < total_pending:
             print(f"警告：最终收集超时，仍有 {total_pending - collected_count} 个视图未响应最终回调。强制保存。")
             # 将仍在 pending_views 中的视为失败
             remaining_keys = list(self.pending_views)
             for key in remaining_keys:
                 url = f"view_{key}_final_callback_timeout"
                 if self.ai_view_container and key in self.ai_view_container.ai_web_views:
                      url = self.ai_view_container.ai_web_views[key].url().toString()
                 self.collected_responses.append({"url": url, "reply": "最终回调超时"})
                 if key in self.pending_views:
                      self.pending_views.remove(key) # 清理
             
             self._save_responses()
        # else: # 如果已经保存过了，则不做任何事
        #     print("最终收集已完成并保存。")


    def _save_responses(self):
        """保存收集到的响应"""
        # 检查是否仍在处理同一个 prompt_id，防止旧的回调触发保存
        if not self.current_prompt_id:
            print("没有当前提示ID，跳过保存响应。")
            return
            
        print(f"准备保存 Prompt ID {self.current_prompt_id} 的响应，共 {len(self.collected_responses)} 个")
            
        # 保存到数据库
        if self.db_manager:
            timestamp = int(time.time()) # 使用当前时间戳
            # timestamp = int(self.current_prompt_id)  # 使用ID作为时间戳 (如果ID保证是时间戳)
            try:
                self.db_manager.add_prompt_details(
                    self.current_prompt_id, 
                    self.current_prompt_text,
                    timestamp,
                    self.collected_responses
                )
                print(f"Prompt ID {self.current_prompt_id} 的响应已保存到数据库。")
            except Exception as e:
                print(f"保存 Prompt ID {self.current_prompt_id} 到数据库时出错: {e}")
        else:
             print("数据库管理器未设置，无法保存响应。")
            
        # 发射信号通知响应已收集
        self.response_collected.emit(self.current_prompt_id, self.collected_responses)
        
        # 清除当前提示词的引用，标记处理完成
        print(f"完成 Prompt ID {self.current_prompt_id} 的处理。")
        self.current_prompt_id = None
        self.current_prompt_text = None
        self.collected_responses = []
        self.pending_views.clear()
        self.previous_responses.clear()
        self.stability_counter.clear()
    
    # def collect_responses(self): # 这个方法似乎是旧的或冗余的，先注释掉
    #     """收集所有AI视图的响应（兼容旧版本方法）"""
    #     if not self.ai_views or not self.current_prompt_id:
    #         return
            
    #     for ai_view in self.ai_views:
    #         ai_view.collect_all_responses(self.handle_responses) # AIView 没有 collect_all_responses
    
    # def handle_responses(self, responses): # 这个方法似乎是旧的或冗余的，先注释掉
    #     """处理收集到的响应（兼容旧版本方法）
        
    #     Args:
    #         responses (list): 响应信息列表，每项包含url和reply
    #     """
    #     if not self.db_manager or not self.current_prompt_id:
    #         return
            
    #     # 保存到数据库
    #     timestamp = int(self.current_prompt_id)  # 使用ID作为时间戳
    #     self.db_manager.add_prompt_details(
    #         self.current_prompt_id, 
    #         self.current_prompt_text,
    #         timestamp,
    #         responses
    #     )
        
    #     # 发射信号通知响应已收集
    #     self.response_collected.emit(self.current_prompt_id, responses)
        
    #     # 清除当前提示词的引用
    #     self.current_prompt_id = None
    #     self.current_prompt_text = None 