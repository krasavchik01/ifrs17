/**
 * IFRS 17 Report Generator
 * Generates financial statements and disclosures
 */

import { prisma } from '@/lib/prisma';
import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import 'jspdf-autotable';

export type ReportType =
  | 'balance_sheet'
  | 'income_statement'
  | 'csm_roll_forward'
  | 'disclosure'
  | 'analytics';

export interface ReportConfig {
  organizationId: string;
  reportType: ReportType;
  periodStart: Date;
  periodEnd: Date;
  format: 'json' | 'xlsx' | 'pdf';
}

/**
 * Generate CSM Roll-Forward Report
 */
export async function generateCSMRollForward(
  organizationId: string,
  periodStart: Date,
  periodEnd: Date
) {
  const csmCalculations = await prisma.cSMCalculation.findMany({
    where: {
      contract: {
        organizationId,
      },
      reportingDate: {
        gte: periodStart,
        lte: periodEnd,
      },
    },
    include: {
      contract: {
        select: {
          contractNumber: true,
          productLine: true,
          measurementModel: true,
        },
      },
    },
    orderBy: {
      reportingDate: 'asc',
    },
  });

  // Aggregate by reporting period
  const summary = {
    totalOpeningBalance: 0,
    totalNewBusiness: 0,
    totalInterestAccretion: 0,
    totalExperienceAdj: 0,
    totalEstimateChanges: 0,
    totalReleaseForService: 0,
    totalForeignExchange: 0,
    totalOther: 0,
    totalClosingBalance: 0,
  };

  csmCalculations.forEach((calc) => {
    summary.totalOpeningBalance += calc.openingBalance;
    summary.totalNewBusiness += calc.newBusiness;
    summary.totalInterestAccretion += calc.interestAccretion;
    summary.totalExperienceAdj += calc.experienceAdj;
    summary.totalEstimateChanges += calc.estimateChanges;
    summary.totalReleaseForService += calc.releaseForService;
    summary.totalForeignExchange += calc.foreignExchange;
    summary.totalOther += calc.other;
    summary.totalClosingBalance += calc.closingBalance;
  });

  return {
    period: {
      start: periodStart,
      end: periodEnd,
    },
    summary,
    details: csmCalculations,
  };
}

/**
 * Generate Balance Sheet Report
 */
export async function generateBalanceSheet(
  organizationId: string,
  reportingDate: Date
) {
  // Get all active contracts
  const contracts = await prisma.insuranceContract.findMany({
    where: {
      organizationId,
      status: 'active',
    },
    include: {
      csmCalculations: {
        where: {
          reportingDate: {
            lte: reportingDate,
          },
        },
        orderBy: {
          reportingDate: 'desc',
        },
        take: 1,
      },
      riskAdjustments: {
        where: {
          reportingDate: {
            lte: reportingDate,
          },
        },
        orderBy: {
          reportingDate: 'desc',
        },
        take: 1,
      },
    },
  });

  const assets = {
    insuranceAssets: 0,
    reinsuranceAssets: 0,
    totalAssets: 0,
  };

  const liabilities = {
    liabilityForRemainingCoverage: 0,
    liabilityForIncurredClaims: 0,
    totalLiabilities: 0,
  };

  const equity = {
    contractualServiceMargin: 0,
    riskAdjustment: 0,
    totalEquity: 0,
  };

  contracts.forEach((contract) => {
    liabilities.liabilityForRemainingCoverage += contract.lrcValue;
    liabilities.liabilityForIncurredClaims += contract.licValue;

    if (contract.csmCalculations[0]) {
      equity.contractualServiceMargin += contract.csmCalculations[0].closingBalance;
    }

    if (contract.riskAdjustments[0]) {
      equity.riskAdjustment += contract.riskAdjustments[0].totalRiskAdj;
    }
  });

  liabilities.totalLiabilities =
    liabilities.liabilityForRemainingCoverage + liabilities.liabilityForIncurredClaims;

  equity.totalEquity = equity.contractualServiceMargin + equity.riskAdjustment;

  assets.totalAssets = liabilities.totalLiabilities + equity.totalEquity;

  return {
    reportingDate,
    assets,
    liabilities,
    equity,
  };
}

/**
 * Generate Income Statement
 */
export async function generateIncomeStatement(
  organizationId: string,
  periodStart: Date,
  periodEnd: Date
) {
  // Get CSM releases (revenue)
  const csmReleases = await prisma.cSMCalculation.findMany({
    where: {
      contract: {
        organizationId,
      },
      reportingDate: {
        gte: periodStart,
        lte: periodEnd,
      },
    },
    select: {
      releaseForService: true,
      interestAccretion: true,
    },
  });

  // Get claims (expenses)
  const claims = await prisma.claim.findMany({
    where: {
      contract: {
        organizationId,
      },
      settledDate: {
        gte: periodStart,
        lte: periodEnd,
      },
    },
    select: {
      paidAmount: true,
    },
  });

  const revenue = {
    insuranceRevenue: csmReleases.reduce((sum, c) => sum + c.releaseForService, 0),
    investmentIncome: csmReleases.reduce((sum, c) => sum + c.interestAccretion, 0),
    totalRevenue: 0,
  };

  revenue.totalRevenue = revenue.insuranceRevenue + revenue.investmentIncome;

  const expenses = {
    claimsPaid: claims.reduce((sum, c) => sum + c.paidAmount, 0),
    totalExpenses: 0,
  };

  expenses.totalExpenses = expenses.claimsPaid;

  const netIncome = revenue.totalRevenue - expenses.totalExpenses;

  return {
    period: {
      start: periodStart,
      end: periodEnd,
    },
    revenue,
    expenses,
    netIncome,
  };
}

/**
 * Export report to Excel
 */
export function exportToExcel(data: any, reportType: string): Buffer {
  const wb = XLSX.utils.book_new();

  if (reportType === 'csm_roll_forward') {
    // Summary sheet
    const summaryData = [
      ['CSM Roll-Forward Report'],
      ['Period', `${data.period.start} to ${data.period.end}`],
      [],
      ['Component', 'Amount'],
      ['Opening Balance', data.summary.totalOpeningBalance],
      ['New Business', data.summary.totalNewBusiness],
      ['Interest Accretion', data.summary.totalInterestAccretion],
      ['Experience Adjustments', data.summary.totalExperienceAdj],
      ['Estimate Changes', data.summary.totalEstimateChanges],
      ['Release for Service', -data.summary.totalReleaseForService],
      ['Foreign Exchange', data.summary.totalForeignExchange],
      ['Other', data.summary.totalOther],
      ['Closing Balance', data.summary.totalClosingBalance],
    ];

    const summaryWS = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, summaryWS, 'Summary');

    // Details sheet
    const detailsData = data.details.map((d: any) => ({
      'Contract Number': d.contract.contractNumber,
      'Product Line': d.contract.productLine,
      'Reporting Date': d.reportingDate.toISOString().split('T')[0],
      'Opening Balance': d.openingBalance,
      'New Business': d.newBusiness,
      'Interest Accretion': d.interestAccretion,
      'Release for Service': d.releaseForService,
      'Closing Balance': d.closingBalance,
    }));

    const detailsWS = XLSX.utils.json_to_sheet(detailsData);
    XLSX.utils.book_append_sheet(wb, detailsWS, 'Details');
  } else if (reportType === 'balance_sheet') {
    const bsData = [
      ['Balance Sheet'],
      ['As at', data.reportingDate.toISOString().split('T')[0]],
      [],
      ['ASSETS'],
      ['Insurance Assets', data.assets.insuranceAssets],
      ['Reinsurance Assets', data.assets.reinsuranceAssets],
      ['Total Assets', data.assets.totalAssets],
      [],
      ['LIABILITIES'],
      ['Liability for Remaining Coverage', data.liabilities.liabilityForRemainingCoverage],
      ['Liability for Incurred Claims', data.liabilities.liabilityForIncurredClaims],
      ['Total Liabilities', data.liabilities.totalLiabilities],
      [],
      ['EQUITY'],
      ['Contractual Service Margin', data.equity.contractualServiceMargin],
      ['Risk Adjustment', data.equity.riskAdjustment],
      ['Total Equity', data.equity.totalEquity],
    ];

    const ws = XLSX.utils.aoa_to_sheet(bsData);
    XLSX.utils.book_append_sheet(wb, ws, 'Balance Sheet');
  }

  return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
}

/**
 * Export report to PDF
 */
export function exportToPDF(data: any, reportType: string): Buffer {
  const doc = new jsPDF();

  doc.setFontSize(18);
  doc.text('IFRS 17 Report', 14, 20);

  doc.setFontSize(12);

  if (reportType === 'csm_roll_forward') {
    doc.text(`CSM Roll-Forward: ${data.period.start} to ${data.period.end}`, 14, 30);

    const tableData = [
      ['Component', 'Amount'],
      ['Opening Balance', data.summary.totalOpeningBalance.toLocaleString()],
      ['New Business', data.summary.totalNewBusiness.toLocaleString()],
      ['Interest Accretion', data.summary.totalInterestAccretion.toLocaleString()],
      ['Experience Adjustments', data.summary.totalExperienceAdj.toLocaleString()],
      ['Estimate Changes', data.summary.totalEstimateChanges.toLocaleString()],
      ['Release for Service', (-data.summary.totalReleaseForService).toLocaleString()],
      ['Foreign Exchange', data.summary.totalForeignExchange.toLocaleString()],
      ['Other', data.summary.totalOther.toLocaleString()],
      ['Closing Balance', data.summary.totalClosingBalance.toLocaleString()],
    ];

    (doc as any).autoTable({
      startY: 40,
      head: [tableData[0]],
      body: tableData.slice(1),
    });
  }

  return Buffer.from(doc.output('arraybuffer'));
}

/**
 * Main report generation function
 */
export async function generateReport(config: ReportConfig) {
  let reportData: any;

  switch (config.reportType) {
    case 'csm_roll_forward':
      reportData = await generateCSMRollForward(
        config.organizationId,
        config.periodStart,
        config.periodEnd
      );
      break;
    case 'balance_sheet':
      reportData = await generateBalanceSheet(config.organizationId, config.periodEnd);
      break;
    case 'income_statement':
      reportData = await generateIncomeStatement(
        config.organizationId,
        config.periodStart,
        config.periodEnd
      );
      break;
    default:
      throw new Error(`Unsupported report type: ${config.reportType}`);
  }

  // Export based on format
  let fileBuffer: Buffer | null = null;
  let fileUrl: string | null = null;

  if (config.format === 'xlsx') {
    fileBuffer = exportToExcel(reportData, config.reportType);
  } else if (config.format === 'pdf') {
    fileBuffer = exportToPDF(reportData, config.reportType);
  }

  // Save report to database
  const report = await prisma.report.create({
    data: {
      organizationId: config.organizationId,
      reportType: config.reportType,
      reportingPeriod: config.periodEnd,
      periodStart: config.periodStart,
      periodEnd: config.periodEnd,
      format: config.format,
      data: reportData,
      status: 'generated',
      fileUrl,
    },
  });

  return {
    report,
    data: reportData,
    fileBuffer,
  };
}
