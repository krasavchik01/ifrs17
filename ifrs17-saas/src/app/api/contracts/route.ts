import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import { z } from 'zod';

// Validation schema
const createContractSchema = z.object({
  contractNumber: z.string().min(1),
  contractType: z.enum(['life', 'non-life', 'reinsurance']),
  productLine: z.string(),
  measurementModel: z.enum(['GMM', 'PAA', 'VFA']),
  profitability: z.enum(['onerous', 'profitable']),
  inceptionDate: z.string(),
  coverageStartDate: z.string(),
  coverageEndDate: z.string(),
  currency: z.string().default('KZT'),
  nominalAmount: z.number().positive(),
  cohortId: z.string().optional(),
});

// GET /api/contracts - List contracts
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.organizationId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '10');
    const skip = (page - 1) * limit;

    const contracts = await prisma.insuranceContract.findMany({
      where: {
        organizationId: session.user.organizationId,
      },
      include: {
        cohort: true,
        csmCalculations: {
          orderBy: { reportingDate: 'desc' },
          take: 1,
        },
      },
      orderBy: { createdAt: 'desc' },
      skip,
      take: limit,
    });

    const total = await prisma.insuranceContract.count({
      where: {
        organizationId: session.user.organizationId,
      },
    });

    return NextResponse.json({
      contracts,
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
      },
    });
  } catch (error) {
    console.error('Error fetching contracts:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}

// POST /api/contracts - Create contract
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.organizationId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Check permissions
    if (!['admin', 'manager', 'actuary'].includes(session.user.role)) {
      return NextResponse.json({ error: 'Insufficient permissions' }, { status: 403 });
    }

    const body = await request.json();
    const validatedData = createContractSchema.parse(body);

    // Create contract
    const contract = await prisma.insuranceContract.create({
      data: {
        ...validatedData,
        organizationId: session.user.organizationId,
        inceptionDate: new Date(validatedData.inceptionDate),
        coverageStartDate: new Date(validatedData.coverageStartDate),
        coverageEndDate: new Date(validatedData.coverageEndDate),
      },
    });

    // Log audit
    await prisma.auditLog.create({
      data: {
        userId: session.user.id,
        organizationId: session.user.organizationId,
        action: 'CREATE',
        entityType: 'contract',
        entityId: contract.id,
        changes: body,
      },
    });

    return NextResponse.json(contract, { status: 201 });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Validation error', details: error.errors }, { status: 400 });
    }
    console.error('Error creating contract:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
