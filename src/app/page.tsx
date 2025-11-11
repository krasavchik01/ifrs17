import Link from "next/link";
import {
  Shield,
  TrendingUp,
  FileText,
  CheckCircle,
  BarChart3,
  Lock,
  Zap,
  Globe
} from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Shield className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              IFRS 17 Pro
            </span>
          </div>
          <nav className="hidden md:flex space-x-6">
            <a href="#features" className="hover:text-blue-600 transition">Возможности</a>
            <a href="#pricing" className="hover:text-blue-600 transition">Тарифы</a>
            <a href="#contact" className="hover:text-blue-600 transition">Контакты</a>
          </nav>
          <div className="flex gap-4">
            <Link
              href="/auth/signin"
              className="px-4 py-2 text-blue-600 hover:text-blue-700 transition"
            >
              Вход
            </Link>
            <Link
              href="/auth/signup"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-lg hover:shadow-xl"
            >
              Начать
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-block px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold mb-6">
            🇰🇿 Для страхового рынка Казахстана
          </div>
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Автоматизация IFRS 17
            <br />
            Уровня Большой Четверки
          </h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            Профессиональная SaaS-платформа для полной автоматизации расчетов,
            отчетности и управления рисками по стандарту IFRS 17
          </p>
          <div className="flex justify-center gap-4">
            <Link
              href="/auth/signup"
              className="px-8 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition shadow-xl hover:shadow-2xl text-lg font-semibold"
            >
              Попробовать бесплатно
            </Link>
            <Link
              href="#demo"
              className="px-8 py-4 border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition text-lg font-semibold"
            >
              Смотреть демо
            </Link>
          </div>

          {/* Trust Badges */}
          <div className="mt-12 flex flex-wrap justify-center gap-8 items-center text-gray-500">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span>Полное соответствие IFRS 17</span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="h-5 w-5 text-green-600" />
              <span>Безопасность данных</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-green-600" />
              <span>Облачная платформа</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="bg-white py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Все для IFRS 17 в одном месте</h2>
            <p className="text-xl text-gray-600">Комплексное решение для страховых компаний</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-blue-50 to-white">
              <div className="bg-blue-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <FileText className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Управление контрактами</h3>
              <p className="text-gray-600">
                Полный жизненный цикл страховых контрактов с автоматической группировкой и учетом
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-indigo-50 to-white">
              <div className="bg-indigo-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <TrendingUp className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Расчет CSM</h3>
              <p className="text-gray-600">
                Автоматический расчет Contractual Service Margin с учетом всех компонентов
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-purple-50 to-white">
              <div className="bg-purple-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Risk Adjustment</h3>
              <p className="text-gray-600">
                Профессиональная оценка рисков с применением актуарных методов
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-green-50 to-white">
              <div className="bg-green-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <BarChart3 className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Отчетность IFRS 17</h3>
              <p className="text-gray-600">
                Автоматическая генерация всех необходимых отчетов и раскрытий
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-orange-50 to-white">
              <div className="bg-orange-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <Zap className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Аналитика в реальном времени</h3>
              <p className="text-gray-600">
                Интерактивные дашборды с ключевыми метриками и KPI
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 border rounded-xl hover:shadow-lg transition bg-gradient-to-br from-red-50 to-white">
              <div className="bg-red-600 w-12 h-12 rounded-lg flex items-center justify-center mb-4">
                <Lock className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-xl font-bold mb-2">Аудит и Compliance</h3>
              <p className="text-gray-600">
                Полный аудит-трейл всех операций для соответствия регуляторным требованиям
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Прозрачные тарифы</h2>
            <p className="text-xl text-gray-600">Выберите план, который подходит вашей компании</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Starter */}
            <div className="p-8 border-2 rounded-xl hover:shadow-xl transition bg-white">
              <h3 className="text-2xl font-bold mb-2">Starter</h3>
              <div className="text-4xl font-bold mb-4">$499<span className="text-lg text-gray-500">/мес</span></div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>До 1,000 контрактов</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Базовые расчеты IFRS 17</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Стандартная отчетность</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Email поддержка</span>
                </li>
              </ul>
              <Link
                href="/auth/signup?plan=starter"
                className="block w-full py-3 text-center border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition font-semibold"
              >
                Начать
              </Link>
            </div>

            {/* Professional */}
            <div className="p-8 border-4 border-blue-600 rounded-xl hover:shadow-2xl transition bg-white relative">
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                Популярный
              </div>
              <h3 className="text-2xl font-bold mb-2">Professional</h3>
              <div className="text-4xl font-bold mb-4">$1,499<span className="text-lg text-gray-500">/мес</span></div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>До 10,000 контрактов</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Все расчеты IFRS 17</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Расширенная аналитика</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>API интеграция</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Приоритетная поддержка</span>
                </li>
              </ul>
              <Link
                href="/auth/signup?plan=professional"
                className="block w-full py-3 text-center bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-semibold shadow-lg"
              >
                Начать
              </Link>
            </div>

            {/* Enterprise */}
            <div className="p-8 border-2 rounded-xl hover:shadow-xl transition bg-white">
              <h3 className="text-2xl font-bold mb-2">Enterprise</h3>
              <div className="text-4xl font-bold mb-4">Custom</div>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Неограниченные контракты</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Кастомизация под требования</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Dedicated infrastructure</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>SLA 99.9%</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <span>Персональный менеджер</span>
                </li>
              </ul>
              <Link
                href="#contact"
                className="block w-full py-3 text-center border-2 border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition font-semibold"
              >
                Связаться
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold mb-4">Готовы начать?</h2>
          <p className="text-xl mb-8 opacity-90">
            Присоединяйтесь к ведущим страховым компаниям Казахстана
          </p>
          <Link
            href="/auth/signup"
            className="inline-block px-8 py-4 bg-white text-blue-600 rounded-lg hover:bg-gray-100 transition text-lg font-semibold shadow-xl"
          >
            Начать бесплатный период
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <Shield className="h-6 w-6" />
                <span className="text-xl font-bold">IFRS 17 Pro</span>
              </div>
              <p className="text-gray-400">
                Профессиональная автоматизация IFRS 17 для страхового рынка Казахстана
              </p>
            </div>
            <div>
              <h4 className="font-bold mb-4">Продукт</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#features" className="hover:text-white transition">Возможности</a></li>
                <li><a href="#pricing" className="hover:text-white transition">Тарифы</a></li>
                <li><a href="#demo" className="hover:text-white transition">Демо</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Компания</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#about" className="hover:text-white transition">О нас</a></li>
                <li><a href="#contact" className="hover:text-white transition">Контакты</a></li>
                <li><a href="#blog" className="hover:text-white transition">Блог</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold mb-4">Поддержка</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#docs" className="hover:text-white transition">Документация</a></li>
                <li><a href="#support" className="hover:text-white transition">Поддержка</a></li>
                <li><a href="#privacy" className="hover:text-white transition">Конфиденциальность</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 IFRS 17 Pro. Все права защищены.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
