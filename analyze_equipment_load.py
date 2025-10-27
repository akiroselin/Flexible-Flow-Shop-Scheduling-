import pandas as pd
import os

GA_PATH = 'schedule_results_GA.csv'
NSGA2_PATH = 'schedule_results_NSGA2.csv'
OUTPUT_PATH = 'equipment_load_comparison.csv'

COL_DEVICE = '设备ID'
COL_DURATION_H = '加工时长(小时)'


def load_stats(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'未找到文件: {csv_path}')
    df = pd.read_csv(csv_path)
    # 统一数值类型
    if COL_DURATION_H not in df.columns:
        raise KeyError(f'文件中缺少列: {COL_DURATION_H}')
    df[COL_DURATION_H] = pd.to_numeric(df[COL_DURATION_H], errors='coerce').fillna(0.0)
    # 分组统计
    grp = df.groupby(COL_DEVICE)
    stats = grp[COL_DURATION_H].sum().to_frame(name='总加工小时').reset_index()
    stats['工序数'] = grp.size().values
    # 占比
    total_hours = stats['总加工小时'].sum()
    stats['小时占比(%)'] = (stats['总加工小时'] / total_hours * 100).round(2) if total_hours > 0 else 0
    return stats.sort_values('总加工小时', ascending=False)


def main():
    ga = load_stats(GA_PATH)
    ns = load_stats(NSGA2_PATH)

    # 合并对比
    comp = pd.merge(ga, ns, on=COL_DEVICE, how='outer', suffixes=('_GA', '_NSGA2'))
    for col in ['总加工小时_GA', '总加工小时_NSGA2', '工序数_GA', '工序数_NSGA2', '小时占比(%)_GA', '小时占比(%)_NSGA2']:
        if col not in comp.columns:
            comp[col] = 0
        comp[col] = comp[col].fillna(0)
    comp['小时差(N2-GA)'] = (comp['总加工小时_NSGA2'] - comp['总加工小时_GA']).round(2)
    comp['工序差(N2-GA)'] = comp['工序数_NSGA2'] - comp['工序数_GA']

    comp = comp.sort_values('总加工小时_NSGA2', ascending=False)
    comp.to_csv(OUTPUT_PATH, index=False)

    print('\n✅ 设备负载对比已导出 ->', OUTPUT_PATH)
    # 打印EQ-04摘要
    eq = comp[comp[COL_DEVICE] == 'EQ-04']
    if eq.empty:
        print('EQ-04在NSGA-II或GA中未被使用。')
    else:
        row = eq.iloc[0]
        print('\n📌 EQ-04摘要:')
        print(f"  - GA: 工序数={int(row['工序数_GA'])}, 总小时={row['总加工小时_GA']:.2f}, 占比={row['小时占比(%)_GA']:.2f}%")
        print(f"  - NSGA2: 工序数={int(row['工序数_NSGA2'])}, 总小时={row['总加工小时_NSGA2']:.2f}, 占比={row['小时占比(%)_NSGA2']:.2f}%")
        print(f"  - 差异: 工序差={int(row['工序差(N2-GA)'])}, 小时差={row['小时差(N2-GA)']:.2f}")

    # 打印NSGA-II下前5负载设备
    print('\n🏭 NSGA-II下负载Top5设备:')
    cols_show = [COL_DEVICE, '工序数_NSGA2', '总加工小时_NSGA2', '小时占比(%)_NSGA2']
    print(comp[cols_show].head(5).to_string(index=False))


if __name__ == '__main__':
    main()