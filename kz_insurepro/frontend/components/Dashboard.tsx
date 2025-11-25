// KZ-InsurePro: Full-Suite Dashboard (Phase 2B)
// Unified IFRS 9/17/Solvency visualization with Recharts

'use client';

import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@radix-ui/react-tabs';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import axios from 'axios';
import { IFRS9View } from './views/IFRS9View';
import { IFRS17View } from './views/IFRS17View';
import { SolvencyView } from './views/SolvencyView';
import { UnifiedView } from './views/UnifiedView';
import { UploadForm } from './forms/UploadForm';
import { CalculationHistory } from './tables/CalculationHistory';

interface CalculationResult {
  status: string;
  job_id: string;
  calculation_date: string;
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
    ifrs17: {
      bel_kzt: number;
      ra_kzt: number;
      csm_kzt: number;
      total_liability_kzt: number;
      onerous_cohorts: string[];
    };
    solvency: {
      mmp_kzt: number;
      own_funds_kzt: number;
      ratio_pct: number;
      is_compliant: boolean;
      scr_total_kzt: number;
    };
    compliance: {
      status: string;
      warnings: string[];
      errors: string[];
    };
  };
  processing_time_ms: number;
}

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState('unified');
  const [calculationResult, setCalculationResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<CalculationResult[]>([]);

  // Fetch calculation history on mount
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        // TODO: Implement endpoint in Phase 2
        // const response = await axios.get('/api/calculations/history');
        // setHistory(response.data);
      } catch (err) {
        console.error('Error fetching history:', err);
      }
    };
    fetchHistory();
  }, []);

  const handleCalculationSubmit = async (payload: any) => {
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('/api/calculate/suite', payload);
      setCalculationResult(response.data);

      // Add to history
      setHistory([response.data, ...history.slice(0, 9)]);

      // Auto-switch to unified view on success
      if (response.data.status !== 'error') {
        setActiveTab('unified');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Calculation failed');
      console.error('Calculation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-slate-900">
                KZ-InsurePro Dashboard
              </h1>
              <p className="text-sm text-slate-600 mt-1">
                МСФО 9 (ECL) • МСФО 17 (Insurance Liabilities) • АРФР R (Solvency)
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500">Powered by Phase 1 Core Engine</p>
              <p className="text-xs font-mono text-slate-400">
                {calculationResult?.job_id.slice(0, 8) || 'Ready'}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-900 font-semibold">Error: {error}</p>
          </div>
        )}

        {/* Compliance Status Bar */}
        {calculationResult && (
          <div className="mb-6 p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-sm font-semibold text-slate-700">Last Calculation</h3>
                <p className="text-xs text-slate-500">{calculationResult.calculation_date}</p>
              </div>
              <div className="flex gap-6">
                <div className="text-center">
                  <p className="text-xs text-slate-600">Status</p>
                  <p className={`text-lg font-bold ${
                    calculationResult.results.compliance.status === 'compliant' ? 'text-green-600' :
                    calculationResult.results.compliance.status === 'warning' ? 'text-yellow-600' :
                    'text-red-600'
                  }`}>
                    {calculationResult.results.compliance.status.toUpperCase()}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-600">Processing</p>
                  <p className="text-lg font-bold text-slate-900">{calculationResult.processing_time_ms}ms</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-slate-600">Issues</p>
                  <p className="text-lg font-bold text-slate-900">
                    {calculationResult.results.compliance.errors.length + calculationResult.results.compliance.warnings.length}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid grid-cols-5 gap-2 bg-white p-1 rounded-lg border border-slate-200 shadow-sm">
            <TabsTrigger value="upload" className="px-4 py-2 text-sm font-medium rounded-md data-[state=active]:bg-blue-100 data-[state=active]:text-blue-900 hover:bg-slate-100">
              Upload
            </TabsTrigger>
            <TabsTrigger value="unified" className="px-4 py-2 text-sm font-medium rounded-md data-[state=active]:bg-blue-100 data-[state=active]:text-blue-900 hover:bg-slate-100">
              Unified View
            </TabsTrigger>
            <TabsTrigger value="ifrs9" className="px-4 py-2 text-sm font-medium rounded-md data-[state=active]:bg-blue-100 data-[state=active]:text-blue-900 hover:bg-slate-100">
              МСФО 9 (ECL)
            </TabsTrigger>
            <TabsTrigger value="ifrs17" className="px-4 py-2 text-sm font-medium rounded-md data-[state=active]:bg-blue-100 data-[state=active]:text-blue-900 hover:bg-slate-100">
              МСФО 17
            </TabsTrigger>
            <TabsTrigger value="solvency" className="px-4 py-2 text-sm font-medium rounded-md data-[state=active]:bg-blue-100 data-[state=active]:text-blue-900 hover:bg-slate-100">
              АРФР R
            </TabsTrigger>
          </TabsList>

          {/* Upload Tab */}
          <TabsContent value="upload" className="space-y-6">
            <UploadForm onSubmit={handleCalculationSubmit} loading={loading} />
            {history.length > 0 && (
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">Calculation History</h3>
                <CalculationHistory results={history} onSelectResult={setCalculationResult} />
              </div>
            )}
          </TabsContent>

          {/* Unified View Tab */}
          <TabsContent value="unified">
            {calculationResult && <UnifiedView result={calculationResult} />}
            {!calculationResult && (
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
                <p className="text-slate-600">No calculation results yet. Upload portfolio data to begin.</p>
              </div>
            )}
          </TabsContent>

          {/* IFRS 9 Tab */}
          <TabsContent value="ifrs9">
            {calculationResult && <IFRS9View result={calculationResult} />}
            {!calculationResult && (
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
                <p className="text-slate-600">No IFRS 9 results available.</p>
              </div>
            )}
          </TabsContent>

          {/* IFRS 17 Tab */}
          <TabsContent value="ifrs17">
            {calculationResult && <IFRS17View result={calculationResult} />}
            {!calculationResult && (
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
                <p className="text-slate-600">No IFRS 17 results available.</p>
              </div>
            )}
          </TabsContent>

          {/* Solvency Tab */}
          <TabsContent value="solvency">
            {calculationResult && <SolvencyView result={calculationResult} />}
            {!calculationResult && (
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-12 text-center">
                <p className="text-slate-600">No solvency results available.</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-xs text-slate-500">
          <p>KZ-InsurePro Phase 2B • Built for Kazakhstan's IFRS Journey • ARRF Compliant</p>
        </div>
      </footer>
    </div>
  );
};
