// МСФО 17: Insurance Contract Liabilities

'use client';

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface IFRS17ViewProps {
  result: {
    results: {
      ifrs17: {
        bel_kzt: number;
        ra_kzt: number;
        csm_kzt: number;
        total_liability_kzt: number;
        onerous_cohorts: string[];
      };
    };
  };
}

export const IFRS17View: React.FC<IFRS17ViewProps> = ({ result }) => {
  const ifrs17 = result.results.ifrs17;

  const liabilityData = [
    { name: 'BEL', value: ifrs17.bel_kzt / 1e6, color: '#3b82f6' },
    { name: 'RA', value: ifrs17.ra_kzt / 1e6, color: '#f59e0b' },
    { name: 'CSM', value: Math.max(ifrs17.csm_kzt / 1e6, 0), color: '#10b981' },
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">BEL</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs17.bel_kzt / 1e6).toFixed(1)}M
          </p>
          <p className="text-xs text-slate-500 mt-1">Best Estimate Liability</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">RA</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs17.ra_kzt / 1e6).toFixed(1)}M
          </p>
          <p className="text-xs text-slate-500 mt-1">Risk Adjustment</p>
        </div>

        <div className={`rounded-lg border shadow-sm p-6 ${
          ifrs17.csm_kzt > 0
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <h4 className={`text-xs font-semibold uppercase ${
            ifrs17.csm_kzt > 0 ? 'text-green-600' : 'text-red-600'
          }`}>CSM</h4>
          <p className={`text-2xl font-bold mt-2 ${
            ifrs17.csm_kzt > 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {(ifrs17.csm_kzt / 1e6).toFixed(1)}M
          </p>
          <p className="text-xs text-slate-500 mt-1">Service Margin</p>
        </div>

        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h4 className="text-xs font-semibold text-slate-600 uppercase">Liability</h4>
          <p className="text-2xl font-bold text-slate-900 mt-2">
            {(ifrs17.total_liability_kzt / 1e6).toFixed(1)}M
          </p>
          <p className="text-xs text-slate-500 mt-1">BEL + RA</p>
        </div>
      </div>

      {/* Components Chart */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-4">Liability Components</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={liabilityData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis label={{ value: 'KZT (Millions)', angle: -90, position: 'insideLeft' }} />
            <Tooltip formatter={(value: any) => `${value.toFixed(1)}M KZT`} />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Onerous Contracts Alert */}
      {ifrs17.onerous_cohorts.length > 0 && (
        <div className="bg-red-50 rounded-lg border border-red-200 p-4">
          <h4 className="text-sm font-semibold text-red-900">Onerous Contracts Detected</h4>
          <p className="text-sm text-red-800 mt-2">
            The following cohorts have CSM &lt; 0 (loss-making):
          </p>
          <ul className="list-disc list-inside text-sm text-red-800 mt-2">
            {ifrs17.onerous_cohorts.map((cohort) => (
              <li key={cohort}>{cohort}</li>
            ))}
          </ul>
          <p className="text-xs text-red-700 mt-2">
            CSM is set to 0 for onerous contracts per IFRS 17.
          </p>
        </div>
      )}

      {/* Methodology */}
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
        <h4 className="text-sm font-semibold text-blue-900">IFRS 17 Measurement Model (GMM)</h4>
        <ul className="text-xs text-blue-800 mt-2 space-y-1 list-disc list-inside">
          <li><strong>BEL:</strong> PV(Claims + Expenses) escalated for inflation</li>
          <li><strong>RA:</strong> 75th percentile × claim_volatility (uncertainty margin)</li>
          <li><strong>CSM:</strong> PV(Premiums) - BEL - RA (profit recognition)</li>
          <li><strong>Liability:</strong> BEL + RA (no CSM on balance sheet)</li>
        </ul>
      </div>
    </div>
  );
};
