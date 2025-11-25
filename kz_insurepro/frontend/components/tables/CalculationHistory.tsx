// Calculation History Table

'use client';

import React from 'react';

interface CalculationHistoryProps {
  results: any[];
  onSelectResult: (result: any) => void;
}

export const CalculationHistory: React.FC<CalculationHistoryProps> = ({
  results,
  onSelectResult,
}) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="px-6 py-3 text-left font-semibold text-slate-900">Date</th>
            <th className="px-6 py-3 text-left font-semibold text-slate-900">Portfolio</th>
            <th className="px-6 py-3 text-left font-semibold text-slate-900">Status</th>
            <th className="px-6 py-3 text-right font-semibold text-slate-900">ECL</th>
            <th className="px-6 py-3 text-right font-semibold text-slate-900">Ratio</th>
            <th className="px-6 py-3 text-center font-semibold text-slate-900">Time</th>
            <th className="px-6 py-3 text-center font-semibold text-slate-900">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {results.map((result, idx) => (
            <tr key={idx} className="hover:bg-slate-50 transition">
              <td className="px-6 py-3 text-slate-600 font-mono text-xs">
                {new Date(result.calculation_date).toLocaleDateString()}
              </td>
              <td className="px-6 py-3 text-slate-900">
                <div className="font-medium">{result.job_id.slice(0, 8)}...</div>
                <p className="text-xs text-slate-500">{result.processing_time_ms}ms</p>
              </td>
              <td className="px-6 py-3">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  result.results.compliance.status === 'compliant'
                    ? 'bg-green-100 text-green-800'
                    : result.results.compliance.status === 'warning'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {result.results.compliance.status.toUpperCase()}
                </span>
              </td>
              <td className="px-6 py-3 text-right font-mono text-slate-900">
                {(result.results.ifrs9.total_ecl_kzt / 1e6).toFixed(1)}M
              </td>
              <td className="px-6 py-3 text-right">
                <span className={`font-medium ${
                  result.results.solvency.ratio_pct >= 100
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}>
                  {result.results.solvency.ratio_pct.toFixed(1)}%
                </span>
              </td>
              <td className="px-6 py-3 text-center text-slate-600 font-mono">
                {result.processing_time_ms}ms
              </td>
              <td className="px-6 py-3 text-center">
                <button
                  onClick={() => onSelectResult(result)}
                  className="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded transition"
                >
                  View
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
