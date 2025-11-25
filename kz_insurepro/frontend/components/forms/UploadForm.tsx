// Portfolio Upload Form with Excel/CSV Parser

'use client';

import React, { useState } from 'react';
import Papa from 'papaparse';

interface UploadFormProps {
  onSubmit: (payload: any) => void;
  loading: boolean;
}

export const UploadForm: React.FC<UploadFormProps> = ({ onSubmit, loading }) => {
  const [tenantId, setTenantId] = useState('demo_tenant_kz');
  const [portfolioName, setPortfolioName] = useState('Q4 2024 Portfolio');
  const [loansFile, setLoansFile] = useState<File | null>(null);
  const [contractsFile, setContractsFile] = useState<File | null>(null);
  const [inflation, setInflation] = useState(0.085);
  const [riskFreeRate, setRiskFreeRate] = useState(0.05);
  const [ownFunds, setOwnFunds] = useState(2e12);
  const [errors, setErrors] = useState<string[]>([]);

  const parseCSV = (file: File): Promise<any[]> => {
    return new Promise((resolve, reject) => {
      Papa.parse(file, {
        complete: (results: any) => {
          if (results.errors.length > 0) {
            reject(new Error('CSV parsing error: ' + results.errors[0].message));
          } else {
            resolve(results.data);
          }
        },
        error: (error: Error) => reject(error),
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
      });
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'loans' | 'contracts') => {
    const file = e.target.files?.[0];
    if (file) {
      if (type === 'loans') {
        setLoansFile(file);
      } else {
        setContractsFile(file);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors([]);

    try {
      let loans: any[] = [];
      let contracts: any[] = [];

      // Parse loans
      if (loansFile) {
        const parsedLoans = await parseCSV(loansFile);
        loans = parsedLoans.map((row) => ({
          id: row.id || `L${Math.random().toString(36).substr(2, 9)}`,
          ead: parseFloat(row.ead || row.Exposure) || 500e6,
          pd: parseFloat(row.pd || row.ProbabilityOfDefault) || 0.05,
          lgd: parseFloat(row.lgd || row.LossGivenDefault) || 0.4,
          stage: parseInt(row.stage || row.Stage) || 1,
          days_past_due: parseInt(row.days_past_due || row.DaysPastDue) || 0,
          sector: row.sector || row.Sector || 'retail',
          maturity_years: parseInt(row.maturity_years || row.MaturityYears) || 3,
        }));
      }

      // Parse contracts
      if (contractsFile) {
        const parsedContracts = await parseCSV(contractsFile);
        contracts = parsedContracts.map((row) => ({
          id: row.id || `C${Math.random().toString(36).substr(2, 9)}`,
          type: row.type || row.ContractType || 'life',
          inception_date: row.inception_date || row.InceptionDate || new Date().toISOString().split('T')[0],
          coverage_units: parseFloat(row.coverage_units || row.CoverageUnits) || 2e7,
          annual_premium: parseFloat(row.annual_premium || row.AnnualPremium) || 100e6,
          annual_claims_expected: parseFloat(row.annual_claims_expected || row.Claims) || 50e6,
          annual_expenses: parseFloat(row.annual_expenses || row.Expenses) || 5e6,
          discount_rate: parseFloat(row.discount_rate || row.DiscountRate) || 0.05,
          contract_term_years: parseInt(row.contract_term_years || row.TermYears) || 10,
          cohort: row.cohort || row.Cohort || `${new Date().getFullYear()}-cohort`,
        }));
      }

      // Validate
      if (loans.length === 0 && contracts.length === 0) {
        setErrors(['Please upload at least loans or contracts file']);
        return;
      }

      // Build payload
      const payload = {
        tenant_id: tenantId,
        portfolio_id: portfolioName.toLowerCase().replace(/\s+/g, '-'),
        portfolio_name: portfolioName,
        calculation_date: new Date().toISOString().split('T')[0],
        inflation_rate: inflation,
        risk_free_rate: riskFreeRate,
        base_currency: 'KZT',
        loans,
        contracts,
        risks: {
          market_volatility: 0.15,
          credit_exposure: 5e12,
          credit_default_rate: 0.05,
          operational_loss_rate: 0.02,
          own_funds: ownFunds,
        },
      };

      onSubmit(payload);
    } catch (error: any) {
      setErrors([error.message || 'Error processing files']);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Calculate Compliance</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Error Messages */}
        {errors.length > 0 && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            {errors.map((error, idx) => (
              <p key={idx} className="text-red-900 text-sm">{error}</p>
            ))}
          </div>
        )}

        {/* Portfolio Settings */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Tenant ID
            </label>
            <input
              type="text"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Portfolio Name
            </label>
            <input
              type="text"
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Market Parameters */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Inflation Rate (%)
            </label>
            <input
              type="number"
              step={0.001}
              value={inflation * 100}
              onChange={(e) => setInflation(parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 mt-1">NaRB 2024: 8.5%</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Risk-Free Rate (%)
            </label>
            <input
              type="number"
              step={0.001}
              value={riskFreeRate * 100}
              onChange={(e) => setRiskFreeRate(parseFloat(e.target.value) / 100)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-slate-500 mt-1">KASE 10Y: 5.0%</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-900 mb-2">
              Own Funds (Billions KZT)
            </label>
            <input
              type="number"
              value={ownFunds / 1e9}
              onChange={(e) => setOwnFunds(parseFloat(e.target.value) * 1e9)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* File Uploads */}
        <div className="grid grid-cols-2 gap-4">
          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-400 transition">
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => handleFileChange(e, 'loans')}
              className="hidden"
              id="loans-upload"
            />
            <label htmlFor="loans-upload" className="cursor-pointer">
              <p className="text-sm font-medium text-slate-900">Loans Portfolio (CSV/XLSX)</p>
              <p className="text-xs text-slate-600 mt-1">
                {loansFile ? loansFile.name : 'Click to upload or drag and drop'}
              </p>
              <p className="text-xs text-slate-500 mt-2">
                Columns: id, ead, pd, lgd, stage, sector, maturity_years
              </p>
            </label>
          </div>

          <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 text-center hover:border-blue-400 transition">
            <input
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => handleFileChange(e, 'contracts')}
              className="hidden"
              id="contracts-upload"
            />
            <label htmlFor="contracts-upload" className="cursor-pointer">
              <p className="text-sm font-medium text-slate-900">Insurance Contracts (CSV/XLSX)</p>
              <p className="text-xs text-slate-600 mt-1">
                {contractsFile ? contractsFile.name : 'Click to upload or drag and drop'}
              </p>
              <p className="text-xs text-slate-500 mt-2">
                Columns: id, type, inception_date, annual_premium, cohort
              </p>
            </label>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 px-4 rounded-lg font-medium transition ${
            loading
              ? 'bg-slate-300 text-slate-600 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'
          }`}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
              Calculating...
            </span>
          ) : (
            'Calculate Compliance'
          )}
        </button>

        {/* Sample Data Info */}
        <div className="bg-blue-50 rounded-lg border border-blue-200 p-4">
          <h4 className="text-sm font-semibold text-blue-900">Sample Data Format</h4>
          <p className="text-xs text-blue-800 mt-2">
            Create CSV files with headers matching the column names above. Use decimal formats (e.g., 0.05 for 5%).
          </p>
          <pre className="bg-blue-100 text-blue-900 text-xs p-2 rounded mt-2 overflow-x-auto">
{`id,ead,pd,lgd,stage,sector,maturity_years
L001,500000000,0.05,0.4,1,retail,3
L002,300000000,0.08,0.45,2,corporate,5`}
          </pre>
        </div>
      </form>
    </div>
  );
};
