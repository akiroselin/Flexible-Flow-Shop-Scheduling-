"""
数据预处理模块
功能: 加载CSV数据并构建GA仿真器所需的数据结构
严格遵循Agent 1的数学元素提取报告
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class DataPreprocessor:
    """FFS调度数据预处理器"""
    
    def __init__(self, orders_file: str, process_times_file: str, machines_file: str):
        """
        初始化数据预处理器
        
        参数:
            orders_file: 订单数据CSV路径
            process_times_file: 工序加工时间CSV路径
            machines_file: 设备可用时间CSV路径
        """
        self.orders_file = orders_file
        self.process_times_file = process_times_file
        self.machines_file = machines_file
        
        # 数据容器
        self.orders_df = None
        self.process_times_df = None
        self.machines_df = None
        
        # 核心数据结构
        self.order_list = []  # 订单ID列表
        self.quantities = {}  # {order_id: quantity}
        self.due_dates = {}  # {order_id: due_date_in_days}
        self.weights = {}  # {order_id: priority_weight}
        
        self.stage_names = []  # 工序名称列表
        self.machine_list = []  # 设备ID列表
        self.machine_capacity = {}  # {machine_id: available_time_in_seconds}
        
        self.p_matrix = None  # 3D numpy数组: [order_idx, stage_idx, machine_idx]
        self.stage_to_machines = {}  # {stage_idx: [machine_ids]}
        self.op_map_inv = {}  # {(order_idx, stage_idx): global_op_idx}
        self.op_k_map = {}  # {global_op_idx: [available_machine_ids]}
        
    def load_data(self):
        """加载所有CSV文件"""
        # 加载订单数据
        self.orders_df = pd.read_csv(self.orders_file, encoding='utf-8-sig')
        # 列名别名处理(鲁棒性)
        col_aliases = {
            '订单ID': 'order_id',
            'OrderID': 'order_id',
            '产品类型': 'product_type',
            'ProductType': 'product_type',
            '数量': 'quantity',
            'Quantity': 'quantity',
            '交货日期': 'due_date',
            'DueDate': 'due_date',
            '订单优先级': 'priority',
            'Priority': 'priority'
        }
        self.orders_df.rename(columns=col_aliases, inplace=True)
        
        # 加载工序加工时间数据
        self.process_times_df = pd.read_csv(self.process_times_file, encoding='utf-8-sig')
        col_aliases_pt = {
            '流水线': 'line',
            'Line': 'line',
            '工序': 'stage',
            'Stage': 'stage',
            '标准加工时间(秒/片)': 'time',
            'ProcessTime': 'time',
            '工序良率(%)': 'yield_rate'
        }
        self.process_times_df.rename(columns=col_aliases_pt, inplace=True)
        
        # 加载设备可用时间数据
        self.machines_df = pd.read_csv(self.machines_file, encoding='utf-8-sig')
        col_aliases_m = {
            '设备ID': 'machine_id',
            'MachineID': 'machine_id',
            '设备类型': 'machine_type',
            'MachineType': 'machine_type',
            '可用时间(分钟)': 'available_time',
            'AvailableTime': 'available_time'
        }
        self.machines_df.rename(columns=col_aliases_m, inplace=True)
        
        print("✅ 数据加载完成")
        print(f"  - 订单数: {len(self.orders_df)}")
        print(f"  - 设备数: {len(self.machines_df)}")
        print(f"  - 工序数据行: {len(self.process_times_df)}")
        
    def parse_priority_weight(self, priority_str: str) -> float:
        """解析优先级字符串为权重系数"""
        if pd.isna(priority_str):
            return 1.0
        priority_str = str(priority_str).upper()
        if 'P1' in priority_str or '紧急' in priority_str:
            return 1.2
        elif 'P4' in priority_str or '低' in priority_str:
            return 0.8
        else:
            return 1.0
    
    def parse_due_date(self, date_str: str) -> float:
        """解析交货日期,返回相对于2025-10-26的天数"""
        from datetime import datetime
        base_date = datetime(2025, 10, 26)
        due_date = pd.to_datetime(date_str)
        delta_days = (due_date - base_date).days
        return float(delta_days)
    
    def build_data_structures(self):
        """构建GA仿真器所需的核心数据结构"""
        # 1. 订单参数
        self.order_list = self.orders_df['order_id'].tolist()
        for _, row in self.orders_df.iterrows():
            order_id = row['order_id']
            self.quantities[order_id] = int(row['quantity'])
            self.due_dates[order_id] = self.parse_due_date(row['due_date'])
            self.weights[order_id] = self.parse_priority_weight(row['priority'])
        
        # 2. 工序和设备信息
        self.stage_names = self.process_times_df['stage'].unique().tolist()
        num_stages = len(self.stage_names)
        
        self.machine_list = self.machines_df['machine_id'].tolist()
        for _, row in self.machines_df.iterrows():
            machine_id = row['machine_id']
            # 转换分钟为秒
            self.machine_capacity[machine_id] = row['available_time'] * 60.0
        
        # 3. 构建设备类型到工序的映射
        machine_type_map = {}
        for _, row in self.machines_df.iterrows():
            mtype = row['machine_type']
            mid = row['machine_id']
            if mtype not in machine_type_map:
                machine_type_map[mtype] = []
            machine_type_map[mtype].append(mid)
        
        # 根据工序名称映射设备
        stage_type_mapping = {
            'COG/FOG绑定': 'COG/FOG绑定设备',
            '点胶': '点胶设备',
            'BLU组装': 'BLU组装设备',
            'Inspection': 'BLU组装设备',  # 假设使用BLU设备
            'Final Inspection': 'BLU组装设备'
        }
        
        self.stage_to_machines = {}
        for stage_idx, stage_name in enumerate(self.stage_names):
            machine_type = stage_type_mapping.get(stage_name, 'BLU组装设备')
            machines_list = machine_type_map.get(machine_type, [])
            if not machines_list:
                # 容错:如果该类型没有设备,使用所有设备
                print(f"⚠️ 警告: 工序 '{stage_name}' 没有找到类型为 '{machine_type}' 的设备,使用所有设备")
                machines_list = self.machine_list
            self.stage_to_machines[stage_idx] = machines_list
        
        # 4. 构建p_matrix [order_idx, stage_idx, machine_idx]
        num_orders = len(self.order_list)
        num_machines = len(self.machine_list)
        self.p_matrix = np.full((num_orders, num_stages, num_machines), np.inf)
        
        # 创建line到machine的映射(需要更精确的逻辑)
        line_to_stage_to_machine = {}
        
        for _, row in self.process_times_df.iterrows():
            line = row['line']
            stage = row['stage']
            time = row['time']
            
            # 找到对应的stage_idx
            if stage not in self.stage_names:
                continue
            stage_idx = self.stage_names.index(stage)
            
            # 确定这个line-stage组合对应的设备
            machine_type = stage_type_mapping.get(stage, 'BLU组装设备')
            machines_of_type = machine_type_map.get(machine_type, [])
            
            if len(machines_of_type) == 0:
                print(f"⚠️ 警告: 工序 '{stage}' 没有可用设备,跳过")
                continue
            
            # 映射逻辑:Line_1 -> 第1台设备, Line_2 -> 第2台设备
            machine_id = None
            if 'Line_1' in line or 'line_1' in line.lower():
                machine_id = machines_of_type[0]
            elif 'Line_2' in line or 'line_2' in line.lower():
                machine_id = machines_of_type[1] if len(machines_of_type) > 1 else machines_of_type[0]
            
            if machine_id and machine_id in self.machine_list:
                machine_idx = self.machine_list.index(machine_id)
                # 对所有订单设置相同的加工时间
                for order_idx in range(num_orders):
                    self.p_matrix[order_idx, stage_idx, machine_idx] = time
                
                # 记录映射关系
                if line not in line_to_stage_to_machine:
                    line_to_stage_to_machine[line] = {}
                line_to_stage_to_machine[line][stage_idx] = machine_id
        
        # 关键修复:检查并填充缺失的p_matrix值
        print("\n🔍 检查p_matrix完整性...")
        for stage_idx in range(num_stages):
            stage_name = self.stage_names[stage_idx]
            available_machines = self.stage_to_machines[stage_idx]
            
            for machine_id in available_machines:
                machine_idx = self.machine_list.index(machine_id)
                
                # 检查是否有订单-工序-设备的时间是inf
                has_inf = False
                for order_idx in range(num_orders):
                    if self.p_matrix[order_idx, stage_idx, machine_idx] == np.inf:
                        has_inf = True
                        break
                
                if has_inf:
                    # 尝试从其他设备复制时间(作为备用)
                    for other_machine_id in available_machines:
                        other_machine_idx = self.machine_list.index(other_machine_id)
                        if self.p_matrix[0, stage_idx, other_machine_idx] < np.inf:
                            # 找到了有效值,复制给当前设备
                            for order_idx in range(num_orders):
                                if self.p_matrix[order_idx, stage_idx, machine_idx] == np.inf:
                                    self.p_matrix[order_idx, stage_idx, machine_idx] = \
                                        self.p_matrix[order_idx, stage_idx, other_machine_idx]
                            print(f"  ✓ 修复: 工序 '{stage_name}' 设备 '{machine_id}' 使用了设备 '{other_machine_id}' 的时间")
                            break
        
        # 最终检查:如果某个工序的所有可用设备都是inf,使用默认值
        for stage_idx in range(num_stages):
            stage_name = self.stage_names[stage_idx]
            available_machines = self.stage_to_machines[stage_idx]
            
            all_inf = True
            for machine_id in available_machines:
                machine_idx = self.machine_list.index(machine_id)
                if self.p_matrix[0, stage_idx, machine_idx] < np.inf:
                    all_inf = False
                    break
            
            if all_inf:
                print(f"  ⚠️ 警告: 工序 '{stage_name}' 所有设备的时间都是inf,使用默认值20秒/片")
                for machine_id in available_machines:
                    machine_idx = self.machine_list.index(machine_id)
                    for order_idx in range(num_orders):
                        self.p_matrix[order_idx, stage_idx, machine_idx] = 20.0  # 默认值
        
        # 5. 构建工序映射
        global_op_idx = 0
        for order_idx in range(num_orders):
            for stage_idx in range(num_stages):
                self.op_map_inv[(order_idx, stage_idx)] = global_op_idx
                self.op_k_map[global_op_idx] = self.stage_to_machines[stage_idx]
                global_op_idx += 1
        
        print("✅ 数据结构构建完成")
        print(f"  - p_matrix shape: {self.p_matrix.shape}")
        print(f"  - 总工序数: {len(self.op_map_inv)}")
        print(f"  - 工序-设备映射: {self.stage_to_machines}")
        
        # 详细检查p_matrix
        print("\n🔍 p_matrix完整性检查:")
        for stage_idx in range(num_stages):
            stage_name = self.stage_names[stage_idx]
            available_machines = self.stage_to_machines[stage_idx]
            print(f"  工序{stage_idx} ({stage_name}):")
            for machine_id in available_machines:
                machine_idx = self.machine_list.index(machine_id)
                sample_time = self.p_matrix[0, stage_idx, machine_idx]
                if sample_time < np.inf:
                    print(f"    ✓ {machine_id}: {sample_time:.2f} 秒/片")
                else:
                    print(f"    ✗ {machine_id}: inf (数据缺失!)")
        
        # 检查是否有工序完全没有可用设备
        for stage_idx in range(num_stages):
            if len(self.stage_to_machines[stage_idx]) == 0:
                raise ValueError(f"❌ 错误: 工序{stage_idx}没有任何可用设备!")
    
    def get_preprocessed_data(self) -> Dict:
        """返回所有预处理数据的字典"""
        return {
            'order_list': self.order_list,
            'quantities': self.quantities,
            'due_dates': self.due_dates,
            'weights': self.weights,
            'stage_names': self.stage_names,
            'machine_list': self.machine_list,
            'machine_capacity': self.machine_capacity,
            'p_matrix': self.p_matrix,
            'stage_to_machines': self.stage_to_machines,
            'op_map_inv': self.op_map_inv,
            'op_k_map': self.op_k_map,
            'num_orders': len(self.order_list),
            'num_stages': len(self.stage_names),
            'num_machines': len(self.machine_list)
        }
    
    def process(self) -> Dict:
        """执行完整的数据预处理流程"""
        self.load_data()
        self.build_data_structures()
        return self.get_preprocessed_data()


if __name__ == "__main__":
    # 测试代码
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    data = preprocessor.process()
    
    print("\n📊 预处理数据摘要:")
    print(f"订单: {data['order_list']}")
    print(f"数量: {data['quantities']}")
    print(f"交货期(天): {data['due_dates']}")
    print(f"权重: {data['weights']}")
    print(f"设备: {data['machine_list']}")
    print(f"设备容量(秒): {data['machine_capacity']}")