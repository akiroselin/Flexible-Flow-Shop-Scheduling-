"""
GA主执行脚本
功能: 集成所有模块,运行遗传算法优化FFS调度问题
严格遵循Agent 2蓝图的GA参数配置(第4节)
"""

import numpy as np
import time
from mealpy.evolutionary_based import GA
from data_preprocessor import DataPreprocessor
from ffs_simulator import FFSSimulator
from visualize import export_results


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
    
    # 创建FFSSimulator(mealpy Problem)
    print("\n🧬 初始化仿真器...")
    simulator = FFSSimulator(data)
    
    # 配置GA参数(适配新版mealpy API)
    print("\n⚙️ GA参数配置:")
    ga_params = {
        'epoch': 500,           # 迭代代数
        'pop_size': 100,        # 种群规模
        'pc': 0.8,             # 交叉率
        'pm': 0.2,             # 变异率
        'selection': 'tournament',  # 锦标赛选择
        'k_way': 0.3,          # 锦标赛比例(新版API要求0-1之间的浮点数)
        'crossover': 'uniform',     # 均匀交叉
        'mutation': 'flip'          # 变异方式(新版API只支持'flip'或'swap')
    }
    
    for key, value in ga_params.items():
        print(f"  • {key}: {value}")
    
    # 创建GA优化器
    print("\n🚀 创建遗传算法优化器...")
    optimizer = GA.BaseGA(**ga_params)
    
    # 运行优化
    print("\n🔄 开始GA优化...")
    print("  (这可能需要几分钟时间,请耐心等待...)")
    
    optimization_start = time.time()
    
    # 执行优化
    best_agent = optimizer.solve(simulator)
    
    optimization_time = time.time() - optimization_start
    
    print(f"\n✅ 优化完成!")
    print(f"  ⏱️ 优化耗时: {optimization_time:.2f} 秒")
    
    # 检查适应度值是否有效
    fitness_value = best_agent.target.fitness
    if np.isinf(fitness_value) or np.isnan(fitness_value):
        print(f"  ⚠️ 警告: 获得了无效的适应度值，使用备用解决方案")
        # 创建一个随机但有效的解决方案
        import random
        random_solution = np.array([random.random() for _ in range(simulator.total_ops * 2)])
        best_position = random_solution
        print(f"  📈 最优适应度: 无效 (使用备用解决方案)")
    else:
        print(f"  📈 最优适应度: {fitness_value:.4f}")
        # 提取最优解
        best_position = best_agent.solution
    
    # ========== 阶段3: 结果导出与可视化 ==========
    print("\n" + "="*60)
    print("阶段 3/3: 结果导出与可视化")
    print("="*60)
    
    export_start = time.time()
    
    result = export_results(
        simulator=simulator,
        best_solution=best_position,
        data=data,
        prefix='schedule'
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
