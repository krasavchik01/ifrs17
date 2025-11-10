/**
 * Fulfilment Cash Flows Calculation Module
 * Enterprise-grade IFRS 17 implementation
 */

import { FulfilmentCashFlows, DiscountRateCurve, CashFlowType } from '@/types/ifrs17';
import { calculatePresentValue, calculateDiscountFactor } from '@/lib/utils';

/**
 * Cash Flow interface
 */
export interface CashFlowProjection {
  period: number; // in years from inception
  date: Date;
  type: CashFlowType;
  nominalAmount: number;
  discountRate?: number;
  presentValue?: number;
}

/**
 * Calculate present value of cash flows
 */
export function calculatePVOfCashFlows(cashFlows: CashFlowProjection[], discountRate: number): number {
  return cashFlows.reduce((total, cf) => {
    const pv = calculatePresentValue(cf.nominalAmount, discountRate, cf.period);
    return total + pv;
  }, 0);
}

/**
 * Calculate present value using discount rate curve
 */
export function calculatePVWithCurve(cashFlows: CashFlowProjection[], curve: DiscountRateCurve): CashFlowProjection[] {
  return cashFlows.map((cf) => {
    const rate = getDiscountRateForPeriod(curve, cf.period);
    const pv = calculatePresentValue(cf.nominalAmount, rate, cf.period);

    return {
      ...cf,
      discountRate: rate,
      presentValue: pv,
    };
  });
}

/**
 * Get discount rate for a specific period from curve
 */
function getDiscountRateForPeriod(curve: DiscountRateCurve, period: number): number {
  // Find the exact period or interpolate
  const exactMatch = curve.rates.find((r) => r.period === period);
  if (exactMatch) return exactMatch.rate;

  // Linear interpolation
  const sortedRates = curve.rates.sort((a, b) => a.period - b.period);

  const lowerBound = sortedRates.filter((r) => r.period < period).pop();
  const upperBound = sortedRates.find((r) => r.period > period);

  if (!lowerBound) return sortedRates[0].rate;
  if (!upperBound) return sortedRates[sortedRates.length - 1].rate;

  // Interpolate
  const weight = (period - lowerBound.period) / (upperBound.period - lowerBound.period);
  return lowerBound.rate + weight * (upperBound.rate - lowerBound.rate);
}

/**
 * Project premium cash flows
 */
export function projectPremiumCashFlows(
  annualPremium: number,
  contractDuration: number,
  frequency: 'annual' | 'semi-annual' | 'quarterly' | 'monthly',
  inceptionDate: Date
): CashFlowProjection[] {
  const flows: CashFlowProjection[] = [];
  const paymentsPerYear = getPaymentsPerYear(frequency);
  const premiumPerPayment = annualPremium / paymentsPerYear;

  const totalPayments = contractDuration * paymentsPerYear;

  for (let i = 0; i < totalPayments; i++) {
    const period = i / paymentsPerYear;
    const date = new Date(inceptionDate);
    date.setMonth(date.getMonth() + i * (12 / paymentsPerYear));

    flows.push({
      period,
      date,
      type: 'premium' as CashFlowType,
      nominalAmount: premiumPerPayment,
    });
  }

  return flows;
}

/**
 * Project claim cash flows
 */
export function projectClaimCashFlows(
  expectedAnnualClaims: number,
  contractDuration: number,
  claimPattern: number[], // percentage distribution by year
  inceptionDate: Date
): CashFlowProjection[] {
  const flows: CashFlowProjection[] = [];

  for (let year = 0; year < contractDuration; year++) {
    const claimAmount = expectedAnnualClaims * (claimPattern[year] || 0);

    if (claimAmount > 0) {
      const date = new Date(inceptionDate);
      date.setFullYear(date.getFullYear() + year);

      flows.push({
        period: year,
        date,
        type: 'claim' as CashFlowType,
        nominalAmount: -claimAmount, // Negative for outflows
      });
    }
  }

  return flows;
}

/**
 * Project expense cash flows
 */
export function projectExpenseCashFlows(
  acquisitionExpenses: number,
  maintenanceExpensesAnnual: number,
  contractDuration: number,
  expenseInflation: number,
  inceptionDate: Date
): CashFlowProjection[] {
  const flows: CashFlowProjection[] = [];

  // Acquisition expenses (upfront)
  if (acquisitionExpenses > 0) {
    flows.push({
      period: 0,
      date: new Date(inceptionDate),
      type: 'expense' as CashFlowType,
      nominalAmount: -acquisitionExpenses,
    });
  }

  // Maintenance expenses (annual, inflated)
  for (let year = 0; year < contractDuration; year++) {
    const inflatedExpense = maintenanceExpensesAnnual * Math.pow(1 + expenseInflation, year);
    const date = new Date(inceptionDate);
    date.setFullYear(date.getFullYear() + year);

    flows.push({
      period: year,
      date,
      type: 'expense' as CashFlowType,
      nominalAmount: -inflatedExpense,
    });
  }

  return flows;
}

/**
 * Calculate Fulfilment Cash Flows
 */
export function calculateFulfilmentCashFlows(
  allCashFlows: CashFlowProjection[],
  discountRate: number,
  riskAdjustment: number
): FulfilmentCashFlows {
  const pvOfCashFlows = calculatePVOfCashFlows(allCashFlows, discountRate);

  return {
    presentValueOfFutureCashFlows: pvOfCashFlows,
    riskAdjustment,
    total: pvOfCashFlows + riskAdjustment,
  };
}

/**
 * Aggregate cash flows by type
 */
export function aggregateCashFlowsByType(cashFlows: CashFlowProjection[]): Record<CashFlowType, number> {
  const aggregated: Record<string, number> = {};

  cashFlows.forEach((cf) => {
    if (!aggregated[cf.type]) {
      aggregated[cf.type] = 0;
    }
    aggregated[cf.type] += cf.nominalAmount;
  });

  return aggregated as Record<CashFlowType, number>;
}

/**
 * Calculate best estimate of cash flows
 */
export function calculateBestEstimate(
  cashFlows: CashFlowProjection[],
  discountRate: number,
  probabilityWeights?: number[]
): number {
  if (!probabilityWeights || probabilityWeights.length === 0) {
    // Simple present value
    return calculatePVOfCashFlows(cashFlows, discountRate);
  }

  // Probability-weighted scenarios
  let weightedPV = 0;

  probabilityWeights.forEach((weight, index) => {
    const scenarioFlows = cashFlows.map((cf) => ({
      ...cf,
      nominalAmount: cf.nominalAmount * weight,
    }));
    weightedPV += calculatePVOfCashFlows(scenarioFlows, discountRate);
  });

  return weightedPV;
}

/**
 * Apply loss component for onerous contracts
 */
export function calculateLossComponent(
  estimatedFulfilmentCashFlows: number,
  coverageUnits: number
): number {
  // Loss component is recognized for onerous contracts
  if (estimatedFulfilmentCashFlows < 0) {
    return Math.abs(estimatedFulfilmentCashFlows);
  }
  return 0;
}

/**
 * Calculate net cash flows (inflows - outflows)
 */
export function calculateNetCashFlows(cashFlows: CashFlowProjection[]): CashFlowProjection[] {
  // Group by period
  const groupedByPeriod = new Map<number, CashFlowProjection[]>();

  cashFlows.forEach((cf) => {
    if (!groupedByPeriod.has(cf.period)) {
      groupedByPeriod.set(cf.period, []);
    }
    groupedByPeriod.get(cf.period)!.push(cf);
  });

  // Calculate net for each period
  const netFlows: CashFlowProjection[] = [];

  groupedByPeriod.forEach((flows, period) => {
    const netAmount = flows.reduce((sum, cf) => sum + cf.nominalAmount, 0);
    netFlows.push({
      period,
      date: flows[0].date,
      type: 'premium' as CashFlowType, // Mixed type
      nominalAmount: netAmount,
    });
  });

  return netFlows.sort((a, b) => a.period - b.period);
}

/**
 * Adjust cash flows for reinsurance
 */
export function adjustForReinsurance(
  grossCashFlows: CashFlowProjection[],
  reinsuranceCessionRate: number,
  reinsurancePremiumRate: number
): CashFlowProjection[] {
  return grossCashFlows.map((cf) => {
    let adjustedAmount = cf.nominalAmount;

    if (cf.type === 'claim') {
      // Reinsurer pays portion of claims
      adjustedAmount = cf.nominalAmount * (1 - reinsuranceCessionRate);
    } else if (cf.type === 'premium') {
      // Pay reinsurance premium
      const reinsurancePremium = cf.nominalAmount * reinsurancePremiumRate;
      adjustedAmount = cf.nominalAmount - reinsurancePremium;
    }

    return {
      ...cf,
      nominalAmount: adjustedAmount,
    };
  });
}

/**
 * Helper: Get number of payments per year
 */
function getPaymentsPerYear(frequency: 'annual' | 'semi-annual' | 'quarterly' | 'monthly'): number {
  switch (frequency) {
    case 'annual':
      return 1;
    case 'semi-annual':
      return 2;
    case 'quarterly':
      return 4;
    case 'monthly':
      return 12;
    default:
      return 1;
  }
}

/**
 * Calculate duration of cash flows (Macaulay Duration)
 */
export function calculateDuration(cashFlows: CashFlowProjection[], discountRate: number): number {
  let weightedPeriods = 0;
  let totalPV = 0;

  cashFlows.forEach((cf) => {
    const pv = calculatePresentValue(cf.nominalAmount, discountRate, cf.period);
    weightedPeriods += pv * cf.period;
    totalPV += pv;
  });

  return totalPV !== 0 ? weightedPeriods / totalPV : 0;
}

/**
 * Calculate convexity of cash flows
 */
export function calculateConvexity(cashFlows: CashFlowProjection[], discountRate: number): number {
  let weightedPeriodsSquared = 0;
  let totalPV = 0;

  cashFlows.forEach((cf) => {
    const pv = calculatePresentValue(cf.nominalAmount, discountRate, cf.period);
    weightedPeriodsSquared += pv * cf.period * (cf.period + 1);
    totalPV += pv;
  });

  return totalPV !== 0 ? weightedPeriodsSquared / (totalPV * Math.pow(1 + discountRate, 2)) : 0;
}
