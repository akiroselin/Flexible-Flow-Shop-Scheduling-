import React, { useState, ChangeEvent } from 'react';
import { Upload, Play, Download, FileText, Settings, BarChart3, AlertCircle, CheckCircle, Loader } from 'lucide-react';

type FileMap = {
  orders: File | null;
  processTimes: File | null;
  machines: File | null;
};

type KPI = {
  total_weighted_tardiness?: number;
  on_time_delivery_rate?: number;
  avg_utilization?: number;
  makespan_days?: number;
};

type OrderResult = {
  order_id: string;
  completion_days?: number;
  due_date?: number;
  tardiness?: number;
  on_time?: boolean;
};

type ScheduleResults = {
  kpis?: KPI;
  orders?: OrderResult[];
  gantt_html?: string;
  schedule_csv?: string;
};

const FFSSchedulerApp = () => {
  const [activeTab, setActiveTab] = useState<'logic' | 'input' | 'results'>('logic');
  const [files, setFiles] = useState<FileMap>({
    orders: null,
    processTimes: null,
    machines: null
  });
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [results, setResults] = useState<ScheduleResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 文件上传处理
  const handleFileUpload = (type: keyof FileMap, event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    if (file) {
      setFiles(prev => ({ ...prev, [type]: file }));
    }
  };

  // 运行排程
  const runScheduler = async () => {
    if (!files.orders || !files.processTimes || !files.machines) {
      setError('请上传所有必需的数据文件');
      return;
    }

    setIsRunning(true);
    setError(null);

    const formData = new FormData();
    formData.append('orders', files.orders!);
    formData.append('process_times', files.processTimes!);
    formData.append('machines', files.machines!);

    try {
      const response = await fetch('http://localhost:5000/api/schedule', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error('排程计算失败');
      }

      const data = await response.json();
      setResults(data);
      setActiveTab('results');
    } catch (err: any) {
      setError(err?.message ?? '排程计算失败');
    } finally {
      setIsRunning(false);
    }
  };

  // 逻辑展示组件
  const LogicDisplay = () => (
    <div className="space-y-8">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
          <BarChart3 className="mr-3 text-blue-600" size={28} />
          排程逻辑流程图
        </h2>
        
        <div className="space-y-6">
          {/* 优先级规则 */}
          <div className="border-l-4 border-blue-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">1. 订单优先级规则 (EDD)</h3>
            <div className="bg-blue-50 p-4 rounded">
              <p className="text-sm text-gray-600 mb-2">主规则: 最早交货期优先 (Earliest Due Date)</p>
              <div className="flex items-center space-x-2 text-sm">
                <span className="px-3 py-1 bg-red-100 text-red-700 rounded">P1-紧急 (权重1.2)</span>
                <span>→</span>
                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded">P3-中等 (权重1.0)</span>
                <span>→</span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded">P4-低 (权重0.8)</span>
              </div>
              <p className="text-sm text-gray-600 mt-2">次规则: 最短加工时间优先 (SPT)</p>
            </div>
          </div>

          {/* 设备分配 */}
          <div className="border-l-4 border-green-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">2. 设备分配机制</h3>
            <div className="bg-green-50 p-4 rounded">
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>负载均衡: 优先分配负载率最低的设备</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>并行处理: 2条流水线可同时处理不同订单</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">•</span>
                  <span>不支持批量拆分: 同一工序一次只能在一台设备加工</span>
                </li>
              </ul>
            </div>
          </div>

          {/* 约束条件 */}
          <div className="border-l-4 border-purple-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">3. 调度约束</h3>
            <div className="bg-purple-50 p-4 rounded">
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start">
                  <span className="mr-2">✓</span>
                  <span>工序顺序: COG/FOG → 点胶 → BLU组装 → Inspection → Final Inspection</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">✓</span>
                  <span>设备互斥: 同一时间每台设备只能处理一个任务</span>
                </li>
                <li className="flex items-start">
                  <span className="mr-2">✓</span>
                  <span>设备容量: 每日22小时可用时间 (2小时维护)</span>
                </li>
              </ul>
            </div>
          </div>

          {/* 优化目标 */}
          <div className="border-l-4 border-orange-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">4. 优化目标</h3>
            <div className="bg-orange-50 p-4 rounded">
              <div className="text-sm text-gray-600">
                <p className="font-mono bg-white p-2 rounded border mb-2">
                  min Σ(w<sub>i</sub> × max(0, C<sub>i</sub> - d<sub>i</sub>))
                </p>
                <p>最小化加权总拖期，优先保证紧急订单准时交付</p>
              </div>
            </div>
          </div>

          {/* GA算法 */}
          <div className="border-l-4 border-pink-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">5. 遗传算法 (GA)</h3>
            <div className="bg-pink-50 p-4 rounded">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-semibold text-gray-700">染色体编码</p>
                  <p className="text-gray-600">OS(工序排序) + MS(机器分配)</p>
                </div>
                <div>
                  <p className="font-semibold text-gray-700">参数配置</p>
                  <p className="text-gray-600">种群100, 迭代500代</p>
                </div>
                <div>
                  <p className="font-semibold text-gray-700">交叉率</p>
                  <p className="text-gray-600">pc = 0.8</p>
                </div>
                <div>
                  <p className="font-semibold text-gray-700">变异率</p>
                  <p className="text-gray-600">pm = 0.2</p>
                </div>
              </div>
            </div>
          </div>

          {/* NSGA-II算法 */}
          <div className="border-l-4 border-indigo-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">6. NSGA-II 多目标优化</h3>
            <div className="bg-indigo-50 p-4 rounded">
              <p className="text-sm text-gray-600 mb-3">
                同时优化拖期、利用率、Makespan等多个目标，生成帕累托前沿解集
              </p>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-semibold text-gray-700">核心机制</p>
                  <p className="text-gray-600">非支配排序 + 拥挤距离</p>
                </div>
                <div>
                  <p className="font-semibold text-gray-700">优势</p>
                  <p className="text-gray-600">无需权重设定，解集多样性好</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  // 数据输入组件
  const DataInput = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
          <Upload className="mr-3 text-green-600" size={28} />
          数据文件上传
        </h2>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded flex items-start">
            <AlertCircle className="text-red-600 mr-2 flex-shrink-0" size={20} />
            <span className="text-red-700 text-sm">{error}</span>
          </div>
        )}

        <div className="grid gap-6">
          {/* 订单数据 */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-blue-400 transition">
            <label className="block">
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-semibold text-gray-700">1. 订单数据 (orders.csv)</span>
                {files.orders && <CheckCircle className="text-green-600" size={20} />}
              </div>
              <p className="text-sm text-gray-500 mb-3">
                包含: 订单ID, 产品类型, 数量, 交货日期, 订单优先级
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileUpload('orders', e)}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
              {files.orders && (
                <p className="mt-2 text-sm text-green-600">✓ 已上传: {files.orders.name}</p>
              )}
            </label>
          </div>

          {/* 工序加工时间 */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-blue-400 transition">
            <label className="block">
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-semibold text-gray-700">2. 工序加工时间 (process_times.csv)</span>
                {files.processTimes && <CheckCircle className="text-green-600" size={20} />}
              </div>
              <p className="text-sm text-gray-500 mb-3">
                包含: 流水线, 工序, 标准加工时间(秒/片), 工序良率(%)
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileUpload('processTimes', e)}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
              />
              {files.processTimes && (
                <p className="mt-2 text-sm text-green-600">✓ 已上传: {files.processTimes.name}</p>
              )}
            </label>
          </div>

          {/* 设备可用时间 */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-blue-400 transition">
            <label className="block">
              <div className="flex items-center justify-between mb-3">
                <span className="text-lg font-semibold text-gray-700">3. 设备可用时间 (machines.csv)</span>
                {files.machines && <CheckCircle className="text-green-600" size={20} />}
              </div>
              <p className="text-sm text-gray-500 mb-3">
                包含: 设备ID, 设备类型, 可用时间(分钟)
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => handleFileUpload('machines', e)}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-50 file:text-purple-700 hover:file:bg-purple-100"
              />
              {files.machines && (
                <p className="mt-2 text-sm text-green-600">✓ 已上传: {files.machines.name}</p>
              )}
            </label>
          </div>
        </div>

        {/* 运行按钮 */}
        <div className="mt-8">
          <button
            onClick={runScheduler}
            disabled={isRunning || !files.orders || !files.processTimes || !files.machines}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white py-4 px-6 rounded-lg font-semibold text-lg hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center space-x-3 shadow-lg"
          >
            {isRunning ? (
              <>
                <Loader className="animate-spin" size={24} />
                <span>正在运行排程优化... (预计2-3分钟)</span>
              </>
            ) : (
              <>
                <Play size={24} />
                <span>运行GA排程优化</span>
              </>
            )}
          </button>
        </div>

        {/* 示例数据下载 */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600 mb-2">
            <FileText className="inline mr-1" size={16} />
            没有数据？下载示例文件:
          </p>
          <div className="flex space-x-4 text-sm">
            <a href="/examples/orders.csv" className="text-blue-600 hover:underline">订单示例</a>
            <a href="/examples/process_times.csv" className="text-blue-600 hover:underline">工序示例</a>
            <a href="/examples/machines.csv" className="text-blue-600 hover:underline">设备示例</a>
          </div>
        </div>
      </div>
    </div>
  );

  // 结果展示组件
  const ResultsDisplay = () => {
    if (!results) {
      return (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <Settings className="mx-auto text-gray-400 mb-4" size={64} />
          <p className="text-gray-500 text-lg">尚未运行排程，请先上传数据并运行优化</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* KPI指标 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">优化结果 KPI</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-lg">
              <p className="text-sm text-gray-600">总加权拖期</p>
              <p className="text-3xl font-bold text-blue-700">{results.kpis?.total_weighted_tardiness?.toFixed(2)}</p>
              <p className="text-xs text-gray-500">天</p>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-lg">
              <p className="text-sm text-gray-600">准时交付率</p>
              <p className="text-3xl font-bold text-green-700">{results.kpis?.on_time_delivery_rate?.toFixed(1)}</p>
              <p className="text-xs text-gray-500">%</p>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-lg">
              <p className="text-sm text-gray-600">设备利用率</p>
              <p className="text-3xl font-bold text-purple-700">{results.kpis?.avg_utilization?.toFixed(1)}</p>
              <p className="text-xs text-gray-500">%</p>
            </div>
            <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-lg">
              <p className="text-sm text-gray-600">Makespan</p>
              <p className="text-3xl font-bold text-orange-700">{results.kpis?.makespan_days?.toFixed(2)}</p>
              <p className="text-xs text-gray-500">天</p>
            </div>
          </div>
        </div>

        {/* 订单完工情况 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">订单完工情况</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left">订单ID</th>
                  <th className="px-4 py-2 text-right">完工时间(天)</th>
                  <th className="px-4 py-2 text-right">交货期(天)</th>
                  <th className="px-4 py-2 text-right">拖期(天)</th>
                  <th className="px-4 py-2 text-center">状态</th>
                </tr>
              </thead>
              <tbody>
                {results.orders?.map((order, idx) => (
                  <tr key={idx} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{order.order_id}</td>
                    <td className="px-4 py-2 text-right">{order.completion_days?.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right">{order.due_date?.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right">{order.tardiness?.toFixed(2)}</td>
                    <td className="px-4 py-2 text-center">
                      {order.on_time ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">准时</span>
                      ) : (
                        <span className="px-2 py-1 bg-red-100 text-red-700 rounded-full text-xs">延迟</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 甘特图 */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-xl font-bold text-gray-800 mb-4">调度甘特图</h3>
          {results.gantt_html ? (
            <iframe
              srcDoc={results.gantt_html}
              className="w-full h-[600px] border rounded"
              title="Gantt Chart"
            />
          ) : (
            <p className="text-gray-500">甘特图加载中...</p>
          )}
        </div>

        {/* 下载按钮 */}
        <div className="flex space-x-4">
          <button
            onClick={() => {
              const blob = new Blob([results.schedule_csv], { type: 'text/csv' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'schedule_results.csv';
              a.click();
            }}
            className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 transition flex items-center justify-center space-x-2"
          >
            <Download size={20} />
            <span>下载调度结果 (CSV)</span>
          </button>
          <button
            onClick={() => {
              const blob = new Blob([results.gantt_html], { type: 'text/html' });
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = 'gantt_chart.html';
              a.click();
            }}
            className="flex-1 bg-green-600 text-white py-3 px-6 rounded-lg hover:bg-green-700 transition flex items-center justify-center space-x-2"
          >
            <Download size={20} />
            <span>下载甘特图 (HTML)</span>
          </button>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            FFS 柔性流水车间调度优化系统
          </h1>
          <p className="text-gray-600 mt-1">基于遗传算法的智能排程解决方案</p>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('logic')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition ${
                activeTab === 'logic'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              排程逻辑展示
            </button>
            <button
              onClick={() => setActiveTab('input')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition ${
                activeTab === 'input'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              数据输入
            </button>
            <button
              onClick={() => setActiveTab('results')}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition ${
                activeTab === 'results'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              结果展示
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {activeTab === 'logic' && <LogicDisplay />}
        {activeTab === 'input' && <DataInput />}
        {activeTab === 'results' && <ResultsDisplay />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-sm text-gray-500">
          <p>© 2025 FFS调度优化系统 | Powered by Genetic Algorithm + React + Flask</p>
        </div>
      </footer>
    </div>
  );
};

export default FFSSchedulerApp;