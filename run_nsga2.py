"""
NSGA-II多目标优化主执行脚本
功能: 使用NSGA-II算法同时优化拖期、利用率和Makespan三个目标
生成帕累托前沿并分析最优解集
"""

import numpy as np
import time
import pandas as pd
import matplotlib.pyplot as plt
import random
from deap import algorithms, base, creator, tools
from data_preprocessor import DataPreprocessor
from ffs_simulator import FFSSimulator
from visualize import export_results


# 全局变量存储仿真器
simulator = None

def evaluate_individual(individual):
    """评估个体的多目标适应度"""
    solution = np.array(individual)
    objectives = simulator.pareto_fitness(solution)
    return objectives


def run_nsga2_optimization():
    """运行NSGA-II多目标优化"""
    global simulator
    
    print("🚀 开始NSGA-II多目标优化...")
    start_time = time.time()
    
    # ========== 步骤1: 数据预处理 ==========
    print("\n📊 加载和预处理数据...")
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    data = preprocessor.process()
    
    # ========== 步骤2: 创建仿真器 ==========
    print("🎯 创建FFS仿真器...")
    simulator = FFSSimulator(data)
    
    # ========== 步骤3: 配置DEAP框架 ==========
    print("⚙️ 配置DEAP NSGA-II框架...")
    
    # 染色体维度
    total_ops = data['num_orders'] * data['num_stages']
    CHROMOSOME_LENGTH = total_ops * 2  # OS + MS
    
    # 创建适应度类和个体类
    creator.create("FitnessMulti", base.Fitness, weights=(-1.0, 1.0, -1.0))  # 最小化拖期，最大化利用率，最小化makespan
    creator.create("Individual", list, fitness=creator.FitnessMulti)
    
    # 创建工具箱
    toolbox = base.Toolbox()
    
    # 注册基因生成函数
    toolbox.register("attr_float", random.uniform, 0.0, 0.9999)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_float, CHROMOSOME_LENGTH)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # 注册遗传操作
    toolbox.register("evaluate", evaluate_individual)
    toolbox.register("mate", tools.cxSimulatedBinaryBounded, low=0.0, up=0.9999, eta=20.0)
    toolbox.register("mutate", tools.mutPolynomialBounded, low=0.0, up=0.9999, eta=20.0, indpb=1.0/CHROMOSOME_LENGTH)
    toolbox.register("select", tools.selNSGA2)
    
    # ========== 步骤4: 运行NSGA-II优化 ==========
    print("🔄 开始NSGA-II优化...")
    
    # 参数设置
    POPULATION_SIZE = 80
    GENERATIONS = 200
    CROSSOVER_PROB = 0.9
    MUTATION_PROB = 0.1
    
    print(f"  - 目标函数: [拖期+惩罚, -利用率, Makespan]")
    print(f"  - 种群大小: {POPULATION_SIZE}")
    print(f"  - 迭代次数: {GENERATIONS}")
    print(f"  - 交叉概率: {CROSSOVER_PROB}")
    print(f"  - 变异概率: {MUTATION_PROB}")
    
    # 创建初始种群
    population = toolbox.population(n=POPULATION_SIZE)
    
    # 评估初始种群
    fitnesses = list(map(toolbox.evaluate, population))
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit
    
    # 统计信息
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", np.mean, axis=0)
    stats.register("min", np.min, axis=0)
    stats.register("max", np.max, axis=0)
    
    # 运行NSGA-II算法
    population, logbook = algorithms.eaMuPlusLambda(
        population, toolbox, mu=POPULATION_SIZE, lambda_=POPULATION_SIZE,
        cxpb=CROSSOVER_PROB, mutpb=MUTATION_PROB, ngen=GENERATIONS,
        stats=stats, verbose=True
    )
    
    optimization_time = time.time() - start_time
    print(f"\n✅ NSGA-II优化完成! 耗时: {optimization_time:.2f}秒")
    
    # ========== 步骤5: 获取帕累托前沿 ==========
    print("\n📈 分析帕累托前沿...")
    
    # 获取帕累托前沿
    pareto_front = tools.sortNondominated(population, len(population), first_front_only=True)[0]
    
    pareto_solutions = [list(ind) for ind in pareto_front]
    pareto_objectives = [ind.fitness.values for ind in pareto_front]
    pareto_objectives = np.array(pareto_objectives)
    
    print(f"帕累托前沿包含 {len(pareto_solutions)} 个解")
    print(f"目标函数范围:")
    print(f"  - 拖期+惩罚: [{pareto_objectives[:, 0].min():.2f}, {pareto_objectives[:, 0].max():.2f}]")
    print(f"  - 利用率: [{pareto_objectives[:, 1].min():.3f}, {pareto_objectives[:, 1].max():.3f}]")  # 注意DEAP中利用率已经是正值
    print(f"  - Makespan: [{pareto_objectives[:, 2].min():.2f}, {pareto_objectives[:, 2].max():.2f}]天")
    
    # ========== 步骤6: 选择代表性解 ==========
    print("\n🎯 选择代表性解...")
    
    # 解1: 最小拖期解
    min_tardiness_idx = np.argmin(pareto_objectives[:, 0])
    min_tardiness_solution = pareto_solutions[min_tardiness_idx]
    min_tardiness_obj = pareto_objectives[min_tardiness_idx]
    
    # 解2: 最大利用率解
    max_utilization_idx = np.argmax(pareto_objectives[:, 1])  # DEAP中利用率是正值，取最大
    max_utilization_solution = pareto_solutions[max_utilization_idx]
    max_utilization_obj = pareto_objectives[max_utilization_idx]
    
    # 解3: 最小Makespan解
    min_makespan_idx = np.argmin(pareto_objectives[:, 2])
    min_makespan_solution = pareto_solutions[min_makespan_idx]
    min_makespan_obj = pareto_objectives[min_makespan_idx]
    
    # 解4: 平衡解(使用加权和方法)
    # 标准化目标函数
    obj_normalized = pareto_objectives.copy()
    for i in range(3):
        obj_min = pareto_objectives[:, i].min()
        obj_max = pareto_objectives[:, i].max()
        if obj_max > obj_min:
            if i == 1:  # 利用率目标，越大越好
                obj_normalized[:, i] = (obj_max - pareto_objectives[:, i]) / (obj_max - obj_min)
            else:  # 拖期和makespan，越小越好
                obj_normalized[:, i] = (pareto_objectives[:, i] - obj_min) / (obj_max - obj_min)
    
    # 计算加权和(等权重)
    weighted_sum = np.sum(obj_normalized, axis=1)
    balanced_idx = np.argmin(weighted_sum)
    balanced_solution = pareto_solutions[balanced_idx]
    balanced_obj = pareto_objectives[balanced_idx]
    
    # ========== 步骤7: 详细评估代表性解 ==========
    print("\n📊 详细评估代表性解...")
    
    solutions_to_evaluate = [
        ("最小拖期解", min_tardiness_solution, min_tardiness_obj),
        ("最大利用率解", max_utilization_solution, max_utilization_obj),
        ("最小Makespan解", min_makespan_solution, min_makespan_obj),
        ("平衡解", balanced_solution, balanced_obj)
    ]
    
    results = {}
    
    for name, solution, objectives in solutions_to_evaluate:
        print(f"\n--- {name} ---")
        print(f"目标函数值: 拖期={objectives[0]:.2f}, 利用率={objectives[1]:.3f}, Makespan={objectives[2]:.2f}天")
        
        # 详细评估
        result = simulator.evaluate_solution(solution)
        results[name] = result
        
        # 输出KPI
        kpis = result['kpis']
        print(f"KPI指标:")
        print(f"  - 总加权拖期: {kpis['total_weighted_tardiness']:.2f}天")
        print(f"  - 订单准时交付率: {kpis['on_time_delivery_rate']:.1f}%")
        print(f"  - 平均拖期: {kpis['avg_tardiness']:.2f}天")
        print(f"  - Makespan: {kpis['makespan_days']:.2f}天")
        print(f"  - 设备平均利用率: {kpis['avg_utilization']:.2f}%")
        print(f"  - 瓶颈设备负载率: {kpis['bottleneck_load']:.2f}%")
        print(f"  - 负载均衡度: {kpis['load_balance_std']:.2f}%")
    
    # ========== 步骤8: 导出结果 ==========
    print("\n💾 导出结果...")
    
    # 选择平衡解作为最终解进行导出
    final_result = results["平衡解"]
    
    # 导出调度结果
    export_results(
        final_result['completion_times'],
        final_result['schedule'],
        final_result['kpis'],
        data,
        algorithm="NSGA2"
    )
    
    # 保存帕累托前沿数据
    pareto_df = pd.DataFrame(pareto_objectives, columns=['Tardiness_Penalty', 'Neg_Utilization', 'Makespan'])
    pareto_df['Utilization'] = -pareto_df['Neg_Utilization']
    pareto_df.drop('Neg_Utilization', axis=1, inplace=True)
    pareto_df.to_csv('pareto_front_NSGA2.csv', index=False)
    
    # 保存代表性解的KPI对比
    comparison_data = []
    for name, result in results.items():
        kpis = result['kpis']
        comparison_data.append({
            'Solution': name,
            'Total_Weighted_Tardiness': kpis['total_weighted_tardiness'],
            'On_Time_Delivery_Rate': kpis['on_time_delivery_rate'],
            'Avg_Tardiness': kpis['avg_tardiness'],
            'Makespan_Days': kpis['makespan_days'],
            'Avg_Utilization': kpis['avg_utilization'],
            'Bottleneck_Load': kpis['bottleneck_load'],
            'Load_Balance_Std': kpis['load_balance_std']
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv('nsga2_solutions_comparison.csv', index=False)
    
    print(f"✅ 结果已导出:")
    print(f"  - 帕累托前沿: pareto_front_NSGA2.csv")
    print(f"  - 解集对比: nsga2_solutions_comparison.csv")
    print(f"  - 调度结果: schedule_orders_NSGA2.csv, schedule_kpis_NSGA2.csv")
    print(f"  - 甘特图: schedule_gantt_NSGA2.html")
    
    return results, pareto_objectives, pareto_solutions


if __name__ == "__main__":
    try:
        results, pareto_front, pareto_solutions = run_nsga2_optimization()
        print("\n🎉 NSGA-II多目标优化成功完成!")
        
    except Exception as e:
        print(f"\n❌ NSGA-II优化过程中出现错误: {e}")
        import traceback
        traceback.print_exc()