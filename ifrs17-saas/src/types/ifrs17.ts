// IFRS 17 Core Types

export enum MeasurementModel {
  GMM = 'GMM', // General Measurement Model
  PAA = 'PAA', // Premium Allocation Approach
  VFA = 'VFA', // Variable Fee Approach
}

export enum ContractType {
  LIFE = 'life',
  NON_LIFE = 'non-life',
  REINSURANCE = 'reinsurance',
}

export enum Profitability {
  ONEROUS = 'onerous',
  PROFITABLE = 'profitable',
}

export enum CashFlowType {
  PREMIUM = 'premium',
  CLAIM = 'claim',
  EXPENSE = 'expense',
  COMMISSION = 'commission',
  TAX = 'tax',
}

export enum FlowDirection {
  INFLOW = 'inflow',
  OUTFLOW = 'outflow',
}

export interface CSMRollForward {
  openingBalance: number;
  newBusiness: number;
  interestAccretion: number;
  experienceAdjustments: number;
  estimateChanges: number;
  releaseForService: number;
  foreignExchange: number;
  other: number;
  closingBalance: number;
}

export interface RiskAdjustmentCalculation {
  method: 'confidence_level' | 'cost_of_capital' | 'quantile';
  confidenceLevel?: number;
  insuranceRisk: number;
  financialRisk: number;
  operationalRisk: number;
  total: number;
}

export interface FulfilmentCashFlows {
  presentValueOfFutureCashFlows: number;
  riskAdjustment: number;
  total: number;
}

export interface LiabilityComponents {
  liabilityForRemainingCoverage: number; // LRC
  liabilityForIncurredClaims: number; // LIC
  contractualServiceMargin: number; // CSM
  total: number;
}

export interface DiscountRateCurve {
  currency: string;
  date: Date;
  rates: Array<{
    period: number; // in years
    rate: number; // as decimal, e.g., 0.05 for 5%
  }>;
}

export interface ActuarialAssumptions {
  mortalityRate?: number;
  lapseRate?: number;
  expenseInflation?: number;
  claimInflation?: number;
  discountRate: number;
}

export interface ContractGrouping {
  productLine: string;
  issueYear: number;
  profitability: Profitability;
  measurementModel: MeasurementModel;
}

// Dashboard & Analytics Types
export interface DashboardMetrics {
  totalContracts: number;
  totalCSM: number;
  totalLiabilities: number;
  netIncome: number;
  profitMargin: number;
  averageRiskAdjustment: number;
}

export interface CSMTrend {
  date: Date;
  amount: number;
  change: number;
}

export interface ContractAnalytics {
  byProductLine: Record<string, number>;
  byMeasurementModel: Record<MeasurementModel, number>;
  byProfitability: Record<Profitability, number>;
  byCohort: Record<string, number>;
}
