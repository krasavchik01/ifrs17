import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  TrendingUp,
  FileText,
  Shield,
  DollarSign,
  BarChart3,
  AlertCircle,
} from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

async function getDashboardData(organizationId: string) {
  // Get total contracts
  const totalContracts = await prisma.insuranceContract.count({
    where: { organizationId },
  });

  // Get active contracts
  const activeContracts = await prisma.insuranceContract.count({
    where: { organizationId, status: 'active' },
  });

  // Get total CSM
  const latestCSM = await prisma.cSMCalculation.findMany({
    where: {
      contract: {
        organizationId,
      },
    },
    orderBy: {
      reportingDate: 'desc',
    },
    distinct: ['contractId'],
  });

  const totalCSM = latestCSM.reduce((sum, csm) => sum + csm.closingBalance, 0);

  // Get total liabilities
  const contracts = await prisma.insuranceContract.findMany({
    where: { organizationId },
    select: { lcValue: true, lrcValue: true, licValue: true },
  });

  const totalLiabilities = contracts.reduce(
    (sum, c) => sum + c.lcValue + c.lrcValue + c.licValue,
    0
  );

  // Get contracts by product line
  const contractsByProduct = await prisma.insuranceContract.groupBy({
    by: ['productLine'],
    where: { organizationId },
    _count: true,
  });

  // Get recent contracts
  const recentContracts = await prisma.insuranceContract.findMany({
    where: { organizationId },
    orderBy: { createdAt: 'desc' },
    take: 5,
    include: {
      cohort: true,
    },
  });

  // Get onerous contracts count
  const onerousContracts = await prisma.insuranceContract.count({
    where: { organizationId, profitability: 'onerous' },
  });

  return {
    totalContracts,
    activeContracts,
    totalCSM,
    totalLiabilities,
    contractsByProduct,
    recentContracts,
    onerousContracts,
  };
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  if (!session) {
    redirect('/auth/signin');
  }

  const data = await getDashboardData(session.user.organizationId);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Панель управления IFRS 17
              </h1>
              <p className="text-gray-500 mt-1">
                {session.user.organization.name}
              </p>
            </div>
            <div className="flex gap-4">
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  session.user.organization.subscriptionStatus === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                {session.user.organization.subscriptionPlan.toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Contracts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Всего контрактов
              </CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.totalContracts}</div>
              <p className="text-xs text-muted-foreground">
                {data.activeContracts} активных
              </p>
            </CardContent>
          </Card>

          {/* Total CSM */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Общий CSM
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(data.totalCSM)}
              </div>
              <p className="text-xs text-muted-foreground">
                Маржа по контрактам
              </p>
            </CardContent>
          </Card>

          {/* Total Liabilities */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Обязательства
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatCurrency(data.totalLiabilities)}
              </div>
              <p className="text-xs text-muted-foreground">
                Совокупные обязательства
              </p>
            </CardContent>
          </Card>

          {/* Onerous Contracts */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Убыточные контракты
              </CardTitle>
              <AlertCircle className="h-4 w-4 text-red-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {data.onerousContracts}
              </div>
              <p className="text-xs text-muted-foreground">
                Требуют внимания
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Charts and Tables Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Contracts by Product Line */}
          <Card>
            <CardHeader>
              <CardTitle>Контракты по линиям продуктов</CardTitle>
              <CardDescription>
                Распределение по видам страхования
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.contractsByProduct.map((item) => (
                  <div key={item.productLine} className="flex items-center">
                    <div className="w-32 font-medium">{item.productLine}</div>
                    <div className="flex-1 mx-4">
                      <div className="bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{
                            width: `${
                              (item._count / data.totalContracts) * 100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                    <div className="w-12 text-right text-sm text-gray-600">
                      {item._count}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Последние контракты</CardTitle>
              <CardDescription>
                Недавно добавленные в систему
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {data.recentContracts.map((contract) => (
                  <div
                    key={contract.id}
                    className="flex items-center justify-between border-b pb-3 last:border-0"
                  >
                    <div>
                      <div className="font-medium">{contract.contractNumber}</div>
                      <div className="text-sm text-gray-500">
                        {contract.productLine}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(contract.nominalAmount)}
                      </div>
                      <div
                        className={`text-xs px-2 py-1 rounded ${
                          contract.profitability === 'profitable'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {contract.profitability === 'profitable'
                          ? 'Прибыльный'
                          : 'Убыточный'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Быстрые действия</CardTitle>
            <CardDescription>
              Часто используемые операции
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <a
                href="/contracts/new"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition"
              >
                <FileText className="h-8 w-8 text-blue-600" />
                <div>
                  <div className="font-medium">Новый контракт</div>
                  <div className="text-sm text-gray-500">
                    Добавить страховой контракт
                  </div>
                </div>
              </a>

              <a
                href="/csm/calculate"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition"
              >
                <TrendingUp className="h-8 w-8 text-green-600" />
                <div>
                  <div className="font-medium">Расчет CSM</div>
                  <div className="text-sm text-gray-500">
                    Выполнить расчеты маржи
                  </div>
                </div>
              </a>

              <a
                href="/reports"
                className="flex items-center gap-3 p-4 border rounded-lg hover:bg-gray-50 transition"
              >
                <BarChart3 className="h-8 w-8 text-purple-600" />
                <div>
                  <div className="font-medium">Отчеты</div>
                  <div className="text-sm text-gray-500">
                    Генерировать отчетность
                  </div>
                </div>
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
