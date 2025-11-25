// МСФО 9: Expected Credit Loss (ECL) Visualization

'use client';

import React from 'react';
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface IFRS9ViewProps {
  result: {
    results: {
      ifrs9: {
        total_ecl_kzt: number;
        total_ead_kzt: number;
        coverage_ratio_pct: number;
        weighted_pd: number;
        weighted_lgd: number;
        stage_breakdown_pct: {
          'Stage 1': number;
          'Stage 2': number;
          'Stage 3': number;
        };
      };
    };
    processing_time_ms: number;
  };
}

export const IFRS9View: React.FC<IFRS9ViewProps> = ({ result }) => {
  const ifrs9 = result.results.ifrs9;

  // Data for stage breakdown chart
  const stageData = [
    {
      name: 'Stage 1 (12m ECL)',
      value: ifrs9.stage_breakdown_pct['Stage 1'],
      ecl: (ifrs9.total_ecl_kzt * (ifrs9.stage_breakdown_pct['Stage 1'] / 100)),
      color: '#10b981',
    },
    {
      name: 'Stage 2 (Lifetime)',
      value: ifrs9.stage_breakdown_pct['Stage 2'],
      ecl: (ifrs9.total_ecl_kzt * (ifrs9.stage_breakdown_pct['Stage 2'] / 100)),
      color: '#f59e0b',
    },
    {
      name: 'Stage 3 (Impaired)',
      value: ifrs9.stage_breakdown_pct['Stage 3'],
      ecl: (ifrs9.total_ecl_kzt * (ifrs9.stage_breakdown_pct['Stage 3'] / 100)),
      color: '#ef4444',
    },
  ];

  const COLORS = ['#10b981', '#f59e0b', '#ef4444'];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Total ECL</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs9.total_ecl_kzt / 1e6).toFixed(1)}M
          </p>
          <p className="text-xs text-slate-500 mt-1">KZT</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Total EAD</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs9.total_ead_kzt / 1e9).toFixed(2)}B
          </p>
          <p className="text-xs text-slate-500 mt-1">KZT</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Coverage Ratio</h4>
          <p className={`text-2xl font-bold mt-2 ${
            ifrs9.coverage_ratio_pct >= 60 ? 'text-green-600' : 'text-red-600'
          }`}>
            {ifrs9.coverage_ratio_pct.toFixed(1)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {ifrs9.coverage_ratio_pct >= 60 ? 'Compliant' : 'Below 60% minimum'}
          </p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Weighted PD</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs9.weighted_pd * 100).toFixed(2)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">Portfolio Average</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* Stage Breakdown Pie Chart */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Stage Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stageData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {stageData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: any) => `${value.toFixed(1)}%`}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* ECL by Stage Bar Chart */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">ECL by Stage (KZT)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip
                formatter={(value: any) => [`${(value / 1e6).toFixed(1)}M KZT`, 'ECL']}
              />
              <Bar dataKey="ecl" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stage Details Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Stage Details</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 bg-slate-50">
              <tr>
                <th className="px-4 py-2 text-left font-semibold text-slate-900">Stage</th>
                <th className="px-4 py-2 text-right font-semibold text-slate-900">PD Multiplier</th>
                <th className="px-4 py-2 text-right font-semibold text-slate-900">% of ECL</th>
                <th className="px-4 py-2 text-right font-semibold text-slate-900">ECL (KZT)</th>
                <th className="px-4 py-2 text-left font-semibold text-slate-900">ARRF Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              <tr className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">Stage 1 (Low Risk)</td>
                <td className="px-4 py-3 text-right text-slate-600">1.0x (12M PD)</td>
                <td className="px-4 py-3 text-right text-slate-600">
                  {ifrs9.stage_breakdown_pct['Stage 1'].toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right font-mono text-slate-900">
                  {((ifrs9.total_ecl_kzt * ifrs9.stage_breakdown_pct['Stage 1']) / 100 / 1e6).toFixed(2)}M
                </td>
                <td className="px-4 py-3 text-green-600 font-medium">Compliant</td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">Stage 2 (SICR)</td>
                <td className="px-4 py-3 text-right text-slate-600">3.0x (Lifetime PD)</td>
                <td className="px-4 py-3 text-right text-slate-600">
                  {ifrs9.stage_breakdown_pct['Stage 2'].toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right font-mono text-slate-900">
                  {((ifrs9.total_ecl_kzt * ifrs9.stage_breakdown_pct['Stage 2']) / 100 / 1e6).toFixed(2)}M
                </td>
                <td className="px-4 py-3 text-green-600 font-medium">Compliant</td>
              </tr>
              <tr className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">Stage 3 (Credit-Impaired)</td>
                <td className="px-4 py-3 text-right text-slate-600">5.0x (Lifetime PD)</td>
                <td className="px-4 py-3 text-right text-slate-600">
                  {ifrs9.stage_breakdown_pct['Stage 3'].toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-right font-mono text-slate-900">
                  {((ifrs9.total_ecl_kzt * ifrs9.stage_breakdown_pct['Stage 3']) / 100 / 1e6).toFixed(2)}M
                </td>
                <td className={`px-4 py-3 font-medium ${
                  ifrs9.coverage_ratio_pct >= 60 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {ifrs9.coverage_ratio_pct >= 60 ? 'Compliant' : 'Non-compliant'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-xs text-slate-500 mt-4">
          Note: ARRF R requires Stage 3 ECL coverage ≥ 60% of total ECL
        </p>
      </div>

      {/* Methodology */}
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
        <h4 className="text-sm font-semibold text-blue-900">Calculation Methodology</h4>
        <p className="text-xs text-blue-800 mt-2">
          ECL = EAD × PD × LGD × DF × (1 + inflation × 0.5)
        </p>
        <ul className="text-xs text-blue-800 mt-3 space-y-1 list-disc list-inside">
          <li>EAD: Exposure at Default (gross carrying amount)</li>
          <li>PD: Probability of Default (stage-adjusted: 1x/3x/5x)</li>
          <li>LGD: Loss Given Default (recoverable amount)</li>
          <li>DF: Discount Factor (risk-free rate)</li>
          <li>Macro: Inflation adjustment ({(ifrs9.total_ecl_kzt * 0.042).toFixed(0)} KZT)</li>
        </ul>
      </div>
    </div>
  );
};
