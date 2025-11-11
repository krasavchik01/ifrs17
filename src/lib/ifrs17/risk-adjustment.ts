/**
 * Risk Adjustment Calculation Module
 * Enterprise-grade IFRS 17 implementation
 */

import { RiskAdjustmentCalculation } from '@/types/ifrs17';

/**
 * Calculate Risk Adjustment using Confidence Level approach
 * Most common method used in practice
 */
export function calculateRiskAdjustmentConfidenceLevel(
  expectedValue: number,
  standardDeviation: number,
  confidenceLevel: number = 0.75 // 75% is common for IFRS 17
): number {
  // Use normal distribution approximation
  const zScore = getZScoreForConfidenceLevel(confidenceLevel);
  const riskAdjustment = standardDeviation * zScore;

  return Math.max(0, riskAdjustment);
}

/**
 * Get Z-score for given confidence level
 */
function getZScoreForConfidenceLevel(confidenceLevel: number): number {
  // Common confidence levels and their z-scores
  const zScores: Record<number, number> = {
    0.50: 0.0,
    0.60: 0.253,
    0.70: 0.524,
    0.75: 0.674,
    0.80: 0.842,
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
  };

  return zScores[confidenceLevel] || 0.674; // Default to 75%
}

/**
 * Calculate Risk Adjustment using Cost of Capital approach
 */
export function calculateRiskAdjustmentCostOfCapital(
  capitalRequired: number,
  costOfCapitalRate: number,
  duration: number
): number {
  // Risk Adjustment = Capital Required × Cost of Capital Rate × Duration
  return capitalRequired * costOfCapitalRate * duration;
}

/**
 * Calculate Risk Adjustment using Quantile approach
 */
export function calculateRiskAdjustmentQuantile(
  expectedValue: number,
  quantileValue: number,
  quantileLevel: number = 0.75
): number {
  // Risk Adjustment = Quantile Value - Expected Value
  return Math.max(0, quantileValue - expectedValue);
}

/**
 * Calculate comprehensive Risk Adjustment with multiple risk types
 */
export function calculateComprehensiveRiskAdjustment(
  insuranceRiskStdDev: number,
  financialRiskStdDev: number,
  operationalRiskStdDev: number,
  confidenceLevel: number = 0.75,
  correlations?: {
    insuranceFinancial?: number;
    insuranceOperational?: number;
    financialOperational?: number;
  }
): RiskAdjustmentCalculation {
  // Calculate individual risk adjustments
  const insuranceRisk = calculateRiskAdjustmentConfidenceLevel(0, insuranceRiskStdDev, confidenceLevel);
  const financialRisk = calculateRiskAdjustmentConfidenceLevel(0, financialRiskStdDev, confidenceLevel);
  const operationalRisk = calculateRiskAdjustmentConfidenceLevel(0, operationalRiskStdDev, confidenceLevel);

  // Apply correlation if provided
  let totalRisk: number;

  if (correlations) {
    // Use correlation matrix to aggregate risks
    const corrInsuranceFinancial = correlations.insuranceFinancial || 0;
    const corrInsuranceOperational = correlations.insuranceOperational || 0;
    const corrFinancialOperational = correlations.financialOperational || 0;

    totalRisk = Math.sqrt(
      Math.pow(insuranceRisk, 2) +
        Math.pow(financialRisk, 2) +
        Math.pow(operationalRisk, 2) +
        2 * insuranceRisk * financialRisk * corrInsuranceFinancial +
        2 * insuranceRisk * operationalRisk * corrInsuranceOperational +
        2 * financialRisk * operationalRisk * corrFinancialOperational
    );
  } else {
    // Simple aggregation (assuming independence)
    totalRisk = Math.sqrt(
      Math.pow(insuranceRisk, 2) + Math.pow(financialRisk, 2) + Math.pow(operationalRisk, 2)
    );
  }

  return {
    method: 'confidence_level',
    confidenceLevel,
    insuranceRisk,
    financialRisk,
    operationalRisk,
    total: totalRisk,
  };
}

/**
 * Calculate Risk Adjustment release for the period
 */
export function calculateRiskAdjustmentRelease(
  openingRiskAdjustment: number,
  expectedReleaseRate: number
): number {
  return openingRiskAdjustment * expectedReleaseRate;
}

/**
 * Perform Risk Adjustment roll-forward
 */
export function performRiskAdjustmentRollForward(
  openingBalance: number,
  newBusiness: number,
  changesInEstimates: number,
  releaseForService: number,
  experienceAdjustments: number = 0
): {
  openingBalance: number;
  newBusiness: number;
  changes: number;
  releaseForService: number;
  closingBalance: number;
} {
  const closingBalance = openingBalance + newBusiness + changesInEstimates - releaseForService + experienceAdjustments;

  return {
    openingBalance,
    newBusiness,
    changes: changesInEstimates + experienceAdjustments,
    releaseForService,
    closingBalance: Math.max(0, closingBalance),
  };
}

/**
 * Calculate Insurance Risk component
 * Based on claims volatility
 */
export function calculateInsuranceRisk(
  historicalClaims: number[],
  expectedClaims: number
): number {
  if (historicalClaims.length === 0) return 0;

  // Calculate standard deviation of claims
  const mean = historicalClaims.reduce((sum, claim) => sum + claim, 0) / historicalClaims.length;

  const variance =
    historicalClaims.reduce((sum, claim) => sum + Math.pow(claim - mean, 2), 0) / historicalClaims.length;

  const stdDev = Math.sqrt(variance);

  return stdDev;
}

/**
 * Calculate Financial Risk component
 * Based on discount rate and market volatility
 */
export function calculateFinancialRisk(
  presentValue: number,
  discountRateVolatility: number,
  duration: number
): number {
  // Financial risk = PV × Duration × Discount Rate Volatility
  return presentValue * duration * discountRateVolatility;
}

/**
 * Calculate Operational Risk component
 * Typically a percentage of expected claims or premiums
 */
export function calculateOperationalRisk(
  expectedClaims: number,
  operationalRiskFactor: number = 0.03 // 3% is common assumption
): number {
  return expectedClaims * operationalRiskFactor;
}

/**
 * Adjust Risk Adjustment for diversification benefits
 */
export function applyDiversificationBenefit(
  totalRiskAdjustment: number,
  diversificationFactor: number = 0.85 // 15% diversification benefit
): number {
  return totalRiskAdjustment * diversificationFactor;
}

/**
 * Calculate Risk Adjustment for reinsurance
 */
export function calculateReinsuranceRiskAdjustment(
  grossRiskAdjustment: number,
  reinsuranceRecoveryRate: number,
  reinsuranceCounterpartyRisk: number
): number {
  const cededRiskAdjustment = grossRiskAdjustment * reinsuranceRecoveryRate;
  const counterpartyAdjustment = cededRiskAdjustment * reinsuranceCounterpartyRisk;

  return cededRiskAdjustment - counterpartyAdjustment;
}

/**
 * Estimate Risk Adjustment for new business
 * Used when historical data is limited
 */
export function estimateRiskAdjustmentForNewBusiness(
  expectedPremiums: number,
  productLine: string,
  benchmarkRiskMargins: Record<string, number>
): number {
  // Use industry benchmark risk margins
  const riskMargin = benchmarkRiskMargins[productLine] || 0.05; // 5% default
  return expectedPremiums * riskMargin;
}
