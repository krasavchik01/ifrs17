// Unified 3-Column View: IFRS 9 | IFRS 17 | Solvency

'use client';

import React from 'react';

interface UnifiedViewProps {
  result: any;
}

export const UnifiedView: React.FC<UnifiedViewProps> = ({ result }) => {
  const { ifrs9, ifrs17, solvency, compliance } = result.results;

  return (
    <div className="space-y-6">
      {/* Compliance Alert */}
      {compliance.status !== 'compliant' && (
        <div className={`rounded-lg border p-4 ${
          compliance.status === 'warning'
            ? 'bg-yellow-50 border-yellow-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <h4 className={`font-semibold ${
            compliance.status === 'warning' ? 'text-yellow-900' : 'text-red-900'
          }`}>
            {compliance.status === 'warning' ? 'Warnings Detected' : 'Compliance Issues'}
          </h4>
          <ul className={`text-sm mt-2 list-disc list-inside ${
            compliance.status === 'warning' ? 'text-yellow-800' : 'text-red-800'
          }`}>
            {compliance.warnings?.map((w: string, i: number) => (
              <li key={i}>{w}</li>
            ))}
            {compliance.errors?.map((e: string, i: number) => (
              <li key={`err-${i}`} className="font-medium">{e}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 3-Column Layout */}
      <div className="grid grid-cols-3 gap-6">
        {/* Column 1: IFRS 9 */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-bold text-slate-900 mb-4">МСФО 9</h3>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-600">Total ECL</p>
              <p className="text-2xl font-bold text-slate-900">
                {(ifrs9.total_ecl_kzt / 1e6).toFixed(1)}M
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">Coverage Ratio</p>
              <p className={`text-2xl font-bold ${
                ifrs9.coverage_ratio_pct >= 60 ? 'text-green-600' : 'text-red-600'
              }`}>
                {ifrs9.coverage_ratio_pct.toFixed(1)}%
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">Stage Breakdown</p>
              <div className="mt-2 space-y-1 text-sm">
                <p>Stage 1: {ifrs9.stage_breakdown_pct['Stage 1'].toFixed(1)}%</p>
                <p>Stage 2: {ifrs9.stage_breakdown_pct['Stage 2'].toFixed(1)}%</p>
                <p>Stage 3: {ifrs9.stage_breakdown_pct['Stage 3'].toFixed(1)}%</p>
              </div>
            </div>
          </div>
        </div>

        {/* Column 2: IFRS 17 */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-bold text-slate-900 mb-4">МСФО 17</h3>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-600">BEL</p>
              <p className="text-2xl font-bold text-slate-900">
                {(ifrs17.bel_kzt / 1e6).toFixed(1)}M
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">RA + CSM</p>
              <p className="text-lg font-bold text-slate-900">
                {((ifrs17.ra_kzt + ifrs17.csm_kzt) / 1e6).toFixed(1)}M
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">Liability</p>
              <p className="text-2xl font-bold text-slate-900">
                {(ifrs17.total_liability_kzt / 1e6).toFixed(1)}M
              </p>
            </div>
            {ifrs17.onerous_cohorts.length > 0 && (
              <div className="bg-red-50 p-2 rounded mt-3">
                <p className="text-xs text-red-900 font-semibold">
                  {ifrs17.onerous_cohorts.length} onerous cohort(s)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Column 3: Solvency */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <h3 className="text-lg font-bold text-slate-900 mb-4">АРФР R</h3>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-slate-600">Solvency Ratio</p>
              <p className={`text-2xl font-bold ${
                solvency.ratio_pct >= 100 ? 'text-green-600' : 'text-red-600'
              }`}>
                {solvency.ratio_pct.toFixed(1)}%
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">Own Funds / SCR</p>
              <p className="text-sm text-slate-600">
                {(solvency.own_funds_kzt / 1e9).toFixed(2)}B / {(solvency.scr_total_kzt / 1e9).toFixed(2)}B
              </p>
            </div>
            <div className="border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-600">Status</p>
              <p className={`text-lg font-bold ${
                solvency.is_compliant ? 'text-green-600' : 'text-red-600'
              }`}>
                {solvency.is_compliant ? 'COMPLIANT' : 'NON-COMPLIANT'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-6 py-3 text-left font-semibold text-slate-900">Metric</th>
              <th className="px-6 py-3 text-left font-semibold text-slate-900">МСФО 9</th>
              <th className="px-6 py-3 text-left font-semibold text-slate-900">МСФО 17</th>
              <th className="px-6 py-3 text-left font-semibold text-slate-900">АРФР R</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            <tr className="hover:bg-slate-50">
              <td className="px-6 py-3 text-slate-900 font-medium">Primary Value</td>
              <td className="px-6 py-3 font-mono text-slate-600">{(ifrs9.total_ecl_kzt / 1e6).toFixed(1)}M KZT</td>
              <td className="px-6 py-3 font-mono text-slate-600">{(ifrs17.bel_kzt / 1e6).toFixed(1)}M KZT</td>
              <td className="px-6 py-3 font-mono text-slate-600">{solvency.ratio_pct.toFixed(1)}%</td>
            </tr>
            <tr className="hover:bg-slate-50">
              <td className="px-6 py-3 text-slate-900 font-medium">Compliance</td>
              <td className="px-6 py-3">
                <span className={`text-sm font-medium ${
                  ifrs9.coverage_ratio_pct >= 60 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {ifrs9.coverage_ratio_pct >= 60 ? 'Pass' : 'Fail'}
                </span>
              </td>
              <td className="px-6 py-3">
                <span className={`text-sm font-medium ${
                  ifrs17.csm_kzt >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {ifrs17.csm_kzt >= 0 ? 'Pass' : 'Fail'}
                </span>
              </td>
              <td className="px-6 py-3">
                <span className={`text-sm font-medium ${
                  solvency.is_compliant ? 'text-green-600' : 'text-red-600'
                }`}>
                  {solvency.is_compliant ? 'Pass' : 'Fail'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
};
