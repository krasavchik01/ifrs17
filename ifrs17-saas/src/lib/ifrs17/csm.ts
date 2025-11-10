/**
 * CSM (Contractual Service Margin) Calculation Module
 * Enterprise-grade IFRS 17 implementation
 */

import { CSMRollForward, DiscountRateCurve } from '@/types/ifrs17';

/**
 * Calculate CSM at initial recognition
 */
export function calculateInitialCSM(
  presentValueOfCashInflows: number,
  presentValueOfCashOutflows: number,
  riskAdjustment: number
): number {
  const result = presentValueOfCashInflows - presentValueOfCashOutflows - riskAdjustment;

  // If negative (onerous contract), loss is recognized immediately and CSM = 0
  return Math.max(0, result);
}

/**
 * Calculate interest accretion on CSM
 */
export function calculateInterestAccretion(
  openingCSM: number,
  discountRate: number,
  periodInYears: number = 1
): number {
  return openingCSM * discountRate * periodInYears;
}

/**
 * Calculate CSM release for services provided in the period
 */
export function calculateCSMRelease(
  csmBalance: number,
  coverageUnitsProvidedInPeriod: number,
  totalExpectedCoverageUnits: number
): number {
  if (totalExpectedCoverageUnits === 0) return 0;

  const releaseRate = coverageUnitsProvidedInPeriod / totalExpectedCoverageUnits;
  return csmBalance * releaseRate;
}

/**
 * Calculate coverage units for a period
 * Coverage units represent the quantity of coverage provided
 */
export function calculateCoverageUnits(
  sumInsured: number,
  durationInYears: number,
  expectedClaims?: number
): number {
  // Simple approach: sum insured × duration
  // More sophisticated: adjust for expected claims pattern
  const baseUnits = sumInsured * durationInYears;

  if (expectedClaims && expectedClaims > 0) {
    // Weight by expected claims profile
    return baseUnits * (expectedClaims / sumInsured);
  }

  return baseUnits;
}

/**
 * Perform CSM roll-forward for a period
 */
export function performCSMRollForward(
  openingBalance: number,
  newBusinessCSM: number,
  discountRate: number,
  experienceAdjustments: number,
  estimateChanges: number,
  coverageUnitsReleased: number,
  totalCoverageUnits: number,
  foreignExchangeImpact: number = 0,
  otherAdjustments: number = 0
): CSMRollForward {
  // Step 1: Interest accretion
  const interestAccretion = calculateInterestAccretion(openingBalance, discountRate);

  // Step 2: Release for service
  const releaseForService = calculateCSMRelease(
    openingBalance + interestAccretion,
    coverageUnitsReleased,
    totalCoverageUnits
  );

  // Step 3: Calculate closing balance
  const closingBalance =
    openingBalance +
    newBusinessCSM +
    interestAccretion +
    experienceAdjustments +
    estimateChanges -
    releaseForService +
    foreignExchangeImpact +
    otherAdjustments;

  return {
    openingBalance,
    newBusiness: newBusinessCSM,
    interestAccretion,
    experienceAdjustments,
    estimateChanges,
    releaseForService,
    foreignExchange: foreignExchangeImpact,
    other: otherAdjustments,
    closingBalance: Math.max(0, closingBalance), // CSM cannot be negative
  };
}

/**
 * Calculate expected profit margin from CSM
 */
export function calculateProfitMargin(
  totalCSM: number,
  presentValueOfPremiums: number
): number {
  if (presentValueOfPremiums === 0) return 0;
  return (totalCSM / presentValueOfPremiums) * 100;
}

/**
 * Allocate CSM across multiple cohorts
 */
export function allocateCSMByCohort(
  totalCSM: number,
  cohorts: Array<{
    id: string;
    coverageUnits: number;
  }>
): Record<string, number> {
  const totalCoverageUnits = cohorts.reduce((sum, c) => sum + c.coverageUnits, 0);

  if (totalCoverageUnits === 0) return {};

  const allocation: Record<string, number> = {};

  cohorts.forEach((cohort) => {
    allocation[cohort.id] = (cohort.coverageUnits / totalCoverageUnits) * totalCSM;
  });

  return allocation;
}

/**
 * Adjust CSM for changes in discount rates
 */
export function adjustCSMForDiscountRateChanges(
  currentCSM: number,
  oldDiscountRate: number,
  newDiscountRate: number,
  remainingDuration: number
): number {
  // Calculate the impact of discount rate change
  const oldPVFactor = Math.pow(1 + oldDiscountRate, -remainingDuration);
  const newPVFactor = Math.pow(1 + newDiscountRate, -remainingDuration);

  const adjustment = currentCSM * ((newPVFactor - oldPVFactor) / oldPVFactor);

  return adjustment;
}

/**
 * Check if a contract is onerous at initial recognition
 */
export function isOnerousContract(
  estimatedCashInflows: number,
  estimatedCashOutflows: number,
  riskAdjustment: number
): boolean {
  return estimatedCashInflows < estimatedCashOutflows + riskAdjustment;
}

/**
 * Calculate onerous contract loss
 */
export function calculateOnerousLoss(
  estimatedCashInflows: number,
  estimatedCashOutflows: number,
  riskAdjustment: number
): number {
  const loss = estimatedCashOutflows + riskAdjustment - estimatedCashInflows;
  return Math.max(0, loss);
}
