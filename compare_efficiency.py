#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
比较设备加工效率
"""

from data_preprocessor import DataPreprocessor

def main():
    # 加载数据
    preprocessor = DataPreprocessor(
        orders_file='订单数据.csv',
        process_times_file='工序加工时间.csv',
        machines_file='设备可用时间.csv'
    )
    data = preprocessor.process()
    
    # 获取设备索引
    eq01_idx = data['machine_list'].index('EQ-01')
    eq04_idx = data['machine_list'].index('EQ-04')
    
    # 获取点胶工序索引
    stage_idx = -1
    for i, stage in enumerate(data['stage_names']):
        if stage == '点胶':
            stage_idx = i
            break
    
    if stage_idx == -1:
        print("未找到点胶工序")
        return
    
    print("\n===== 点胶设备加工效率对比 =====")
    print(f"EQ-01 (点胶设备) 索引: {eq01_idx}")
    print(f"EQ-04 (点胶设备) 索引: {eq04_idx}")
    print(f"点胶工序索引: {stage_idx}")
    
    print("\n各订单在点胶工序的加工时间(秒/片):")
    for order_idx, order_id in enumerate(data['order_list']):
        time_eq01 = data['p_matrix'][order_idx, stage_idx, eq01_idx]
        time_eq04 = data['p_matrix'][order_idx, stage_idx, eq04_idx]
        diff = time_eq04 - time_eq01
        diff_percent = (diff / time_eq01 * 100) if time_eq01 != 0 else float('inf')
        
        print(f"{order_id}: EQ-01={time_eq01:.2f}秒 vs EQ-04={time_eq04:.2f}秒 " + 
              f"(差异: {diff:.2f}秒, {diff_percent:.2f}%)")
    
    # 计算平均加工时间
    avg_eq01 = 0
    avg_eq04 = 0
    count = 0
    
    for order_idx in range(len(data['order_list'])):
        time_eq01 = data['p_matrix'][order_idx, stage_idx, eq01_idx]
        time_eq04 = data['p_matrix'][order_idx, stage_idx, eq04_idx]
        
        if time_eq01 < float('inf') and time_eq04 < float('inf'):
            avg_eq01 += time_eq01
            avg_eq04 += time_eq04
            count += 1
    
    if count > 0:
        avg_eq01 /= count
        avg_eq04 /= count
        diff = avg_eq04 - avg_eq01
        diff_percent = (diff / avg_eq01 * 100) if avg_eq01 != 0 else float('inf')
        
        print(f"\n平均加工时间: EQ-01={avg_eq01:.2f}秒 vs EQ-04={avg_eq04:.2f}秒 " + 
              f"(差异: {diff:.2f}秒, {diff_percent:.2f}%)")
        
        if diff > 0:
            print(f"结论: EQ-04的加工效率比EQ-01低 {diff_percent:.2f}%")
        elif diff < 0:
            print(f"结论: EQ-04的加工效率比EQ-01高 {-diff_percent:.2f}%")
        else:
            print("结论: EQ-04和EQ-01的加工效率相同")

if __name__ == "__main__":
    main()