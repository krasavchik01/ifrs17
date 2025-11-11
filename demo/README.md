# Actuary Cloud KZ - Интерактивное Демо

Полнофункциональная демо-среда "полного погружения" для enterprise IFRS 17 платформы.

## 🚀 Быстрый старт

### Локальное тестирование

1. Откройте `tour.html` в браузере для выбора режима демонстрации
2. Или откройте `index.html?tour=guided` для прямого запуска guided tour
3. Или откройте `index.html` для свободного исследования

### Режимы работы

**🎯 Интерактивный тур (Рекомендуется)**
- 11-шаговая демонстрация полного workflow
- Автоматическая навигация с подсказками
- Длительность: ~5 минут
- URL: `tour.html` → выбрать "Интерактивный тур"

**🚀 Свободный режим (Для экспертов)**
- Полная свобода действий
- Все 51,520 договоров доступны
- Drill-down в любые данные
- URL: `tour.html` → выбрать "Свободный режим"

## 📊 Что включено

### Разделы приложения
- **🏠 Командный центр** - Dashboard с живыми KPI
- **📊 Управление данными** - Синхронизация из 1С
- **📑 Реестр договоров** - 51,520 записей с полным drill-down
- **🧮 Расчеты IFRS 17** - Real-time calculation engine
- **📈 Отчетность** - Генерация PDF/Excel отчетов
- **🗂️ Аудит** - Audit trail (disabled in demo)
- **👤 Настройки** - User management (disabled in demo)

### Технические возможности
- Генерация 51,520 моковых договоров
- Пагинация, поиск, фильтрация
- Интерактивные графики и KPI
- Анимированные progress bars
- Terminal-style logs
- Модальные окна с детализацией

## 🎨 Дизайн

- **Цветовая схема**: Professional dark theme (#0f172a)
- **Акцентный цвет**: #0066cc (Actuary Cloud Blue)
- **Шрифт**: Segoe UI / system fonts
- **Адаптивность**: Desktop-first (1280px+)

## 🔗 Интеграция с основным сайтом

Основной сайт (`../index.html`) имеет кнопки "Запросить Демо", которые:
1. Открывают модальное окно с формой
2. Собирают данные клиента (имя, компания, email, телефон)
3. Сохраняют в localStorage
4. Редиректят на `demo/tour.html`

## 📁 Структура файлов

```
demo/
├── index.html      # Основное демо-приложение (2000+ строк)
├── tour.html       # Landing page выбора режима
└── README.md       # Этот файл
```

## 🛠️ Технологии

- Pure HTML5/CSS3/JavaScript (no dependencies)
- CSS Grid & Flexbox
- Modern ES6+ JavaScript
- LocalStorage API
- CSS Animations

## 🎯 Ключевые особенности

### WOW-моменты
1. **Реестр договоров** - Клиент видит 51,520 реальных записей и может drill-down в любую
2. **Real-time расчеты** - Terminal logs показывают мощь движка (8.2 сек на 51,520 договоров)
3. **Профессиональный интерфейс** - Enterprise-grade UI с sidebar, header, модалями

### Guided Tour сценарий
1. Command Center overview
2. Period closure reminder
3. Navigate to Data Management
4. Sync from 1C (with animated progress)
5. View Contract Registry
6. Drill-down into contract details
7. Navigate to Calculations
8. Execute IFRS 17 calculation
9. Navigate to Reports
10. Generate report for regulator
11. Completion message

## 🚢 Деплой

Для размещения на GitHub Pages или любом статическом хостинге:
1. Все файлы самодостаточны (no build step)
2. Просто загрузите папку `demo/` на хостинг
3. Убедитесь, что основной сайт корректно ссылается на `demo/tour.html`

## 📞 Контакты

Для вопросов по демо-приложению обращайтесь к разработчикам Actuary Cloud KZ.

---

**Цель демо**: Клиент должен подумать "Как быстро мы можем это внедрить?", а не "Сколько это стоит?"
