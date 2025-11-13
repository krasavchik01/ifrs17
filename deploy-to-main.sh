#!/bin/bash

# 🚀 Автоматический деплой в main для GitHub Pages

echo "🚀 Actuary Cloud KZ - Deploy to Main Branch"
echo "=========================================="
echo ""

# Проверяем что мы не на main
CURRENT_BRANCH=$(git branch --show-current)
echo "📍 Текущая ветка: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" = "main" ]; then
    echo "✅ Вы уже на main ветке!"
    echo "   Просто запушьте изменения: git push origin main"
    exit 0
fi

echo ""
echo "🔄 Начинаем деплой..."
echo ""

# Сохраняем имя текущей ветки
FEATURE_BRANCH=$CURRENT_BRANCH

# Проверяем что все изменения закоммичены
if ! git diff-index --quiet HEAD --; then
    echo "❌ У вас есть незакоммиченные изменения!"
    echo "   Сначала закоммитьте их: git add -A && git commit -m 'your message'"
    exit 1
fi

echo "✅ Все изменения закоммичены"
echo ""

# Переключаемся на main
echo "📥 Переключаемся на main..."
git checkout main

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при переключении на main"
    exit 1
fi

echo "✅ На main ветке"
echo ""

# Мержим нашу ветку
echo "🔀 Мержим $FEATURE_BRANCH в main..."
git merge $FEATURE_BRANCH --no-edit

if [ $? -ne 0 ]; then
    echo "❌ Конфликт при мерже! Разрешите конфликты вручную."
    exit 1
fi

echo "✅ Мерж успешен"
echo ""

# Пушим в main
echo "📤 Пушим в origin/main..."
git push origin main

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при push. Попробуйте вручную: git push origin main"
    exit 1
fi

echo ""
echo "🎉 ДЕПЛОЙ УСПЕШЕН!"
echo ""
echo "✅ Ваш сайт будет доступен через 1-2 минуты:"
echo ""
echo "   🌐 https://krasavchik01.github.io/ifrs17/"
echo "   🌐 https://krasavchik01.github.io/ifrs17/demo-app.html"
echo ""
echo "📝 Не забудьте настроить GitHub Pages в Settings → Pages!"
echo "   (См. инструкцию в SETUP_GITHUB_PAGES.md)"
echo ""

# Возвращаемся на исходную ветку
echo "🔙 Возвращаемся на $FEATURE_BRANCH..."
git checkout $FEATURE_BRANCH

echo ""
echo "✅ Готово! Ваша ветка: $FEATURE_BRANCH"
