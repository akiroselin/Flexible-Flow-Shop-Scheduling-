"""
GA主执行脚本
功能: 集成所有模块,运行遗传算法优化FFS调度问题
严格遵循Agent 2蓝图的GA参数配置(第4节)
"""

import numpy as np
import time
import random
from typing import List, Tuple
from data_preprocessor import DataPreprocessor
from ffs_simulator import FFSSimulator
from visualize import export_results


# ========== 新增: 自适应GA与局部搜索 ==========
class AdaptiveGA:
    def __init__(self, pc: float = 0.8, pm: float = 0.2):
        self.pc = pc
        self.pm = pm
        self.best_fitness_history: List[float] = []

    def adapt_parameters(self, generation: int):
        # 如果10代内无明显改进,增加变异率、降低交叉率
        if len(self.best_fitness_history) > 10:
            recent_improvement = abs(
                self.best_fitness_history[-1] - self.best_fitness_history[-10]
            )
            if recent_improvement < 0.01:
                self.pm = min(0.5, self.pm * 1.2)  # 增加探索
                self.pc = max(0.6, self.pc * 0.9)  # 减少利用


def local_search(solution: np.ndarray, simulator: FFSSimulator) -> np.ndarray:
    """邻域搜索改进解: 尝试交换相邻基因"""
    best_solution = solution.copy()
    best_fitness = simulator.fit_func(best_solution)

    # 为控制开销,仅在前200个位置进行相邻交换尝试
    upper = min(len(solution) - 1, 200)
    for i in range(upper):
        neighbor = best_solution.copy()
        neighbor[i], neighbor[i+1] = neighbor[i+1], neighbor[i]
        fitness = simulator.fit_func(neighbor)
        if fitness < best_fitness:
            best_solution = neighbor
            best_fitness = fitness
    return best_solution


def print_banner():
    """打印启动横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║       FFS调度优化系统 - 遗传算法求解器                          ║
║       Flexible Flow Shop Scheduling with Genetic Algorithm    ║
║                                                               ║
║       Based on Agent 1 + Agent 2 + Agent 3 协作框架           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    print_banner()
    
    # ========== 阶段1: 数据加载与预处理 ==========
    print("\n" + "="*60)
    print("阶段 1/3: 数据加载与预处理")
    print("="*60)
    
    start_time = time.time()
    
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    
    data = preprocessor.process()
    
    preprocess_time = time.time() - start_time
    print(f"\n⏱️ 数据预处理耗时: {preprocess_time:.2f} 秒")
    
    # ========== 阶段2: GA优化求解 ==========
    print("\n" + "="*60)
    print("阶段 2/3: 遗传算法优化")
    print("="*60)
    
    # 创建FFSSimulator
    print("\n🧬 初始化仿真器...")
    simulator = FFSSimulator(data)
    
    # 新增: 调整目标函数权重与偏好设备以提升利用率与均衡度
    simulator.lambda_balance = 30.0           # 加强均衡约束
    simulator.lambda_utilization = 8.0        # 鼓励平均利用率提升
    simulator.target_avg_util = 0.12          # 目标平均利用率(12%)
    simulator.preferred_machines = {"EQ-06", "EQ-01", "EQ-03", "EQ-04"}
    simulator.lambda_preferred = 2.0          # 偏好设备占比不足惩罚系数(温和)
    simulator.target_preferred_ratio = 0.35   # 偏好设备目标占比(35%)
    
    # 配置GA参数
    print("\n⚙️ GA参数配置:")
    pop_size = 100
    epochs = 100  # 提升到100以获得更稳定的自适应轨迹
    k_tourn_frac = 0.2
    ga_ctrl = AdaptiveGA(pc=0.8, pm=0.2)
    print(f"  • pop_size: {pop_size}")
    print(f"  • epochs: {epochs}")
    print(f"  • pc (初始): {ga_ctrl.pc}")
    print(f"  • pm (初始): {ga_ctrl.pm}")
    print(f"  • selection: tournament (比例={k_tourn_frac})")
    print(f"  • crossover: uniform")
    print(f"  • mutation: random-reset")
    
    # 生成混合初始种群(50%启发式 + 50%随机)
    print("\n🧬 生成混合初始种群...")
    initial_population: List[np.ndarray] = []
    for i in range(pop_size):
        if i < pop_size // 2:
            edd_sol = simulator.generate_edd_solution()
            noise = np.random.normal(0, 0.05, len(edd_sol))
            solution = np.clip(edd_sol + noise, 0, 0.9999)
        else:
            solution = np.random.uniform(0, 0.9999, simulator.total_ops * 2)
        initial_population.append(solution)
    
    # 评估初始种群
    fitness = np.array([simulator.fit_func(ind) for ind in initial_population])
    
    def tournament_select(pop: List[np.ndarray], fit: np.ndarray, k_frac: float) -> List[np.ndarray]:
        k = max(2, int(len(pop) * k_frac))
        selected = []
        for _ in range(len(pop)):
            idxs = np.random.choice(len(pop), size=k, replace=False)
            best_idx = idxs[np.argmin(fit[idxs])]  # 最小化目标
            selected.append(pop[best_idx].copy())
        return selected
    
    def uniform_crossover(p1: np.ndarray, p2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mask = np.random.rand(len(p1)) < 0.5
        c1 = np.where(mask, p1, p2)
        c2 = np.where(mask, p2, p1)
        return c1, c2
    
    def mutate(ind: np.ndarray, pm: float) -> np.ndarray:
        # 逐基因随机重置
        mask = np.random.rand(len(ind)) < pm
        ind[mask] = np.random.uniform(0.0, 0.9999, size=mask.sum())
        return np.clip(ind, 0.0, 0.9999)
    
    population = initial_population
    
    print("\n🔄 开始GA优化...")
    optimization_start = time.time()
    
    for gen in range(epochs):
        # 选择
        mating_pool = tournament_select(population, fitness, k_tourn_frac)
    
        # 交叉
        offspring: List[np.ndarray] = []
        for i in range(0, pop_size, 2):
            p1 = mating_pool[i]
            p2 = mating_pool[(i+1) % pop_size]
            if random.random() < ga_ctrl.pc:
                c1, c2 = uniform_crossover(p1, p2)
            else:
                c1, c2 = p1.copy(), p2.copy()
            offspring.append(c1)
            offspring.append(c2)
    
        # 变异
        for i in range(len(offspring)):
            offspring[i] = mutate(offspring[i], ga_ctrl.pm)
    
        # 局部搜索: 对当前最优个体进行邻域提升
        best_idx = int(np.argmin(fitness))
        best_ind = population[best_idx]
        improved_best = local_search(best_ind, simulator)
    
        # 形成新一代: 保留改进的精英 + 其他子代
        population = offspring
        population[0] = improved_best  # 简单精英保留
    
        # 评估
        fitness = np.array([simulator.fit_func(ind) for ind in population])
        best_fit = float(np.min(fitness))
        ga_ctrl.best_fitness_history.append(best_fit)
    
        # 参数自适应
        ga_ctrl.adapt_parameters(gen)
    
        if gen % 20 == 0 or gen == epochs - 1:
            print(f"代 {gen:03d} | 最优适应度={best_fit:.4f} | pc={ga_ctrl.pc:.3f} pm={ga_ctrl.pm:.3f}")
    
    optimization_time = time.time() - optimization_start
    best_idx = int(np.argmin(fitness))
    best_position = population[best_idx]
    best_fitness = float(fitness[best_idx])
    
    print(f"\n✅ 优化完成!")
    print(f"  ⏱️ 优化耗时: {optimization_time:.2f} 秒")
    print(f"  📈 最优适应度: {best_fitness:.4f}")
    
    # ========== 阶段3: 结果导出与可视化 ==========
    print("\n" + "="*60)
    print("阶段 3/3: 结果导出与可视化")
    print("="*60)
    
    export_start = time.time()
    
    # 评估最优解以导出
    eval_result = simulator.evaluate_solution(best_position)
    result = export_results(
        eval_result['completion_times'],
        eval_result['schedule'],
        eval_result['kpis'],
        data,
        algorithm="GA",
    )
    
    export_time = time.time() - export_start
    print(f"\n⏱️ 结果导出耗时: {export_time:.2f} 秒")
    
    # ========== 总结报告 ==========
    total_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("执行总结")
    print("="*60)
    print(f"\n⏱️ 总耗时: {total_time:.2f} 秒")
    print(f"  • 数据预处理: {preprocess_time:.2f} 秒 ({preprocess_time/total_time*100:.1f}%)")
    print(f"  • GA优化: {optimization_time:.2f} 秒 ({optimization_time/total_time*100:.1f}%)")
    print(f"  • 结果导出: {export_time:.2f} 秒 ({export_time/total_time*100:.1f}%)")
    
    print("\n📁 输出文件:")
    print("  ✓ schedule_results_GA.csv  - 详细调度方案")
    print("  ✓ schedule_kpis_GA.csv     - KPI指标汇总")
    print("  ✓ schedule_orders_GA.csv   - 订单完工情况")
    print("  ✓ schedule_gantt_GA.html   - 交互式甘特图")
    
    print("\n🎯 优化目标达成情况:")
    kpis = result['kpis']
    
    # 计算改进指标
    on_time_rate = kpis['on_time_delivery_rate']
    avg_utilization = kpis['avg_utilization']
    
    if on_time_rate >= 80:
        print(f"  ✅ 订单准时交付率: {on_time_rate:.2f}% (优秀)")
    elif on_time_rate >= 60:
        print(f"  ⚠️ 订单准时交付率: {on_time_rate:.2f}% (良好)")
    else:
        print(f"  ❌ 订单准时交付率: {on_time_rate:.2f}% (需改进)")
    
    if avg_utilization >= 80:
        print(f"  ✅ 设备平均利用率: {avg_utilization:.2f}% (优秀)")
    elif avg_utilization >= 60:
        print(f"  ⚠️ 设备平均利用率: {avg_utilization:.2f}% (良好)")
    else:
        print(f"  ❌ 设备平均利用率: {avg_utilization:.2f}% (偏低)")
    
    # 瓶颈分析
    print("\n🔍 瓶颈分析:")
    bottleneck_load = kpis['bottleneck_load']
    print(f"  • 瓶颈设备负载率: {bottleneck_load:.2f}%")
    
    if bottleneck_load > 95:
        print("  ⚠️ 瓶颈设备接近满负荷,建议考虑产能扩充或加班")
    elif bottleneck_load > 90:
        print("  ⚠️ 瓶颈设备负载较高,需密切监控")
    else:
        print("  ✅ 瓶颈设备负载在合理范围内")
    
    # 拖期分析
    print("\n📅 交期分析:")
    total_tardiness = kpis['total_weighted_tardiness']
    avg_tardiness = kpis['avg_tardiness']
    
    print(f"  • 总加权拖期: {total_tardiness:.2f} 天")
    print(f"  • 平均拖期: {avg_tardiness:.2f} 天")
    
    if total_tardiness == 0:
        print("  ✅ 所有订单均准时完成!")
    elif avg_tardiness < 2:
        print("  ⚠️ 存在少量延迟,总体可控")
    else:
        print("  ❌ 存在较严重延迟,建议调整交货期或增加产能")
    
    print("\n" + "="*60)
    print("🎉 FFS调度优化完成!")
    print("="*60)
    print("\n💡 下一步操作:")
    print("  1. 打开 schedule_gantt_GA.html 查看可视化调度方案")
    print("  2. 查看 schedule_results_GA.csv 了解详细调度明细")
    print("  3. 参考 schedule_kpis_GA.csv 评估优化效果")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断执行")
    except Exception as e:
        print(f"\n\n❌ 程序执行错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n💡 请检查:")
        print("  1. 数据文件是否存在且格式正确")
        print("  2. 依赖库是否正确安装 (pip install -r requirements.txt)")
        print("  3. Python版本是否 >= 3.8")