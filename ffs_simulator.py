"""
FFS调度仿真器
功能: 实现Agent 2设计的适应度函数(GA核心)
严格遵循蓝图第3.3节的状态变量逻辑和约束强制执行机制
"""

import numpy as np
from typing import Dict, List, Tuple
from mealpy import Problem
from mealpy.utils.space import FloatVar


class FFSSimulator(Problem):
    """
    FFS调度问题仿真器(mealpy Problem类)
    实现双染色体编码(OS + MS)的适应度评估
    """
    
    def obj_func(self, solution):
        """
        适应度函数(必须实现，新版mealpy API要求)
        """
        return self.fit_func(solution)
    
    def __init__(self, data: Dict, **kwargs):
        """
        初始化仿真器
        
        参数:
            data: 预处理后的数据字典(来自DataPreprocessor)
        """
        self.data = data
        
        # 提取核心数据
        self.order_list = data['order_list']
        self.quantities = data['quantities']
        self.due_dates = data['due_dates']
        self.weights = data['weights']
        self.machine_list = data['machine_list']
        self.machine_capacity = data['machine_capacity']
        self.p_matrix = data['p_matrix']
        self.stage_to_machines = data['stage_to_machines']
        self.op_k_map = data['op_k_map']
        
        self.num_orders = data['num_orders']
        self.num_stages = data['num_stages']
        self.num_machines = data['num_machines']
        self.total_ops = self.num_orders * self.num_stages
        
        # 染色体维度: OS(25) + MS(25) = 50
        # 使用FloatVar定义变量边界，适配新版mealpy API
        bounds = []
        for _ in range(self.total_ops * 2):
            bounds.append(FloatVar(lb=0.0, ub=0.9999))
        
        super().__init__(bounds=bounds, minmax="min", **kwargs)
        
        # 缓存数据
        self._total_processing_times = {}
        self._precompute_processing_times()
        
        print(f"✅ FFSSimulator初始化完成")
        print(f"  - 染色体维度: {len(bounds)}")
        print(f"  - 订单数: {self.num_orders}")
        print(f"  - 工序阶段数: {self.num_stages}")
        print(f"  - 设备数: {self.num_machines}")
        print(f"  - 总工序数: {self.total_ops}")
    
    def _precompute_processing_times(self):
        """预计算每个订单每个工序的加工时间(考虑数量)"""
        for order_idx, order_id in enumerate(self.order_list):
            qty = self.quantities[order_id]
            for stage_idx in range(self.num_stages):
                key = (order_idx, stage_idx)
                # 找到该工序可用的最小加工时间
                available_machines = self.stage_to_machines[stage_idx]
                min_time = np.inf
                for machine_id in available_machines:
                    machine_idx = self.machine_list.index(machine_id)
                    time_per_unit = self.p_matrix[order_idx, stage_idx, machine_idx]
                    if time_per_unit < np.inf:
                        min_time = min(min_time, time_per_unit)
                self._total_processing_times[key] = min_time * qty if min_time < np.inf else 0.0
    
    def _decode_chromosome(self, chromosome: np.ndarray) -> Tuple[List, Dict]:
        """
        解码染色体为工序列表和机器分配
        严格遵循Agent 2蓝图第2.2和2.3节
        
        参数:
            chromosome: 长度为50的染色体 [OS(25), MS(25)]
        
        返回:
            operations: 工序列表,每个元素为字典
            machine_assignment: {(order_idx, stage_idx): machine_id}
        """
        # 分离OS和MS染色体
        os_chromosome = chromosome[:self.total_ops]
        ms_chromosome = chromosome[self.total_ops:]
        
        # 解码MS染色体(机器分配)
        machine_assignment = {}
        for order_idx in range(self.num_orders):
            for stage_idx in range(self.num_stages):
                op_idx = order_idx * self.num_stages + stage_idx
                m_value = ms_chromosome[op_idx]
                
                # 获取可用设备
                available_machines = self.stage_to_machines[stage_idx]
                if len(available_machines) == 0:
                    raise ValueError(f"工序{stage_idx}没有可用设备!")
                
                # 区间映射选择设备
                machine_idx_in_list = int(m_value * len(available_machines))
                machine_idx_in_list = min(machine_idx_in_list, len(available_machines) - 1)
                selected_machine_id = available_machines[machine_idx_in_list]
                
                machine_assignment[(order_idx, stage_idx)] = selected_machine_id
        
        # 构建工序列表
        operations = []
        for order_idx in range(self.num_orders):
            order_id = self.order_list[order_idx]
            qty = self.quantities[order_id]
            
            for stage_idx in range(self.num_stages):
                op_idx = order_idx * self.num_stages + stage_idx
                r_value = os_chromosome[op_idx]
                
                machine_id = machine_assignment[(order_idx, stage_idx)]
                machine_idx = self.machine_list.index(machine_id)
                
                # 计算加工时间
                time_per_unit = self.p_matrix[order_idx, stage_idx, machine_idx]
                processing_time = time_per_unit * qty
                
                operations.append({
                    'order_idx': order_idx,
                    'order_id': order_id,
                    'stage_idx': stage_idx,
                    'priority': r_value,  # OS基因值作为优先级
                    'machine_id': machine_id,
                    'processing_time': processing_time
                })
        
        return operations, machine_assignment
    
    def _sort_with_precedence(self, operations: List[Dict]) -> List[Dict]:
        """
        对工序按priority排序,同时满足前驱约束
        严格遵循Agent 2蓝图第5.1节
        
        约束: 同一订单的工序j必须在j-1完成后才能排入
        """
        sorted_ops = []
        stage_counters = {order_idx: 0 for order_idx in range(self.num_orders)}
        
        # 按priority升序排序
        remaining_ops = sorted(operations, key=lambda op: op['priority'])
        
        # 迭代调度
        max_iterations = len(operations) * 2  # 防止死循环
        iteration = 0
        
        while remaining_ops and iteration < max_iterations:
            iteration += 1
            progress_made = False
            
            for op in remaining_ops[:]:  # 复制列表以便安全删除
                order_idx = op['order_idx']
                stage_idx = op['stage_idx']
                
                # 检查前驱约束
                if stage_idx == stage_counters[order_idx]:
                    sorted_ops.append(op)
                    stage_counters[order_idx] += 1
                    remaining_ops.remove(op)
                    progress_made = True
                    break  # 重新开始遍历
            
            if not progress_made:
                # 无法继续排序,强制添加剩余工序(容错机制)
                sorted_ops.extend(remaining_ops)
                break
        
        return sorted_ops
    
    def _simulate_schedule(self, sorted_operations: List[Dict]) -> Tuple[Dict, List]:
        """
        顺序调度仿真(适应度函数核心)
        严格遵循Agent 2蓝图第3.3节的状态变量逻辑
        
        返回:
            completion_times: {order_idx: completion_time_in_seconds}
            schedule: 详细调度记录列表
        """
        # ========== 步骤3: 初始化状态变量 ==========
        machine_available_time = {machine_id: 0.0 for machine_id in self.machine_list}
        job_stage_available_time = {
            order_idx: {stage_idx: 0.0 for stage_idx in range(self.num_stages)}
            for order_idx in range(self.num_orders)
        }
        
        schedule = []
        
        # ========== 步骤4: 顺序调度仿真 ==========
        for op in sorted_operations:
            order_idx = op['order_idx']
            stage_idx = op['stage_idx']
            machine_id = op['machine_id']
            processing_time = op['processing_time']
            
            # 核心约束强制执行: start_time = max(...)
            earliest_start = max(
                machine_available_time[machine_id],          # 设备可用时刻(C4)
                job_stage_available_time[order_idx][stage_idx]  # 前驱完成时刻(C2)
            )
            
            start_time = earliest_start
            finish_time = start_time + processing_time
            
            # ========== 步骤5: 更新状态 ==========
            machine_available_time[machine_id] = finish_time
            
            # 更新下一工序的可开始时刻
            if stage_idx < self.num_stages - 1:
                job_stage_available_time[order_idx][stage_idx + 1] = finish_time
            
            # 记录调度结果
            schedule.append({
                'order_idx': order_idx,
                'order_id': op['order_id'],
                'stage_idx': stage_idx,
                'machine_id': machine_id,
                'start_time': start_time,
                'finish_time': finish_time,
                'processing_time': processing_time
            })
        
        # ========== 步骤6: 计算完工时间 ==========
        completion_times = {}
        for order_idx in range(self.num_orders):
            # 订单完工时间 = 最后工序(stage_idx=4)的完成时间
            last_stage_records = [
                s for s in schedule 
                if s['order_idx'] == order_idx and s['stage_idx'] == self.num_stages - 1
            ]
            if last_stage_records:
                completion_times[order_idx] = last_stage_records[0]['finish_time']
            else:
                completion_times[order_idx] = 0.0
        
        return completion_times, schedule
    
    def _calculate_objective(self, completion_times: Dict, schedule: List) -> Tuple[float, float]:
        """
        计算目标函数和惩罚
        
        返回:
            total_tardiness: 总加权拖期
            penalty: 约束违反惩罚
        """
        # ========== 步骤6: 计算加权总拖期 ==========
        total_tardiness = 0.0
        for order_idx in range(self.num_orders):
            order_id = self.order_list[order_idx]
            C_i_seconds = completion_times.get(order_idx, 0.0)
            C_i_days = C_i_seconds / 86400.0  # 秒转天
            d_i = self.due_dates[order_id]
            w_i = self.weights[order_id]
            
            tardiness = max(0.0, C_i_days - d_i)
            total_tardiness += w_i * tardiness
        
        # ========== 步骤7: 约束违反检查 ==========
        penalty = 0.0
        lambda_penalty = 1e6  # 惩罚系数
        
        for machine_id in self.machine_list:
            # 计算设备实际工作时间
            total_workload = sum([
                s['processing_time'] for s in schedule if s['machine_id'] == machine_id
            ])
            
            # 设备容量(可用时间 + 2小时加班)
            capacity = self.machine_capacity[machine_id] + 7200.0
            
            # 违反容量约束
            if total_workload > capacity:
                violation = total_workload - capacity
                penalty += lambda_penalty * violation
        
        return total_tardiness, penalty
    
    def fit_func(self, solution: np.ndarray) -> float:
        """
        适应度函数(mealpy接口)
        
        参数:
            solution: 染色体(numpy数组,长度50)
        
        返回:
            fitness: 适应度值(越小越好)
        """
        try:
            # 步骤1: 解码染色体
            operations, machine_assignment = self._decode_chromosome(solution)
            
            # 步骤2: 工序排序(满足前驱约束)
            sorted_operations = self._sort_with_precedence(operations)
            
            # 步骤3-5: 顺序调度仿真
            completion_times, schedule = self._simulate_schedule(sorted_operations)
            
            # 步骤6-7: 计算目标函数和惩罚
            total_tardiness, penalty = self._calculate_objective(completion_times, schedule)
            
            # 步骤8: 返回适应度(负目标函数,因为mealpy最小化)
            fitness = total_tardiness + penalty
            
            return fitness
        
        except Exception as e:
            print(f"❌ 适应度评估错误: {e}")
            return 1e10  # 返回极大但有限的惩罚值
    
    def evaluate_solution(self, solution: np.ndarray) -> Dict:
        """
        详细评估解决方案(用于最终结果分析)
        
        返回:
            result: 包含适应度、调度方案、KPI等的字典
        """
        # 解码
        operations, machine_assignment = self._decode_chromosome(solution)
        sorted_operations = self._sort_with_precedence(operations)
        completion_times, schedule = self._simulate_schedule(sorted_operations)
        total_tardiness, penalty = self._calculate_objective(completion_times, schedule)
        
        # 计算KPI
        kpis = self._calculate_kpis(completion_times, schedule)
        
        return {
            'fitness': total_tardiness + penalty,
            'total_tardiness': total_tardiness,
            'penalty': penalty,
            'completion_times': completion_times,
            'schedule': schedule,
            'kpis': kpis
        }
    
    def _calculate_kpis(self, completion_times: Dict, schedule: List) -> Dict:
        """计算关键性能指标"""
        kpis = {}
        
        # KPI1: 总加权拖期
        total_tardiness = 0.0
        num_on_time = 0
        tardiness_list = []
        
        for order_idx in range(self.num_orders):
            order_id = self.order_list[order_idx]
            C_i_days = completion_times[order_idx] / 86400.0
            d_i = self.due_dates[order_id]
            w_i = self.weights[order_id]
            tardiness = max(0.0, C_i_days - d_i)
            
            total_tardiness += w_i * tardiness
            tardiness_list.append(tardiness)
            if tardiness == 0:
                num_on_time += 1
        
        kpis['total_weighted_tardiness'] = total_tardiness
        kpis['on_time_delivery_rate'] = (num_on_time / self.num_orders) * 100.0
        kpis['avg_tardiness'] = np.mean(tardiness_list) if tardiness_list else 0.0
        
        # KPI2: Makespan
        if completion_times:
            kpis['makespan_days'] = max(completion_times.values()) / 86400.0
        else:
            kpis['makespan_days'] = 0.0
        
        # KPI3: 设备利用率
        machine_workload = {}
        for machine_id in self.machine_list:
            total_work = sum([
                s['processing_time'] for s in schedule if s['machine_id'] == machine_id
            ])
            machine_workload[machine_id] = total_work
            capacity = self.machine_capacity[machine_id]
            util = (total_work / capacity) * 100.0 if capacity > 0 else 0.0
            kpis[f'utilization_{machine_id}'] = util
        
        # 平均利用率
        utilizations = [
            (machine_workload[m] / self.machine_capacity[m]) * 100.0
            for m in self.machine_list if self.machine_capacity[m] > 0
        ]
        kpis['avg_utilization'] = np.mean(utilizations) if utilizations else 0.0
        kpis['bottleneck_load'] = max(utilizations) if utilizations else 0.0
        
        # 负载均衡度
        kpis['load_balance_std'] = np.std(utilizations) if utilizations else 0.0
        
        return kpis


if __name__ == "__main__":
    # 测试代码
    from data_preprocessor import DataPreprocessor
    
    print("🧪 测试FFSSimulator...")
    
    # 加载数据
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    data = preprocessor.process()
    
    # 创建仿真器
    simulator = FFSSimulator(data)
    
    # 测试随机解
    random_solution = np.random.uniform(0, 0.9999, 50)
    fitness = simulator.fit_func(random_solution)
    print(f"\n📊 随机解适应度: {fitness:.2f}")
    
    # 详细评估
    result = simulator.evaluate_solution(random_solution)
    print(f"\n📈 KPI指标:")
    for key, value in result['kpis'].items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
    
    print("\n✅ FFSSimulator测试完成!")