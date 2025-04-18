#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提示词同步控制器 (PromptSync Controller)

负责将提示词从辅助窗口同步到主窗口的AI视图，并收集多平台AI回复。

主要功能:
1. 提示词同步管理 - 将用户输入的提示词同步发送到多个AI平台
2. 响应智能收集 - 监控并收集各AI平台的回复内容
3. 内容稳定性检测 - 基于内容变化检测AI回复是否已完成
4. 数据库存储 - 将提示词和所有平台回复持久化保存
5. 超时处理 - 自动处理长时间未响应的平台

技术实现:
- 使用定时轮询检测AI平台回复状态，避免阻塞主UI线程
- 采用稳定性计数器判断AI回复是否完成（连续多次内容不变视为稳定）
- 实现最大等待时间限制，防止无限等待
- 统一管理多平台回复收集过程，并在完成后发出信号通知

通信方式:
- 使用PyQt信号-槽机制实现组件间通信
- 通过prompt_synced和response_collected信号通知上层应用

作者: Tengle
日期: 2024-04-18
"""

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import time
import json
import traceback

class PromptSync(QObject):
    """提示词同步管理器，负责将提示词从输入区同步到AI视图并收集回复"""
    
    # 信号定义
    prompt_synced = pyqtSignal(str)  # 提示词同步成功信号
    response_collected = pyqtSignal(str, list)  # 回复收集完成信号，参数: prompt_id, responses
    
    # 轮询参数
    INITIAL_WAIT_TIME = 5000  # 初始等待时间（毫秒）
    POLLING_INTERVAL = 2000   # 轮询间隔时间（毫秒）
    STABILITY_THRESHOLD = 3   # 内容稳定阈值（连续几次内容相同视为稳定）
    MAX_WAIT_TIME = 90000     # 最大等待时间（毫秒）- 增加到90秒
    SAFETY_BUFFER = 10000     # 安全缓冲时间（毫秒）- 相比最大等待增加10秒
    
    def __init__(self):
        super().__init__()
        self.db_manager = None
        # self.ai_views = [] # 不再使用列表存储多个AIView
        self.ai_view_container = None # 存储单个AIView容器实例
        
        self.current_prompt_id = None
        self.current_prompt_text = None
        self.collected_responses = []
        self.response_map = {}  # 新增: 存储ai_key到响应的映射 {ai_key: response}
        self.original_view_order = []  # 新增: 记录WebView的原始顺序
        
        # 轮询相关状态 - 使用 AI key 作为字典键
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_responses)
        self.poll_start_time = None
        self.pending_views = set() # 存储待处理的 AI key
        self.previous_responses = {} # 存储上一次响应 {ai_key: response_text}
        self.stability_counter = {} # 存储稳定计数 {ai_key: count}
        
        # 安全计时器追踪
        self.safety_timer = None  # 追踪安全超时计时器
        self.safety_timer_prompt_id = None  # 存储安全计时器关联的prompt_id
    
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
            self.response_map = {}
            self.original_view_order = []
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
            
            # 记录原始WebView顺序（在遍历前记录顺序）
            self.original_view_order = list(dict.fromkeys(active_views.keys()))  # 使用dict.fromkeys确保不重复
            print(f"记录WebView原始顺序: {self.original_view_order}")
            
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
                        self.response_map[ai_key] = None
                        self.original_view_order.append(ai_key)
                        
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
        
        # 取消可能存在的旧安全计时器
        self._cancel_safety_timer()
        
        # 添加一个超时安全定时器，确保无论如何都会在最大等待时间后保存数据
        safety_timeout = self.MAX_WAIT_TIME + self.SAFETY_BUFFER  # 使用配置的安全缓冲时间
        print(f"设置安全超时计时器: {safety_timeout}ms (提示词ID: {self.current_prompt_id})")
        
        # 创建并存储安全计时器，关联当前的prompt_id
        self.safety_timer = QTimer(self)
        self.safety_timer.setSingleShot(True)
        self.safety_timer.timeout.connect(self._safety_timeout_handler)
        self.safety_timer_prompt_id = self.current_prompt_id
        self.safety_timer.start(safety_timeout)
        
    def _stop_polling(self):
        """停止轮询"""
        if self.poll_timer.isActive():
            print("停止响应轮询。")
            self.poll_timer.stop()
            self.poll_start_time = None
            
            # 同时取消安全计时器
            self._cancel_safety_timer()
    
    def _poll_responses(self):
        """轮询所有AI视图的响应"""
        # 检查是否超时
        elapsed_time = (time.time() - self.poll_start_time) * 1000
        
        # 计算轮询进度
        progress_percent = min(100, int(elapsed_time / self.MAX_WAIT_TIME * 100))
        
        # 每10%或每15秒显示一次进度信息
        if progress_percent % 10 == 0 or int(elapsed_time / 15000) != int((elapsed_time - self.POLLING_INTERVAL) / 15000):
            print(f"轮询进度: {progress_percent}%, 已用时间: {int(elapsed_time)}ms, 最大等待: {self.MAX_WAIT_TIME}ms")
            print(f"待处理视图数: {len(self.pending_views)}, 已收集响应: {len(self.collected_responses)}")
            
        if elapsed_time > self.MAX_WAIT_TIME:
            print(f"轮询超时（超过 {self.MAX_WAIT_TIME}ms），强制结束收集。")
            # 直接调用保存方法而不是_finalize_collection
            print("由于超时，强制保存当前已收集的响应...")
            self._save_responses()
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
             # 尝试保存已收集的数据
             if self.collected_responses:
                 print("AI视图容器丢失，但尝试保存已收集的响应...")
                 self._save_responses()
             return

        print(f"轮询检查响应，剩余待处理视图: {len(self.pending_views)}")
        # 遍历所有注册的视图
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
                self.response_map[ai_key] = {"url": f"view_{ai_key}_removed", "reply": "视图已移除"}

        # 如果检查后所有视图都完成，则结束
        if not self.pending_views:
            self._finalize_collection()

    def _check_view_response(self, ai_key, web_view):
        """检查单个AI视图的响应并处理稳定性"""
        
        # 定义响应回调
        def response_callback(result):
            if not result:
                print(f"视图 {ai_key} ({web_view.ai_name}) 获取响应失败。")
                # 考虑是否需要重试或标记为失败
                return

            # 提取回复内容，如果 result 或 reply 不存在则为空字符串
            reply_content = result.get('reply', '') if result else ''
            
            # 如果回复内容为空，可能还在加载中，不做任何操作
            if not reply_content:
                print(f"视图 {ai_key} ({web_view.ai_name}) 返回空内容，可能仍在加载中")
                return
            
            # 检查内容是否稳定
            previous_reply = self.previous_responses.get(ai_key)
            
            # 调试信息
            reply_preview = reply_content[:50] + "..." if len(reply_content) > 50 else reply_content
            prev_preview = previous_reply[:50] + "..." if previous_reply and len(previous_reply) > 50 else previous_reply
            stability = self.stability_counter.get(ai_key, 0)
            
            # 只在内容变化或即将稳定时输出日志，减少输出量
            if previous_reply != reply_content or stability >= self.STABILITY_THRESHOLD - 1:
                print(f"视图 {ai_key} 内容对比: 长度={len(reply_content)}字符, 预览='{reply_preview}'")
                print(f"稳定状态: {stability}/{self.STABILITY_THRESHOLD}")

            if reply_content and reply_content == previous_reply:
                # 内容未变，增加稳定计数
                self.stability_counter[ai_key] += 1
                
                # 检查是否达到稳定阈值
                if self.stability_counter[ai_key] >= self.STABILITY_THRESHOLD:
                    # 检查内容是否看起来完整
                    is_likely_complete = True
                    
                    # 回复已稳定，从待处理列表中移除
                    if ai_key in self.pending_views:
                        self.pending_views.remove(ai_key)
                    
                    # 添加到已收集的响应中并更新映射
                    self.collected_responses.append(result)
                    self.response_map[ai_key] = result
                    print(f"✓ 视图 {ai_key} ({web_view.ai_name}) 的回复已稳定 ({len(reply_content)}字符)")
            else:
                # 内容变化，重置稳定计数
                self.stability_counter[ai_key] = 0
                # 更新上一次的响应内容
                self.previous_responses[ai_key] = reply_content
        
        # 获取视图的响应
        web_view.get_prompt_response(response_callback)
    
    def _finalize_collection(self):
        """
        完成AI平台响应收集，并按照视觉布局顺序整理响应
        """
        print("完成AI平台响应收集")
        
        # 停止轮询计时器
        self._stop_polling()
        
        # 整理收集到的响应并保存
        print(f"已收集 {len(self.collected_responses)} 个响应，准备保存")
        
        # 直接调用保存方法
        self._save_responses()
        
        print("响应收集和保存流程完成")
    
    def _ensure_final_save_by_order(self, total_views, collected_count):
        """确保在最终收集中所有回调都已执行或超时后按顺序保存"""
        print(f"确保最终保存，总视图数: {total_views}，已收集: {collected_count}")
        
        # 检查是否所有视图都已响应
        if collected_count < total_views:
            print(f"警告：最终收集超时，仍有 {total_views - collected_count} 个视图未响应最终回调。使用已收集数据保存。")
            # 对于未响应的，使用空回复
            for key in self.original_view_order:
                if key not in self.response_map:
                    url = f"view_{key}_timeout"
                    if self.ai_view_container and key in self.ai_view_container.ai_web_views:
                        url = self.ai_view_container.ai_web_views[key].url().toString()
                    self.response_map[key] = {"url": url, "reply": "最终收集超时"}
                    print(f"为未响应的视图 {key} 添加超时占位回复")
        
        # 不管是否有未响应的视图，都进行保存
        print("执行有序保存...")
        self._save_responses_by_order()
        print("最终保存完成")
    
    def _save_responses_with_current_data(self):
        """使用当前已收集的数据保存（兼容旧逻辑）"""
        # 检查是否仍在处理同一个 prompt_id
        if not self.current_prompt_id:
            print("没有当前提示ID，跳过保存响应。")
            return
            
        print(f"使用当前已收集数据保存 Prompt ID {self.current_prompt_id} 的响应，共 {len(self.collected_responses)} 个")
            
        # 保存到数据库
        if self.db_manager:
            timestamp = int(time.time()) # 使用当前时间戳
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
        
        # 清除状态
        self._clear_state()
    
    def _save_responses_by_order(self):
        """按视觉布局顺序（从左到右）保存响应"""
        # 检查是否仍在处理同一个 prompt_id
        if not self.current_prompt_id:
            print("没有当前提示ID，跳过保存响应。")
            return
        
        # 获取视图的视觉顺序
        visual_order = []
        if self.ai_view_container:
            try:
                visual_order = self.ai_view_container.get_visual_order_of_views()
                print(f"使用视觉顺序保存响应: {visual_order}")
            except Exception as e:
                print(f"获取视觉顺序时出错: {str(e)}")
        
        # 如果无法获取视觉顺序，回退到原始记录顺序
        if not visual_order and self.original_view_order:
            visual_order = self.original_view_order
            print(f"无法获取视觉顺序，回退到原始记录顺序: {visual_order}")
        elif not visual_order:
            print("无法获取视觉顺序，也没有原始顺序记录，使用响应映射中的所有键")
            visual_order = list(self.response_map.keys())
            
        # 构建按顺序排列的响应列表 - 确保不重复处理
        ordered_responses = []
        processed_keys = set()  # 用于跟踪已处理的key
        
        for ai_key in visual_order:
            # 跳过已处理的key
            if ai_key in processed_keys:
                print(f"跳过重复的key: {ai_key}")
                continue
                
            response = self.response_map.get(ai_key)
            if response:
                ordered_responses.append(response)
                processed_keys.add(ai_key)  # 标记为已处理
                print(f"添加 {ai_key} 的响应到有序列表，URL: {response.get('url', 'N/A')}")
        
        # 添加任何不在视觉顺序中但在响应映射中的项（以防万一）
        for ai_key, response in self.response_map.items():
            if ai_key not in processed_keys:
                ordered_responses.append(response)
                processed_keys.add(ai_key)
                print(f"添加额外的来自 {ai_key} 的响应（不在视觉顺序中）")
        
        print(f"按视觉顺序保存 Prompt ID {self.current_prompt_id} 的响应，共 {len(ordered_responses)} 个")
        
        # 保存到数据库
        if self.db_manager:
            timestamp = int(time.time()) # 使用当前时间戳
            try:
                self.db_manager.add_prompt_details(
                    self.current_prompt_id, 
                    self.current_prompt_text,
                    timestamp,
                    ordered_responses  # 使用有序列表
                )
                print(f"Prompt ID {self.current_prompt_id} 的有序响应已保存到数据库。")
            except Exception as e:
                print(f"保存 Prompt ID {self.current_prompt_id} 的有序响应到数据库时出错: {str(e)}")
        else:
            print("数据库管理器未设置，无法保存响应。")
            
        # 发射信号通知响应已收集
        self.response_collected.emit(self.current_prompt_id, ordered_responses)
        
        # 清除状态
        self._clear_state()
    
    def _clear_state(self):
        """清除当前状态"""
        print(f"完成 Prompt ID {self.current_prompt_id} 的处理。")
        self.current_prompt_id = None
        self.current_prompt_text = None
        self.collected_responses = []
        self.pending_views.clear()
        self.previous_responses.clear()
        self.stability_counter.clear()
        self.response_map.clear()
        self.original_view_order = []  # 使用[]代替clear()以便更明确
    
    def _save_responses(self):
        """保存收集到的响应（兼容旧方法，调用新方法）"""
        # 如果有原始顺序数据，使用有序保存，否则使用传统方式
        if self.original_view_order:
            self._save_responses_by_order()
        else:
            self._save_responses_with_current_data()

    def _safety_timeout_handler(self):
        """安全超时处理，确保在任何情况下数据都会被保存"""
        # 检查是否仍在进行轮询
        if not self.poll_timer.isActive():
            print("安全计时器触发，但轮询已结束，忽略处理")
            return
            
        # 检查当前prompt_id与计时器关联的prompt_id是否一致
        if self.safety_timer_prompt_id != self.current_prompt_id:
            print(f"安全计时器触发，但关联的提示ID不匹配 (计时器ID: {self.safety_timer_prompt_id}, 当前ID: {self.current_prompt_id})，忽略处理")
            return
            
        # 计算实际经过的时间
        elapsed_ms = 0
        if self.poll_start_time:
            elapsed_ms = int((time.time() - self.poll_start_time) * 1000)
            
        print("="*50)
        print(f"安全超时触发！轮询未在预期时间内正常结束，已经过时间: {elapsed_ms}ms")
        
        # 立即停止轮询
        self._stop_polling()
        
        # 检查是否有未处理完的视图
        if self.pending_views:
            print(f"仍有 {len(self.pending_views)} 个未处理完的视图")
            # 为未完成的视图填充超时响应
            for key in self.pending_views:
                if key not in self.response_map or not self.response_map[key]:
                    url = f"view_{key}_safety_timeout"
                    if self.ai_view_container and key in self.ai_view_container.ai_web_views:
                        url = self.ai_view_container.ai_web_views[key].url().toString()
                    self.response_map[key] = {"url": url, "reply": "安全超时机制触发"}
                    print(f"为视图 {key} 添加安全超时响应")
        
        # 强制保存已收集的数据
        print("强制保存当前收集的响应...")
        total_views = len(self.original_view_order)
        collected_count = len(self.response_map)
        self._ensure_final_save_by_order(total_views, collected_count)
        print("安全超时保存完成")
        print("="*50)

    def _cancel_safety_timer(self):
        """取消可能存在的旧安全计时器"""
        if self.safety_timer and self.safety_timer.isActive():
            print(f"取消旧安全超时计时器: {self.safety_timer_prompt_id}")
            self.safety_timer.stop()
            self.safety_timer = None
            self.safety_timer_prompt_id = None