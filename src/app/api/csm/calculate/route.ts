import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import {
  performCSMRollForward,
  calculateInitialCSM,
  calculateCoverageUnits,
} from '@/lib/ifrs17/csm';
import { z } from 'zod';

const calculateCSMSchema = z.object({
  contractId: z.string(),
  reportingDate: z.string(),
  periodStart: z.string(),
  periodEnd: z.string(),
  discountRate: z.number(),
  newBusiness: z.number().optional().default(0),
  experienceAdj: z.number().optional().default(0),
  estimateChanges: z.number().optional().default(0),
  coverageUnitsReleased: z.number().optional().default(0),
  totalCoverageUnits: z.number().positive(),
});

// POST /api/csm/calculate - Calculate CSM for a contract
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.organizationId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Only actuaries and admins can calculate CSM
    if (!['admin', 'actuary'].includes(session.user.role)) {
      return NextResponse.json({ error: 'Insufficient permissions' }, { status: 403 });
    }

    const body = await request.json();
    const validatedData = calculateCSMSchema.parse(body);

    // Verify contract belongs to organization
    const contract = await prisma.insuranceContract.findFirst({
      where: {
        id: validatedData.contractId,
        organizationId: session.user.organizationId,
      },
    });

    if (!contract) {
      return NextResponse.json({ error: 'Contract not found' }, { status: 404 });
    }

    // Get previous CSM calculation
    const previousCSM = await prisma.cSMCalculation.findFirst({
      where: {
        contractId: validatedData.contractId,
      },
      orderBy: {
        reportingDate: 'desc',
      },
    });

    const openingBalance = previousCSM?.closingBalance || 0;

    // Perform CSM roll-forward
    const rollForward = performCSMRollForward(
      openingBalance,
      validatedData.newBusiness,
      validatedData.discountRate,
      validatedData.experienceAdj,
      validatedData.estimateChanges,
      validatedData.coverageUnitsReleased,
      validatedData.totalCoverageUnits
    );

    // Save calculation
    const csmCalculation = await prisma.cSMCalculation.create({
      data: {
        contractId: validatedData.contractId,
        reportingDate: new Date(validatedData.reportingDate),
        periodStart: new Date(validatedData.periodStart),
        periodEnd: new Date(validatedData.periodEnd),
        discountRate: validatedData.discountRate,
        coverageUnits: validatedData.totalCoverageUnits,
        releasedUnits: validatedData.coverageUnitsReleased,
        ...rollForward,
      },
    });

    // Update contract with new CSM value
    await prisma.insuranceContract.update({
      where: { id: validatedData.contractId },
      data: {
        lcValue: rollForward.closingBalance,
      },
    });

    // Log audit
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        organizationId: session.user.organizationId,
        action: 'CALCULATE',
        entityType: 'csm',
        entityId: csmCalculation.id,
        changes: JSON.parse(JSON.stringify(rollForward)),
      },
    });

    return NextResponse.json({
      calculation: csmCalculation,
      rollForward,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Validation error', details: error.errors }, { status: 400 });
    }
    console.error('Error calculating CSM:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
