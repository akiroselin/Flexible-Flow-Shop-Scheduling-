"""
可视化模块
功能: 生成交互式甘特图(HTML)和结果导出(CSV)
严格遵循Agent 2蓝图第10节的输出格式要求
"""

import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List


class ScheduleVisualizer:
    """调度方案可视化工具"""
    
    def __init__(self, data: Dict):
        """
        初始化可视化工具
        
        参数:
            data: 预处理数据字典
        """
        self.data = data
        self.order_list = data['order_list']
        self.machine_list = data['machine_list']
        self.stage_names = data['stage_names']
        self.due_dates = data['due_dates']
        
        # 颜色映射
        self.order_colors = {
            order_id: self._get_color(idx) 
            for idx, order_id in enumerate(self.order_list)
        }
    
    def _get_color(self, idx: int) -> str:
        """获取订单颜色"""
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        return colors[idx % len(colors)]
    
    def export_schedule_csv(self, schedule: List[Dict], output_file: str):
        """
        导出调度结果为CSV
        严格遵循Agent 2蓝图第10.1节格式
        
        参数:
            schedule: 调度方案列表
            output_file: 输出文件路径
        """
        records = []
        for task in schedule:
            records.append({
                '订单ID': task['order_id'],
                '工序阶段': self.stage_names[task['stage_idx']],
                '设备ID': task['machine_id'],
                '开始时间(秒)': f"{task['start_time']:.2f}",
                '完成时间(秒)': f"{task['finish_time']:.2f}",
                '加工时长(秒)': f"{task['processing_time']:.2f}",
                '开始时间(小时)': f"{task['start_time']/3600:.2f}",
                '完成时间(小时)': f"{task['finish_time']/3600:.2f}",
                '加工时长(小时)': f"{task['processing_time']/3600:.2f}"
            })
        
        df = pd.DataFrame(records)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 调度结果已导出: {output_file}")
        print(f"  - 总记录数: {len(records)}")
    
    def export_kpis_csv(self, kpis: Dict, completion_times: Dict, output_file: str):
        """
        导出KPI指标为CSV
        
        参数:
            kpis: KPI字典
            completion_times: 订单完工时间字典
            output_file: 输出文件路径
        """
        # 汇总指标
        summary_records = []
        summary_records.append({'指标': '总加权拖期', '数值': f"{kpis['total_weighted_tardiness']:.2f}", '单位': '天'})
        summary_records.append({'指标': '订单准时交付率', '数值': f"{kpis['on_time_delivery_rate']:.2f}", '单位': '%'})
        summary_records.append({'指标': '平均拖期', '数值': f"{kpis['avg_tardiness']:.2f}", '单位': '天'})
        summary_records.append({'指标': 'Makespan', '数值': f"{kpis['makespan_days']:.2f}", '单位': '天'})
        summary_records.append({'指标': '设备平均利用率', '数值': f"{kpis['avg_utilization']:.2f}", '单位': '%'})
        summary_records.append({'指标': '瓶颈设备负载率', '数值': f"{kpis['bottleneck_load']:.2f}", '单位': '%'})
        summary_records.append({'指标': '负载均衡度(标准差)', '数值': f"{kpis['load_balance_std']:.2f}", '单位': '%'})
        
        df_summary = pd.DataFrame(summary_records)
        df_summary.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ KPI指标已导出: {output_file}")
    
    def export_order_summary_csv(self, completion_times: Dict, output_file: str):
        """
        导出订单完工汇总
        
        参数:
            completion_times: {order_idx: completion_time}
            output_file: 输出文件路径
        """
        records = []
        for order_idx, order_id in enumerate(self.order_list):
            completion_time_seconds = completion_times.get(order_idx, 0.0)
            completion_days = completion_time_seconds / 86400.0
            due_date = self.due_dates[order_id]
            tardiness = max(0.0, completion_days - due_date)
            is_on_time = '是' if tardiness == 0 else '否'
            
            records.append({
                '订单ID': order_id,
                '完工时间(天)': f"{completion_days:.2f}",
                '交货期(天)': f"{due_date:.2f}",
                '拖期(天)': f"{tardiness:.2f}",
                '是否准时': is_on_time
            })
        
        df = pd.DataFrame(records)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ 订单汇总已导出: {output_file}")
    
    def generate_gantt_chart(self, schedule: List[Dict], output_file: str):
        """
        生成交互式甘特图(HTML)
        严格遵循Agent 2蓝图第10.2节要求
        
        参数:
            schedule: 调度方案列表
            output_file: 输出HTML文件路径
        """
        # 准备甘特图数据
        gantt_data = []
        base_date = datetime(2025, 10, 26)  # 基准日期
        
        for task in schedule:
            # 处理可能的无穷大值
            start_time = task['start_time'] if not np.isinf(task['start_time']) else 0
            finish_time = task['finish_time'] if not np.isinf(task['finish_time']) else start_time + 3600  # 默认1小时
            
            start_datetime = base_date + timedelta(seconds=start_time)
            finish_datetime = base_date + timedelta(seconds=finish_time)
            
            gantt_data.append({
                'Task': f"{task['order_id']}-{self.stage_names[task['stage_idx']]}",
                'Start': start_datetime,
                'Finish': finish_datetime,
                'Resource': task['machine_id'],
                'Description': (
                    f"订单: {task['order_id']}<br>"
                    f"工序: {self.stage_names[task['stage_idx']]}<br>"
                    f"设备: {task['machine_id']}<br>"
                    f"开始: {task['start_time']/3600:.2f}h<br>"
                    f"结束: {task['finish_time']/3600:.2f}h<br>"
                    f"时长: {task['processing_time']/3600:.2f}h"
                )
            })
        
        # 创建甘特图
        if not gantt_data:
            print("⚠️ 警告: 调度方案为空,无法生成甘特图")
            return
        
        # 使用plotly创建甘特图
        # 创建一个简单的颜色映射，使用Resource作为索引列
        unique_resources = set(task['Resource'] for task in gantt_data)
        colors_dict = {}
        color_palette = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c', '#d35400', '#34495e']
        
        for i, resource in enumerate(unique_resources):
            colors_dict[resource] = color_palette[i % len(color_palette)]
            
        fig = ff.create_gantt(
            gantt_data,
            colors=colors_dict,
            index_col='Resource',
            show_colorbar=True,
            group_tasks=True,
            showgrid_x=True,
            showgrid_y=True,
            title='FFS调度甘特图 (Genetic Algorithm)'
        )
        
        # 添加交货期垂直线
        for order_idx, order_id in enumerate(self.order_list):
            due_date_days = self.due_dates[order_id]
            due_datetime = base_date + timedelta(days=due_date_days)
            
            fig.add_vline(
                x=due_datetime.timestamp() * 1000,
                line_dash="dash",
                line_color=self.order_colors[order_id],
                annotation_text=f"{order_id}交期",
                annotation_position="top"
            )
        
        # 更新布局
        fig.update_layout(
            xaxis_title="时间",
            yaxis_title="设备",
            height=600,
            hovermode='closest',
            font=dict(size=10)
        )
        
        # 保存HTML
        fig.write_html(output_file)
        print(f"✅ 甘特图已生成: {output_file}")
        print(f"  - 打开浏览器查看交互式图表")



def export_results(completion_times: Dict, schedule: List, kpis: Dict, data: Dict, 
                   algorithm: str = "GA"):
    """
    导出所有结果文件
    
    参数:
        completion_times: 订单完成时间字典
        schedule: 调度方案列表
        kpis: KPI指标字典
        data: 预处理数据
        algorithm: 算法名称(GA/NSGA2等)
    """
    print("\n📤 导出结果...")
    
    # 创建可视化工具
    visualizer = ScheduleVisualizer(data)
    
    # 导出CSV
    visualizer.export_schedule_csv(schedule, f"schedule_results_{algorithm}.csv")
    visualizer.export_kpis_csv(kpis, completion_times, f"schedule_kpis_{algorithm}.csv")
    visualizer.export_order_summary_csv(completion_times, f"schedule_orders_{algorithm}.csv")
    
    # 生成甘特图
    visualizer.generate_gantt_chart(schedule, f"schedule_gantt_{algorithm}.html")
    
    # 打印KPI摘要
    print("\n📊 优化结果KPI:")
    print(f"  ✓ 总加权拖期: {kpis['total_weighted_tardiness']:.2f} 天")
    print(f"  ✓ 订单准时交付率: {kpis['on_time_delivery_rate']:.2f} %")
    print(f"  ✓ 平均拖期: {kpis['avg_tardiness']:.2f} 天")
    print(f"  ✓ Makespan: {kpis['makespan_days']:.2f} 天")
    print(f"  ✓ 设备平均利用率: {kpis['avg_utilization']:.2f} %")
    print(f"  ✓ 瓶颈设备负载率: {kpis['bottleneck_load']:.2f} %")
    print(f"  ✓ 负载均衡度: {kpis['load_balance_std']:.2f} %")
    
    return {
        'completion_times': completion_times,
        'schedule': schedule,
        'kpis': kpis
    }


if __name__ == "__main__":
    # 测试代码
    from data_preprocessor import DataPreprocessor
    from ffs_simulatorv2 import FFSSimulator
    
    print("🧪 测试可视化模块...")
    
    # 加载数据
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    data = preprocessor.process()
    
    # 创建仿真器
    simulator = FFSSimulator(data)
    
    # 测试解
    test_solution = np.random.uniform(0, 0.9999, 50)
    
    # 导出结果
    export_results(simulator, test_solution, data, prefix="test_schedule")
    
    print("\n✅ 可视化模块测试完成!")