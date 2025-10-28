// @ts-nocheck
/* global React, ReactDOM */
/** @jsx React.createElement */
/** @jsxFrag React.Fragment */
/* @jsxRuntime classic */
declare const React: any;
declare const ReactDOM: any;

// Provide a permissive JSX namespace to silence IntrinsicElements diagnostics in browser-run TSX
declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }
  }
}

// Adapted for browser-run via Babel Standalone: remove imports, use global React/ReactDOM
const { useState, useEffect } = React;

// Minimal icon placeholders to keep layout; replace lucide-react usage
const Icon = ({ label, className }: { label: string; className?: string }) => (
  <span className={className} style={{ display: 'inline-block' }}>{label}</span>
);
const Upload = (props: any) => <Icon label="⬆️" {...props} />;
const Play = (props: any) => <Icon label="▶️" {...props} />;
const Download = (props: any) => <Icon label="⤓" {...props} />;
const FileText = (props: any) => <Icon label="📄" {...props} />;
const Settings = (props: any) => <Icon label="⚙️" {...props} />;
const BarChart3 = (props: any) => <Icon label="📊" {...props} />;
const AlertCircle = (props: any) => <Icon label="⚠️" {...props} />;
const CheckCircle = (props: any) => <Icon label="✅" {...props} />;
const Loader = (props: any) => <Icon label="⏳" {...props} />;

type Results = {
  kpis: {
    total_weighted_tardiness: number;
    on_time_delivery_rate: number;
    avg_utilization: number;
    makespan_days: number;
  };
  orders: Array<{
    order_id: string;
    completion_days: number;
    due_date: string;
    tardiness: number;
    on_time: boolean;
  }>;
  gantt_html: string;
  schedule_csv: string;
  // 以下为兼容老版接口的可选字段
  gantt_url?: string;
  schedule_csv_url?: string;
  files?: Array<{ name: string; url: string }>;
};

function LogicDisplay() {
  return (
    <div className="space-y-8">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
          <BarChart3 className="mr-3 text-blue-600" />
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
            <h3 className="text-lg font-semibold text-gray-700 mb-2">5. 遗传算法 (GA)：自适应与均衡策略</h3>
            <div className="bg-pink-50 p-4 rounded space-y-3">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-semibold text-gray-700">染色体编码</p>
                  <p className="text-gray-600">OS(工序排序) + MS(机器分配)</p>
                </div>
                <div>
                  <p className="font-semibold text-gray-700">基础参数</p>
                  <p className="text-gray-600">种群100，代数500；交叉pc≈0.8，变异pm≈0.2</p>
                </div>
              </div>
              <ul className="list-disc pl-5 text-sm text-gray-700 space-y-1">
                <li>自适应交叉/变异：根据代内适应度分布动态调整pc/pm，提升收敛稳定性。</li>
                <li>均衡分配启发式：评估设备实时负载，优先选择负载更均衡的机器以降低瓶颈。</li>
                <li>选择策略：锦标赛/轮盘选择，兼顾探索与利用；保留精英解。</li>
                <li>可行性修复：确保工序顺序与设备互斥，违规解在解码后修复。</li>
              </ul>
            </div>
          </div>

          {/* NSGA-II 多目标优化简介 */}
          <div className="border-l-4 border-indigo-500 pl-4">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">6. NSGA-II：多目标进化与帕累托前沿</h3>
            <div className="bg-indigo-50 p-4 rounded space-y-3 text-sm text-gray-700">
              <p>
                NSGA-II（非支配排序遗传算法）用于同时优化多个目标，不依赖单一加权和。通过“非支配排序”与“拥挤距离”选择，维持解的多样性与均衡性，得到一组互不支配的帕累托解。
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="bg-white rounded border p-3">
                  <p className="font-semibold">典型目标</p>
                  <ul className="list-disc pl-5 mt-1 text-gray-600">
                    <li>最小化总加权拖期</li>
                    <li>最小化Makespan</li>
                    <li>最大化准时交付率/设备利用率</li>
                  </ul>
                </div>
                <div className="bg-white rounded border p-3">
                  <p className="font-semibold">关键机制</p>
                  <ul className="list-disc pl-5 mt-1 text-gray-600">
                    <li>非支配排序：按支配关系分层选择</li>
                    <li>拥挤距离：保持帕累托前沿的解分布均匀</li>
                    <li>精英保留：避免优秀解被遗忘</li>
                  </ul>
                </div>
                <div className="bg-white rounded border p-3">
                  <p className="font-semibold">使用建议</p>
                  <ul className="list-disc pl-5 mt-1 text-gray-600">
                    <li>当需要权衡多指标时优先考虑NSGA-II</li>
                    <li>从帕累托集合中按业务偏好选取最终解</li>
                    <li>可与GA的均衡分配启发式结合以提升可行性</li>
                  </ul>
                </div>
              </div>
              <p className="text-gray-600">
                说明：当前结果页默认展示 GA 的单目标视图；如需启用 NSGA-II 结果展示，可在后端保留多目标接口，并在前端增加帕累托曲线与解选择器。
              </p>
            </div>
          </div>

        
        </div>
      </div>
    </div>
  );
}

function DataInput({ files, onFilesChange, onRun, onRunNsga2, isRunning, error }: { files: Record<string, File | null>; onFilesChange: (f: Record<string, File | null>) => void; onRun: () => void; onRunNsga2: () => void; isRunning: boolean; error?: string | null; }) {
  const handleFile = (key: string, file: File | null) => {
    onFilesChange({ ...files, [key]: file });
  };
  const inputClass = "mt-2 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-700 file:mr-4 file:rounded-md file:border-0 file:bg-gray-200 file:px-3 file:py-2 hover:file:bg-gray-300";
  const cardClass = "border-2 border-dashed border-gray-300 rounded-lg p-5 hover:border-indigo-400 transition";
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-2 mb-6">
          <Upload className="w-5 h-5 text-gray-700" />
          <h3 className="text-lg font-semibold text-gray-800">数据文件上传</h3>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 text-red-700 bg-red-50 border border-red-100 rounded-lg p-3">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className={cardClass}>
              <label className="block">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-base font-semibold text-gray-700">1. 订单数据（orders.csv）</span>
                  {files.orders && <CheckCircle className="w-5 h-5 text-green-600" />}
                </div>
                <p className="text-xs text-gray-500 mb-3">包含：订单ID、产品类型、数量、交货日期、订单优先级</p>
                <input className={inputClass} type="file" accept=".csv" onChange={(e) => handleFile('orders', e.target.files?.[0] || null)} />
                {files.orders && <p className="mt-2 text-xs text-green-600">✓ 已上传：{files.orders.name}</p>}
              </label>
            </div>

            <div className={cardClass}>
              <label className="block">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-base font-semibold text-gray-700">2. 工序加工时间（process_times.csv）</span>
                  {files.process_times && <CheckCircle className="w-5 h-5 text-green-600" />}
                </div>
                <p className="text-xs text-gray-500 mb-3">包含：订单ID、工序序列、设备类型、加工时间（分钟）</p>
                <input className={inputClass} type="file" accept=".csv" onChange={(e) => handleFile('process_times', e.target.files?.[0] || null)} />
                {files.process_times && <p className="mt-2 text-xs text-green-600">✓ 已上传：{files.process_times.name}</p>}
              </label>
            </div>

            <div className={cardClass}>
              <label className="block">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-base font-semibold text-gray-700">3. 设备可用时间（machines.csv）</span>
                  {files.machines && <CheckCircle className="w-5 h-5 text-green-600" />}
                </div>
                <p className="text-xs text-gray-500 mb-3">包含：设备ID、设备类型、可用时间（分钟）</p>
                <input className={inputClass} type="file" accept=".csv" onChange={(e) => handleFile('machines', e.target.files?.[0] || null)} />
                {files.machines && <p className="mt-2 text-xs text-green-600">✓ 已上传：{files.machines.name}</p>}
              </label>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-4 h-4 text-gray-700" />
              <span className="font-medium text-gray-800">上传说明</span>
            </div>
            <ul className="text-sm text-gray-600 space-y-2 list-disc pl-5">
              <li>支持 .csv 文件，UTF-8 编码。</li>
              <li>字段顺序与示例一致即可。</li>
              <li>未上传数据时，将使用系统内置 CSV 运行。</li>
            </ul>
          </div>
        </div>

        <div className="mt-6">
          <div className="flex flex-col md:flex-row md:items-center md:gap-3">
            <button onClick={onRun} disabled={isRunning} className="w-full md:w-auto px-5 py-2.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
              {isRunning ? <Loader className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isRunning ? '运行中...' : '运行排程（GA）'}</span>
            </button>
            <button onClick={onRunNsga2} disabled={isRunning} className="w-full md:w-auto px-5 py-2.5 rounded-lg bg-fuchsia-600 text-white hover:bg-fuchsia-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
              {isRunning ? <Loader className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isRunning ? '运行中...' : '运行排程（NSGA-II）'}</span>
            </button>
          </div>
          <p className="mt-2 text-sm text-gray-600">未上传数据时，将使用当前系统内的 CSV 文件运行。</p>
        </div>
      </div>
    </div>
  );
}

function FFSSchedulerApp() {
  const [activeTab, setActiveTab] = useState<'logic' | 'input' | 'results'>('results');
  const [files, setFiles] = useState<Record<string, File | null>>({ orders: null, process_times: null, machines: null });
  const [isRunning, setIsRunning] = useState(false);
  const [results, setResults] = useState<Results | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 加载已仿真生成的结果（老版方式）：自动读取 /api/results
  useEffect(() => {
    const fetchExistingResults = async () => {
      try {
        const resp = await fetch('/api/results');
        if (!resp.ok) return; // 若不存在则保持为空
        const data = await resp.json();
        setResults(data);
      } catch (e) {
        // 静默失败，不影响其他流程
      }
    };
    fetchExistingResults();
  }, []);

  const handleFileUpload = (newFiles: Record<string, File | null>) => setFiles(newFiles);

  const runScheduler = async () => {
    setError(null);
    setIsRunning(true);
    try {
      const formData = new FormData();
      if (files.orders) formData.append('orders', files.orders);
      if (files.process_times) formData.append('process_times', files.process_times);
      if (files.machines) formData.append('machines', files.machines);
      const resp = await fetch('/api/schedule', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error(`后端错误：${resp.status}`);
      const data = await resp.json();
      setResults(data);
      setActiveTab('results');
    } catch (e: any) {
      setError(e?.message || '运行失败');
    } finally {
      setIsRunning(false);
    }
  };

  const runSchedulerNsga2 = async () => {
    setError(null);
    setIsRunning(true);
    try {
      const formData = new FormData();
      if (files.orders) formData.append('orders', files.orders);
      if (files.process_times) formData.append('process_times', files.process_times);
      if (files.machines) formData.append('machines', files.machines);
      const resp = await fetch('/api/schedule_nsga2', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error(`后端错误：${resp.status}`);
      const data = await resp.json();
      setResults(data);
      setActiveTab('results');
    } catch (e: any) {
      setError(e?.message || '运行失败');
    } finally {
      setIsRunning(false);
    }
  };

  

  const TabButton = ({ id, icon, label }: { id: 'logic'|'input'|'results'; icon: any; label: string; }) => (
    <button onClick={() => setActiveTab(id)} className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-medium ${activeTab===id? 'bg-gray-900 text-white shadow-sm':'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'}`}>
      {icon}
      <span>{label}</span>
    </button>
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">FFS 柔性流水车间调度优化系统</h1>
      </div>

      <div className="flex gap-3 mb-6">
        <TabButton id="logic" icon={<Settings className="w-4 h-4"/>} label="模型与逻辑" />
        <TabButton id="input" icon={<Upload className="w-4 h-4"/>} label="数据输入" />
        <TabButton id="results" icon={<BarChart3 className="w-4 h-4"/>} label="排程优化与结果" />
      </div>

      {activeTab === 'logic' && <LogicDisplay />}
      {activeTab === 'input' && <DataInput files={files} onFilesChange={handleFileUpload} onRun={runScheduler} onRunNsga2={runSchedulerNsga2} isRunning={isRunning} error={error} />}

      {activeTab === 'results' && (
        <div className="space-y-6">

          {/* 结果展示：改为两个独立条件块，避免嵌套三元带来的括号复杂度 */}
          {results?.ga && (
            <div className="space-y-10">
              {/* GA 结果块 */}
              <div className="space-y-6">
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-gray-900">GA 结果</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100">
                    <div className="text-xs text-gray-600">总加权拖期</div>
                    <div className="mt-1 text-2xl font-bold text-indigo-900">{results.ga.kpis?.total_weighted_tardiness}</div>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100">
                    <div className="text-xs text-gray-600">准时交付率</div>
                    <div className="mt-1 text-2xl font-bold text-emerald-900">{(results.ga.kpis?.on_time_delivery_rate*100).toFixed(1)}%</div>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100">
                    <div className="text-xs text-gray-600">设备平均利用率</div>
                    <div className="mt-1 text-2xl font-bold text-amber-900">{(results.ga.kpis?.avg_utilization*100).toFixed(1)}%</div>
                  </div>
                  <div className="p-4 rounded-xl bg-gradient-to-br from-fuchsia-50 to-fuchsia-100">
                    <div className="text-xs text-gray-600">Makespan（天）</div>
                    <div className="mt-1 text-2xl font-bold text-fuchsia-900">{results.ga.kpis?.makespan_days}</div>
                  </div>
                </div>
                {(() => {
                  const orders = results.ga.orders || [];
                  const tardyOrders = orders.filter((o: any) => (o?.tardiness ?? 0) > 0);
                  const tardyCount = tardyOrders.length;
                  const top5 = [...tardyOrders].sort((a, b) => (b.tardiness || 0) - (a.tardiness || 0)).slice(0, 5);
                  const worst = top5[0];
                  const avgTardiness = (results.ga.kpis as any)?.avg_tardiness;
                  const loadStd = (results.ga.kpis as any)?.load_balance_std;
                  return (
                    <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-gray-700" />
                        <span className="font-medium text-gray-800">结果数据分析（GA）</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                        <div className="p-3 rounded-lg bg-gray-50">
                          <div className="text-xs text-gray-600">逾期订单数</div>
                          <div className="mt-1 text-xl font-bold text-gray-900">{tardyCount}</div>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <div className="text-xs text-gray-600">平均拖期（天）</div>
                          <div className="mt-1 text-xl font-bold text-gray-900">{avgTardiness ?? '-'}</div>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <div className="text-xs text-gray-600">最严重拖期订单</div>
                          <div className="mt-1 text-sm text-gray-900">{worst ? `${worst.order_id}（${worst.tardiness}天）` : '-'}</div>
                        </div>
                        <div className="p-3 rounded-lg bg-gray-50">
                          <div className="text-xs text-gray-600">负载均衡度（Std）</div>
                          <div className="mt-1 text-xl font-bold text-gray-900">{loadStd ?? '-'}</div>
                        </div>
                      </div>
                      {top5.length > 0 && (
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-sm">
                            <thead>
                              <tr className="bg-gray-50">
                                <th className="px-4 py-2 text-left text-gray-700">订单ID</th>
                                <th className="px-4 py-2 text-left text-gray-700">拖期（天）</th>
                                <th className="px-4 py-2 text-left text-gray-700">交期</th>
                                <th className="px-4 py-2 text-left text-gray-700">完工（天）</th>
                              </tr>
                            </thead>
                            <tbody>
                              {top5.map((o: any, idx: number) => (
                                <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                  <td className="px-4 py-2 text-gray-800">{o.order_id}</td>
                                  <td className="px-4 py-2 text-gray-800">{o.tardiness}</td>
                                  <td className="px-4 py-2 text-gray-800">{o.due_date}</td>
                                  <td className="px-4 py-2 text-gray-800">{o.completion_days}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  );
                })()}
                <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                  <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-gray-700" />
                    <span className="font-medium text-gray-800">甘特图（GA）</span>
                  </div>
                  {results.ga.gantt_html ? (
                    <iframe title="Gantt-GA" className="w-full h-[560px]" srcDoc={results.ga.gantt_html}></iframe>
                  ) : results.ga.gantt_url ? (
                    <iframe title="Gantt-GA" className="w-full h-[560px]" src="/gantt"></iframe>
                  ) : (
                    <div className="p-6 text-gray-500">暂无甘特图数据</div>
                  )}
                </div>
                <div className="flex flex-wrap gap-3">
                  {results.ga.schedule_csv_url ? (
                    <a className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-black flex items-center gap-2" download href={results.ga.schedule_csv_url}>
                      <Download className="w-4 h-4" /> 下载排程结果 CSV（GA）
                    </a>
                  ) : results.ga.schedule_csv ? (
                    <a className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-black flex items-center gap-2" download="schedule_results_GA.csv" href={URL.createObjectURL(new Blob([results.ga.schedule_csv], { type: 'text/csv' }))}>
                      <Download className="w-4 h-4" /> 下载排程结果 CSV（GA）
                    </a>
                  ) : null}
                  {results.ga.gantt_html ? (
                    <a className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-2" download="schedule_gantt_GA.html" href={URL.createObjectURL(new Blob([results.ga.gantt_html], { type: 'text/html' }))}>
                      <Download className="w-4 h-4" /> 下载甘特图 HTML（GA）
                    </a>
                  ) : results.ga.gantt_url ? (
                    <a className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-2" download href={results.ga.gantt_url}>
                      <Download className="w-4 h-4" /> 下载甘特图 HTML（GA）
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          )}

          {/* NSGA-II 结果块（聚合接口） */}
          {results && (results as any).nsga2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-gray-900">NSGA-II 结果</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100">
                  <div className="text-xs text-gray-600">总加权拖期</div>
                  <div className="mt-1 text-2xl font-bold text-indigo-900">{(results as any).nsga2.kpis?.total_weighted_tardiness}</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100">
                  <div className="text-xs text-gray-600">准时交付率</div>
                  <div className="mt-1 text-2xl font-bold text-emerald-900">{(((results as any).nsga2.kpis?.on_time_delivery_rate || 0)*100).toFixed(1)}%</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100">
                  <div className="text-xs text-gray-600">设备平均利用率</div>
                  <div className="mt-1 text-2xl font-bold text-amber-900">{(((results as any).nsga2.kpis?.avg_utilization || 0)*100).toFixed(1)}%</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-fuchsia-50 to-fuchsia-100">
                  <div className="text-xs text-gray-600">Makespan（天）</div>
                  <div className="mt-1 text-2xl font-bold text-fuchsia-900">{(results as any).nsga2.kpis?.makespan_days}</div>
                </div>
              </div>
              {(() => {
                const orders = (results as any).nsga2.orders || [];
                const tardyOrders = orders.filter((o: any) => (o?.tardiness ?? 0) > 0);
                const tardyCount = tardyOrders.length;
                const top5 = [...tardyOrders].sort((a, b) => (b.tardiness || 0) - (a.tardiness || 0)).slice(0, 5);
                const worst = top5[0];
                const avgTardiness = ((results as any).nsga2.kpis as any)?.avg_tardiness;
                const loadStd = ((results as any).nsga2.kpis as any)?.load_balance_std;
                return (
                  <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
                    <div className="flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-gray-700" />
                      <span className="font-medium text-gray-800">结果数据分析（NSGA-II）</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                      <div className="p-3 rounded-lg bg-gray-50">
                        <div className="text-xs text-gray-600">逾期订单数</div>
                        <div className="mt-1 text-xl font-bold text-gray-900">{tardyCount}</div>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50">
                        <div className="text-xs text-gray-600">平均拖期（天）</div>
                        <div className="mt-1 text-xl font-bold text-gray-900">{avgTardiness ?? '-'}</div>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50">
                        <div className="text-xs text-gray-600">最严重拖期订单</div>
                        <div className="mt-1 text-sm text-gray-900">{worst ? `${worst.order_id}（${worst.tardiness}天）` : '-'}</div>
                      </div>
                      <div className="p-3 rounded-lg bg-gray-50">
                        <div className="text-xs text-gray-600">负载均衡度（Std）</div>
                        <div className="mt-1 text-xl font-bold text-gray-900">{loadStd ?? '-'}</div>
                      </div>
                    </div>
                    {top5.length > 0 && (
                      <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                          <thead>
                            <tr className="bg-gray-50">
                              <th className="px-4 py-2 text-left text-gray-700">订单ID</th>
                              <th className="px-4 py-2 text-left text-gray-700">拖期（天）</th>
                              <th className="px-4 py-2 text-left text-gray-700">交期</th>
                              <th className="px-4 py-2 text-left text-gray-700">完工（天）</th>
                            </tr>
                          </thead>
                          <tbody>
                            {top5.map((o: any, idx: number) => (
                              <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                <td className="px-4 py-2 text-gray-800">{o.order_id}</td>
                                <td className="px-4 py-2 text-gray-800">{o.tardiness}</td>
                                <td className="px-4 py-2 text-gray-800">{o.due_date}</td>
                                <td className="px-4 py-2 text-gray-800">{o.completion_days}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })()}
              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-gray-700" />
                  <span className="font-medium text-gray-800">甘特图（NSGA-II）</span>
                </div>
                {(results as any).nsga2.gantt_html ? (
                  <iframe title="Gantt-NSGA2" className="w-full h-[560px]" srcDoc={(results as any).nsga2.gantt_html}></iframe>
                ) : (results as any).nsga2.gantt_url ? (
                  <iframe title="Gantt-NSGA2" className="w-full h-[560px]" src="/gantt_nsga2"></iframe>
                ) : (
                  <div className="p-6 text-gray-500">暂无甘特图数据</div>
                )}
              </div>
              <div className="flex flex-wrap gap-3">
                {(results as any).nsga2.schedule_csv_url ? (
                  <a className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-black flex items-center gap-2" download href={(results as any).nsga2.schedule_csv_url}>
                    <Download className="w-4 h-4" /> 下载排程结果 CSV（NSGA-II）
                  </a>
                ) : null}
                {(results as any).nsga2.gantt_url ? (
                  <a className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-2" download href={(results as any).nsga2.gantt_url}>
                    <Download className="w-4 h-4" /> 下载甘特图 HTML（NSGA-II）
                  </a>
                ) : null}
              </div>
            </div>
          )}

          {!results?.ga && results && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100">
                  <div className="text-xs text-gray-600">总加权拖期</div>
                  <div className="mt-1 text-2xl font-bold text-indigo-900">{results.kpis.total_weighted_tardiness}</div>
                </div>
                <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100">
                  <div className="text-xs text-gray-600">准时交付率</div>
                  <div className="mt-1 text-2xl font-bold text-emerald-900">{(results.kpis.on_time_delivery_rate*100).toFixed(1)}%</div>
                </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100">
                <div className="text-xs text-gray-600">设备平均利用率</div>
                <div className="mt-1 text-2xl font-bold text-amber-900">{(results.kpis.avg_utilization*100).toFixed(1)}%</div>
              </div>
              <div className="p-4 rounded-xl bg-gradient-to-br from-fuchsia-50 to-fuchsia-100">
                <div className="text-xs text-gray-600">Makespan（天）</div>
                <div className="mt-1 text-2xl font-bold text-fuchsia-900">{results.kpis.makespan_days}</div>
              </div>
            </div>
            {(() => {
              const orders = results.orders || [];
              const tardyOrders = orders.filter((o: any) => (o?.tardiness ?? 0) > 0);
              const tardyCount = tardyOrders.length;
              const top5 = [...tardyOrders].sort((a, b) => (b.tardiness || 0) - (a.tardiness || 0)).slice(0, 5);
              const worst = top5[0];
              const avgTardiness = (results.kpis as any)?.avg_tardiness;
              const loadStd = (results.kpis as any)?.load_balance_std;
              return (
                <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-gray-700" />
                    <span className="font-medium text-gray-800">结果数据分析</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="p-3 rounded-lg bg-gray-50">
                      <div className="text-xs text-gray-600">逾期订单数</div>
                      <div className="mt-1 text-xl font-bold text-gray-900">{tardyCount}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50">
                      <div className="text-xs text-gray-600">平均拖期（天）</div>
                      <div className="mt-1 text-xl font-bold text-gray-900">{avgTardiness ?? '-'}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50">
                      <div className="text-xs text-gray-600">最严重拖期订单</div>
                      <div className="mt-1 text-sm text-gray-900">{worst ? `${worst.order_id}（${worst.tardiness}天）` : '-'}</div>
                    </div>
                    <div className="p-3 rounded-lg bg-gray-50">
                      <div className="text-xs text-gray-600">负载均衡度（Std）</div>
                      <div className="mt-1 text-xl font-bold text-gray-900">{loadStd ?? '-'}</div>
                    </div>
                  </div>
                  {top5.length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50">
                            <th className="px-4 py-2 text-left text-gray-700">订单ID</th>
                            <th className="px-4 py-2 text-left text-gray-700">拖期（天）</th>
                            <th className="px-4 py-2 text-left text-gray-700">交期</th>
                            <th className="px-4 py-2 text-left text-gray-700">完工（天）</th>
                          </tr>
                        </thead>
                        <tbody>
                          {top5.map((o: any, idx: number) => (
                            <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                              <td className="px-4 py-2 text-gray-800">{o.order_id}</td>
                              <td className="px-4 py-2 text-gray-800">{o.tardiness}</td>
                              <td className="px-4 py-2 text-gray-800">{o.due_date}</td>
                              <td className="px-4 py-2 text-gray-800">{o.completion_days}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              );
            })()}

              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-gray-700" />
                  <span className="font-medium text-gray-800">订单完工情况</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-4 py-2 text-left text-gray-700">订单ID</th>
                        <th className="px-4 py-2 text-left text-gray-700">完工（天）</th>
                        <th className="px-4 py-2 text-left text-gray-700">交期</th>
                        <th className="px-4 py-2 text-left text-gray-700">拖期</th>
                        <th className="px-4 py-2 text-left text-gray-700">是否准时</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.orders.map((o, idx) => (
                        <tr key={idx} className={idx%2===0? 'bg-white':'bg-gray-50'}>
                          <td className="px-4 py-2 text-gray-800">{o.order_id}</td>
                          <td className="px-4 py-2 text-gray-800">{o.completion_days}</td>
                          <td className="px-4 py-2 text-gray-800">{o.due_date}</td>
                          <td className="px-4 py-2 text-gray-800">{o.tardiness}</td>
                          <td className="px-4 py-2">{o.on_time? <CheckCircle className="w-4 h-4 text-emerald-600"/> : <AlertCircle className="w-4 h-4 text-red-600"/>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="bg-white rounded-xl shadow-sm overflow-hidden">
                <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-gray-700" />
                  <span className="font-medium text-gray-800">甘特图{(results as any)?.algorithm ? `（${(results as any).algorithm}）` : ''}</span>
                </div>
                {results.gantt_html ? (
                  <iframe title="Gantt" className="w-full h-[560px]" srcDoc={results.gantt_html}></iframe>
                ) : results.gantt_url ? (
                  <iframe title="Gantt" className="w-full h-[560px]" src={(results as any)?.algorithm==='NSGA2'? '/gantt_nsga2' : '/gantt'}></iframe>
                ) : (
                  <div className="p-6 text-gray-500">暂无甘特图数据</div>
                )}
              </div>
              {/* 老版仿真结果文件与下载 */}
              <div className="space-y-3">
                <div className="flex flex-wrap gap-3">
                  {/* 排程结果 CSV 下载：兼容老版URL或现有字符串 */}
                  {results.schedule_csv_url ? (
                    <a className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-black flex items-center gap-2" download href={results.schedule_csv_url}>
                      <Download className="w-4 h-4" /> 下载排程结果 CSV
                    </a>
                  ) : results.schedule_csv ? (
                    <a className="px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-black flex items-center gap-2" download="schedule_results_GA.csv" href={URL.createObjectURL(new Blob([results.schedule_csv], { type: 'text/csv' }))}>
                      <Download className="w-4 h-4" /> 下载排程结果 CSV
                    </a>
                  ) : null}

                  {/* 甘特图 HTML 下载：兼容老版URL或现有字符串 */}
                  {results.gantt_html ? (
                    <a className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-2" download="schedule_gantt_GA.html" href={URL.createObjectURL(new Blob([results.gantt_html], { type: 'text/html' }))}>
                      <Download className="w-4 h-4" /> 下载甘特图 HTML
                    </a>
                  ) : results.gantt_url ? (
                    <a className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-2" download href={results.gantt_url}>
                      <Download className="w-4 h-4" /> 下载甘特图 HTML
                    </a>
                  ) : null}
                </div>

                {/* 已仿真生成的结果文件列表（老版样式） */}
                {results.files && results.files.length > 0 && (
                  <div className="bg-white rounded-xl shadow-sm">
                    <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-700" />
                      <span className="font-medium text-gray-800">已生成的仿真结果文件</span>
                    </div>
                    <ul className="divide-y">
                      {results.files.map((f) => (
                        <li key={f.name} className="flex items-center justify-between px-4 py-3 hover:bg-gray-50">
                          <span className="text-gray-700">{f.name}</span>
                          <a className="px-3 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-800 text-sm flex items-center gap-2" download href={f.url}>
                            <Download className="w-4 h-4" /> 下载
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// mount
const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(React.createElement(FFSSchedulerApp));
}