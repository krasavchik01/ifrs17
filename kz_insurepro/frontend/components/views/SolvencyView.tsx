// АРФР R: Solvency Capital Requirement (SCR) Visualization

'use client';

import React from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

interface SolvencyViewProps {
  result: {
    results: {
      solvency: {
        mmp_kzt: number;
        own_funds_kzt: number;
        ratio_pct: number;
        is_compliant: boolean;
        scr_total_kzt: number;
      };
    };
  };
}

export const SolvencyView: React.FC<SolvencyViewProps> = ({ result }) => {
  const solvency = result.results.solvency;

  // Data for SCR waterfall (simplified representation)
  const scrWaterfallData = [
    {
      name: 'Market SCR',
      value: (solvency.scr_total_kzt * 0.6) / 1e9,
      color: '#ef4444',
    },
    {
      name: 'Credit SCR',
      value: (solvency.scr_total_kzt * 0.35) / 1e9,
      color: '#f59e0b',
    },
    {
      name: 'Op SCR',
      value: (solvency.scr_total_kzt * 0.05) / 1e9,
      color: '#eab308',
    },
  ];

  // Data for ratio gauge
  const ratioPercentage = Math.min(solvency.ratio_pct, 200);

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">SCR Total</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(solvency.scr_total_kzt / 1e9).toFixed(2)}B
          </p>
          <p className="text-xs text-slate-500 mt-1">KZT</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Own Funds</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(solvency.own_funds_kzt / 1e9).toFixed(2)}B
          </p>
          <p className="text-xs text-slate-500 mt-1">KZT</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">MMP</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(solvency.mmp_kzt / 1e9).toFixed(2)}B
          </p>
          <p className="text-xs text-slate-500 mt-1">Minimum Capital</p>
        </div>

        <div className={`rounded-lg border shadow-sm p-6 ${
          solvency.is_compliant
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <h4 className={`text-xs font-semibold uppercase ${
            solvency.is_compliant ? 'text-green-600' : 'text-red-600'
          }`}>
            Status
          </h4>
          <p className={`text-2xl font-bold mt-2 ${
            solvency.is_compliant ? 'text-green-600' : 'text-red-600'
          }`}>
            {solvency.is_compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Ratio &gt;= 100% required
          </p>
        </div>
      </div>

      {/* Solvency Ratio Gauge */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-6">Solvency Ratio</h3>
          <div className="space-y-4">
            {/* Ratio Bar */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium text-slate-900">
                  Own Funds / SCR = {solvency.ratio_pct.toFixed(1)}%
                </span>
                <span className={`text-sm font-bold ${
                  solvency.ratio_pct >= 100 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {solvency.ratio_pct >= 100 ? 'Compliant' : 'Below minimum'}
                </span>
              </div>
              <div className="w-full h-8 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                <div
                  className={`h-full transition-all ${
                    solvency.ratio_pct >= 100 ? 'bg-green-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(ratioPercentage, 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-xs text-slate-500 mt-2">
                <span>0%</span>
                <span>100% (Minimum)</span>
                <span>200%</span>
              </div>
            </div>

            {/* Detailed Calculation */}
            <div className="bg-slate-50 rounded-lg p-4 mt-6">
              <h4 className="text-sm font-semibold text-slate-900 mb-3">Calculation Details</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-600">Own Funds (Total Capital):</span>
                  <span className="font-mono text-slate-900">
                    {(solvency.own_funds_kzt / 1e9).toFixed(2)}B KZT
                  </span>
                </div>
                <div className="border-t border-slate-200 pt-2 flex justify-between font-semibold">
                  <span className="text-slate-900">÷ SCR (Total):</span>
                  <span className="font-mono text-slate-900">
                    {(solvency.scr_total_kzt / 1e9).toFixed(2)}B KZT
                  </span>
                </div>
                <div className="border-t border-slate-200 pt-2 flex justify-between">
                  <span className="text-slate-900 font-bold">= Solvency Ratio:</span>
                  <span className={`font-mono font-bold text-lg ${
                    solvency.ratio_pct >= 100 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {solvency.ratio_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Compliance Checklist */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">Compliance Checklist</h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                solvency.ratio_pct >= 100
                  ? 'bg-green-100 text-green-600'
                  : 'bg-red-100 text-red-600'
              }`}>
                <span className="text-sm font-bold">
                  {solvency.ratio_pct >= 100 ? '✓' : '✗'}
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">Ratio &gt;= 100%</p>
                <p className="text-xs text-slate-500">
                  Own funds must cover SCR
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 bg-slate-100 text-slate-400">
                <span className="text-sm font-bold">→</span>
              </div>
              <div>
                <p className="text-sm font-medium text-slate-600">Minimum: &gt;=100%</p>
                <p className="text-xs text-slate-500">
                  Current: {solvency.ratio_pct.toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* SCR Components */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">SCR Components Breakdown</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={scrWaterfallData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis label={{ value: 'KZT (Billions)', angle: -90, position: 'insideLeft' }} />
            <Tooltip
              formatter={(value: any) => [`${value.toFixed(2)}B KZT`, 'SCR']}
            />
            <Bar dataKey="value" fill="#3b82f6">
              {scrWaterfallData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ARRF R Methodology */}
      <div className="bg-amber-50 rounded-lg border border-amber-200 p-4">
        <h4 className="text-sm font-semibold text-amber-900">ARRF R Methodology</h4>
        <p className="text-xs text-amber-800 mt-2">
          SCR = √(Market² + Credit² + Op² + 2×Correlations)
        </p>
        <ul className="text-xs text-amber-800 mt-3 space-y-1 list-disc list-inside">
          <li><strong>Market SCR:</strong> volatility × own_funds × 2.576 (99.5% VaR)</li>
          <li><strong>Credit SCR:</strong> max(exposure × default × 0.45, ECL × 0.5)</li>
          <li><strong>Op SCR:</strong> (CSM proxy / 0.15) × loss_rate</li>
          <li><strong>Correlation:</strong> 25% between modules</li>
          <li><strong>Minimum Ratio:</strong> Own Funds / SCR ≥ 1.0 (100%)</li>
        </ul>
      </div>

      {/* Stress Scenarios */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Stress Scenarios</h3>
        <div className="grid grid-cols-3 gap-4">
          {[
            { name: 'Base Case', ratio: solvency.ratio_pct, stress: 'Current parameters' },
            { name: 'Inflation +5%', ratio: solvency.ratio_pct * 0.98, stress: 'Conservative assumption' },
            { name: 'Rate Shock', ratio: solvency.ratio_pct * 0.95, stress: 'Worst case 250bps' },
          ].map((scenario, idx) => (
            <div key={idx} className="bg-slate-50 rounded-lg p-4">
              <h5 className="text-sm font-semibold text-slate-900">{scenario.name}</h5>
              <p className={`text-2xl font-bold mt-2 ${
                scenario.ratio >= 100 ? 'text-green-600' : 'text-red-600'
              }`}>
                {scenario.ratio.toFixed(1)}%
              </p>
              <p className="text-xs text-slate-500 mt-2">{scenario.stress}</p>
              <p className={`text-xs font-medium mt-1 ${
                scenario.ratio >= 100 ? 'text-green-600' : 'text-red-600'
              }`}>
                {scenario.ratio >= 100 ? 'Compliant' : 'Non-compliant'}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
